---
id: S3-Object-Lock-and-Retention
title: "S3 Object Lock and Retention"
sidebar_label: "S3 Object Lock and Retention"
---

# S3 Object Lock and Retention

SeaweedFS provides comprehensive support for Amazon S3 Object Lock functionality, including object versioning, retention policies, legal holds, and WORM (Write Once Read Many) compliance features.

## Overview

Object Lock is a feature that allows you to store objects using a WORM (Write Once Read Many) model. It helps prevent objects from being deleted or overwritten for a fixed amount of time or indefinitely. Object Lock works in conjunction with versioning and is enabled at the bucket level.

## Prerequisites

- **Versioning Required**: Object Lock can only be enabled on buckets that have versioning enabled
- **Immutable Setting**: Object Lock can only be enabled when creating a bucket, not on existing buckets
- **S3 API**: All Object Lock operations are available through the S3 API

### Configuration
```bash
export S3_ENDPOINT=http://localhost:8333
```

## Key Features

### 1. Retention Modes

#### Governance Mode
- Objects are protected from deletion or modification by most users
- Users with `s3:BypassGovernanceRetention` permission can override protection
- Admin users can always bypass governance retention
- Suitable for internal compliance and governance requirements

#### Compliance Mode
- Objects cannot be deleted or modified by any user, including the root user
- Retention periods cannot be shortened
- Provides the highest level of protection
- Suitable for regulatory compliance requirements

### 2. Legal Hold
- Independent protection mechanism that can be applied to any object
- When enabled, objects cannot be deleted or modified until the legal hold is removed
- Can be used alongside retention policies
- Useful for litigation, investigation, or audit requirements



## API Support

SeaweedFS implements the complete S3 Object Lock API:

### Bucket-Level Operations
- `GET /?object-lock` - Get bucket Object Lock configuration
- `PUT /?object-lock` - Set bucket Object Lock configuration

### Object-Level Operations
- `GET /{object}?retention` - Get object retention settings
- `PUT /{object}?retention` - Set object retention settings
- `GET /{object}?legal-hold` - Get object legal hold status
- `PUT /{object}?legal-hold` - Set object legal hold status

### Versioning Operations
- `GET /?versioning` - Get bucket versioning status
- `PUT /?versioning` - Set bucket versioning status
- `GET /?versions` - List object versions

## Setup and Configuration

### 1. Enable Object Lock on Bucket Creation

Object Lock must be enabled when creating a bucket:

```bash
# Create bucket with Object Lock enabled
aws --endpoint-url $S3_ENDPOINT s3api create-bucket \
    --bucket my-secure-bucket \
    --object-lock-enabled-for-bucket

# Enable versioning (automatically done with Object Lock)
aws --endpoint-url $S3_ENDPOINT s3api put-bucket-versioning \
    --bucket my-secure-bucket \
    --versioning-configuration Status=Enabled
```

### 2. Configure Governance Bypass Permissions

Grant users permission to bypass governance retention:

```json
{
    "identities": [
        {
            "name": "compliance-admin",
            "credentials": [
                {
                    "accessKey": "admin123",
                    "secretKey": "secret123"
                }
            ],
            "actions": [
                "Read:my-secure-bucket/*",
                "Write:my-secure-bucket/*",
                "BypassGovernanceRetention:my-secure-bucket/*"
            ]
        }
    ]
}
```

## Usage Examples

### 1. Object Retention

#### Set Governance Retention
```bash
# Set 30-day governance retention
aws --endpoint-url $S3_ENDPOINT s3api put-object-retention \
    --bucket my-secure-bucket \
    --key important-document.pdf \
    --retention '{
        "Mode": "GOVERNANCE",
        "RetainUntilDate": "2024-12-31T23:59:59Z"
    }'
```

#### Set Compliance Retention
```bash
# Set 7-year compliance retention
aws --endpoint-url $S3_ENDPOINT s3api put-object-retention \
    --bucket my-secure-bucket \
    --key regulatory-record.json \
    --retention '{
        "Mode": "COMPLIANCE",
        "RetainUntilDate": "2031-01-01T00:00:00Z"
    }'
```

#### Get Object Retention
```bash
aws --endpoint-url $S3_ENDPOINT s3api get-object-retention \
    --bucket my-secure-bucket \
    --key important-document.pdf
```

### 2. Legal Hold

#### Apply Legal Hold
```bash
aws --endpoint-url $S3_ENDPOINT s3api put-object-legal-hold \
    --bucket my-secure-bucket \
    --key investigation-file.doc \
    --legal-hold Status=ON
```

#### Remove Legal Hold
```bash
aws --endpoint-url $S3_ENDPOINT s3api put-object-legal-hold \
    --bucket my-secure-bucket \
    --key investigation-file.doc \
    --legal-hold Status=OFF
```

