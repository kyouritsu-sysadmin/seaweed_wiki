---
id: Server-Side-Encryption-SSE-C
title: "Server Side Encryption SSE C"
sidebar_label: "Server Side Encryption SSE C"
---

# Server-Side Encryption with Customer-provided Keys (SSE-C)

With SSE-C, you bring your own keys and SeaweedFS does the heavy lifting. Your app sends the key with each request, and we encrypt/decrypt on the server side—without ever storing your key.

## Overview

SSE-C gives you client-side key management with server-side encryption:

- **Client provides**: AES-256 encryption key and MD5 hash
- **SeaweedFS handles**: Encryption/decryption operations transparently  
- **Security**: Keys are never stored on the server

## Required Headers

For all SSE-C operations, include these headers:

```http
X-Amz-Server-Side-Encryption-Customer-Algorithm: AES256
X-Amz-Server-Side-Encryption-Customer-Key: <base64-encoded-256-bit-key>
X-Amz-Server-Side-Encryption-Customer-Key-MD5: <md5-of-key>
```

## HTTP Examples

### Upload Encrypted Object

```bash
# Set endpoint environment variable
export S3_ENDPOINT=http://localhost:8333

# Generate a 256-bit key
KEY=$(openssl rand -base64 32)
KEY_MD5=$(echo -n "$KEY" | base64 -d | md5sum | cut -d' ' -f1)

# Upload encrypted object
curl -X PUT "$S3_ENDPOINT/bucket/encrypted-file.txt" \
  -H "X-Amz-Server-Side-Encryption-Customer-Algorithm: AES256" \
  -H "X-Amz-Server-Side-Encryption-Customer-Key: $KEY" \
  -H "X-Amz-Server-Side-Encryption-Customer-Key-MD5: $KEY_MD5" \
  -H "Content-Type: text/plain" \
  --data "This content will be encrypted"
```

### Download Encrypted Object

```bash
# Download and decrypt object (must use same key)
curl "$S3_ENDPOINT/bucket/encrypted-file.txt" \
  -H "X-Amz-Server-Side-Encryption-Customer-Algorithm: AES256" \
  -H "X-Amz-Server-Side-Encryption-Customer-Key: $KEY" \
  -H "X-Amz-Server-Side-Encryption-Customer-Key-MD5: $KEY_MD5"
```

### Get Object Metadata

```bash
# Get metadata for encrypted object
curl -I "$S3_ENDPOINT/bucket/encrypted-file.txt" \
  -H "X-Amz-Server-Side-Encryption-Customer-Algorithm: AES256" \
  -H "X-Amz-Server-Side-Encryption-Customer-Key: $KEY" \
  -H "X-Amz-Server-Side-Encryption-Customer-Key-MD5: $KEY_MD5"
```

### Copy Operations

```bash
# Copy encrypted object to new location (same key)
curl -X PUT "$S3_ENDPOINT/bucket/copied-file.txt" \
  -H "x-amz-copy-source: /bucket/encrypted-file.txt" \
  -H "X-Amz-Server-Side-Encryption-Customer-Algorithm: AES256" \
  -H "X-Amz-Server-Side-Encryption-Customer-Key: $KEY" \
  -H "X-Amz-Server-Side-Encryption-Customer-Key-MD5: $KEY_MD5" \
  -H "x-amz-copy-source-server-side-encryption-customer-algorithm: AES256" \
  -H "x-amz-copy-source-server-side-encryption-customer-key: $KEY" \
  -H "x-amz-copy-source-server-side-encryption-customer-key-md5: $KEY_MD5"

# Copy encrypted object with different key
NEW_KEY=$(openssl rand -base64 32)
NEW_KEY_MD5=$(echo -n "$NEW_KEY" | base64 -d | md5sum | cut -d' ' -f1)

curl -X PUT "$S3_ENDPOINT/bucket/reencrypted-file.txt" \
  -H "x-amz-copy-source: /bucket/encrypted-file.txt" \
  -H "X-Amz-Server-Side-Encryption-Customer-Algorithm: AES256" \
  -H "X-Amz-Server-Side-Encryption-Customer-Key: $NEW_KEY" \
  -H "X-Amz-Server-Side-Encryption-Customer-Key-MD5: $NEW_KEY_MD5" \
  -H "x-amz-copy-source-server-side-encryption-customer-algorithm: AES256" \
  -H "x-amz-copy-source-server-side-encryption-customer-key: $KEY" \
  -H "x-amz-copy-source-server-side-encryption-customer-key-md5: $KEY_MD5"
```

### AWS CLI Usage

```bash
# Upload with SSE-C
aws --endpoint-url $S3_ENDPOINT s3 cp file.txt s3://mybucket/file.txt \
  --sse-c AES256 \
  --sse-c-key fileb://customer-key.bin

# Download with SSE-C
aws --endpoint-url $S3_ENDPOINT s3 cp s3://mybucket/file.txt downloaded-file.txt \
  --sse-c AES256 \
  --sse-c-key fileb://customer-key.bin

# Copy with SSE-C (same key)
aws --endpoint-url $S3_ENDPOINT s3 cp s3://mybucket/file.txt s3://mybucket/file-copy.txt \
  --sse-c AES256 \
  --sse-c-key fileb://customer-key.bin \
  --sse-c-copy-source AES256 \
  --sse-c-copy-source-key fileb://customer-key.bin
```

## Error Codes

| Error | HTTP Status | Description |
|-------|-------------|-------------|
| `InvalidEncryptionAlgorithmError` | 400 | Algorithm must be "AES256" |
| `InvalidArgument` | 400 | Invalid key format or MD5 mismatch |
| `InvalidRequest` | 400 | Missing SSE-C headers |

## Common Issues

**Wrong algorithm:**
```bash
X-Amz-Server-Side-Encryption-Customer-Algorithm: AES128  # Error!
```

**Invalid key length:**
```bash
X-Amz-Server-Side-Encryption-Customer-Key: dGVzdA==      # Error! (too short)
```

**Missing key for encrypted object:**
```bash
curl "$S3_ENDPOINT/bucket/encrypted-file.txt"     # Error!
```

## Related Documentation

- [Server-Side Encryption](./Server-Side-Encryption.md)
- [Amazon S3 API](./Amazon-S3-API.md)
