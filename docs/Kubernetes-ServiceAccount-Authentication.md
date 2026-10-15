---
id: Kubernetes-ServiceAccount-Authentication
title: "Kubernetes ServiceAccount Authentication"
sidebar_label: "Kubernetes ServiceAccount Authentication"
---

# Kubernetes ServiceAccount Authentication (IRSA-style)

> **This page covers advanced IAM features** using the `-s3.iam.config` / `-iam.config` option.
>
> It builds on [OIDC Integration](./OIDC-Integration.md) — read that first for the general STS/OIDC model. This page is the Kubernetes-specific recipe.

---

A Kubernetes ServiceAccount (SA) token is just an OIDC JWT. That means SeaweedFS can accept it directly through `AssumeRoleWithWebIdentity` and hand back temporary S3 credentials — the same pattern AWS calls **IRSA** (IAM Roles for Service Accounts), but vendor-neutral.

This works on **any** cluster — managed or on-prem, kind/k3s/kubeadm — because SeaweedFS only needs to reach the cluster's OIDC discovery (JWKS) endpoint to verify token signatures. There is no dependency on EKS or AWS STS.

The result: pods authenticate to the S3 gateway with a short-lived, auto-rotated token instead of a static access key + secret.

## How it works

```
Pod                         kube-apiserver / JWKS            SeaweedFS S3 gateway
 |                                  |                                 |
 | 1. kubelet projects a SA token   |                                 |
 |    (OIDC JWT, audience=X)        |                                 |
 |<---------------------------------|                                 |
 |                                                                    |
 | 2. AssumeRoleWithWebIdentity(RoleArn, WebIdentityToken=JWT)        |
 |------------------------------------------------------------------->|
 |                                                                    | 3. fetch JWKS, verify
 |                                                                    |    signature + iss + aud
 |                                                                    | 4. match role trust policy
 |                                                                    |    (oidc:sub = the SA)
 | 5. temporary {AccessKeyId, SecretAccessKey, SessionToken}          |
 |<-------------------------------------------------------------------|
 |                                                                    |
 | 6. normal S3 calls signed with the temporary credentials           |
 |------------------------------------------------------------------->|
```

SeaweedFS plays **both** the relying party (validating the cluster as an OIDC provider) and the STS service (issuing the temporary credentials). The credentials are stateless JWTs, so any S3 gateway instance can issue and validate them — no shared session store. See [OIDC Integration](./OIDC-Integration.md) for the distributed-deployment notes.

## Prerequisites

