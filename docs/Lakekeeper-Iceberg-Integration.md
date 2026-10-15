---
id: Lakekeeper-Iceberg-Integration
title: "Lakekeeper Iceberg Integration"
sidebar_label: "Lakekeeper Iceberg Integration"
---

# Lakekeeper Iceberg Integration

[Lakekeeper](https://lakekeeper.io/) is an open-source Iceberg catalog that can use SeaweedFS as its storage backend via S3 Tables and STS-vended credentials.

## Architecture

In a Lakekeeper setup with SeaweedFS:

1. **Lakekeeper** acts as the Iceberg catalog, managing namespace and table metadata
2. **SeaweedFS** provides S3-compatible storage for data files (Parquet) and metadata
3. **STS (Security Token Service)** issues temporary credentials that Lakekeeper vends to clients

This architecture supports credential vending — Lakekeeper assumes an IAM role via STS and passes short-lived credentials to query engines, avoiding the need to distribute long-lived secrets.

## Prerequisites

- SeaweedFS running with IAM and STS enabled
- A table bucket created via `weed shell` or the S3 Tables API
- Lakekeeper configured to use SeaweedFS as its storage

## SeaweedFS IAM Configuration

Lakekeeper requires STS support for credential vending. Configure SeaweedFS with an IAM config that includes STS settings and an assumable role:

```json
{
  "identities": [
    {
      "name": "admin",
      "credentials": [
        {
          "accessKey": "admin",
          "secretKey": "admin"
        }
      ],
      "actions": ["Admin", "Read", "List", "Tagging", "Write"]
    }
  ],
  "sts": {
    "tokenDuration": "12h",
    "maxSessionLength": "24h",
    "issuer": "seaweedfs-sts",
    "signingKey": "BASE64_ENCODED_SIGNING_KEY"
  },
  "roles": [
    {
      "roleName": "LakekeeperVendedRole",
      "roleArn": "arn:aws:iam::000000000000:role/LakekeeperVendedRole",
      "trustPolicy": {
        "Version": "2012-10-17",
        "Statement": [
          {
            "Effect": "Allow",
            "Principal": "*",
            "Action": "sts:AssumeRole"
          }
        ]
      },
      "attachedPolicies": ["FullAccess"]
    }
  ],
  "policies": [
    {
      "name": "FullAccess",
      "document": {
        "Version": "2012-10-17",
        "Statement": [
          {
            "Effect": "Allow",
            "Action": "*",
            "Resource": "*"
          }
        ]
      }
    }
  ]
}
```

Start SeaweedFS with IAM enabled:

```bash
weed mini \
    -s3.config /path/to/iam_config.json \
    -s3.iam.config /path/to/iam_config.json \
    -s3.iam.readOnly=false
```

## STS Credential Vending

Lakekeeper uses STS `AssumeRole` to obtain temporary credentials for accessing SeaweedFS S3:

```
POST http://localhost:8333/?Action=AssumeRole
    &RoleArn=arn:aws:iam::000000000000:role/LakekeeperVendedRole
    &RoleSessionName=lakekeeper-session
    &Version=2011-06-15
```

The response includes temporary `AccessKeyId`, `SecretAccessKey`, and `SessionToken` that Lakekeeper vends to query engines.

## S3 Tables Operations

Lakekeeper interacts with SeaweedFS via the S3 Tables REST API using SigV4 signing with the `s3tables` service name:

```
# Create a table bucket
PUT /buckets
Content-Type: application/x-amz-json-1.1
{"name": "iceberg-tables"}

# Create a namespace
PUT /namespaces/{bucketARN}
{"namespace": ["my_namespace"]}

# Create a table
PUT /tables/{bucketARN}/{namespace}
{"name": "my_table", "format": "ICEBERG"}
```

All requests must be signed with SigV4 using the `s3tables` service name and the appropriate region.

## Key Configuration Parameters

| Parameter | Value |
|-----------|-------|
| S3 endpoint | `http://localhost:8333` |
| STS endpoint | `http://localhost:8333` (same as S3) |
| Region | `us-east-1` |
| SigV4 service (S3 Tables) | `s3tables` |
| SigV4 service (S3 data) | `s3` |
| Role ARN | `arn:aws:iam::000000000000:role/LakekeeperVendedRole` |

## See Also

- [SeaweedFS Iceberg Catalog](./SeaweedFS-Iceberg-Catalog.md) - Architecture and concepts
- [S3 Tables Security](./S3-Tables-Security.md) - IAM policies for table access
- [S3 Table Bucket](./S3-Table-Bucket.md) - Managing table buckets
- [STS Integration Tests](./Amazon-IAM-API.md) - STS API details
