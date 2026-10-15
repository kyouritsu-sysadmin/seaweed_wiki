---
id: S3-Configuration
title: "S3 Configuration"
sidebar_label: "S3 Configuration"
---

# S3 Configuration Overview

SeaweedFS S3 gateway has two separate configuration systems for different purposes. Understanding the difference is crucial for proper setup.

## Quick Reference

| Option | Purpose | Use When |
|--------|---------|----------|
| **No Config** | **Zero Configuration** | **Simplest way to use STS features immediately** |
| `-s3.config` | Basic S3 credentials | You need simple user authentication with access keys |
| `-s3.iam.config` | Advanced IAM (STS, OIDC) | You need OIDC integration or role-based access |

## Zero Configuration (Simplest)

`weed s3` enables **Advanced IAM (STS)** by default with secure, auto-generated keys.

**Use this for**: Immediate access to STS features like `AssumeRoleWithWebIdentity` (e.g., for Kubernetes workloads) without any setup.

```bash
# S3 server starts with STS enabled, allowing both anonymous and STS access
weed s3 -filer=localhost:8888
```

### Security & Persistence
-   **Default Effect: Allow**: This defaults to **Open Access** (same as legacy behavior). It does **not** secure your data by default. To enforce access control, you must provide a config file with `"defaultEffect": "Deny"`.
-   **Policy Store: Memory**: By default, policies are stored in memory and **lost on restart**. This ensures "Zero Config" instances are isolated and don't accidentally enforce cluster-wide policies. For persistent policies, use `-s3.iam.config` and configure `"storeType": "filer"`.

## Basic Credentials (`-s3.config`)

**Use this for**: Simple username/password style authentication with access keys.

**Documentation**: [S3 Credentials](./S3-Credentials.md)

```bash
weed s3 -config=/path/to/s3.json -filer=localhost:8888
# OR
weed server -s3 -s3.config=/path/to/s3.json
# OR
weed mini -s3.config=/path/to/s3.json
```

### Configuration Format

```json
{
  "identities": [
    {
      "name": "admin_user",
      "credentials": [
        {
          "accessKey": "your_access_key",
          "secretKey": "your_secret_key"
        }
      ],
      "actions": ["Admin", "Read", "Write", "List", "Tagging"]
    },
    {
      "name": "readonly_user",
      "credentials": [
        {
          "accessKey": "readonly_key",
          "secretKey": "readonly_secret"
        }
      ],
      "actions": ["Read", "List"]
    }
  ]
}
```

### Available Actions

| Action | Description |
|--------|-------------|
| `Admin` | Full access, create/delete buckets |
| `Read` | Read objects |
| `Write` | Write/upload objects |
| `List` | List buckets and objects |
| `Tagging` | Manage object tags |
| `Read:bucket1` | Read access to specific bucket |
| `Write:bucket1` | Write access to specific bucket |

## S3 with Reverse Proxy

When SeaweedFS S3 is behind a reverse proxy (Nginx, HAProxy, AWS ALB, etc.), it needs to know the correct host and protocol to verify S3 signatures.

By default, SeaweedFS automatically detects the following headers from your proxy:
- `X-Forwarded-Host` (e.g. `s3.example.com`)
- `X-Forwarded-Proto` (e.g. `https`)
- `X-Forwarded-Port` (e.g. `443`)

Alternatively, you can explicitly set the public-facing URL using the `externalUrl` flag. This is recommended for complex proxy setups or when you cannot easily modify proxy headers.

```bash
# Explicitly set the external S3 endpoint
weed s3 -s3.externalUrl=https://s3.example.com
```

For detailed configuration examples, see the **[S3 Nginx Proxy](./S3-Nginx-Proxy.md)** page.

---

## Advanced IAM (`-s3.iam.config`)

**Use this for**: Enterprise features like OIDC/Keycloak integration, STS (Security Token Service), IAM policies, and role-based access control.

**Documentation**: [OIDC Integration](./OIDC-Integration.md)

