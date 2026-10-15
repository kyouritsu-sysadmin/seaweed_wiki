---
id: S3-Object-Versioning
title: "S3 Object Versioning"
sidebar_label: "S3 Object Versioning"
---

# S3 Object Versioning

SeaweedFS supports S3 object versioning, which allows you to keep multiple variants of an object in the same bucket. This provides data protection against accidental deletion or modification.

### Configuration
```bash
export S3_ENDPOINT=http://localhost:8333
```

To enable versioning on a bucket, use the `PutBucketVersioning` API:

```bash
aws --endpoint-url $S3_ENDPOINT s3api put-bucket-versioning \
    --bucket my-bucket \
    --versioning-configuration Status=Enabled
```

## Check Versioning Status

To check the versioning status of a bucket:

```bash
aws --endpoint-url $S3_ENDPOINT s3api get-bucket-versioning --bucket my-bucket
```

Response:
```json
{
    "Status": "Enabled"
}
```

## Suspend Versioning

To suspend versioning (not disable completely):

```bash
aws --endpoint-url $S3_ENDPOINT s3api put-bucket-versioning \
    --bucket my-bucket \
    --versioning-configuration Status=Suspended
```

## List Object Versions

To list all versions of objects in a bucket:

```bash
aws --endpoint-url $S3_ENDPOINT s3api list-object-versions --bucket my-bucket
```

Response includes both object versions and delete markers:
```json
{
    "Versions": [
        {
            "Key": "example.txt",
            "VersionId": "v_1234567890abcdef",
            "IsLatest": true,
            "LastModified": "2023-12-01T10:00:00Z",
            "ETag": "\"abcdef1234567890\"",
            "Size": 1024
        }
    ],
    "DeleteMarkers": [
        {
            "Key": "deleted-file.txt",
            "VersionId": "v_fedcba0987654321",
            "IsLatest": true,
            "LastModified": "2023-12-01T11:00:00Z"
        }
    ]
}
```

## Access Specific Versions

### Get a specific version of an object:
```bash
aws --endpoint-url $S3_ENDPOINT s3api get-object \
    --bucket my-bucket \
    --key example.txt \
    --version-id v_1234567890abcdef \
    output.txt
```

### Copy a specific version:
```bash
aws --endpoint-url $S3_ENDPOINT s3api copy-object \
    --copy-source my-bucket/example.txt?versionId=v_1234567890abcdef \
    --bucket my-bucket \
    --key example-copy.txt
```

### Delete a specific version:
```bash
aws --endpoint-url $S3_ENDPOINT s3api delete-object \
    --bucket my-bucket \
    --key example.txt \
    --version-id v_1234567890abcdef
```

## Versioning Behavior

### When Versioning is Enabled:
- **PUT Object**: Creates a new version with a unique version ID
- **GET Object**: Returns the latest version (unless version ID is specified)
- **DELETE Object**: Creates a delete marker (soft delete)
- **DELETE Object with version ID**: Permanently deletes that specific version

### When Versioning is Suspended:
- **PUT Object**: Overwrites the object with version ID "null"
- **GET Object**: Returns the current version
- **DELETE Object**: Permanently deletes the object

### POST Policy Uploads:

Uploads using an S3 POST policy, including presigned POST uploads, follow
the bucket's versioning state:

* Enabled: Creates a new version with a unique version ID and returns it
  in the `x-amz-version-id` response header.
* Suspended: Replaces the null version while preserving existing non-null
  versions. The `x-amz-version-id` response header is omitted.
* Never enabled: Uses the unversioned write path and omits the
  `x-amz-version-id` response header.

POST-created versions can be listed and retrieved using the same APIs
shown above.

Added in [PR #11316](https://github.com/seaweedfs/seaweedfs/pull/11316).

## Storage Layout

SeaweedFS stores versioned objects using the following structure:
```
/buckets/my-bucket/
├── example.txt          # Current version (if versioning suspended)
└── example.txt.versions/
    ├── v_1234567890abcdef  # Version 1
    ├── v_fedcba0987654321  # Version 2
    └── v_abcdef1234567890  # Version 3 (latest)
```

## Limitations

- **Version ID Format**: SeaweedFS generates version IDs in the format `v_&lt;32-char-hex&gt;`
- **Restore Operations**: Only partial support for `RestoreObject` API
- **Lifecycle Policies**: Version-specific lifecycle rules are not fully implemented
- **MFA Delete**: Not currently supported

## Best Practices

1. **Enable versioning before storing important data** to ensure all versions are captured
2. **Monitor storage usage** as versioning can increase storage consumption
3. **Implement lifecycle policies** to automatically clean up old versions
4. **Use version-specific operations** when you need to access historical data
5. **Consider performance impact** when listing many versions of objects 