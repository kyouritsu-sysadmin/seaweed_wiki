---
id: OIDC-Integration
title: "OIDC Integration"
sidebar_label: "OIDC Integration"
---

# OIDC Integration with SeaweedFS S3 Gateway

> **This page covers advanced IAM features** using the `-s3.iam.config` / `-iam.config` option.
>
> For basic S3 credentials with access keys, see [S3 Credentials](./S3-Credentials.md) which uses the `-s3.config` / `-config` option.
>
> For a comparison of both options, see [S3 Configuration](./S3-Configuration.md).

---

This guide shows how to integrate OpenID Connect (OIDC) identity providers with SeaweedFS S3 Gateway using the advanced IAM and STS configuration. It supports:

- Direct OIDC authentication to S3 with Bearer tokens (RSA and ECDSA)
- OIDC to STS role assumption using trust policies and role mapping

## Supported Identity Providers

SeaweedFS works with any OIDC-compliant identity provider, including:

| Provider | Configuration Notes |
|----------|-------------------|
| **Keycloak** | See [Keycloak Example](#keycloak-example) below |
| **Okta** | Use your Okta domain as issuer |
| **Auth0** | Use `https://YOUR_DOMAIN.auth0.com/` as issuer |
| **Azure AD** | Use `https://login.microsoftonline.com/TENANT_ID/v2.0` as issuer |
| **Google** | Use `https://accounts.google.com` as issuer |
| **AWS Cognito** | Use `https://cognito-idp.REGION.amazonaws.com/POOL_ID` as issuer |

## When to Use This

Use `-s3.iam.config` when you need:
- **OIDC/OAuth2 integration** with identity providers
- **STS (Security Token Service)** for temporary credentials
- **AWS IAM-style policies** with fine-grained permissions
- **Role-based access control** with trust policies

> **Important**: The `-s3.iam.config` does NOT support the `identities` field with access keys. If you need simple access key authentication, use `-s3.config` instead. You can use both options together.

## Configuration Structure

The IAM configuration file has these main sections:

```json
{
  "sts": { ... },        // Security Token Service settings
  "providers": [ ... ],  // OIDC identity providers
  "policies": [ ... ],   // IAM policy documents
  "roles": [ ... ]       // IAM roles with trust policies
}
```

### STS Configuration

```json
{
  "sts": {
    "tokenDuration": "1h",
    "maxSessionLength": "12h",
    "issuer": "seaweedfs-sts",
    "signingKey": "base64-encoded-32-byte-key"
  }
}
```

| Field | Description |
|-------|-------------|
| `tokenDuration` | Duration of issued STS tokens |
| `maxSessionLength` | Maximum session length |
| `issuer` | Issuer name for STS tokens |
| `signingKey` | Base64-encoded signing key (32+ bytes) |

### OIDC Provider Configuration

```json
{
  "providers": [
    {
      "name": "my-idp",
      "type": "oidc",
      "enabled": true,
      "config": {
        "issuer": "https://idp.example.com",
        "clientId": "seaweedfs-s3",
        "clientSecret": "optional-for-confidential-clients",
        "jwksUri": "https://idp.example.com/.well-known/jwks.json",
        "userInfoUri": "https://idp.example.com/userinfo",
        "scopes": ["openid", "profile", "email", "groups"],
        "tlsCaCert": "/etc/seaweedfs/certs/ca.pem",
        "tlsInsecureSkipVerify": false,
        "roleMapping": {
          "rules": [
            { "claim": "groups", "value": "admins", "role": "arn:aws:iam::role/S3AdminRole" }
          ],
          "defaultRole": "arn:aws:iam::role/S3ReadOnlyRole"
        }
      }
    }
  ]
}
```

#### Configuration Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `issuer` | Yes | string | OIDC issuer URL (e.g., `https://idp.example.com`) |
| `clientId` | Yes | string | OAuth2 client ID registered with the provider |
| `clientSecret` | No | string | OAuth2 client secret (required for confidential clients) |
| `jwksUri` | No | string | JSON Web Key Set URI. If not specified, defaults to `{issuer}/.well-known/jwks.json` |
| `userInfoUri` | No | string | UserInfo endpoint URI. If not specified, defaults to `{issuer}/userinfo` |
| `scopes` | No | string[] | OAuth2 scopes to request (default: `["openid"]`) |
| `tlsCaCert` | No | string | Path to CA certificate file for verifying the provider's TLS certificate |
| `tlsInsecureSkipVerify` | No | boolean | Skip TLS certificate verification (default: `false`). **Use only for testing** |
| `jwksCacheTTLSeconds` | No | integer | How long to cache JWKS before refresh in seconds (default: `3600`) |
| `roleMapping` | No | object | Configuration for mapping OIDC claims to SeaweedFS roles (see below) |
| `claimsMapping` | No | object | Map OIDC claims to identity attributes |


### Policies

```json
{
  "policies": [
    {
      "name": "S3ReadOnlyPolicy",
      "document": {
        "Version": "2012-10-17",
        "Statement": [
          { "Effect": "Allow", "Action": ["s3:Get*", "s3:List*"], "Resource": ["*"] }
        ]
      }
    }
  ]
}
```

Policies can reference JWT claims dynamically via `&#36;&#123;jwt:&lt;claim-name&gt;&#125;` — any claim on the validated OIDC token is available (e.g. `&#36;&#123;jwt:project_path&#125;` for GitLab CI tokens, `&#36;&#123;jwt:preferred_username&#125;` for Keycloak). See [S3 Policy Variables](./S3-Policy-Variables.md) for the full list of supported variables and a GitLab CI walkthrough.

### Roles

```json
{
  "roles": [
    {
      "roleName": "S3ReadOnlyRole",
      "roleArn": "arn:aws:iam::role/S3ReadOnlyRole",
      "attachedPolicies": ["S3ReadOnlyPolicy"],
      "trustPolicy": {
        "Version": "2012-10-17",
        "Statement": [
          {
            "Effect": "Allow",
            "Principal": { "Federated": "*" },
            "Action": ["sts:AssumeRoleWithWebIdentity"],
            "Condition": {
              "StringEquals": { "oidc:iss": "https://idp.example.com" }
            }
          }
        ]
      }
    }
  ]
}
```

---

## Keycloak Example

### Prerequisites

- A running Keycloak server and a realm (e.g. `seaweedfs`)
- A Keycloak client (e.g. `seaweedfs-s3`) created in that realm
- SeaweedFS with advanced IAM enabled via `-iam.config`

### Step 1: Configure Keycloak

1) **Create a client**
   - Client ID: `seaweedfs-s3`
   - Access Type: public or confidential (confidential requires a client secret)
   - Standard Flow: enabled (for browser login flows)

