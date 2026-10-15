---
id: Cryptography-and-FIPS-Compliance
title: "Cryptography and FIPS Compliance"
sidebar_label: "Cryptography and FIPS Compliance"
---

# Cryptography and FIPS Compliance

This document describes the cryptographic algorithms used in SeaweedFS and provides guidance for FIPS 140-3 compliance.

## Overview

SeaweedFS uses Go's standard library cryptographic packages (`crypto/*`) for all encryption operations. All algorithms used are **FIPS-approved algorithms**. Starting with Go 1.24, native FIPS 140-3 mode can be enabled at runtime.

## Cryptographic Algorithms Used

### Data Encryption (At Rest)

| Feature | Algorithm | Key Size | Notes |
|---------|-----------|----------|-------|
| Filer Data Encryption | AES-256-GCM | 256-bit | Per-file random keys stored in filer metadata |
| SSE-C (Customer Keys) | AES-256-CTR | 256-bit | Customer-provided keys, never stored |
| SSE-S3 (Managed Keys) | AES-256-GCM | 256-bit | SeaweedFS-managed keys |
| SSE-KMS | AES-256-GCM | 256-bit | External KMS-managed data encryption keys |

### Authentication & Signatures

| Feature | Algorithm | Notes |
|---------|-----------|-------|
| S3 Signature V4 | HMAC-SHA256 | AWS-compatible request signing |
| S3 Signature V2 | HMAC-SHA1 | Legacy AWS signature support |
| JWT Tokens | HMAC-SHA256 | For volume server and filer access control |
| OIDC Tokens | RSA, ECDSA | For OIDC identity provider integration |
| SSE-C Key Validation | MD5 | For key integrity verification (AWS S3 compatible) |

### Transport Encryption (In Transit)

| Feature | Protocol | Configuration |
|---------|----------|---------------|
| gRPC (Control Plane) | TLS 1.2/1.3 | mTLS with configurable cipher suites |
| HTTP (Data Plane) | HTTPS (TLS 1.2/1.3) | Certificate-based with configurable versions |

## FIPS 140-3 Compliance

### Algorithm Compliance

All cryptographic algorithms used by SeaweedFS are **FIPS-approved**:

| SeaweedFS Feature | Algorithm | FIPS 140-3 Status |
|-------------------|-----------|-------------------|
| Data Encryption | AES-256-GCM | ✅ Approved |
| SSE-C Encryption | AES-256-CTR | ✅ Approved |
| S3 Signatures | HMAC-SHA256 | ✅ Approved |
| Hashing | SHA-256 | ✅ Approved |
| OIDC Validation | RSA, ECDSA | ✅ Approved |
| Transport | TLS 1.2/1.3 | ✅ Approved |
| Legacy S3 Signatures | HMAC-SHA1 | ⚠️ Approved (use V4 preferred) |
| SSE-C Key Validation | MD5 | ⚠️ Used for AWS S3 compatibility only |

### FIPS 140-3 Mode

**FIPS 140-3 mode is enabled by default** in Docker containers. SeaweedFS requires Go 1.24+, which has native FIPS 140-3 support.

```bash
# FIPS is enabled by default in Docker
docker run chrislusf/seaweedfs server ...

# To disable FIPS mode
docker run -e GODEBUG=fips140=off chrislusf/seaweedfs server ...

# For non-Docker: enable FIPS mode
GODEBUG=fips140=on ./weed server ...

# Strict FIPS mode (non-approved functions will error/panic)
GODEBUG=fips140=only ./weed server ...
```

You can verify FIPS mode is enabled programmatically:

```go
import "crypto/fips140"

if fips140.Enabled() {
    fmt.Println("FIPS 140-3 mode is enabled")
}
```

## Recommended Configuration for FIPS Environments

1. **Enable FIPS mode** at runtime:
   ```bash
   GODEBUG=fips140=on ./weed server ...
   ```

2. **Use S3 Signature V4** (not V2) to avoid SHA1:
   - All modern S3 clients use V4 by default

3. **Enable TLS 1.2 or higher** with FIPS-approved cipher suites:
   ```toml
   # In security.toml
   [tls]
   min_version = "TLS 1.2"
   cipher_suites = "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384,TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256"
   ```

4. **Use SSE-KMS or SSE-S3** for encryption:
   - Both use AES-256-GCM which is FIPS approved
   - SSE-C also uses FIPS-approved algorithms but relies on MD5 for key validation (AWS S3 compatibility requirement)

## Cryptographic Implementation Details

### Random Number Generation

SeaweedFS uses `crypto/rand` for all cryptographic random number generation:

- Cipher key generation
- Nonce/IV generation  
- Upload ID generation
- Version ID generation

### Key Storage

| Key Type | Storage Location | Protection |
|----------|-----------------|------------|
| Filer encryption keys | Filer metadata store | Per-file, randomly generated |
| SSE-C keys | Never stored | Customer-provided per request |
| SSE-S3 keys | In-memory or KMS | Managed by SeaweedFS or external KMS |
| SSE-KMS keys | External KMS | AWS KMS, Google Cloud KMS, OpenBao/Vault, Azure Key Vault |
| TLS certificates | File system | User-managed |
| JWT signing keys | security.toml | User-configured |

## Security Best Practices

1. **Enable FIPS mode** with `GODEBUG=fips140=on` in regulated environments
2. **Enable mTLS** for all gRPC communications
3. **Use HTTPS** for all HTTP endpoints in production
4. **Configure JWT signing** for volume server access control
5. **Use external KMS** (SSE-KMS) for enterprise key management with audit trails
6. **Regularly rotate** TLS certificates and JWT signing keys
7. **Restrict cipher suites** to FIPS-approved algorithms

## Related Documentation

- [Security Overview](./Security-Overview.md)
- [Security Configuration](./Security-Configuration.md)
- [Server-Side Encryption](./Server-Side-Encryption.md)
- [Filer Data Encryption](./Filer-Data-Encryption.md)
