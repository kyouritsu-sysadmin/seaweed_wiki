---
id: Server-Side-Encryption
title: "Server Side Encryption"
sidebar_label: "Server Side Encryption"
---

# Server-Side Encryption (SSE)

If you're using SeaweedFS with the S3 API, you can encrypt objects at rest without changing your apps. We support the same server-side encryption (SSE) options as Amazon S3, so you can pick the one that fits how you already manage keys.

## Overview

Use this quick guide to choose the right option:

| Encryption Type | Key Management | Use Case |
|------------------|----------------|----------|
| **SSE-KMS** | External KMS providers | Enterprise key management, audit trails |
| **SSE-C** | Customer-provided | Full customer control, regulatory compliance |
| **SSE-S3** | SeaweedFS-managed | Simple server-managed encryption, bucket defaults |

## Encryption Types

### SSE-KMS (Server-Side Encryption with Key Management Service)
- **Pick this if**: You already use a KMS and want strong audit trails
- **Keys live in**: External providers (AWS KMS, Google Cloud KMS, OpenBao/Vault, Azure Key Vault [experimental])
- **Why teams like it**: Centralized key management, detailed audit logs, per-bucket key assignment, optional Bucket Key optimization
- **Configuration**: Requires KMS provider setup in the S3 config
- **Documentation**: [SSE-KMS Guide](./Server-Side-Encryption-SSE-KMS.md)

### SSE-C (Server-Side Encryption with Customer-Provided Keys)
- **Pick this if**: You want to bring your own keys and keep full control
- **Keys live in**: Your application (sent per request)
- **Why teams like it**: No key storage on the server; maximum control for compliance-heavy environments
- **Configuration**: Keys provided via HTTP headers
- **Documentation**: [SSE-C Guide](./Server-Side-Encryption-SSE-C.md)

