---
id: Admin-UI-OIDC
title: "Admin UI OIDC"
sidebar_label: "Admin UI OIDC"
---

# Admin UI: OIDC Single Sign-On

> **Enterprise feature.** OIDC Authorization Code login on the `weed admin` UI is part of SeaweedFS Enterprise (`chrislusf/seaweedfs-enterprise`). The OSS `weed admin` binary only supports the local `-adminUser` / `-adminPassword` flow.
>
> For S3-side OIDC (token exchange, STS, role assumption), see [OIDC Integration](./OIDC-Integration.md) — that is a separate, OSS feature and is unrelated to admin-UI login.

This page covers configuring OIDC sign-in for the Admin UI: which keys are required, how to inject the client secret from a Kubernetes Secret, and how role mapping works.

## How it works

1. When OIDC is enabled, the login page renders a **Sign in with OIDC** button next to the local username/password form.
2. Clicking it starts an Authorization Code flow against your IdP (Keycloak, Okta, Azure AD, Auth0, Google, AWS Cognito, …).
3. On callback, the ID token is validated (signature via JWKS, `nonce`, `state`, expiration).
4. Claims are mapped to an admin role (`admin` or `readonly`) using `role_mapping` rules (or the `admin_groups` / `readonly_groups` shortcuts).
5. The admin session lifetime is capped by the ID token's `exp` — when the token expires, the user is signed out.

Local and OIDC auth can be enabled together. Local logins continue to work even if OIDC discovery fails at startup (the OIDC button is hidden and a warning is logged, instead of refusing to start).

## Minimum configuration to make the OIDC button appear

The button is rendered only when an OIDC service is successfully constructed at startup. The minimum set is:

- `admin.oidc.enabled = true`
- `admin.oidc.issuer` (HTTPS, except for `localhost` development)
- `admin.oidc.client_id`
- `admin.oidc.client_secret`
- `admin.oidc.redirect_url` (must match what the IdP has registered)
- Either `admin.oidc.role_mapping.default_role` **or** one or more rules / group entries (so users can be mapped to a role)

If any required key is missing or invalid, the UI starts without the button and a warning is logged. Check the admin container logs at startup — that is where `OIDC: Enabled (issuer: …)` or the rejection reason will appear.

## Configuration reference

Every key below can be set in `security.toml` under `[admin.oidc]` **or** as an environment variable. Environment variables use the `WEED_ADMIN_OIDC_` prefix with dots replaced by underscores; env values override `security.toml`.

| Key in `security.toml` | Environment variable | Type | Notes |
|---|---|---|---|
| `enabled` | `WEED_ADMIN_OIDC_ENABLED` | bool | Master switch. |
| `issuer` | `WEED_ADMIN_OIDC_ISSUER` | string | Base URL; used for OIDC discovery (`/.well-known/openid-configuration`). |
| `client_id` | `WEED_ADMIN_OIDC_CLIENT_ID` | string | OAuth client registered with the IdP. |
| `client_secret` | `WEED_ADMIN_OIDC_CLIENT_SECRET` | string | OAuth client secret. **Inject from a Secret** in Kubernetes — see below. |
| `redirect_url` | `WEED_ADMIN_OIDC_REDIRECT_URL` | string | Must match the IdP-registered URL exactly. Path is `/login/oidc/callback` (or `&lt;urlPrefix&gt;/login/oidc/callback`). |
| `scopes` | `WEED_ADMIN_OIDC_SCOPES` | list / comma-separated | Defaults to `openid,profile,email`. `openid` is always added. |
| `jwks_uri` | `WEED_ADMIN_OIDC_JWKS_URI` | string | Optional override; otherwise read from discovery. |
| `tls_ca_cert` | `WEED_ADMIN_OIDC_TLS_CA_CERT` | string | Absolute path to a CA bundle (PEM) for the IdP's TLS cert. |
| `tls_insecure_skip_verify` | `WEED_ADMIN_OIDC_TLS_INSECURE_SKIP_VERIFY` | bool | Skip IdP TLS verification. **Testing only.** |
| `role_mapping.default_role` | `WEED_ADMIN_OIDC_ROLE_MAPPING_DEFAULT_ROLE` | `admin` \| `readonly` | Role assigned when no rule matches. Leave unset to require an explicit match. |
| `admin_groups` | `WEED_ADMIN_OIDC_ADMIN_GROUPS` | list / comma-separated | Shortcut: each entry becomes a rule `claim=groups, value=&lt;entry&gt;, role=admin`. |
| `readonly_groups` | `WEED_ADMIN_OIDC_READONLY_GROUPS` | list / comma-separated | Shortcut: each entry becomes a rule `claim=groups, value=&lt;entry&gt;, role=readonly`. |
| `**admin.oidc.role_mapping.rules**` | *(not env-settable)* | array of `{claim, value, role}` | Use this for custom claims or non-`groups` matching. |

