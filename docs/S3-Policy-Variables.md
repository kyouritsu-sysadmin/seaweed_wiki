---
id: S3-Policy-Variables
title: "S3 Policy Variables"
sidebar_label: "S3 Policy Variables"
---

# S3 Policy Variables

SeaweedFS supports AWS S3 policy variables, allowing you to create dynamic, flexible bucket policies that adapt based on the requester's identity and context.

## Overview

Policy variables enable you to write a single policy that applies to multiple users by substituting values at request time. Instead of creating separate policies for each user, you can use variables like `&#36;&#123;aws:username&#125;` that get replaced with the actual username during policy evaluation.

## Supported Variable Types

### AWS Context Variables

These variables are automatically extracted from the principal ARN:

| Variable | Description | Available For |
|----------|-------------|---------------|
| `&#36;&#123;aws:username&#125;` | Username or role name | IAM Users, IAM Roles, Assumed Roles |
| `&#36;&#123;aws:userid&#125;` | User ID | IAM Users, Assumed Roles only |
| `&#36;&#123;aws:principaltype&#125;` | Type of principal | IAM Users, IAM Roles, Assumed Roles |
| `&#36;&#123;aws:PrincipalAccount&#125;` | AWS account ID | IAM Users, Assumed Roles only |

#### Principal Type Values

- `IAMUser` - For IAM user ARNs (`arn:aws:iam::account:user/username`)
- `IAMRole` - For IAM role ARNs (`arn:aws:iam::account:role/rolename`)
- `AssumedRole` - For assumed role ARNs (`arn:aws:sts::account:assumed-role/role/session`)

> **Important**: IAM Roles do NOT have `aws:userid` or `aws:PrincipalAccount` variables. These are only available for IAM Users and Assumed Roles.

### JWT Claim Variables

Access any JWT claim using the `&#36;&#123;jwt:claim-name&#125;` syntax — `claim-name` can be any claim present in the JWT issued by the identity provider (e.g., OIDC ID tokens, GitLab CI job tokens). Numeric and boolean claims are stringified, so values like `project_id: 301` expand to `"301"`.

| Variable | Description |
|----------|-------------|
| `&#36;&#123;jwt:sub&#125;` | Subject (user ID) from JWT |
| `&#36;&#123;jwt:iss&#125;` | Issuer of the JWT |
| `&#36;&#123;jwt:aud&#125;` | Audience of the JWT |
| `&#36;&#123;jwt:preferred_username&#125;` | Preferred username (common OIDC claim) |
| `&#36;&#123;jwt:email&#125;` | Email address from JWT |
| `&#36;&#123;jwt:&lt;any-other-claim&gt;&#125;` | Any other claim carried by the JWT (e.g., `project_path`, `department`, `tenant_id`) |

> If a claim is missing from the JWT, the `&#36;&#123;jwt:...&#125;` placeholder is left in place so the policy statement does not match — instead of silently expanding to an empty string.

#### SAML and OIDC Claim Variables

The same pattern applies for SAML and OIDC prefixes: `&#36;&#123;saml:&lt;claim&gt;&#125;` and `&#36;&#123;oidc:&lt;claim&gt;&#125;` expand from the corresponding attributes on a validated federated assertion.

### LDAP Claim Variables

Access LDAP attributes using the `&#36;&#123;ldap:attribute&#125;` syntax:

| Variable | Description |
|----------|-------------|
| `&#36;&#123;ldap:username&#125;` | LDAP username |
| `&#36;&#123;ldap:dn&#125;` | LDAP distinguished name |
| `&#36;&#123;ldap:*&#125;` | Any custom LDAP attribute |

### S3 Request Variables

Standard S3 condition variables can also be used:

| Variable | Description |
|----------|-------------|
| `&#36;&#123;s3:prefix&#125;` | Prefix parameter from ListBucket |
| `&#36;&#123;aws:SourceIp&#125;` | Source IP address |
| `&#36;&#123;aws:SecureTransport&#125;` | Whether request uses HTTPS |

---

## Usage Examples

### User Isolation with &#36;&#123;aws:username&#125;