### SSE-S3 (Server-Managed Keys)
- **Pick this if**: You want simple, fully managed encryption with minimal setup
- **Keys live in**: SeaweedFS (we handle the key management for you)
- **Why teams like it**: Works with explicit `x-amz-server-side-encryption: AES256` and bucket default encryption; supports multipart uploads and range requests
- **Configuration**: Optional bucket-level default encryption via the standard S3 bucket encryption API
- **Key Encryption Key (KEK)**: The recommended way to provide the KEK is via the `WEED_S3_SSE_KEK` or `WEED_S3_SSE_KEY` environment variable. This avoids storing the master key on the filer. See [KEK Configuration](#kek-configuration) below.

## Quick Start

### SSE-KMS (Enterprise)
```bash
# Ensure $S3_ENDPOINT is set
export S3_ENDPOINT=http://localhost:8333

# Configure KMS in s3 config file (see KMS Providers Integration guide)
# Then upload with KMS encryption
aws --endpoint-url $S3_ENDPOINT s3 cp file.txt s3://mybucket/file.txt \
  --server-side-encryption aws:kms \
  --ssekms-key-id test-key-123
```

### SSE-C (Customer Keys)
```bash
# Generate customer key
openssl rand 32 > customer-key.bin

# Upload with customer-provided key
aws --endpoint-url $S3_ENDPOINT s3 cp file.txt s3://mybucket/file.txt \
  --sse-c AES256 \
  --sse-c-key fileb://customer-key.bin
```

### SSE-S3 (Server-Managed)
```bash
# Explicit SSE-S3 on upload (or configure bucket default encryption)
aws --endpoint-url $S3_ENDPOINT s3 cp file.txt s3://mybucket/file.txt \
  --server-side-encryption AES256
```

## Configuration

### Basic Setup
Configure KMS providers and IAM settings in your S3 config file:

```json
{
  "identities": [
    {
      "name": "admin",
      "credentials": [{"accessKey": "admin", "secretKey": "password"}],
      "actions": ["Admin", "Read", "Write"]
    }
  ],
  "kms": {
    "default_provider": "openbao",
    "providers": {
      "openbao": {
        "type": "openbao",
        "address": "http://localhost:8200",
        "token": "root-token",
        "transit_path": "transit"
      }
    }
  }
}
```

**Note:** The S3 config JSON file contains both KMS encryption settings AND IAM-style access control (user identities, credentials, permissions).

### Start S3 API with Encryption Support
```bash
# Start with KMS config
weed s3 -config=s3_kms_config.json
```

## Features

**Supported Operations:**
- All standard S3 operations (PUT, GET, HEAD, COPY, DELETE)
- Multipart uploads with consistent encryption
- Cross-encryption copy operations
- Object metadata preservation
- Range requests for SSE-C, SSE-KMS, and SSE-S3

**AWS S3 Compatibility:**
- Identical API behavior and headers
- Compatible with all S3 clients and SDKs
- Same error codes and responses

## KEK Configuration

SSE-S3 uses envelope encryption: a Key Encryption Key (KEK) protects per-object Data Encryption Keys (DEKs). If no KEK is configured, SSE-S3 is disabled and requests with `x-amz-server-side-encryption: AES256` will fail.

### Recommended: `security.toml`

Add an `[s3.sse]` section to your `security.toml`. Set exactly one of `kek` or `key`:

```toml
[s3.sse]
# Option A: hex-encoded 256-bit key (same format as the legacy /etc/s3/sse_kek file).
# Generate with: openssl rand -hex 32
kek = ""

# Option B: any secret string. A 256-bit key is derived via HKDF-SHA256.
# Cannot be used while /etc/s3/sse_kek exists on the filer — delete it first.
key = ""
```

These can also be set via environment variables: `WEED_S3_SSE_KEK` and `WEED_S3_SSE_KEY`.

#### `s3.sse.kek` — hex-encoded, drop-in for existing filer KEK

Same format as the filer file `/etc/s3/sse_kek`. If the filer file also exists, the values **must match** or the server refuses to start. This is ideal for migrating an existing deployment.

```toml
[s3.sse]
kek = "a1b2c3d4..."   # 64 hex characters
```

#### `s3.sse.key` — any secret string (HKDF-derived)

A 256-bit key is derived automatically via HKDF-SHA256, so any passphrase works. However, this **cannot be used while `/etc/s3/sse_kek` exists** on the filer — you must delete the filer file first to avoid silently orphaning data encrypted with the old KEK.

```toml
[s3.sse]
key = "my-secret-passphrase"
```

The same secret always produces the same derived key, so all S3 API servers in a cluster must use the same value.

### Legacy: Filer-Stored KEK (backward compatibility only)

If neither config key is set, SeaweedFS falls back to loading the KEK from `/etc/s3/sse_kek` on the filer. This supports existing deployments that already have the file.

If the filer file does not exist either, **SSE-S3 is disabled**.

### Migration from Filer KEK to `security.toml`

1. Read the existing KEK: `weed shell` → `fs.cat /etc/s3/sse_kek`
2. Add it to `security.toml`: `[s3.sse]` → `kek = "&lt;value from step 1&gt;"`
3. Restart all S3 API servers — they will use the config and verify it matches the filer file
4. Once all servers use the config, optionally delete `/etc/s3/sse_kek` from the filer

> **Note:** Use `s3.sse.kek` (not `s3.sse.key`) for migration — it uses the same hex format as the filer file. `s3.sse.key` derives a different key via HKDF and refuses to start while the filer file exists.

## Replication and Backup with SSE

SSE-encrypted objects are handled transparently during replication and backup. The behavior depends on the replication command and destination type:

### filer.sync (Filer-to-Filer)

`weed filer.sync` copies encrypted chunk data and SSE metadata as-is between SeaweedFS clusters. No decryption or re-encryption occurs — the destination filer stores the same ciphertext with the same encryption metadata.

**Requirement:** Both filers must share the same SSE key configuration:
- **SSE-S3:** Same KEK (via `WEED_S3_SSE_KEK`/`WEED_S3_SSE_KEY` or the filer's `/etc/s3/sse_kek`)
- **SSE-KMS:** Same KMS provider with access to the same keys
- **SSE-C:** Works automatically (encryption metadata is copied with the chunk)

If the destination filer uses different SSE keys, the replicated data will be stored but **cannot be decrypted** — reads will fail silently with corrupt data.

### filer.backup / filer.replicate (To External Storage)

`weed filer.backup` and `weed filer.replicate` decrypt SSE-encrypted objects before uploading to external sinks (S3, GCS, Azure, B2, local disk). The destination receives plaintext — the destination storage system's own encryption (e.g., AWS S3 SSE, Azure Storage encryption) should be used if encryption at rest is required.

| SSE Type | Behavior |
|----------|----------|
| **SSE-S3** | Decrypted automatically using the KEK from `security.toml` or the filer |
| **SSE-KMS** | Decrypted automatically if KMS is configured in `security.toml` `[kms]` section |
| **SSE-C** | **Cannot be decrypted** — the customer key is not available in the backup context. These objects are skipped with an error. |

#### SSE-KMS Configuration for Backup

The S3 API server loads KMS configuration from its config file, but `filer.backup` and `filer.replicate` do not load the S3 config. To enable SSE-KMS decryption during backup, add a `[kms]` section to `security.toml` or set the equivalent `WEED_KMS_*` environment variables:

```toml
[kms]
default_provider = "openbao"

[kms.providers.openbao]
type = "openbao"
address = "http://localhost:8200"
token = "root-token"
transit_path = "transit"
```

If no KMS configuration is provided, SSE-KMS encrypted objects will fail to replicate with a "KMS is not configured" error.

## Implementation Notes

- **SSE-KMS**: Supports AWS KMS, Google Cloud KMS, OpenBao/Vault; Azure Key Vault is available behind the `azurekms` build tag (experimental)
- **SSE-C**: Full support with security best practices
- **SSE-S3**: Supported with SeaweedFS-managed keys and bucket default encryption

For hands-on setup guides and examples, see the individual encryption method docs linked above.