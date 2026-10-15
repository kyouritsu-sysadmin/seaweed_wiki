---
id: S3-Policy-Conditions
title: "S3 Policy Conditions"
sidebar_label: "S3 Policy Conditions"
---

# S3 Policy Conditions

SeaweedFS supports AWS S3-compatible policy conditions for fine-grained access control based on request context such as source IP, transport security, time, and request headers.

## Overview

Conditions allow you to restrict when a policy statement applies. They are used in bucket policies and IAM policies to enforce rules like "allow access only from a specific IP range" or "require HTTPS".

A condition block has the form:

```json
{
  "Condition": {
    "<operator>": {
      "<condition-key>": ["<value1>", "<value2>"]
    }
  }
}
```

Multiple operators within a `Condition` block are ANDed together. Multiple values for a single key are ORed.

## Supported Condition Operators

### String Operators

| Operator | Description |
|----------|-------------|
| `StringEquals` | Exact case-sensitive match |
| `StringNotEquals` | Negated exact match |
| `StringLike` | Case-sensitive match with `*` and `?` wildcards |
| `StringNotLike` | Negated wildcard match |

### Numeric Operators

| Operator | Description |
|----------|-------------|
| `NumericEquals` | Equal |
| `NumericNotEquals` | Not equal |
| `NumericLessThan` | Less than |
| `NumericLessThanEquals` | Less than or equal |
| `NumericGreaterThan` | Greater than |
| `NumericGreaterThanEquals` | Greater than or equal |

### Date Operators

Date values must be in RFC 3339 format (e.g., `2025-01-01T00:00:00Z`).

| Operator | Description |
|----------|-------------|
| `DateEquals` | Exact date match |
| `DateNotEquals` | Negated date match |
| `DateLessThan` | Before date |
| `DateLessThanEquals` | Before or at date |
| `DateGreaterThan` | After date |
| `DateGreaterThanEquals` | After or at date |

### IP Address Operators

Values can be individual IPs or CIDR ranges (e.g., `192.168.1.0/24`).

| Operator | Description |
|----------|-------------|
| `IpAddress` | Source IP is within the specified range |
| `NotIpAddress` | Source IP is not within the specified range |

### Other Operators

| Operator | Description |
|----------|-------------|
| `Bool` | Boolean match (`"true"` or `"false"`) |
| `ArnEquals` | Exact ARN match |
| `ArnLike` | ARN match with wildcards |
| `Null` | Check whether a key is present (`"true"` = key absent, `"false"` = key present) |

### Set Operators

Prefix any string operator with `ForAnyValue:` or `ForAllValues:` for multi-valued keys:

- `ForAnyValue:StringEquals` - at least one value matches
- `ForAllValues:StringEquals` - all values match

## Supported Condition Keys

### AWS Global Context Keys

| Key | Type | Description |
|-----|------|-------------|
| `aws:SourceIp` | IP | Client IP address (supports CIDR) |
| `aws:SecureTransport` | Bool | `true` if the request was sent over HTTPS |
| `aws:CurrentTime` | Date | Current time in RFC 3339 format |
| `aws:UserAgent` | String | Client User-Agent header |
| `aws:Referer` | String | HTTP Referer header |
| `aws:username` | String | Username from principal ARN |
| `aws:userid` | String | User ID from principal ARN |
| `aws:PrincipalAccount` | String | Account ID from principal ARN |
| `aws:principaltype` | String | Principal type (`IAMUser`, `IAMRole`, `AssumedRole`) |
| `aws:PrincipalArn` | String | Full principal ARN |
| `aws:FederatedProvider` | String | Federated identity provider |
| `aws:PrincipalServiceName` | String | Service principal name |

### S3-Specific Keys

| Key | Type | Description |
|-----|------|-------------|
| `s3:prefix` | String | Prefix parameter from list operations |
| `s3:delimiter` | String | Delimiter parameter from list operations |
| `s3:max-keys` | Numeric | Max keys parameter from list operations |
| `s3:ExistingObjectTag/&lt;key&gt;` | String | Value of an existing object tag |
| `s3:RequestMethod` | String | HTTP method (GET, PUT, POST, DELETE) |
| `s3:authType` | String | Auth type (`REST-HEADER` or `REST-QUERY-STRING`) |

| `s3:x-amz-*` | String | Any `x-amz-*` request header (e.g., `s3:x-amz-server-side-encryption`) |

### Identity Provider Keys