Allow each user to access only their own folder:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::my-bucket/${aws:username}/*"
    }
  ]
}
```

When user `alice` makes a request, the policy evaluates as:
- Resource: `arn:aws:s3:::my-bucket/alice/*`

When user `bob` makes a request:
- Resource: `arn:aws:s3:::my-bucket/bob/*`

### Combining Allow and Deny

Explicitly allow own folder and deny everything else:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowOwnFolder",
      "Effect": "Allow",
      "Principal": "*",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::my-bucket/${aws:username}/*"
    },
    {
      "Sid": "DenyOtherFolders",
      "Effect": "Deny",
      "Principal": "*",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "NotResource": "arn:aws:s3:::my-bucket/${aws:username}/*"
    }
  ]
}
```

### JWT Claims in Resources

Use JWT claims for dynamic path isolation:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::uploads/${jwt:preferred_username}/*"
    }
  ]
}
```

### GitLab CI Jobs Uploading to Their Own Project Folder

GitLab CI issues ID tokens whose claims include `project_path`, `namespace_path`, and `project_id` (see the [GitLab ID token docs](https://docs.gitlab.com/ee/ci/secrets/id_token_authentication.html)). A single policy can confine every project to its own prefix:

```json
{
  "name": "GitlabProjectUploadPolicy",
  "document": {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "AllowPutInOwnFolder",
        "Effect": "Allow",
        "Action": ["s3:PutObject"],
        "Resource": ["arn:aws:s3:::softs/${jwt:project_path}/*"]
      }
    ]
  }
}
```

From a `.gitlab-ci.yml`, request an ID token with `aud` matching the S3 gateway's client ID and upload with it:

```yaml
upload:
  image: alpine:latest
  id_tokens:
    SEAWEED_TOKEN:
      aud: "seaweedfs-s3"
  script:
    - apk add -U curl
    - |
      curl -X PUT --fail-with-body \
        -H "Authorization: Bearer $SEAWEED_TOKEN" \
        -T some-file.zip \
        "https://seaweedfs.example.com/softs/${CI_PROJECT_PATH}/some-file.zip"
```

Each project can only write under `softs/&lt;its-own-project-path&gt;/` because the policy resource expands to the requesting token's `project_path` claim.

### Variables in Conditions

Use variables in condition blocks:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::my-bucket",
      "Condition": {
        "StringLike": {
          "s3:prefix": ["${aws:username}/*"]
        }
      }
    }
  ]
}
```

### Account-Based Access Control

Restrict access to specific AWS accounts:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": "arn:aws:s3:::my-bucket/*",
      "Condition": {
        "StringNotEquals": {
          "aws:PrincipalAccount": ["123456789012"]
        }
      }
    },
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": "arn:aws:s3:::my-bucket/*"
    }
  ]
}
```

### LDAP Integration

Use LDAP attributes for access control:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::data/${ldap:username}/*"
    },
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::data/*",
      "Condition": {
        "StringEquals": {
          "ldap:dn": "cn=manager,dc=example,dc=org"
        }
      }
    }
  ]
}
```

---

## Principal ARN Parsing

SeaweedFS automatically extracts variables from principal ARNs:

### IAM User ARN
```
arn:aws:iam::123456789012:user/alice
```
Extracts:
- `aws:username` = `alice`
- `aws:userid` = `alice`
- `aws:principaltype` = `IAMUser`
- `aws:PrincipalAccount` = `123456789012`

### IAM User with Path
```
arn:aws:iam::123456789012:user/division/team/alice
```
Extracts:
- `aws:username` = `alice` (last segment)
- `aws:userid` = `alice`
- `aws:principaltype` = `IAMUser`
- `aws:PrincipalAccount` = `123456789012`

### IAM Role ARN
```
arn:aws:iam::123456789012:role/MyRole
```
Extracts:
- `aws:username` = `MyRole`
- `aws:principaltype` = `IAMRole`

**Note**: IAM Roles do NOT have `aws:userid` or `aws:PrincipalAccount`.

### Assumed Role ARN
```
arn:aws:sts::123456789012:assumed-role/MyRole/session-alice
```
Extracts:
- `aws:username` = `session-alice` (session name)
- `aws:userid` = `session-alice`
- `aws:principaltype` = `AssumedRole`
- `aws:PrincipalAccount` = `123456789012`

---

## Best Practices

### 1. Use Explicit Deny for Security

Combine Allow and Deny statements to prevent unauthorized access:

```json
{
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:*",
      "Resource": "arn:aws:s3:::bucket/${aws:username}/*"
    },
    {
      "Effect": "Deny",
      "Action": "s3:*",
      "NotResource": "arn:aws:s3:::bucket/${aws:username}/*"
    }
  ]
}
```

### 2. Test Policies Thoroughly

Test with different users to ensure variables substitute correctly (ensure `$S3_ENDPOINT` is set, e.g., `export S3_ENDPOINT=http://localhost:8333`):

```bash
# Test as alice
aws --endpoint-url $S3_ENDPOINT s3 cp file.txt s3://bucket/alice/file.txt --profile alice

# Test as bob
aws --endpoint-url $S3_ENDPOINT s3 cp file.txt s3://bucket/bob/file.txt --profile bob

# Verify isolation
aws --endpoint-url $S3_ENDPOINT s3 ls s3://bucket/alice/ --profile bob  # Should fail
```

### 3. Use Conditions for Complex Logic

Combine variables with conditions for fine-grained control:

```json
{
  "Condition": {
    "StringLike": {
      "s3:prefix": ["${aws:username}/*"]
    },
    "StringEquals": {
      "aws:principaltype": "IAMUser"
    }
  }
}
```

### 4. Document Variable Expectations

Clearly document which JWT/LDAP claims your policies expect:

```json
{
  "Comment": "Requires JWT claims: preferred_username, department",
  "Statement": [
    {
      "Resource": "arn:aws:s3:::data/${jwt:department}/${jwt:preferred_username}/*"
    }
  ]
}
```

---

## Troubleshooting

### Variables Not Substituting

**Problem**: Variables appear as literal strings in logs

**Solution**: Ensure the variable exists in the request context. Check:
- Principal ARN format is correct
- JWT claims are present in the token
- LDAP attributes are mapped correctly

### Access Denied Despite Matching Path

**Problem**: User can't access their own folder

**Solution**: Check for conflicting Deny statements. Remember that Deny always wins:

```json
{
  "Statement": [
    {
      "Effect": "Allow",
      "Resource": "arn:aws:s3:::bucket/${aws:username}/*"
    },
    {
      "Effect": "Deny",
      "NotResource": "arn:aws:s3:::bucket/${aws:username}/*"
    }
  ]
}
```

### IAM Role Variables Missing

**Problem**: `aws:userid` or `aws:PrincipalAccount` not available for IAM Roles

**Solution**: This is expected behavior. IAM Roles only have `aws:username` and `aws:principaltype`. Use Assumed Roles if you need these variables.

---

## Related Documentation

- [Amazon S3 API](./Amazon-S3-API.md) - S3 API compatibility
- [S3 Credentials](./S3-Credentials.md) - Managing S3 credentials
- [OIDC Integration](./OIDC-Integration.md) - JWT-based authentication
- [Amazon IAM API](./Amazon-IAM-API.md) - IAM API support