#### Check Legal Hold Status
```bash
aws --endpoint-url $S3_ENDPOINT s3api get-object-legal-hold \
    --bucket my-secure-bucket \
    --key investigation-file.doc
```

### 3. Governance Bypass

#### Delete Object with Governance Bypass
```bash
# User with bypass permission can delete governance-protected objects
aws --endpoint-url $S3_ENDPOINT s3api delete-object \
    --bucket my-secure-bucket \
    --key document.pdf \
    --bypass-governance-retention
```

#### Bulk Delete with Governance Bypass
```bash
# Delete multiple objects with governance bypass
aws --endpoint-url $S3_ENDPOINT s3api delete-objects \
    --bucket my-secure-bucket \
    --delete file://delete-objects.json \
    --bypass-governance-retention
```

### 4. Object Versioning

#### List Object Versions
```bash
aws --endpoint-url $S3_ENDPOINT s3api list-object-versions \
    --bucket my-secure-bucket \
    --prefix documents/
```

#### Get Specific Version
```bash
aws --endpoint-url $S3_ENDPOINT s3api get-object \
    --bucket my-secure-bucket \
    --key document.pdf \
    --version-id "3/L4kqtJlcpXroDTDmpUMLUo"
```

#### Delete Specific Version
```bash
aws --endpoint-url $S3_ENDPOINT s3api delete-object \
    --bucket my-secure-bucket \
    --key document.pdf \
    --version-id "3/L4kqtJlcpXroDTDmpUMLUo"
```

## Permission System

### IAM Actions

SeaweedFS supports the following S3 IAM actions for Object Lock in identity-based permissions:

- `s3:GetObjectRetention` - Get object retention settings
- `s3:PutObjectRetention` - Set object retention settings
- `s3:GetObjectLegalHold` - Get object legal hold status
- `s3:PutObjectLegalHold` - Set object legal hold status
- `s3:BypassGovernanceRetention` - Bypass governance retention
- `s3:GetBucketObjectLockConfiguration` - Get bucket Object Lock configuration
- `s3:PutBucketObjectLockConfiguration` - Set bucket Object Lock configuration

### Identity-Based Permissions

Configure user permissions in `identities.json`:

```json
{
    "identities": [
        {
            "name": "read-only-user",
            "credentials": [{"accessKey": "ro123", "secretKey": "secret123"}],
            "actions": [
                "Read:my-secure-bucket/*",
                "GetObjectRetention:my-secure-bucket/*",
                "GetObjectLegalHold:my-secure-bucket/*"
            ]
        },
        {
            "name": "compliance-admin",
            "credentials": [{"accessKey": "admin123", "secretKey": "secret123"}],
            "actions": [
                "Read:my-secure-bucket/*",
                "Write:my-secure-bucket/*",
                "Admin:my-secure-bucket/*",
                "BypassGovernanceRetention:my-secure-bucket/*"
            ]
        }
    ]
}
```

## Error Handling

### Common Error Scenarios

1. **Object Lock Not Enabled**
   - Error: `InvalidRequest`
   - Solution: Enable Object Lock when creating the bucket

2. **Versioning Not Enabled**
   - Error: `InvalidRequest`
   - Solution: Enable versioning before configuring Object Lock

3. **Governance Bypass Not Permitted**
   - Error: `AccessDenied`
   - Solution: Grant `s3:BypassGovernanceRetention` permission

4. **Compliance Mode Cannot Be Bypassed**
   - Error: `AccessDenied`
   - Solution: Wait for retention period to expire

5. **Object Under Legal Hold**
   - Error: `AccessDenied`
   - Solution: Remove legal hold before deleting/modifying

### Error Response Examples

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Error>
    <Code>AccessDenied</Code>
    <Message>Object is under COMPLIANCE mode retention and cannot be deleted</Message>
    <Resource>/my-secure-bucket/protected-file.pdf</Resource>
    <RequestId>12345</RequestId>