2) **Add role/group claims to tokens**
   - Add a mapper of type "Group Membership" or "User Realm Role" that puts roles/groups into a top-level claim:
     - Claim name: `groups` (recommended) or `roles`
     - Add to ID token: true
     - Add to Access token: true

3) **Confirm OIDC discovery**
   - Open your realm discovery document and note the issuer and certs endpoints:
     - Issuer: `https://KEYCLOAK/realms/&lt;realm&gt;`
     - JWKS (certs): `https://KEYCLOAK/realms/&lt;realm&gt;/protocol/openid-connect/certs`
     - UserInfo: `https://KEYCLOAK/realms/&lt;realm&gt;/protocol/openid-connect/userinfo`

   Note: For older Keycloak distributions, issuer may include `/auth` in the path.

### Step 2: Create IAM Config

Create `/etc/seaweed/iam.json`:

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
      "name": "keycloak",
      "type": "oidc",
      "enabled": true,
      "config": {
        "issuer": "https://KEYCLOAK/realms/seaweedfs",
        "clientId": "seaweedfs-s3",
        "clientSecret": "<optional-if-confidential>",
        "jwksUri": "https://KEYCLOAK/realms/seaweedfs/protocol/openid-connect/certs",
        "userInfoUri": "https://KEYCLOAK/realms/seaweedfs/protocol/openid-connect/userinfo",
        "scopes": ["openid", "profile", "email", "roles", "groups"],
        "roleMapping": {
          "rules": [
            { "claim": "groups", "value": "admins", "role": "arn:aws:iam::role/S3AdminRole" },
            { "claim": "groups", "value": "developers", "role": "arn:aws:iam::role/S3WriteRole" }
          ],
          "defaultRole": "arn:aws:iam::role/S3ReadOnlyRole"
        }
      }
    }
  ],
  "policies": [
    {
      "name": "S3ReadOnlyPolicy",
      "document": {
        "Version": "2012-10-17",
        "Statement": [
          { "Effect": "Allow", "Action": ["s3:List*", "s3:Get*"], "Resource": ["*"] }
        ]
      }
    },
    {
      "name": "S3WritePolicy",
      "document": {
        "Version": "2012-10-17",
        "Statement": [
          { "Effect": "Allow", "Action": ["s3:List*", "s3:Get*", "s3:Put*", "s3:DeleteObject"], "Resource": ["*"] }
        ]
      }
    },
    {
      "name": "S3AdminPolicy",
      "document": {
        "Version": "2012-10-17",
        "Statement": [
          { "Effect": "Allow", "Action": ["s3:*"], "Resource": ["*"] }
        ]
      }
    }
  ],
  "roles": [
    {
      "roleName": "S3ReadOnlyRole",
      "roleArn": "arn:aws:iam::role/S3ReadOnlyRole",
      "attachedPolicies": ["S3ReadOnlyPolicy"],
      "trustPolicy": {
        "Version": "2012-10-17",
        "Statement": [
          {
            "Effect": "Allow",
            "Principal": { "Federated": "*" },
            "Action": ["sts:AssumeRoleWithWebIdentity"],
            "Condition": {
              "StringEquals": { "oidc:iss": "https://KEYCLOAK/realms/seaweedfs" }
            }
          }
        ]
      }
    },
    {
      "roleName": "S3WriteRole",
      "roleArn": "arn:aws:iam::role/S3WriteRole",
      "attachedPolicies": ["S3WritePolicy"],
      "trustPolicy": {
        "Version": "2012-10-17",
        "Statement": [
          {
            "Effect": "Allow",
            "Principal": { "Federated": "*" },
            "Action": ["sts:AssumeRoleWithWebIdentity"],
            "Condition": {
              "StringEquals": { "oidc:iss": "https://KEYCLOAK/realms/seaweedfs" }
            }
          }
        ]
      }
    },
    {
      "roleName": "S3AdminRole",
      "roleArn": "arn:aws:iam::role/S3AdminRole",
      "attachedPolicies": ["S3AdminPolicy"],
      "trustPolicy": {
        "Version": "2012-10-17",
        "Statement": [
          {
            "Effect": "Allow",
            "Principal": { "Federated": "*" },
            "Action": ["sts:AssumeRoleWithWebIdentity"],
            "Condition": {
              "StringEquals": { "oidc:iss": "https://KEYCLOAK/realms/seaweedfs" }
            }
          }
        ]
      }
    }
  ]
}
```

Notes:
- Set `signingKey` to a strong random secret (base64-encoded 32+ bytes). All S3 gateway instances must share the same STS `issuer` and `signingKey`.
- Explicit `jwksUri` and `userInfoUri` are recommended for Keycloak.
- Ensure your Keycloak mappers populate a top-level `groups` (or `roles`) claim.

### Step 3: Start the S3 Gateway

```bash
weed s3 -filer=filer:8888 -port=8333 -iam.config=/etc/seaweed/iam.json
```

For multi-instance deployments, use the same IAM config on each instance.

---

## Using OIDC Authentication

Once configured, obtain an access token from your identity provider and call S3 with:

```bash
curl -H "Authorization: Bearer $OIDC_TOKEN" http://s3-gateway:8333/
```

Role selection is automatic based on your `roleMapping` configuration. With the Keycloak example:
- Users in `admins` group → `S3AdminRole`
- Users in `developers` group → `S3WriteRole`
- All other users → `S3ReadOnlyRole`

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| **Invalid token** | Verify token `iss` equals the configured provider `issuer` and `aud` or `azp` equals the client ID |
| **JWKS errors** | Ensure `jwksUri` is reachable from the S3 gateway |
| **No roles applied** | Confirm your IdP emits `groups` (or `roles`) at top-level in the token |
| **Trust policy denied** | Ensure `oidc:iss` in the trust policy matches your IdP issuer exactly (it equals the token `iss` claim) |