| Key | Type | Description |
|-----|------|-------------|
| `jwt:preferred_username` | String | Username from JWT token |
| `jwt:sub` | String | Subject from JWT token |
| `jwt:iss` | String | Issuer from JWT token |
| `jwt:aud` | String | Audience from JWT token |
| `oidc:sub` | String | Subject from OIDC token |
| `oidc:aud` | String | Audience from OIDC token |
| `oidc:iss` | String | Issuer from OIDC token |
| `oidc:&lt;claim&gt;` | String | Any custom OIDC claim (e.g., `oidc:roles`, `oidc:groups`) |
| `saml:username` | String | Username from SAML assertion |
| `saml:sub` | String | Subject from SAML assertion |
| `saml:aud` | String | Audience from SAML assertion |
| `saml:iss` | String | Issuer from SAML assertion |
| `ldap:username` | String | Username from LDAP |
| `ldap:dn` | String | Distinguished name from LDAP |
| `ldap:&lt;attribute&gt;` | String | Any LDAP attribute |

## Source IP Handling

By default, the `aws:SourceIp` condition key is resolved from the **direct TCP peer address** (`RemoteAddr`), matching AWS S3 semantics. Forwarding headers (`X-Forwarded-For`, `X-Real-IP`) are intentionally ignored — without an explicit allowlist they are client-controlled and spoofable, which would let a caller behind a private-looking peer bypass any `IpAddress`/`NotIpAddress` restriction.

### Trusted Proxy Allowlist

When SeaweedFS runs behind a reverse proxy, configure a trusted-proxy allowlist in `security.toml` so that forwarded headers are honored only from known proxies:

```toml
[s3.trusted_proxies]
white_list = "10.10.10.0/24"  # comma separated; bare IPs or CIDRs
```

Can also be set via the environment variable `WEED_S3_TRUSTED_PROXIES_WHITE_LIST`. Reloaded on `SIGHUP`.

When the direct TCP peer is in the allowlist:
1. `X-Forwarded-For` is walked right-to-left, skipping trusted hops, to find the first non-trusted (public) IP
2. If all hops are trusted, the leftmost valid IP is used
3. `X-Real-IP` is used as a fallback when `X-Forwarded-For` is absent or malformed

When the direct TCP peer is **not** in the allowlist (or no allowlist is configured), forwarded headers are ignored and the direct peer address is used.

## Examples

### Restrict Access by IP Address

Allow reads only from your office network:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::my-bucket/*",
      "Condition": {
        "IpAddress": {
          "aws:SourceIp": ["10.0.0.0/8", "192.168.1.0/24"]
        }
      }
    }
  ]
}
```

Deny access from a specific IP range:

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
        "NotIpAddress": {
          "aws:SourceIp": "203.0.113.0/24"
        }
      }
    }
  ]
}
```

### Require HTTPS

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
        "Bool": {
          "aws:SecureTransport": "false"
        }
      }
    }
  ]
}
```

### Time-Based Access

Allow access only during a specific window:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::my-bucket/*",
      "Condition": {
        "DateGreaterThan": {
          "aws:CurrentTime": "2025-01-01T00:00:00Z"
        },
        "DateLessThan": {
          "aws:CurrentTime": "2025-12-31T23:59:59Z"
        }
      }
    }
  ]
}
```

### Require Encryption Header

```json
{
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
}
```

### Tag-Based Access Control

Allow deletion only if the object is tagged as deletable:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:DeleteObject",
      "Resource": "arn:aws:s3:::my-bucket/*",
      "Condition": {
        "StringEquals": {
          "s3:ExistingObjectTag/status": "deletable"
        }
      }
    }
  ]
}
```

### Combining Multiple Conditions

Multiple operators are ANDed — all must be true:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::my-bucket/*",
      "Condition": {
        "IpAddress": {
          "aws:SourceIp": "192.168.1.0/24"
        },
        "Bool": {
          "aws:SecureTransport": "true"
        },
        "DateGreaterThan": {
          "aws:CurrentTime": "2025-01-01T00:00:00Z"
        }
      }
    }
  ]
}
```

## Policy Evaluation Logic

Conditions follow AWS-compatible evaluation order:

1. **Explicit Deny** — if any statement with a matching condition denies, access is denied
2. **Explicit Allow** — if a statement with a matching condition allows, access is allowed
3. **Default Deny** — if no statement matches, access is denied

## See Also

- [S3 Bucket Policies](./S3-Bucket-Policies.md) — Managing bucket policies
- [S3 Policy Variables](./S3-Policy-Variables.md) — Dynamic policy variables
- [S3 Credentials](./S3-Credentials.md) — S3 authentication
- [Amazon IAM API](./Amazon-IAM-API.md) — IAM API support
- [OIDC Integration](./OIDC-Integration.md) — JWT-based authentication
