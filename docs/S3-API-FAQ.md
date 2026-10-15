---
id: S3-API-FAQ
title: "S3 API FAQ"
sidebar_label: "S3 API FAQ"
---

# FAQ

## Can not upload due to "no free volumes left"

The symptom is similar to https://github.com/seaweedfs/seaweedfs/issues/1631 where the logs show
```
Nov 20 18:49:37 s2375.j weed[31818]: E1120 18:49:37 31818 filer_server_handlers_write.go:42] failing to assign a file id: rpc error: code = Unknown desc = No free volumes left!
Nov 20 18:49:37 s2375.j weed[31818]: I1120 18:49:37 31818 common.go:53] response method:PUT URL:/buckets/dev-passport-video-recordings/02342a46-7435-b698-2437-c778db34ef59.mp4 with httpStatus:500 and JSON:{"error":"rpc error: code = Unknown desc = No free volumes left!"}
Nov 20 18:49:37 s2375.j weed[31818]: E1120 18:49:37 31818 s3api_object_handlers.go:336] upload to filer error: rpc error: code = Unknown desc = No free volumes left!
```

Each bucket will create one collection, with at least 7 volumes by default, and each volume is pre-allocated with a large size, usually 30GB.

There are 2 ways to fix this. 
* Reduce the global volume size by adjusting `-volumeSizeLimitMB` in `weed master` CLI option. 
* Reduce the number of volumes to grow when a collection runs out of volumes. You can configure the per bucket storage this way in `weed shell`:

```
> fs.configure -locationPrefix=/buckets/ -volumeGrowthCount=1 -apply
```

This will add 1 physical volume when existing volumes are full. If using replication, you will need to add more volumes, so that it is a multiple of the number of replicas:
```
 fs.configure -locationPrefix=/buckets/ -replication=001 -volumeGrowthCount=2 -apply
```

See  https://github.com/seaweedfs/seaweedfs/wiki/Path-Specific-Configuration

Or you can change volume growth count in master config file (`weed scaffold -config=master`), You have to change `copy_x` values.

## How to speed up bucket deletion?

One common unexpected problem is the deletion can be slow. To delete a file, we need to delete the file content on the volume servers and delete the file entry from the filer store. It is almost the same amount of work as adding a file. If there are millions of files, it can take a long time to delete.

When you need to create large buckets and delete them often, you may choose `leveldb3` as the filer store, or any other stores that supports **Fast Bucket Deletion** in https://github.com/seaweedfs/seaweedfs/wiki/Filer-Stores

`leveldb3` can automatically create a separate LevelDB instance for each bucket. 
So bucket deletion is as simple as deleting the LevelDB instance files and the collection of volume files.

Having separate LevelDB instance, or separate SQL tables, will help to isolate the storage and improve performance also.

## Setting TTL

It is possible to set a TTL for a specific directory using the S3 API. They are set using [`PutBucketLifecycleConfiguration`](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketLifecycleConfiguration.html).

Example of a JSON configuration is below.  It is an equivalent of calling the following with `weed shell`.
```
fs.configure -locationPrefix  /buckets/f341868e-baff-4e20-896a-08bc148e32f9/my-directory-whose-files-will-expire-in-20-days -ttl 20d -apply
```
:

```
{
  "Rules": [
    {
      "Status": "Enabled",
      "Filter": {
        "Prefix": "my-directory-whose-files-will-expire-in-20-days"
      },
      "Expiration": {
        "Days": 20
      }
    }
  ]
}
```
Save that in a `.json` file and call it, for example, via the `aws` cli (ensure `$S3_ENDPOINT` is set, e.g., `export S3_ENDPOINT=http://localhost:8333`):

```bash
BUCKET_NAME=f341868e-baff-4e20-896a-08bc148e32f9
aws --endpoint-url $S3_ENDPOINT s3api put-bucket-lifecycle-configuration --bucket $BUCKET_NAME --lifecycle-configuration "file://lifecycle_policy.json"
```

Note that you don't need to add the part `/buckets/$BUCKET_NAME` in the configurations "Filter.Prefix" (contrary to using `fs.configure`, this is taken care of for you in the S3 API.

## Does SeaweedFS support S3 object versioning?

Yes, SeaweedFS supports S3 object versioning. You can enable versioning on a bucket using the `PutBucketVersioning` API. When enabled, SeaweedFS will store multiple versions of an object in the same bucket, providing data protection against accidental deletion or modification.

Key features supported:
- Enable/suspend versioning on buckets
- List all versions of objects
- Get, copy, and delete specific versions
- Delete markers for soft deletion

