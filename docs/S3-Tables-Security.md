---
id: S3-Tables-Security
title: "S3 Tables Security"
sidebar_label: "S3 Tables Security"
---

# S3 Tables Security

SeaweedFS S3 Tables implementation supports fine-grained access control using IAM-style policies. These policies can be attached to **Table Buckets** to control access to namespaces and tables.

## Permission Model

Permissions are defined using JSON policy documents similar to AWS IAM. Policies are attached to the **Table Bucket** using the `PutTableBucketPolicy` API.

### Default Permission Behavior

If no policy is attached to a Table Bucket:
- **Zero Configuration**: Access is **Allowed** by default (simplifies development).
- **IAM Configured**: Access is **Denied** by default (security best practice).

### Policy Structure

A policy document consists of a list of statements:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3tables:CreateTable",
      "Resource": "*"
    }
  ]
}
```

- **Effect**: `Allow` or `Deny`. Deny always takes precedence.
- **Principal**: The user or role (e.g., `*`, `arn:aws:iam::123456789012:user/admin`).
- **Action**: The API operation to allow/deny (supports wildcards).
- **Resource**: The resource ARN (supports wildcards).
- **Condition**: (Optional) extra conditions for the rule.

---

## Supported Actions

The following actions are supported in policies. Actions can be specified with the `s3tables:` prefix or without it (for some contexts).

### Table Bucket Operations
- `s3tables:CreateTableBucket`
- `s3tables:DeleteTableBucket`
- `s3tables:GetTableBucket`
- `s3tables:ListTableBuckets`
- `s3tables:PutTableBucketPolicy`
- `s3tables:GetTableBucketPolicy`
- `s3tables:DeleteTableBucketPolicy`
- `s3tables:PutTableBucketMaintenanceConfiguration`
- `s3tables:GetTableBucketMaintenanceConfiguration`

### Namespace Operations
- `s3tables:CreateNamespace`
- `s3tables:DeleteNamespace`
- `s3tables:GetNamespace`
- `s3tables:ListNamespaces`

### Table Operations
- `s3tables:CreateTable`
- `s3tables:DeleteTable`
- `s3tables:GetTable`
- `s3tables:ListTables`
- `s3tables:PutTablePolicy`
- `s3tables:GetTablePolicy`
- `s3tables:DeleteTablePolicy`
- `s3tables:PutTableMaintenanceConfiguration`
- `s3tables:GetTableMaintenanceConfiguration`
- `s3tables:GetTableMaintenanceJobStatus`

---

## Example Policies

### 1. Read-Only Access
Allow listing and getting tables, but no modifications.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": [
        "s3tables:Get*",
        "s3tables:List*"
      ],
      "Resource": "*"
    }
  ]
}
```

### 2. Admin Access for Specific Namespace
Allow full access only to tables within the `finance` namespace.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "arn:aws:iam::123456789012:user/finance-admin",
      "Action": "s3tables:*",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "s3tables:namespace": "finance"
        }
      }
    }
  ]
}
```

### 3. Deny Deletion
Allow everything except deleting tables.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3tables:*",
      "Resource": "*"
    },
    {
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3tables:DeleteTable",
      "Resource": "*"
    }
  ]
}
```