```bash
weed s3 -filer=localhost:8888 -iam.config=/path/to/iam.json
# OR
weed server -s3 -s3.iam.config=/path/to/iam.json
# OR
weed mini -s3.iam.config=/path/to/iam.json
```

### Configuration Format

```json
{
  "sts": {
    "tokenDuration": "1h",       // Optional, default: "1h"
    "maxSessionLength": "12h",   // Optional, default: "12h"
    "issuer": "seaweedfs-sts",   // Optional, default: "seaweedfs-sts"
    "signingKey": "base64-..."   // Optional, auto-fallback if missing
  },
  "providers": [
    {
      "name": "keycloak",
      "type": "oidc",
      "enabled": true,
      "config": {
        "issuer": "https://keycloak.example.com/realms/myrealm",
        "clientId": "seaweedfs-s3",
        "jwksUri": "https://keycloak.example.com/realms/myrealm/protocol/openid-connect/certs"
      }
    }
  ],
  "policies": [
    {
      "name": "ReadOnlyPolicy",
      "document": {
        "Version": "2012-10-17",
        "Statement": [
          { "Effect": "Allow", "Action": ["s3:Get*", "s3:List*"], "Resource": ["*"] }
        ]
      }
    }
  ],
  "roles": [
    {
      "roleName": "ReadOnlyRole",
      "roleArn": "arn:aws:iam::role/ReadOnlyRole",
      "attachedPolicies": ["ReadOnlyPolicy"],
      "trustPolicy": { ... }
    }
  ]
}
```

### Key Components

| Component | Description |
|-----------|-------------|
| `sts` | Security Token Service configuration for temporary credentials |
| `providers` | OIDC identity providers (Keycloak, Okta, Auth0, etc.) |
| `policies` | AWS IAM-style policy documents |
| `roles` | IAM roles with trust policies for role assumption |
 
 ### STS Configuration & Defaults
 
 The `sts` section is optional. If omitted or partially configured, the following defaults apply:
 
 - `tokenDuration`: Defaults to `1h`
 - `maxSessionLength`: Defaults to `12h`
 - `issuer`: Defaults to `seaweedfs-sts`
 
 **Signing Key Fallback Strategy**:
 
 If `signingKey` is not provided in the IAM config, SeaweedFS attempts to find a key in the following order:
 
 1.  **Filer Signing Key**: The `jwt.filer_signing.key` from server configuration (`security.toml` or CLI).
 2.  **SSE-S3 Master Key (KEK)**: If the filer key is missing, it falls back to the cluster-wide SSE-S3 Master Key (stored in filer at `/etc/s3/sse_kek`).
     -   **Auto-Generation**: This key is automatically generated if it does not exist, ensuring a fallback is always available in a healthy cluster.
     -   *Security Note*: A specific `seaweedfs-sts-signing-key` is derived from the master KEK using HKDF-SHA256 to ensure cryptographic isolation between STS and SSE-S3.

> **Important**: The `-s3.iam.config` does NOT support the `identities` field. For basic user credentials, use `-s3.config` instead.

---

## Using Both Together

You can use both configuration options together:

```bash
weed s3 \
  -config=/path/to/s3-credentials.json \
  -iam.config=/path/to/iam-advanced.json \
  -filer=localhost:8888
```

This allows:
- Basic users to authenticate with access keys (from `-s3.config`)
- OIDC users to authenticate with JWT tokens (from `-s3.iam.config`)

---

## Common Mistakes

### Wrong: Using identities in `-s3.iam.config`

```bash
# This will NOT load identities!
weed s3 -iam.config=/path/to/config.json
```

With config file:
```json
{
  "identities": [...]  // This is IGNORED by -iam.config
}
```

### Correct: Using identities in `-s3.config`

```bash
weed s3 -config=/path/to/config.json
```

With config file:
```json
{
  "identities": [...]  // This works with -config
}
```

---

## Configuration Methods Summary

