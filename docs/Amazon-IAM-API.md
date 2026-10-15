---
id: Amazon-IAM-API
title: "Amazon IAM API"
sidebar_label: "Amazon IAM API"
---

# Amazon IAM API

SeaweedFS provides AWS IAM API compatibility for managing users, access keys, and policies.

## Embedded IAM (Default)

Starting with SeaweedFS 3.x, the IAM API is **embedded in the S3 server by default**. This means:

- IAM API is available on the same port as S3 (default: 8333)
- No need to run a separate IAM server
- Simplified deployment - single process handles both S3 and IAM

### Starting S3 with Embedded IAM

```bash
# IAM is enabled by default
weed s3 -filer=localhost:8888

# Or with weed server
weed server -s3

# To explicitly disable embedded IAM
weed s3 -iam=false -filer=localhost:8888
```

### Accessing the Embedded IAM API

The IAM API is available at the root path (`/`) of the S3 server using POST requests with an `Action` parameter:

```bash
# IAM endpoint is the same as S3 endpoint
export AWS_ENDPOINT=http://localhost:8333
```

---

## Standalone IAM (Deprecated)

> **Note**: The standalone `weed iam` command is deprecated. Please use the embedded IAM in the S3 server instead.

For backwards compatibility, you can still run a separate IAM server:

```bash
weed iam -filer=localhost:8888 -port=8111
```

---

## Supported IAM Actions

