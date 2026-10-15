---
id: S3-Bucket-Policies
title: "S3 Bucket Policies"
sidebar_label: "S3 Bucket Policies"
---

# S3 Bucket Policies

SeaweedFS supports AWS S3-compatible bucket policies for controlling access to buckets and objects at the bucket level.

## Overview

Bucket policies allow you to grant or deny permissions for S3 operations on a bucket and its objects. They are resource-based policies that complement user-level IAM policies.

## Quick Setup with Weed Shell

The `s3.bucket.access` shell command provides a simple way to set per-bucket access for any user. The user is auto-created if it does not exist.

```bash
# Grant anonymous read and list access (public download)
> s3.bucket.access -name my-bucket -user anonymous -access Read,List

# Grant full anonymous access
> s3.bucket.access -name my-bucket -user anonymous -access Read,Write,List

# View current access for a user on a bucket
> s3.bucket.access -name my-bucket -user anonymous

# Remove all access
> s3.bucket.access -name my-bucket -user anonymous -access none
```

Supported actions: `Read`, `Write`, `List`, `Tagging`, `Admin` (same as `s3.configure -actions`).

Actions are scoped to the specified bucket and stored on the IAM identity (as `Action:bucket`).

## AWS CLI Setup

First, configure the AWS CLI to connect to your SeaweedFS S3 endpoint:

```bash
aws configure --profile seaweedfs
```

Enter your credentials and configure the endpoint:

```bash
AWS Access Key ID: your_access_key
AWS Secret Access Key: your_secret_key
Default region name: us-east-1
Default output format: json
```

Then use this profile with an endpoint URL for all commands (or configure it in your AWS config file):

```bash
export AWS_PROFILE=seaweedfs
alias s3="aws s3 --endpoint-url http://localhost:8333"
alias s3api="aws s3api --endpoint-url http://localhost:8333"
```

## API Operations

### Get Bucket Policy

Retrieve the current bucket policy:

```bash
aws s3api get-bucket-policy \
  --bucket my-bucket \
  --endpoint-url http://localhost:8333
```

Output:
```json
{
  "Policy": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":\"*\",\"Action\":\"s3:GetObject\",\"Resource\":\"arn:aws:s3:::my-bucket/*\"}]}"
}
```

To view the policy in readable format:

```bash
aws s3api get-bucket-policy \
  --bucket my-bucket \
  --endpoint-url http://localhost:8333 \
  --output text | jq .Policy -r | jq .
```

### Put Bucket Policy

Set or update a bucket policy from a file:

```bash
aws s3api put-bucket-policy \
  --bucket my-bucket \
  --policy file://policy.json \
  --endpoint-url http://localhost:8333
```

Or inline:

```bash
aws s3api put-bucket-policy \
  --bucket my-bucket \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "PublicRead",
        "Effect": "Allow",
        "Principal": "*",
        "Action": "s3:GetObject",
        "Resource": "arn:aws:s3:::my-bucket/*"
      }
    ]
  }' \
  --endpoint-url http://localhost:8333
```

### Delete Bucket Policy

Remove the bucket policy:

```bash
aws s3api delete-bucket-policy \
  --bucket my-bucket \
  --endpoint-url http://localhost:8333
```

## Policy Document Format