- A Kubernetes cluster whose ServiceAccount issuer is a URL with a reachable OIDC discovery / JWKS endpoint (see [Part 1](#part-1-expose-the-clusters-oidc-discovery)).
- SeaweedFS S3 gateway started with advanced IAM enabled (`-iam.config` / `-s3.iam.config`).
- Network path from the S3 gateway to the cluster's JWKS endpoint.

## Part 1: Expose the cluster's OIDC discovery

SeaweedFS verifies the token signature by fetching the cluster's public keys (JWKS). Find your cluster's issuer and JWKS URI:

```bash
kubectl get --raw /.well-known/openid-configuration | jq
# {
#   "issuer": "https://kubernetes.default.svc.cluster.local",
#   "jwks_uri": "https://kubernetes.default.svc.cluster.local/openid/v1/jwks",
#   ...
# }

kubectl get --raw /openid/v1/jwks | jq
```

The `issuer` value is set by the kube-apiserver `--service-account-issuer` flag and is the `iss` claim on every SA token. SeaweedFS's `issuer` config must equal it **exactly**.

Two deployment shapes:

**A. The issuer is a public HTTPS URL.** Many clusters publish the discovery document and JWKS to a public location (an object-store bucket or a static HTTPS endpoint) precisely so external services can validate tokens. If `{issuer}/.well-known/openid-configuration` is reachable from the S3 gateway, SeaweedFS performs discovery automatically and you do **not** need to set `jwksUri`.

**B. The issuer is the in-cluster API server** (e.g. `https://kubernetes.default.svc.cluster.local`). The apiserver serves discovery and JWKS, but the endpoints normally require authentication and the URL is only resolvable inside the cluster. Make them work for SeaweedFS:

1. Allow unauthenticated reads of the discovery + JWKS endpoints (these expose **public keys only**):

   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: ClusterRoleBinding
   metadata:
     name: service-account-issuer-discovery-unauthenticated
   roleRef:
     apiGroup: rbac.authorization.k8s.io
     kind: ClusterRole
     name: system:service-account-issuer-discovery
   subjects:
   - apiGroup: rbac.authorization.k8s.io
     kind: Group
     name: system:unauthenticated
   ```

2. If the S3 gateway runs inside the cluster, point `jwksUri` at the in-cluster service. If it runs outside, expose the JWKS through an ingress / published mirror and set `jwksUri` to that reachable URL.

> If you control the apiserver, the cleanest setup is to give it an externally reachable issuer URL via `--service-account-issuer=https://&lt;public-host&gt;` (and `--service-account-jwks-uri` if the JWKS is served from a different host). Then SeaweedFS discovery just works.

## Part 2: Project a token into the pod

Do **not** use the default token at `/var/run/secrets/kubernetes.io/serviceaccount/token` — its audience targets the API server. Project a separate token with an audience that matches what SeaweedFS expects (its `clientId`). The kubelet rotates this token automatically.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  template:
    spec:
      serviceAccountName: my-app          # subject becomes system:serviceaccount:<ns>:my-app
      containers:
      - name: app
        image: my-app:latest
        env:
        - name: AWS_WEB_IDENTITY_TOKEN_FILE
          value: /var/run/secrets/seaweedfs/token
        - name: AWS_ROLE_ARN
          value: arn:aws:iam::role/K8sAppRole
        volumeMounts:
        - name: seaweedfs-token
          mountPath: /var/run/secrets/seaweedfs
          readOnly: true
      volumes:
      - name: seaweedfs-token
        projected:
          sources:
          - serviceAccountToken:
              path: token
              audience: seaweedfs-s3      # must equal clientId in the SeaweedFS provider config
              expirationSeconds: 3600
```

The token's `sub` claim is `system:serviceaccount:&lt;namespace&gt;:&lt;serviceaccount-name&gt;` — this is what you scope the role's trust policy to.

## Part 3: Configure SeaweedFS

Register the cluster as an OIDC provider and create a role whose trust policy allows that provider's SA to assume it. No `clientSecret` is needed — web-identity validation only checks the signature, issuer, and audience.

`/etc/seaweed/iam.json`:

```json
{
  "sts": {
    "tokenDuration": "1h",
    "maxSessionLength": "12h",
    "issuer": "seaweedfs-sts",
    "signingKey": "c2Vhd2VlZGZzLXNpZ25pbmcta2V5LTMyLWNoYXJzLWxvbmc="
  },
  "providers": [
    {
      "name": "k8s",
      "type": "oidc",
      "enabled": true,
      "config": {
        "issuer": "https://kubernetes.default.svc.cluster.local",
        "clientId": "seaweedfs-s3",
        "jwksUri": "https://kubernetes.default.svc.cluster.local/openid/v1/jwks"
      }
    }
  ],
  "policies": [
    {
      "name": "AppBucketPolicy",
      "document": {
        "Version": "2012-10-17",
        "Statement": [
          {
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"],
            "Resource": ["arn:aws:s3:::app-bucket", "arn:aws:s3:::app-bucket/*"]
          }
        ]
      }
    }
  ],
  "roles": [
    {
      "roleName": "K8sAppRole",
      "roleArn": "arn:aws:iam::role/K8sAppRole",
      "attachedPolicies": ["AppBucketPolicy"],
      "trustPolicy": {
        "Version": "2012-10-17",
        "Statement": [
          {
            "Effect": "Allow",
            "Principal": { "Federated": "k8s" },
            "Action": ["sts:AssumeRoleWithWebIdentity"],
            "Condition": {
              "StringEquals": {
                "oidc:sub": "system:serviceaccount:default:my-app"
              }
            }
          }
        ]
      }
    }
  ]
}
```

Notes:

- `clientId` (`seaweedfs-s3`) must match the projected token `audience`. The `aud` claim on a Kubernetes token is an **array**; SeaweedFS accepts the token if any entry matches `clientId` (or `clientIds` for a list).
- Set `jwksUri` only for case B above; omit it when discovery is reachable.
- The trust policy is scoped to one ServiceAccount via `oidc:sub`. To allow a whole namespace, use `StringLike` with `system:serviceaccount:default:*`. See the [condition key reference](#trust-policy-condition-keys) below.
- `signingKey` must be a strong random base64 value (32+ bytes), identical across all S3 gateway instances.

Start the gateway:

```bash
weed s3 -filer=filer:8888 -port=8333 -iam.config=/etc/seaweed/iam.json
```

## Part 4: Consume the credentials in the pod

The pod has a token file and a role ARN. Three ways to turn that into S3 access:

### Option A — AWS SDK / CLI web-identity provider (recommended)

The standard AWS SDKs already implement the `AssumeRoleWithWebIdentity` credential provider and refresh it automatically. With the env vars from Part 2 set, point the STS calls at SeaweedFS:

```bash
export AWS_ENDPOINT_URL_STS=http://seaweedfs-s3:8333   # SeaweedFS handles STS on the S3 port
export AWS_ENDPOINT_URL=http://seaweedfs-s3:8333       # and the S3 data calls
export AWS_REGION=us-east-1

aws s3 ls s3://app-bucket/ --endpoint-url http://seaweedfs-s3:8333
```

The SDK reads `AWS_ROLE_ARN` + `AWS_WEB_IDENTITY_TOKEN_FILE`, calls SeaweedFS to assume the role, caches the temporary credentials, and re-assumes when they near expiry.

> `AWS_ENDPOINT_URL_STS` is honored by AWS CLI v2 and recent SDKs. Older SDKs may ignore it — in that case set the STS endpoint in code (e.g. a custom `endpoint_url` on the STS client) instead of relying on the env var.

### Option B — call AssumeRoleWithWebIdentity directly

Any HTTP client works. Read the projected token and POST to the gateway:

```bash
TOKEN=$(cat /var/run/secrets/seaweedfs/token)

curl -s "http://seaweedfs-s3:8333/?Action=AssumeRoleWithWebIdentity&Version=2011-06-15&RoleArn=arn:aws:iam::role/K8sAppRole&RoleSessionName=my-app&WebIdentityToken=${TOKEN}"
```

Response (abridged):

```xml
<AssumeRoleWithWebIdentityResponse>
  <AssumeRoleWithWebIdentityResult>
    <Credentials>
      <AccessKeyId>...</AccessKeyId>
      <SecretAccessKey>...</SecretAccessKey>
      <SessionToken>eyJ...</SessionToken>
      <Expiration>2026-01-01T12:00:00Z</Expiration>
    </Credentials>
  </AssumeRoleWithWebIdentityResult>
</AssumeRoleWithWebIdentityResponse>
```

Recognized parameters: `WebIdentityToken` (required), `RoleArn`, `RoleSessionName`, `DurationSeconds`, `Policy` (an inline session policy that further restricts the role). Your client is responsible for re-assuming before `Expiration`.

### Option C — automatic injection across many pods

To avoid editing every Deployment, run the open-source `amazon-eks-pod-identity-webhook` (it works on non-EKS clusters too). It watches for a ServiceAccount annotation and injects the projected token volume and the `AWS_ROLE_ARN` / `AWS_WEB_IDENTITY_TOKEN_FILE` env vars into matching pods:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::role/K8sAppRole
    eks.amazonaws.com/audience: seaweedfs-s3
```

You still override the STS endpoint as in Option A so the SDK targets SeaweedFS rather than the public AWS STS endpoint.

## Trust policy condition keys

During `AssumeRoleWithWebIdentity` the following keys are available to the trust policy (see [S3 Policy Conditions](./S3-Policy-Conditions.md)):

| Key | Value for a Kubernetes token |
|-----|------------------------------|
| `oidc:sub` | `system:serviceaccount:&lt;namespace&gt;:&lt;name&gt;` — the ServiceAccount identity |
| `oidc:iss` | the cluster issuer URL |
| `aws:FederatedProvider` | the provider `name` from config (e.g. `k8s`) when the token issuer matches it, else the issuer URL |
| `aws:userid` | same as `oidc:sub` |
| `oidc:&lt;claim&gt;` | any other top-level claim on the token |

Scope on `oidc:sub` to pin a role to a specific ServiceAccount, or `StringLike` on `system:serviceaccount:&lt;ns&gt;:*` for a whole namespace. Audience is already enforced by the provider `clientId`, so you normally do not condition on it — and note `oidc:aud` is not populated for Kubernetes tokens because their `aud` is an array rather than a string.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| **Invalid issuer** | SeaweedFS `issuer` must exactly equal the token `iss` (`kubectl get --raw /.well-known/openid-configuration`). |
| **JWKS errors / signature verify fails** | The gateway can't reach the JWKS URI. Confirm discovery is reachable, or set `jwksUri` to a URL the gateway can fetch (Part 1, case B). |
| **Audience matches none of the configured client IDs** | The projected token `audience` must equal the provider `clientId` (or be in `clientIds`). |
| **Trust policy denies web identity assumption** | `oidc:sub` in the trust policy must match `system:serviceaccount:&lt;ns&gt;:&lt;sa&gt;` exactly; for a namespace use `StringLike`. |
| **Credentials expire mid-run** | Use the SDK web-identity provider (Option A) which auto-refreshes; if calling STS manually, re-assume before `Expiration`. |
| **SDK still hits real AWS STS** | The STS endpoint override didn't take effect; set `AWS_ENDPOINT_URL_STS` or configure the STS client endpoint in code. |

## See also

- [OIDC Integration](./OIDC-Integration.md) — general OIDC/STS setup and the Keycloak walkthrough
- [S3 Policy Conditions](./S3-Policy-Conditions.md) — full condition-key reference
- [S3 Policy Variables](./S3-Policy-Variables.md) — using claims like `&#36;&#123;oidc:sub&#125;` inside policies
- [S3 Configuration](./S3-Configuration.md) — `-s3.config` vs `-s3.iam.config`
- [Deployment to Kubernetes and Minikube](./Deployment-to-Kubernetes-and-Minikube.md) — running SeaweedFS itself on Kubernetes
