---
id: Server-Side-Encryption-SSE-KMS
title: "Server Side Encryption SSE KMS"
sidebar_label: "Server Side Encryption SSE KMS"
---

# SSE-KMS: Server-Side Encryption with Key Management Service

SeaweedFS works with your existing Key Management Service (KMS) so you can keep keys where they belong. This guide walks you through AWS KMS, Google Cloud KMS, and OpenBao/Vault. Azure Key Vault is also available as experimental (build tag `azurekms`).

## Supported KMS Providers

| Provider | Status | Use Cases |
|----------|--------|-----------|
| **AWS KMS** | Full support | AWS-centric deployments |
| **Google Cloud KMS** | Full support | GCP-centric deployments |
| **OpenBao/Vault** | Full support | Hybrid/on-premises environments |
| **Azure Key Vault** | Experimental (build tag `azurekms`) | Azure-centric deployments |

## Quick Start Guide

### 1. Configure SeaweedFS

Tell SeaweedFS about your KMS in the S3 config JSON file:

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
        "transit_path": "transit",
        "cache_enabled": true,
        "cache_ttl": "1h"
      }
    }
  }
}
```

### 2. Start S3 with KMS Config

```bash
# Start S3 API with KMS and IAM configuration
weed s3 -config=s3_kms_config.json -port=8333
```

**Note:** The S3 config JSON file contains both KMS provider settings AND IAM-style access control (identities, credentials, permissions).

### 3. Test the Integration

```bash
# Ensure $S3_ENDPOINT is set
export S3_ENDPOINT=http://localhost:8333

# Upload object with SSE-KMS
aws --endpoint-url $S3_ENDPOINT s3 cp test-file.txt s3://mybucket/test-file.txt \
  --server-side-encryption aws:kms \
  --ssekms-key-id alias/my-key
```

---

## AWS KMS Integration

### Step 1: Create KMS Key

```bash
# Create customer-managed KMS key
aws kms create-key --description "SeaweedFS encryption key"

# Create key alias
aws kms create-alias \
  --alias-name alias/seaweedfs-key \
  --target-key-id <key-id-from-above>
```

### Step 2: Configure SeaweedFS

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
    "default_provider": "aws-kms",
    "providers": {
      "aws-kms": {
        "type": "aws-kms",
        "region": "us-east-1",
        "key_id": "alias/seaweedfs-key"
      }
    }
  }
}
```

### Step 3: Test AWS KMS

```bash
# Upload with AWS KMS encryption
aws --endpoint-url $S3_ENDPOINT s3 cp file.txt s3://mybucket/file.txt \
  --server-side-encryption aws:kms \
  --ssekms-key-id alias/seaweedfs-key
```

---

## Google Cloud KMS Integration

### Step 1: Create KMS Resources

```bash
# Create key ring
gcloud kms keyrings create seaweedfs-keyring --location us-east1

# Create encryption key
gcloud kms keys create seaweedfs-key \
  --keyring seaweedfs-keyring \
  --location us-east1 \
  --purpose encryption
```

### Step 2: Configure SeaweedFS

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
    "default_provider": "gcp-kms",
    "providers": {
      "gcp-kms": {
        "type": "gcp-kms",
        "project_id": "my-project-id",
        "location": "us-east1", 
        "key_ring": "seaweedfs-keyring",
        "key_name": "seaweedfs-key",
        "credentials_file": "/etc/seaweedfs/gcp-kms-key.json"
      }
    }
  }
}
```

---

## OpenBao/Vault Integration

### Step 1: Setup OpenBao/Vault

```bash
# Start OpenBao in dev mode (for testing)
openbao server -dev -dev-root-token-id="root-token"

# Enable transit secrets engine
openbao secrets enable transit

# Create encryption key
openbao write -f transit/keys/seaweedfs-key
```

### Step 2: Configure SeaweedFS

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
        "transit_path": "transit",
        "cache_enabled": true,
        "cache_ttl": "1h"
      }
    }
  }
}
```

### Step 3: Test OpenBao/Vault

```bash
# Upload with Vault encryption
aws --endpoint-url $S3_ENDPOINT s3 cp file.txt s3://mybucket/file.txt \
  --server-side-encryption aws:kms \
  --ssekms-key-id seaweedfs-key
```

---

## Azure Key Vault Integration (Experimental)

Azure Key Vault support exists behind the build tag `azurekms` and is considered experimental. To enable it, build SeaweedFS with the tag and configure the provider:

```bash
# Build with Azure KMS support (example)
go build -tags azurekms ./weed
```

```json
{
  "kms": {
    "providers": {
      "azure": {
        "type": "azure",
        "vault_url": "https://<your-vault>.vault.azure.net/",
        "tenant_id": "<tenant>",
        "client_id": "<client>",
        "client_secret": "<secret>",
        "use_default_creds": false
      }
    }
  }
}
```

---

## Multi-Provider Configuration

### Provider Selection Strategies

```json
{
  "identities": [...],
  "kms": {
    "default_provider": "openbao",
    "providers": {
      "openbao": {
        "type": "openbao",
        "address": "https://vault.internal:8200",
        "token": "root-token",
        "transit_path": "transit"
      },
      "aws-kms": {
        "type": "aws-kms",
        "region": "us-east-1",
        "key_id": "alias/seaweedfs-aws"
      },
      "gcp-kms": {
        "type": "gcp-kms",
        "project_id": "my-gcp-project",
        "location": "global",
        "key_ring": "seaweedfs-keyring",
        "key_name": "seaweedfs-gcp-key",
        "credentials_file": "/etc/seaweedfs/gcp-key.json"
      }
    },
    "buckets": {
      "financial-data": {"provider": "openbao"},
      "ml-models": {"provider": "gcp-kms"},
      "general-storage": {"provider": "aws-kms"}
    }
  }
}
```

## Security Best Practices

### 1. Key Management

- Grant minimal required KMS permissions
- Use resource-based policies where possible
- Implement proper key rotation policies
- Document key usage and ownership

### 2. Access Control

```json
{
  "identities": [
    {
      "name": "admin",
      "credentials": [{"accessKey": "admin", "secretKey": "password"}],
      "actions": ["Admin", "Read", "Write"]
    },
    {
      "name": "readonly",
      "credentials": [{"accessKey": "readonly", "secretKey": "password"}], 
      "actions": ["Read"]
    }
  ]
}
```

## Related Documentation

- **[Server-Side Encryption](./Server-Side-Encryption.md)**: Overview of all SSE types
- **[SSE-C Guide](./Server-Side-Encryption-SSE-C.md)**: Customer-provided keys
- **[Amazon S3 API](./Amazon-S3-API.md)**: Main S3 API documentation
