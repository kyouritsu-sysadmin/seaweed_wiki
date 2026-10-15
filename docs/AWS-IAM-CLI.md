---
id: AWS-IAM-CLI
title: "AWS IAM CLI"
sidebar_label: "AWS IAM CLI"
---

# AWS IAM CLI with SeaweedFS

This guide shows how to use the AWS CLI to manage IAM users, access keys, and policies in SeaweedFS.

## Installation

See [AWS-CLI-with-SeaweedFS](https://github.com/seaweedfs/seaweedfs/wiki/AWS-CLI-with-SeaweedFS#installation) for AWS CLI installation instructions.

## Prerequisites

### 1. Start SeaweedFS with S3/IAM

The IAM API is embedded in the S3 server by default:

```bash
# Start with embedded IAM (default)
weed s3 -filer=localhost:8888

# Or with weed server
weed server -s3
```

### 2. Create Admin Credentials

Create an admin user to manage IAM:

```bash
echo 's3.configure -apply -user admin -access_key admin_access_key -secret_key admin_secret_key -actions Admin' | weed shell
```

### 3. Configure AWS CLI

Set the endpoint to your S3 server (IAM uses the same endpoint):

```bash
export AWS_ACCESS_KEY_ID=admin_access_key
export AWS_SECRET_ACCESS_KEY=admin_secret_key

# IAM and S3 use the same endpoint
export AWS_ENDPOINT=http://localhost:8333
```

---

## User Management

### Create a User

```bash
aws --endpoint $AWS_ENDPOINT iam create-user --user-name bob
```

Output:
```json
{
    "User": {
        "UserName": "bob"
    }
}
```

### List Users

```bash
aws --endpoint $AWS_ENDPOINT iam list-users
```

Output:
```json
{
    "Users": [
        { "UserName": "admin" },
        { "UserName": "bob" }
    ]
}
```

### Get User Details

```bash
aws --endpoint $AWS_ENDPOINT iam get-user --user-name bob
```

### Delete User

```bash
aws --endpoint $AWS_ENDPOINT iam delete-user --user-name bob
```

### Enable/Disable User

Disable or re-enable a user without deleting them:

```bash
# Disable a user (all their access keys will stop working)
aws --endpoint $AWS_ENDPOINT iam set-user-status --user-name bob --status Inactive

# Re-enable the user
aws --endpoint $AWS_ENDPOINT iam set-user-status --user-name bob --status Active
```

---

## Access Key Management

### Create Access Key

```bash
aws --endpoint $AWS_ENDPOINT iam create-access-key --user-name bob
```

Output:
```json
{
    "AccessKey": {
        "UserName": "bob",
        "AccessKeyId": "X8R439UM7OSQJX28I9QTP",
        "Status": "Active",
        "SecretAccessKey": "FLh9yeeYhzA7qsiyLIXsvuhv4g2cSgoUJJe/EqZw1z"
    }
}
```

### List Access Keys

```bash
aws --endpoint $AWS_ENDPOINT iam list-access-keys --user-name bob
```

Output:
```json
{
    "AccessKeyMetadata": [
        {
            "UserName": "bob",
            "AccessKeyId": "X8R439UM7OSQJX28I9QTP",
            "Status": "Active"
        }
    ]
}
```

### Delete Access Key

```bash
aws --endpoint $AWS_ENDPOINT iam delete-access-key --user-name bob --access-key-id X8R439UM7OSQJX28I9QTP
```

### Update Access Key Status

Deactivate or reactivate an access key without deleting it:

```bash
# Deactivate an access key
aws --endpoint $AWS_ENDPOINT iam update-access-key \
  --user-name bob \
  --access-key-id X8R439UM7OSQJX28I9QTP \
  --status Inactive

# Reactivate the access key
aws --endpoint $AWS_ENDPOINT iam update-access-key \
  --user-name bob \
  --access-key-id X8R439UM7OSQJX28I9QTP \
  --status Active
```

### Self-Service: Manage Your Own Keys

Users can manage their own access keys without admin privileges:

```bash
# Set credentials for the user
export AWS_ACCESS_KEY_ID=bob_access_key
export AWS_SECRET_ACCESS_KEY=bob_secret_key

# Create a new key for yourself (no --user-name needed)
aws --endpoint $AWS_ENDPOINT iam create-access-key

# List your own keys
aws --endpoint $AWS_ENDPOINT iam list-access-keys
```

---

## Policy Management

### Create and Attach a Read-Only Policy

```bash
# Create policy document
cat > readonly-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:Get*",
        "s3:List*"
      ],
      "Resource": [
        "arn:aws:s3:::my-bucket",
        "arn:aws:s3:::my-bucket/*"
      ]
    }
  ]
}
EOF

# Attach to user
aws --endpoint $AWS_ENDPOINT iam put-user-policy \
  --user-name bob \
  --policy-name ReadOnlyPolicy \
  --policy-document file://readonly-policy.json
```

### Create Read-Write Policy for Specific Bucket

```bash
cat > readwrite-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:Get*",
        "s3:Put*",
        "s3:Delete*",
        "s3:List*"
      ],
      "Resource": [
        "arn:aws:s3:::data-bucket",
        "arn:aws:s3:::data-bucket/*"
      ]
    }
  ]
}
EOF

aws --endpoint $AWS_ENDPOINT iam put-user-policy \
  --user-name bob \
  --policy-name DataBucketAccess \
  --policy-document file://readwrite-policy.json
```

### List User Policies

List the names of inline policies attached to a user:

```bash
aws --endpoint $AWS_ENDPOINT iam list-user-policies --user-name bob
```

Output:
```json
{
    "PolicyNames": [
        "ReadOnlyPolicy"
    ],
    "IsTruncated": false
}
```

### Get User Policy

```bash
aws --endpoint $AWS_ENDPOINT iam get-user-policy \
  --user-name bob \
  --policy-name ReadOnlyPolicy
```

### Delete User Policy

```bash
aws --endpoint $AWS_ENDPOINT iam delete-user-policy \
  --user-name bob \
  --policy-name ReadOnlyPolicy
```

### Managed Policies

Managed policies are standalone policies that are stored in the configuration and can be attached to multiple users.

#### Create a Managed Policy

```bash
# Create policy document
cat > readonly-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:Get*", "s3:List*"],
      "Resource": ["*"]
    }
  ]
}
EOF

# Create the policy
aws --endpoint $AWS_ENDPOINT iam create-policy \
  --policy-name ReadOnlyPolicy \
  --policy-document file://readonly-policy.json
```

#### List All Managed Policies

```bash
aws --endpoint $AWS_ENDPOINT iam list-policies
```

#### Get Managed Policy Details

```bash
aws --endpoint $AWS_ENDPOINT iam get-policy \
  --policy-arn arn:aws:iam:::policy/ReadOnlyPolicy
```

#### Attach a Managed Policy to a User

```bash
aws --endpoint $AWS_ENDPOINT iam attach-user-policy \
  --user-name bob \
  --policy-arn arn:aws:iam:::policy/ReadOnlyPolicy
```

#### List Managed Policies Attached to a User

```bash
aws --endpoint $AWS_ENDPOINT iam list-attached-user-policies --user-name bob
```

#### Detach a Managed Policy from a User

```bash
aws --endpoint $AWS_ENDPOINT iam detach-user-policy \
  --user-name bob \
  --policy-arn arn:aws:iam:::policy/ReadOnlyPolicy
```

#### Delete a Managed Policy

> **Note**: A policy must be detached from all users before it can be deleted.

```bash
aws --endpoint $AWS_ENDPOINT iam delete-policy \
  --policy-arn arn:aws:iam:::policy/ReadOnlyPolicy
```

---

## Group Management

Groups allow you to organize users and apply policies at the group level. Policies attached to a group are evaluated for all group members during S3 authorization.

### Create a Group

```bash
aws --endpoint $AWS_ENDPOINT iam create-group --group-name developers
```

Output:
```json
{
    "Group": {
        "GroupName": "developers"
    }
}
```

### List Groups

```bash
aws --endpoint $AWS_ENDPOINT iam list-groups
```

### Get Group Details (including members)

```bash
aws --endpoint $AWS_ENDPOINT iam get-group --group-name developers
```

### Add User to Group

```bash
aws --endpoint $AWS_ENDPOINT iam add-user-to-group --group-name developers --user-name bob
```

### Remove User from Group

```bash
aws --endpoint $AWS_ENDPOINT iam remove-user-from-group --group-name developers --user-name bob
```

### Attach Policy to Group

```bash
aws --endpoint $AWS_ENDPOINT iam attach-group-policy \
  --group-name developers \
  --policy-arn arn:aws:iam:::policy/ReadOnlyPolicy
```

### List Policies Attached to Group

```bash
aws --endpoint $AWS_ENDPOINT iam list-attached-group-policies --group-name developers
```

### Group Inline Policies

Groups can also have inline policies attached directly:

```bash
# Attach an inline policy to a group
cat > group-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:Get*", "s3:List*"],
      "Resource": ["arn:aws:s3:::shared-bucket/*"]
    }
  ]
}
EOF

aws --endpoint $AWS_ENDPOINT iam put-group-policy \
  --group-name developers \
  --policy-name SharedBucketReadOnly \
  --policy-document file://group-policy.json

# List inline policies for a group
aws --endpoint $AWS_ENDPOINT iam list-group-policies --group-name developers

# Get an inline policy
aws --endpoint $AWS_ENDPOINT iam get-group-policy \
  --group-name developers \
  --policy-name SharedBucketReadOnly

# Delete an inline policy from a group
aws --endpoint $AWS_ENDPOINT iam delete-group-policy \
  --group-name developers \
  --policy-name SharedBucketReadOnly
```

### Detach Policy from Group

```bash
aws --endpoint $AWS_ENDPOINT iam detach-group-policy \
  --group-name developers \
  --policy-arn arn:aws:iam:::policy/ReadOnlyPolicy
```

### List Groups for a User

```bash
aws --endpoint $AWS_ENDPOINT iam list-groups-for-user --user-name bob
```

### Delete a Group

> **Note**: A group must have no members and no attached policies before it can be deleted.

```bash
aws --endpoint $AWS_ENDPOINT iam delete-group --group-name developers
```

### Key Behaviors

- **Group policies**: Policies attached to a group apply to all members during S3 authorization
- **Disabled groups**: Groups can be disabled/enabled (SeaweedFS extension, not in AWS CLI)
- **User deletion**: Deleting a user automatically removes them from all groups
- **Policy deletion**: A policy cannot be deleted if it is attached to any group

---

## Verify Configuration

Check the current S3/IAM configuration:

```bash
echo 's3.configure' | weed shell
```

Output:
```json
{
  "identities": [
    {
      "name": "admin",
      "credentials": [
        {
          "accessKey": "admin_access_key",
          "secretKey": "admin_secret_key"
        }
      ],
      "actions": ["Admin"]
    },
    {
      "name": "bob",
      "credentials": [
        {
          "accessKey": "X8R439UM7OSQJX28I9QTP",
          "secretKey": "FLh9yeeYhzA7qsiyLIXsvuhv4g2cSgoUJJe/EqZw1z"
        }
      ],
      "actions": [
        "Read:my-bucket",
        "List:my-bucket"
      ]
    }
  ]
}
```

---

## Complete Workflow Example

```bash
# 1. Set admin credentials
export AWS_ACCESS_KEY_ID=admin_key
export AWS_SECRET_ACCESS_KEY=admin_secret
export AWS_ENDPOINT=http://localhost:8333

# 2. Create a new user
aws --endpoint $AWS_ENDPOINT iam create-user --user-name alice

# 3. Create access key for the user
aws --endpoint $AWS_ENDPOINT iam create-access-key --user-name alice

# 4. Create a read-only policy
cat > alice-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:Get*", "s3:List*"],
      "Resource": ["arn:aws:s3:::shared-bucket/*"]
    }
  ]
}
EOF

# 5. Attach inline policy to user
aws --endpoint $AWS_ENDPOINT iam put-user-policy \
  --user-name alice \
  --policy-name SharedBucketReadOnly \
  --policy-document file://alice-policy.json

# 6. Attach a managed policy (e.g., ReadOnlyPolicy is built-in or previously created)
aws --endpoint $AWS_ENDPOINT iam attach-user-policy \
  --user-name alice \
  --policy-arn arn:aws:iam:::policy/ReadOnlyPolicy

# 7. Verify
echo 's3.configure' | weed shell
```

---

## Related Documentation

- [Amazon IAM API](./Amazon-IAM-API.md) - IAM API reference
- [S3 Credentials](./S3-Credentials.md) - Credential management options
- [AWS CLI with SeaweedFS](./AWS-CLI-with-SeaweedFS.md) - General AWS CLI setup
- [S3 Configuration](./S3-Configuration.md) - S3 server configuration