</Error>
```

## WORM Compliance

SeaweedFS Object Lock provides WORM (Write Once Read Many) compliance:

### Features
- **Immutable Objects**: Once written, objects cannot be modified
- **Retention Enforcement**: Objects cannot be deleted before retention expiry
- **Legal Hold Support**: Additional protection for litigation/investigation
- **Audit Trail**: All access attempts are logged for compliance

### Use Cases
- **Regulatory Compliance**: Financial records, healthcare data, legal documents
- **Data Archiving**: Long-term storage with guaranteed integrity
- **Backup Protection**: Prevent accidental or malicious deletion
- **Audit Requirements**: Maintain evidence for legal proceedings

## Best Practices

### 1. Retention Planning
- **Start with Governance**: Use governance mode for testing and development
- **Compliance for Production**: Use compliance mode for regulatory requirements
- **Gradual Implementation**: Start with short retention periods and increase gradually

### 2. Permission Management
- **Principle of Least Privilege**: Grant minimum required permissions
- **Separate Roles**: Different permissions for different use cases
- **Regular Audits**: Review and update permissions regularly

### 3. Monitoring and Alerting
- **Monitor Bypass Attempts**: Track governance bypass usage
- **Retention Expiry Alerts**: Set up alerts for expiring retention periods
- **Failed Access Attempts**: Monitor and investigate access denials

### 4. Backup and Recovery
- **Multiple Copies**: Maintain backups of Object Lock configurations
- **Cross-Region Replication**: Replicate to different regions for disaster recovery
- **Version Management**: Keep track of object versions and their retention status

## Performance Considerations

### Storage Efficiency
- **Versioning Overhead**: Each version consumes storage space
- **Retention Metadata**: Minimal overhead for Object Lock metadata
- **Cleanup Strategies**: Plan for version cleanup after retention expires

### Access Patterns
- **Read-Heavy Workloads**: Object Lock is optimized for read operations
- **Write-Once Pattern**: Best suited for write-once, read-many scenarios
- **Batch Operations**: Use batch operations for bulk retention management

## Limitations

### Current Limitations
- **Bucket-Level Only**: Object Lock must be enabled during bucket creation
- **No Modification**: Existing buckets cannot be converted to Object Lock
- **Retention Limits**: Maximum 100 years retention period
- **Version Limits**: Consider version proliferation in high-write scenarios

### AWS Compatibility
SeaweedFS Object Lock is fully compatible with AWS S3 Object Lock:
- Same API endpoints and parameters
- Identical error responses
- Compatible with AWS CLI and SDKs
- Consistent behavior across governance and compliance modes

## Troubleshooting

### Common Issues

1. **Cannot Enable Object Lock**
   - Check if versioning is enabled
   - Ensure bucket is being created (not existing)
   - Verify permissions for bucket operations

2. **Retention Settings Not Applied**
   - Verify Object Lock is enabled on bucket
   - Check retention date format (ISO 8601)
   - Ensure retention mode is valid (GOVERNANCE/COMPLIANCE)

3. **Governance Bypass Fails**
   - Verify user has `s3:BypassGovernanceRetention` permission
   - Check if bypass header is included in request
   - Ensure object is in GOVERNANCE mode (not COMPLIANCE)

### Debug Commands

```bash
# Check bucket Object Lock configuration
aws --endpoint-url $S3_ENDPOINT s3api get-object-lock-configuration --bucket my-secure-bucket

# Check bucket versioning status
aws --endpoint-url $S3_ENDPOINT s3api get-bucket-versioning --bucket my-secure-bucket

# Check object retention
aws --endpoint-url $S3_ENDPOINT s3api get-object-retention --bucket my-secure-bucket --key file.pdf

# Check legal hold status
aws --endpoint-url $S3_ENDPOINT s3api get-object-legal-hold --bucket my-secure-bucket --key file.pdf
```

## Migration Guide

### From Non-Object Lock Buckets

1. **Create New Bucket**: Create new bucket with Object Lock enabled
2. **Copy Data**: Use `aws --endpoint-url $S3_ENDPOINT s3 sync` to copy data to new bucket
3. **Apply Retention**: Set retention policies on copied objects
4. **Update Applications**: Update applications to use new bucket
5. **Cleanup**: Remove old bucket after validation

### From Other S3 Providers

Object Lock configurations can be migrated using standard S3 API calls:

```bash
# Export current configuration
aws --endpoint-url $S3_ENDPOINT s3api get-object-lock-configuration --bucket source-bucket > config.json

# Apply to SeaweedFS bucket
aws --endpoint-url $S3_ENDPOINT s3api put-object-lock-configuration \
    --bucket target-bucket \
    --object-lock-configuration file://config.json
```



## Related Documentation

- [S3 API FAQ](./S3-API-FAQ.md)
- [Amazon S3 API](./Amazon-S3-API.md)
- [Security Configuration](./Security-Configuration.md)
- [Production Setup](./Production-Setup.md)

## Support

For issues or questions about Object Lock features:
- GitHub Issues: [SeaweedFS Issues](https://github.com/seaweedfs/seaweedfs/issues)
- Community Forum: [SeaweedFS Discussions](https://github.com/seaweedfs/seaweedfs/discussions)
- Documentation: [SeaweedFS Wiki](https://github.com/seaweedfs/seaweedfs/wiki) 