| Action | Description | Self-Service |
|--------|-------------|--------------|
| `CreateUser` | Create a new IAM user | Admin only |
| `DeleteUser` | Delete an IAM user | Admin only |
| `GetUser` | Get user details | Yes (own user) |
| `UpdateUser` | Update user properties | Admin only |
| `ListUsers` | List all users | Admin only |
| `SetUserStatus` | Enable or disable a user | Admin only |
| `CreateAccessKey` | Create access key for user (supports optional caller-supplied `AccessKeyId`/`SecretAccessKey`, see [below](#caller-supplied-accesskeyid-and-secretaccesskey-extension)) | Yes (own keys) |
| `DeleteAccessKey` | Delete access key | Yes (own keys) |
| `UpdateAccessKey` | Change access key status (Active/Inactive) | Yes (own keys) |
| `ListAccessKeys` | List access keys for user | Yes (own keys) |
| `PutUserPolicy` | Attach inline policy to user | Admin only |
| `GetUserPolicy` | Get user's inline policy | Admin only |
| `DeleteUserPolicy` | Remove user's inline policy | Admin only |
| `ListUserPolicies` | List inline policy names for user | Admin only |
| `CreatePolicy` | Create and store a managed policy | Admin only |
| `DeletePolicy` | Delete a managed policy | Admin only |
| `ListPolicies` | List managed policies | Admin only |
| `GetPolicy` | Get managed policy metadata | Admin only |
| `AttachUserPolicy` | Attach managed policy to user | Admin only |
| `DetachUserPolicy` | Remove managed policy from user | Admin only |
| `ListAttachedUserPolicies` | List managed policies for user | Admin only |
| `CreateGroup` | Create an IAM group | Admin only |
| `DeleteGroup` | Delete an IAM group (must have no members or policies) | Admin only |
| `GetGroup` | Get group details and members | Admin only |
| `ListGroups` | List all groups | Admin only |
| `AddUserToGroup` | Add a user to a group | Admin only |
| `RemoveUserFromGroup` | Remove a user from a group | Admin only |
| `AttachGroupPolicy` | Attach managed policy to group | Admin only |
| `DetachGroupPolicy` | Remove managed policy from group | Admin only |
| `ListAttachedGroupPolicies` | List managed policies for group | Admin only |
| `PutGroupPolicy` | Attach inline policy to group | Admin only |
| `GetGroupPolicy` | Get group's inline policy | Admin only |
| `DeleteGroupPolicy` | Remove inline policy from group | Admin only |
| `ListGroupPolicies` | List inline policy names for group | Admin only |
| `ListGroupsForUser` | List groups a user belongs to | Admin only |
| `UpdateGroup` | Rename or enable/disable a group (SeaweedFS extension) | Admin only |
| `TagUser` | Attach key/value tags to a user (max 50 tags, key 1-128, value 0-256) | Admin only |
| `UntagUser` | Remove tags from a user | Admin only |
| `ListUserTags` | List tags attached to a user | Admin only |
| `GetPolicyVersion` | Read a specific managed-policy version | Admin only |
| `ListPolicyVersions` | List versions of a managed policy | Admin only |
| `CreateServiceAccount` | Create a service-account credential | Admin only |
| `DeleteServiceAccount` | Delete a service-account credential | Admin only |
| `GetServiceAccount` | Get service-account details | Admin only |
| `ListServiceAccounts` | List service-account credentials | Admin only |
| `UpdateServiceAccount` | Update a service-account credential | Admin only |

### Self-Service Operations

Users can manage their own access keys without admin privileges:
- Create, delete, and list their own access keys
- View their own user information

Operations on other users require `Admin` action permission.

---

## Authentication

### Setting Up Admin Credentials

Before using the IAM API, create an admin user with the `Admin` action:

```bash
echo 's3.configure -access_key admin_key -secret_key admin_secret -user admin -actions Admin -apply' | weed shell
```

### Using the IAM API

Set environment variables for AWS CLI:

```bash
export AWS_ACCESS_KEY_ID=admin_key
export AWS_SECRET_ACCESS_KEY=admin_secret
export AWS_ENDPOINT=http://localhost:8333  # S3/IAM endpoint
```

---

## Examples

### Create a User and Access Key

```bash
# Create user
aws --endpoint $AWS_ENDPOINT iam create-user --user-name alice

# Create access key for user
aws --endpoint $AWS_ENDPOINT iam create-access-key --user-name alice
```

### Caller-Supplied AccessKeyId and SecretAccessKey (Extension)

SeaweedFS extends `CreateAccessKey` with two optional form parameters that are
not part of the AWS IAM API: `AccessKeyId` and `SecretAccessKey`. When both are
supplied, they are used verbatim instead of being randomly generated. This is
useful when applications need stable, pre-known credentials — for example, when
provisioning S3 secrets from an external source into a Kubernetes deployment.

**Rules:**

- Both parameters must be supplied together. Supplying only one is rejected
  with `InvalidInput`.
- `AccessKeyId`: 4–128 ASCII alphanumeric characters (`A-Z`, `a-z`, `0-9`).
  The restriction prevents characters that would break AWS SigV4
  canonicalization (e.g. `/`, `=`, `,`).
- `SecretAccessKey`: 8–128 characters.
- `AccessKeyId` must be unique across all identities and service accounts;
  a collision returns `EntityAlreadyExists`.
- Omit both to get the AWS-standard random-generation behavior.

**The AWS CLI does not expose these parameters**, so callers must POST directly
to the IAM endpoint. For example, using the standalone IAM API:

```bash
# The standalone IAM API listens on port 8111 by default.
IAM_ENDPOINT=http://localhost:8111

curl -X POST "$IAM_ENDPOINT" \
  --data-urlencode "Action=CreateAccessKey" \
  --data-urlencode "UserName=alice" \
  --data-urlencode "AccessKeyId=my-app-key" \
  --data-urlencode "SecretAccessKey=my-app-secret-value" \
  --aws-sigv4 "aws:amz:us-east-1:iam" \
  --user "$AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY"
```

The embedded IAM in the S3 server accepts the same parameters on its IAM
endpoint. `SecretAccessKey` is redacted from server logs regardless of log
verbosity. The response format is identical to the AWS `CreateAccessKey`
response.

### Attach a Policy to User

```bash
# Create policy document
cat > policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:Get*", "s3:List*"],
      "Resource": ["arn:aws:s3:::my-bucket/*"]
    }
  ]
}
EOF

# Attach policy to user
aws --endpoint $AWS_ENDPOINT iam put-user-policy \
  --user-name alice \
  --policy-name ReadOnlyPolicy \
  --policy-document file://policy.json
```

### List Users and Access Keys

```bash
# List all users
aws --endpoint $AWS_ENDPOINT iam list-users

# List access keys for a user
aws --endpoint $AWS_ENDPOINT iam list-access-keys --user-name alice
```

### Managed Policies

Managed policies are standalone policies that can be attached to multiple users.

```bash
# Attach a managed policy to user
aws --endpoint $AWS_ENDPOINT iam attach-user-policy \
  --user-name alice \
  --policy-arn arn:aws:iam:::policy/ReadOnlyPolicy

# List attached managed policies for a user
aws --endpoint $AWS_ENDPOINT iam list-attached-user-policies --user-name alice

# Detach a managed policy
aws --endpoint $AWS_ENDPOINT iam detach-user-policy \
  --user-name alice \
  --policy-arn arn:aws:iam:::policy/ReadOnlyPolicy

# Create a managed policy
aws --endpoint $AWS_ENDPOINT iam create-policy \
  --policy-name MyManagedPolicy \
  --policy-document file://policy.json

# List all managed policies
aws --endpoint $AWS_ENDPOINT iam list-policies

# Get managed policy metadata
aws --endpoint $AWS_ENDPOINT iam get-policy \
  --policy-arn arn:aws:iam:::policy/MyManagedPolicy

# Delete a managed policy (must be detached from all users first)
aws --endpoint $AWS_ENDPOINT iam delete-policy \
  --policy-arn arn:aws:iam:::policy/MyManagedPolicy
```

### Self-Service: User Managing Their Own Keys

A non-admin user can manage their own access keys:

```bash
# Set credentials for the user
export AWS_ACCESS_KEY_ID=alice_access_key
export AWS_SECRET_ACCESS_KEY=alice_secret_key

# User can create additional access keys for themselves
aws --endpoint $AWS_ENDPOINT iam create-access-key
# (no --user-name needed, defaults to authenticated user)

# List own access keys
aws --endpoint $AWS_ENDPOINT iam list-access-keys

# Deactivate an access key (key rotation)
aws --endpoint $AWS_ENDPOINT iam update-access-key --access-key-id AKIAEXAMPLE --status Inactive
```

---

## User and Access Key Status Management

SeaweedFS supports enabling/disabling users and access keys without deleting them. This is useful for:

- **Temporary suspension**: Disable user access during investigation
- **Key rotation**: Deactivate old keys before deletion  
- **Offboarding**: Disable rather than delete for audit purposes
- **Emergency response**: Quickly disable compromised credentials

### Disable a User

```bash
# Disable a user (all their access keys will stop working)
aws --endpoint $AWS_ENDPOINT iam set-user-status --user-name alice --status Inactive

# Re-enable the user
aws --endpoint $AWS_ENDPOINT iam set-user-status --user-name alice --status Active
```

### Deactivate an Access Key

```bash
# Deactivate an access key
aws --endpoint $AWS_ENDPOINT iam update-access-key \
  --user-name alice \
  --access-key-id AKIAEXAMPLE \
  --status Inactive

# Reactivate the access key
aws --endpoint $AWS_ENDPOINT iam update-access-key \
  --user-name alice \
  --access-key-id AKIAEXAMPLE \
  --status Active
```

### Check Access Key Status

```bash
# List access keys shows their status
aws --endpoint $AWS_ENDPOINT iam list-access-keys --user-name alice
```

Output:
```json
{
    "AccessKeyMetadata": [
        {
            "UserName": "alice",
            "AccessKeyId": "X8R439UM7OSQJX28I9QTP",
            "Status": "Active"
        },
        {
            "UserName": "alice", 
            "AccessKeyId": "Y9S540VN8PTRKZ39J0URP",
            "Status": "Inactive"
        }
    ]
}
```

---

## Group Management

IAM groups allow you to organize users and apply policies at the group level. Policies attached to a group apply to all members of that group.

### Key Behaviors

- **Authorization**: Group policies are evaluated alongside user policies during S3 request authorization
- **Disabled groups**: A group can be disabled, which suspends its policies for all members without removing membership
- **User deletion**: Deleting a user automatically removes them from all groups
- **Policy deletion**: A policy cannot be deleted if it is attached to any group (must detach first)
- **Group deletion**: A group must have no members and no attached policies before it can be deleted

### Examples

```bash
# Create a group
aws --endpoint $AWS_ENDPOINT iam create-group --group-name developers

# Add user to group
aws --endpoint $AWS_ENDPOINT iam add-user-to-group --group-name developers --user-name alice

# Attach a managed policy to the group
aws --endpoint $AWS_ENDPOINT iam attach-group-policy \
  --group-name developers \
  --policy-arn arn:aws:iam:::policy/ReadOnlyPolicy

# List groups
aws --endpoint $AWS_ENDPOINT iam list-groups

# List group members
aws --endpoint $AWS_ENDPOINT iam get-group --group-name developers

# List policies attached to a group
aws --endpoint $AWS_ENDPOINT iam list-attached-group-policies --group-name developers

# List groups a user belongs to
aws --endpoint $AWS_ENDPOINT iam list-groups-for-user --user-name alice

# Remove user from group
aws --endpoint $AWS_ENDPOINT iam remove-user-from-group --group-name developers --user-name alice

# Detach policy from group
aws --endpoint $AWS_ENDPOINT iam detach-group-policy \
  --group-name developers \
  --policy-arn arn:aws:iam:::policy/ReadOnlyPolicy

# Delete group (must have no members or policies)
aws --endpoint $AWS_ENDPOINT iam delete-group --group-name developers
```

---

## Configuration Storage

IAM configurations are stored on the filer at `/etc/iam/identity.json`. Changes are automatically propagated to all S3 servers subscribed to filer metadata events.

You can view the current configuration:

```bash
echo 's3.configure' | weed shell
```

---

## Related Documentation

- [AWS IAM CLI](./AWS-IAM-CLI.md) - AWS CLI examples for IAM operations
- [S3 Credentials](./S3-Credentials.md) - Managing S3 access credentials
- [S3 Configuration](./S3-Configuration.md) - S3 server configuration options
- [Amazon S3 API](./Amazon-S3-API.md) - S3 API compatibility