**Precedence:** CLI flag (where applicable) > env var > `security.toml` > default.

> The `WEED_ADMIN_OIDC_ADMIN_GROUPS` / `WEED_ADMIN_OIDC_READONLY_GROUPS` env vars are convenience shortcuts. If your IdP exposes roles under a claim other than `groups`, or you need regex/wildcard matching, use `**admin.oidc.role_mapping.rules**` in `security.toml` instead.

## Role mapping

After token validation, the user's claims are evaluated against the rules:

```toml
[admin.oidc.role_mapping]
default_role = "readonly"

[[admin.oidc.role_mapping.rules]]
claim = "groups"
value = "seaweedfs-admin"
role  = "admin"

[[admin.oidc.role_mapping.rules]]
claim = "groups"
value = "seaweedfs-readonly"
role  = "readonly"
```

- If any rule produces role `admin`, the user gets `admin`.
- Otherwise, if any rule produces `readonly`, the user gets `readonly`.
- Otherwise, `default_role` is used.
- If no rule matches and no `default_role` is set, the login is rejected.

The convenience env vars expand at startup into equivalent rules with `claim=groups`. So this:

```yaml
env:
  - name: WEED_ADMIN_OIDC_ADMIN_GROUPS
    value: "seaweedfs-admin,platform-admins"
  - name: WEED_ADMIN_OIDC_READONLY_GROUPS
    value: "seaweedfs-readonly"
```

…is equivalent to the `security.toml` block above (plus an extra `platform-admins → admin` rule). They can be combined with explicit rules; both sets are evaluated.

## `security.toml` example

```toml
[admin.oidc]
enabled       = true
issuer        = "https://keycloak.example.com/realms/seaweed"
client_id     = "seaweedfs-admin-ui"
client_secret = "..."
redirect_url  = "https://admin.example.com/login/oidc/callback"
scopes        = ["openid", "profile", "email"]

[admin.oidc.role_mapping]
default_role = "readonly"

[[admin.oidc.role_mapping.rules]]
claim = "groups"
value = "seaweedfs-admin"
role  = "admin"
```

Place it in one of: `.`, `$HOME/.seaweedfs/`, `/usr/local/etc/seaweedfs/`, or `/etc/seaweedfs/`. Generate a starter with `weed scaffold -config=security`.

## Environment-only example (no `security.toml`)

For container deployments, `security.toml` is often inconvenient. Set everything via env:

```bash
WEED_ADMIN_OIDC_ENABLED=true
WEED_ADMIN_OIDC_ISSUER=https://keycloak.example.com/realms/seaweed
WEED_ADMIN_OIDC_CLIENT_ID=seaweedfs-admin-ui
WEED_ADMIN_OIDC_CLIENT_SECRET=...           # inject from a Secret, see Helm below
WEED_ADMIN_OIDC_REDIRECT_URL=https://admin.example.com/login/oidc/callback
WEED_ADMIN_OIDC_SCOPES=openid,profile,email
WEED_ADMIN_OIDC_ROLE_MAPPING_DEFAULT_ROLE=readonly
WEED_ADMIN_OIDC_ADMIN_GROUPS=seaweedfs-admin
WEED_ADMIN_OIDC_READONLY_GROUPS=seaweedfs-readonly
```

## Helm / Kubernetes

The admin Helm template supports both `extraEnvironmentVars` (plain values) and `secretExtraEnvironmentVars` (values from a Kubernetes `Secret`). Put non-sensitive settings in the first, the client secret in the second.