| Method | Priority | Auto-Reload | Best For |
|--------|----------|-------------|----------|
| `-config` file | Highest | SIGHUP | Production static config |
| Filer storage | Medium | Yes | Dynamic management |
| [Admin UI](./Admin-UI.md) | Medium | Yes | Web-based management |
| Environment variables | Fallback | No | Development/testing |
| **Allow All** | Lowest (Fallback) | N/A | Quick start / Dev / Local testing |

See [S3 Credentials](./S3-Credentials.md) for detailed information on each method.

---

## Embedded IAM API

Starting with SeaweedFS 3.x, the IAM API is embedded in the S3 server by default. This allows managing users, access keys, and policies using AWS IAM CLI commands on the same endpoint as S3.

```bash
# Start S3 with embedded IAM (default)
weed s3 -filer=localhost:8888

# IAM and S3 use the same endpoint
aws --endpoint http://localhost:8333 iam create-user --user-name bob
aws --endpoint http://localhost:8333 s3 ls
```

### Disabling Embedded IAM

If you don't need IAM API functionality, you can disable it:

```bash
weed s3 -iam=false -filer=localhost:8888
```

See [Amazon IAM API](./Amazon-IAM-API.md) for detailed IAM usage, or use the [weed shell](./weed-shell.md) commands for interactive management:

```bash
weed shell
> s3.user.create -name alice
> s3.policy -put -name my-policy -file policy.json
> s3.policy.attach -policy my-policy -user alice
> s3.config.show
```

---

## File Permissions for S3 Uploads

By default, objects uploaded via S3 are created with Unix file mode `0660` (`-rw-rw----`). This can be controlled per-object via the `X-Amz-Acl` header, or overridden server-wide with the `-defaultFileMode` flag.

### Per-Object Permissions via S3 ACL

The `X-Amz-Acl` (canned ACL) header is mapped to Unix file permissions:

| Canned ACL | File Mode | Permissions |
|------------|-----------|-------------|
| `private` | `0660` | `-rw-rw----` |
| `public-read` | `0644` | `-rw-r--r--` |
| `public-read-write` | `0666` | `-rw-rw-rw-` |
| `authenticated-read` | `0644` | `-rw-r--r--` |
| `bucket-owner-read` | `0644` | `-rw-r--r--` |
| `bucket-owner-full-control` | `0660` | `-rw-rw----` |

Example with rclone:

```bash
# Upload with world-readable permissions
rclone copy myfile.txt remote:mybucket/ --s3-acl=public-read
```

Example with AWS CLI:

```bash
aws s3 cp myfile.txt s3://mybucket/ --acl public-read --endpoint-url http://localhost:8333
```

### Server-Wide Default File Mode

To change the default for all uploads (when no ACL header is provided):

```bash
# Standalone S3 server
weed s3 -defaultFileMode=0644

# Embedded in weed server
weed server -s3 -s3.defaultFileMode=0644

# Embedded in weed filer
weed filer -s3 -s3.defaultFileMode=0644

# Mini mode
weed mini -s3.defaultFileMode=0644
```

The value is an octal file mode string (e.g. `0644`, `0666`, `0660`).

### Priority Order

1. **Per-object `X-Amz-Acl` header** (if present and recognized)
2. **Server-wide `-defaultFileMode`** (if configured)
3. **Built-in default `0660`**

---

## Related Documentation

- [S3 Credentials](./S3-Credentials.md) - Detailed documentation for basic credentials
- [OIDC Integration](./OIDC-Integration.md) - OIDC/STS integration guide
- [Amazon S3 API](./Amazon-S3-API.md) - S3 API compatibility reference
- [Amazon IAM API](./Amazon-IAM-API.md) - IAM API support (embedded in S3)
- [AWS IAM CLI](./AWS-IAM-CLI.md) - AWS CLI examples for IAM
- [SeaweedFS-Iceberg-Catalog](./SeaweedFS-Iceberg-Catalog.md) - Iceberg REST Catalog documentation
- [Admin UI](./Admin-UI.md) - Web-based credential management