For detailed documentation and examples, see [Amazon S3 API#s3-object-versioning](./Amazon-S3-API.md#s3-object-versioning).

## How does versioning affect storage usage?

When versioning is enabled, each uploaded object creates a new version instead of overwriting the existing one. This means:
- Storage usage will increase as you accumulate versions
- All versions are preserved until explicitly deleted
- Delete operations create delete markers (soft delete) rather than immediately removing data

To manage storage growth, you should:
- Monitor storage usage regularly
- Implement lifecycle policies to automatically clean up old versions
- Use version-specific deletions for permanent removal when needed

## Does SeaweedFS support encrypted range requests?

Yes. Range requests work just fine with encrypted objects across all SSE modes:
- **SSE-KMS**: Supported
- **SSE-C**: Supported
- **SSE-S3**: Supported

## Does SeaweedFS support bucket default encryption?

Yes. You can set a bucket-level default encryption policy using the standard S3 bucket encryption API. Uploads without explicit encryption headers will follow the bucket policy. This applies to SSE-KMS and SSE-S3.

For setup guides, see [Server-Side-Encryption](./Server-Side-Encryption.md).

## Does SeaweedFS support S3 Object Lock?

Yes! SeaweedFS provides comprehensive support for S3 Object Lock features, including:

### Object Lock Features
- **Governance Mode**: Objects can be deleted/modified by users with `s3:BypassGovernanceRetention` permission
- **Compliance Mode**: Objects cannot be deleted/modified by any user until retention expires
- **Legal Hold**: Objects cannot be deleted/modified until legal hold is explicitly removed

### Supported APIs
- `GetObjectLockConfiguration` / `PutObjectLockConfiguration` (bucket-level)
- `GetObjectRetention` / `PutObjectRetention` (object-level)
- `GetObjectLegalHold` / `PutObjectLegalHold` (object-level)
- Governance bypass via `x-amz-bypass-governance-retention` header

### Requirements
- Object Lock must be enabled when creating the bucket (cannot be added later)
- Versioning is automatically enabled and required for Object Lock
- Compatible with standard AWS S3 tools and SDKs

For complete documentation, examples, and best practices, see [S3 Object Lock and Retention](./S3-Object-Lock-and-Retention.md).

## What's the difference between Governance and Compliance modes?

**Governance Mode**:
- Designed for internal governance and compliance requirements
- Can be bypassed by users with proper permissions (`s3:BypassGovernanceRetention`)
- Admin users can always bypass governance retention
- Suitable for testing and development environments

**Compliance Mode**:
- Designed for regulatory compliance (SEC, FINRA, etc.)
- Cannot be bypassed by any user, including root/admin
- Provides the highest level of data protection
- Suitable for production environments with strict compliance requirements

Both modes prevent accidental deletion and provide audit trails for compliance purposes.

## S3 authentication fails when using reverse proxy

### Symptom

When accessing SeaweedFS S3 API through a reverse proxy, you might encounter signature verification errors such as:
- `SignatureDoesNotMatch` errors
- Authentication failures for presigned URLs
- Inconsistent behavior between direct access and proxied access

### Common Causes and Solutions

**1. Missing X-Forwarded-Host header**

The reverse proxy must set the `X-Forwarded-Host` header to preserve the original host information for signature calculation.

```nginx
proxy_set_header X-Forwarded-Host $host;
```

**2. URL path prefix stripping without X-Forwarded-Prefix**

If your reverse proxy strips URL prefixes (e.g., `/s3/bucket/object` → `/bucket/object`), you must set the `X-Forwarded-Prefix` header:

```nginx
# For /s3/ subpath
location /s3/ {
    proxy_set_header X-Forwarded-Prefix /s3;
    rewrite ^/s3/(.*) /$1 break;
    proxy_pass http://seaweedfs;
}
```

**3. Request buffering enabled**

Nginx request buffering can interfere with chunked transfer encoding and signature verification:

```nginx
proxy_request_buffering off;
proxy_buffering off;
```

**4. Missing or incorrect forwarded headers**

Ensure all necessary headers are forwarded:

```nginx
proxy_set_header Host $host;
proxy_set_header X-Forwarded-Host $host;
proxy_set_header X-Forwarded-Port $server_port;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-For $remote_addr;
```

**Note**: SeaweedFS automatically combines `X-Forwarded-Host` and `X-Forwarded-Port` for signature verification, omitting standard ports (80 for HTTP, 443 for HTTPS).

### Testing Your Configuration

You can test your reverse proxy configuration using AWS CLI:

```bash
# Test basic bucket listing
aws --endpoint-url $S3_ENDPOINT s3 ls

# Test presigned URL generation and access
aws --endpoint-url $S3_ENDPOINT s3 presign s3://test-bucket/test-object
```

For detailed configuration examples, see the [S3-Nginx-Proxy](./S3-Nginx-Proxy.md) documentation.

## TLS error: "client sent an HTTP request to an HTTPS server"

SeaweedFS has two separate communication layers:
- **gRPC (Control Plane)**: Metadata operations - configured via `[grpc.*]`
- **HTTP/HTTPS (Data Plane)**: File data uploads/downloads - configured via `[https.*]`

If you see this error when S3 API communicates with a TLS-enabled Filer, enable HTTPS client mode:

```toml
[https.filer]
cert = "/path/to/filer.crt"
key = "/path/to/filer.key"
ca = "/path/to/ca.crt"

[https.client]
enabled = true
cert = "/path/to/client.crt"
key = "/path/to/client.key"
ca = "/path/to/ca.crt"
```

The `[https.filer]` makes the Filer accept HTTPS, while `[https.client]` with `enabled = true` makes clients (S3 API, mount, etc.) use HTTPS for data operations. See [Security-Overview](./Security-Overview.md) for architecture details and [Security-Configuration](./Security-Configuration.md) for configuration reference.