Bucket policies use the standard AWS S3 policy format with the following structure:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "OptionalStatementId",
      "Effect": "Allow|Deny",
      "Principal": "string or *",
      "Action": ["s3:action1", "s3:action2"],
      "Resource": ["arn:aws:s3:::bucket-name", "arn:aws:s3:::bucket-name/*"],
      "Condition": {
        "condition-operator": {
          "condition-key": ["value"]
        }
      }
    }
  ]
}
```

### Key Components

- **Version**: Must be `"2012-10-17"` (AWS policy language version)
- **Sid**: Optional statement identifier for documentation
- **Effect**: `Allow` or `Deny` - the action's result
- **Principal**: Who the policy applies to (`"*"` for public, or specific user/role ARNs)
- **Action**: S3 operations (e.g., `s3:GetObject`, `s3:PutObject`)
- **Resource**: Bucket or object paths
  - `arn:aws:s3:::bucket-name` - for bucket operations
  - `arn:aws:s3:::bucket-name/*` - for all objects in the bucket
  - `arn:aws:s3:::bucket-name/path/to/object` - for specific objects
  - Simplified formats: `bucket-name`, `bucket-name/*` are also accepted
- **Condition**: Optional conditions for when the policy applies

## Common Examples

### Public Read Access

Allow anyone to read objects in a bucket:

```bash
aws s3api put-bucket-policy \
  --bucket my-bucket \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": "*",
        "Action": "s3:GetObject",
        "Resource": "arn:aws:s3:::my-bucket/*"
      }
    ]
  }' \
  --endpoint-url http://localhost:8333
```

### Restrict by IP Address

Allow reads only from specific IP addresses:

```bash
aws s3api put-bucket-policy \
  --bucket my-bucket \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": "*",
        "Action": "s3:GetObject",
        "Resource": "arn:aws:s3:::my-bucket/*",
        "Condition": {
          "IpAddress": {
            "aws:SourceIp": ["192.168.1.0/24"]
          }
        }
      }
    ]
  }' \
  --endpoint-url http://localhost:8333
```

### Require HTTPS

Allow access only over secure connections:

```bash
aws s3api put-bucket-policy \
  --bucket my-bucket \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": "*",
        "Action": ["s3:GetObject", "s3:PutObject"],
        "Resource": "arn:aws:s3:::my-bucket/*",
        "Condition": {
          "Bool": {
            "aws:SecureTransport": "true"
          }
        }
      }
    ]
  }' \
  --endpoint-url http://localhost:8333
```

### Deny Unencrypted Uploads

Require encryption for all uploads:

```bash
aws s3api put-bucket-policy \
  --bucket my-bucket \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Deny",
        "Principal": "*",
        "Action": "s3:PutObject",
        "Resource": "arn:aws:s3:::my-bucket/*",
        "Condition": {
          "StringNotEquals": {
            "s3:x-amz-server-side-encryption": "AES256"
          }
        }
      }
    ]
  }' \
  --endpoint-url http://localhost:8333
```

## Supported S3 Actions

Common actions in bucket policies:

- **Object Operations**: `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`
- **Bucket Operations**: `s3:ListBucket`, `s3:CreateBucket`, `s3:DeleteBucket`
- **ACL Operations**: `s3:PutObjectAcl`, `s3:GetObjectAcl`
- **Multipart Operations**: `s3:CreateMultipartUpload`, `s3:UploadPart`, `s3:CompleteMultipartUpload`, `s3:AbortMultipartUpload`, `s3:ListBucketMultipartUploads`, `s3:ListMultipartUploadParts`
- **Object Tagging**: `s3:GetObjectTagging`, `s3:PutObjectTagging`
- **Versioning**: `s3:GetObjectVersion`, `s3:PutObjectVersionAcl`

## Multipart Upload Permission Inheritance

When a policy grants `s3:PutObject`, it implicitly allows all multipart upload operations:

- `s3:CreateMultipartUpload` - Start a multipart upload
- `s3:UploadPart` - Upload parts of a multipart upload
- `s3:CompleteMultipartUpload` - Complete a multipart upload
- `s3:AbortMultipartUpload` - Abort an incomplete multipart upload
- `s3:ListBucketMultipartUploads` - List in-progress multipart uploads
- `s3:ListMultipartUploadParts` - List parts of a multipart upload

This behavior aligns with AWS S3 semantics where multipart upload is considered an implementation detail of `s3:PutObject`. Users can upload large objects using either a single direct upload (if `s3:PutObject` is granted) or multiple parts via multipart upload (also allowed by `s3:PutObject`).

**Example**: A policy granting only `s3:PutObject` is sufficient to perform complete multipart uploads without explicitly listing all multipart actions.

## Policy Validation

SeaweedFS validates bucket policies for:

- Correct policy document version (`2012-10-17`)
- Presence of at least one statement
- Required Principal field
- Resources matching the bucket name
- S3 action prefixes
- Valid effect values (Allow/Deny)

## Integration with IAM

Bucket policies work alongside IAM policies (defined at [S3 Credentials](./S3-Credentials.md)) for comprehensive access control:

- **Bucket Policies**: Resource-based, grant access across users
- **IAM Policies**: User-based, define what users can do
- **Evaluation**: Access is allowed only if both allow the operation (or if bucket policy explicitly allows and IAM doesn't deny)

See [Amazon IAM API](./Amazon-IAM-API.md) for more on IAM integration.

## Storage

Bucket policies are stored as metadata in the filer alongside bucket configuration, ensuring they persist across server restarts.

## See Also

- [Amazon S3 API](./Amazon-S3-API.md) - S3 API overview
- [S3 Credentials](./S3-Credentials.md) - S3 authentication
- [Amazon IAM API](./Amazon-IAM-API.md) - User and role management
- [S3 API FAQ](./S3-API-FAQ.md) - Common S3 questions