```yaml
# values.yaml
admin:
  enabled: true
  ingress:
    enabled: true
    host: admin-seaweedfs.example.com
    className: openshift-default
    annotations:
      route.openshift.io/termination: edge

  extraEnvironmentVars:
    WEED_ADMIN_OIDC_ENABLED: "true"
    WEED_ADMIN_OIDC_ISSUER: "https://keycloak.example.com/realms/seaweed"
    WEED_ADMIN_OIDC_CLIENT_ID: "seaweedfs-admin-ui"
    WEED_ADMIN_OIDC_REDIRECT_URL: "https://admin-seaweedfs.example.com/login/oidc/callback"
    WEED_ADMIN_OIDC_SCOPES: "openid,profile,email"
    WEED_ADMIN_OIDC_ROLE_MAPPING_DEFAULT_ROLE: "readonly"
    WEED_ADMIN_OIDC_ADMIN_GROUPS: "seaweedfs-admin"
    WEED_ADMIN_OIDC_READONLY_GROUPS: "seaweedfs-readonly"

  secretExtraEnvironmentVars:
    WEED_ADMIN_OIDC_CLIENT_SECRET:
      secretKeyRef:
        name: seaweedfs-admin-oidc
        key: client_secret
```

Create the backing Secret separately (out-of-band, via ExternalSecret, sealed-secrets, etc.):

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: seaweedfs-admin-oidc
type: Opaque
stringData:
  client_secret: "...the OAuth client secret from your IdP..."
```

`secretExtraEnvironmentVars` requires chart version with the admin secret-env support (added 2026-05; see PR in `seaweedfs/seaweedfs`). On older charts you must inline the client secret in `extraEnvironmentVars`, which is not GitOps-friendly.

## Identity provider configuration

In your IdP, register the admin UI as a **confidential** OAuth client with:

- **Client type / Access type:** confidential (must have a client secret)
- **Grant types / Flow:** Authorization Code (with PKCE optional — SeaweedFS uses `state` + `nonce`)
- **Redirect URI:** the exact value you put in `WEED_ADMIN_OIDC_REDIRECT_URL`. If the admin runs behind a reverse proxy under a sub-path, include that path: `https://host/seaweedfs/login/oidc/callback`.
- **Token signing algorithm:** RS256 / RS384 / RS512 / ES256 / ES384 / ES512 are supported.
- **Groups claim:** if you use `admin_groups` / `readonly_groups` or rules with `claim=groups`, configure the IdP to emit a `groups` claim in the ID token. In Keycloak this is a *Group Membership* mapper added to the client scope; verify with the **Evaluate** tab.

### Keycloak quick checklist

1. Realm → Clients → Create:
   - Client ID: `seaweedfs-admin-ui`
   - Client authentication: **On** (this makes it confidential)
   - Authentication flow: **Standard flow** (only)
2. Settings → **Valid redirect URIs**: `https://admin.example.com/login/oidc/callback`
3. Credentials → copy the **Client secret** into the Kubernetes Secret.
4. Client scopes → `&lt;client&gt;-dedicated` → Add mapper → *Group Membership*:
   - Name: `groups`
   - Token Claim Name: `groups`
   - **Full group path: Off** (so the claim values match short names like `seaweedfs-admin`, not `/seaweedfs-admin`)
   - Add to ID token: **On**
5. Realm → Groups → create `seaweedfs-admin`, `seaweedfs-readonly` (or whatever you reference). Assign users.
6. Test with **Evaluate** that the ID token contains `"groups": ["seaweedfs-admin"]`.

The `issuer` value is what Keycloak prints under *Realm settings → OpenID Endpoint Configuration → issuer*. It must exactly match the `iss` claim in issued tokens — including trailing slash semantics.

## OpenShift Routes / reverse proxies

Edge-terminated OpenShift Routes (and other HTTPS-terminating proxies) work fine with admin OIDC, but two things have to line up:

1. **`redirect_url` is what the browser sees.** Use the public HTTPS host of the Route, *not* the in-cluster service. The IdP will redirect the user's browser there.
2. **The admin pod must be able to reach the IdP** to fetch discovery and JWKS. If the IdP is reachable only through the same Route or a TLS-terminating proxy with a private CA, set `WEED_ADMIN_OIDC_TLS_CA_CERT` to a mounted CA bundle (use a `ConfigMap` mounted as a file) — otherwise discovery will fail with x509 errors at startup.

The Route's TLS does not need to be mutual; the OIDC flow is between the user's browser and the IdP. The admin pod only makes server-to-IdP HTTPS calls (discovery, JWKS, code exchange).

`global.enableSecurity: true` (mTLS for SeaweedFS internal gRPC) **does not** interfere with OIDC. Those certificates secure the worker/master/filer/admin gRPC channels — they are unrelated to the HTTPS calls the admin makes to your IdP, and they are unrelated to the user-facing HTTPS terminated by the Route.

## Troubleshooting

The login page renders the OIDC button only when the admin process successfully constructed an OIDC service at startup. If the button is missing:

| Symptom | Where to look | Likely cause |
|---|---|---|
| Startup logs say `OIDC: Enabled (issuer: …)` but no button on `/login` | Admin container logs around the `OIDC: Enabled` line; look for `Warning: disabling admin OIDC authentication: …` | Discovery fetch failed (network / CA), config validation failed, or `enableUI` is false. The startup banner is printed from a direct env-var read; the service is only created if validation and discovery succeed. |
| No `OIDC: Enabled` line at all | Verify `WEED_ADMIN_OIDC_ENABLED=true` is actually present in the pod (`kubectl exec … env | grep WEED_ADMIN_OIDC`) | Env var typo, value other than a bool literal, or values file not applied. |
| `admin.oidc.role_mapping must include at least one rule or default_role` | Admin container logs | Add `WEED_ADMIN_OIDC_ROLE_MAPPING_DEFAULT_ROLE=readonly` or `WEED_ADMIN_OIDC_ADMIN_GROUPS=…`, or define rules in `security.toml`. |
| `admin.oidc.redirect_url must use HTTPS` | Admin container logs | Use HTTPS (or `http://localhost…` for dev). The validator only allows HTTP for localhost. |
| `fetch OIDC discovery document: … x509: certificate signed by unknown authority` | Admin container logs | Set `WEED_ADMIN_OIDC_TLS_CA_CERT` to a path inside the pod that contains the IdP's CA chain in PEM. Use `tls_insecure_skip_verify` only for short-term debugging. |
| Browser redirects to IdP, then back with `error=invalid_redirect_uri` | IdP audit log | The redirect URL registered in the IdP doesn't byte-match what SeaweedFS sends. Trailing slashes, scheme, port, and any `urlPrefix` all matter. |
| Login succeeds at IdP but admin redirects back with `OIDC login failed` | Admin container logs (look for `OIDC callback failed`) | Common causes: clock skew (token `exp` already past), nonce mismatch (session lost between auth start and callback — check that the cookie's `Path` covers `/login/oidc/callback`), or no role rule matches and no `default_role` is set. |
| `OIDC user does not map to an allowed admin role` | Admin container logs | The token's claims don't satisfy any rule and `default_role` is unset. Verify the IdP is emitting the expected claim (e.g. `groups`) and that the value spelling matches. |

To inspect what the IdP is actually emitting, paste a sample ID token into [jwt.io](https://jwt.io) (or `weed jwt decode`) and compare the claim names/values against your rules.

### Quick liveness check

```bash
# 1. Is the env actually in the pod?
kubectl exec deploy/seaweedfs-admin -- env | grep WEED_ADMIN_OIDC | sort

# 2. What does discovery look like from the pod's network namespace?
kubectl exec deploy/seaweedfs-admin -- \
  wget -O- -q "$WEED_ADMIN_OIDC_ISSUER/.well-known/openid-configuration" | head -c 200

# 3. Does the /login page render the OIDC button?
curl -sk https://admin.example.com/login | grep -i oidc
```

If step 2 fails, fix networking/CA before anything else — the admin can't validate tokens without JWKS.

## See also

- [Admin UI](./Admin-UI.md) — the main admin UI reference
- [OIDC Integration](./OIDC-Integration.md) — OIDC on the S3 side (separate, OSS feature)
- `weed scaffold -config=security` — generate an annotated `security.toml`
