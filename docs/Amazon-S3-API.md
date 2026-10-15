---
id: Amazon-S3-API
title: "Amazon S3 API"
sidebar_label: "Amazon S3 API"
---

To be compatible with Amazon S3 API, a separate "weed s3" command is provided. This provides much faster access when reading or writing files, compared to operating files on the cloud.

# How It Works

`weed s3` starts a stateless gateway server to bridge the Amazon S3 API to SeaweedFS Filer.
For convenience, `weed server -s3` starts a master, a volume server, a filer, and the S3 gateway. `weed filer -s3` can start a filer and the S3 gateway together also.

Each bucket is stored in one collection, and mapped to folder `/buckets/&lt;bucket_name&gt;` by default. A bucket can be deleted efficiently by deleting the whole collection.

From version 3.51 the collection name is `filerGroup_bucketname` or `bucketname` if filer group is not set.

## Support Many Buckets

Each bucket has its own collection. Usually one collection uses 7 volumes, where each volume is 30GB by default. So if you want to create multiple buckets, you may run out of volumes very quickly unless you have a large disk.

Try to keep the volume size low. For example,
```bash
weed master -volumeSizeLimitMB=1024
```

In addition, you can also configure the per bucket storage this way in `weed shell`:
```bash
fs.configure -locationPrefix=/buckets/ -volumeGrowthCount=1 -apply
```
This will add 1 physical volume when existing volumes are full. If using replication, you will need to add more volumes, so that it is a multiple of the number of replicas:
```bash
fs.configure -locationPrefix=/buckets/ -replication=001 -volumeGrowthCount=2 -apply
```

See [Path Specific Configuration](./Path-Specific-Configuration.md)

## Multiple S3 Nodes

You can start multiple S3 instances pointing to a filer for horizontal scaling. The easiest way is to run filer together with S3:

```bash
weed filer -s3
```

# Supported APIs

The following tables list all standard AWS S3 API operations and their support status in SeaweedFS, using official AWS API operation names.

For IAM action names used in bucket policies (e.g., `s3:ListBucketMultipartUploads`), see [S3 Bucket Policies](./S3-Bucket-Policies.md).

## Bucket Operations

| API Operation | Supported | Notes |
|---|---|---|
| CreateBucket | Yes | |
| DeleteBucket | Yes | Deletes the entire collection |
| HeadBucket | Yes | |
| ListBuckets | Yes | |
| ListDirectoryBuckets | No | S3 Express One Zone |

## Bucket Configuration

| API Operation | Supported | Notes |
|---|---|---|
| GetBucketAcl | Yes | |
| PutBucketAcl | Yes | |
| GetBucketCors | Yes | See [S3 CORS](./S3-CORS.md) |
| PutBucketCors | Yes | |
| DeleteBucketCors | Yes | |
| GetBucketEncryption | Yes | See [Server-Side Encryption](./Server-Side-Encryption.md) |
| PutBucketEncryption | Yes | |
| DeleteBucketEncryption | Yes | |
| GetBucketLifecycleConfiguration | Yes | See [S3 Lifecycle](./S3-Lifecycle.md) |
| PutBucketLifecycleConfiguration | Yes | Transition rules not supported |
| DeleteBucketLifecycle | Yes | |
| GetBucketLocation | Yes | Returns default location |
| GetBucketOwnershipControls | Yes | |
| PutBucketOwnershipControls | Yes | |
| DeleteBucketOwnershipControls | Yes | |
| GetBucketPolicy | Yes | See [S3 Bucket Policies](./S3-Bucket-Policies.md) |
| PutBucketPolicy | Yes | |
| DeleteBucketPolicy | Yes | |
| GetBucketRequestPayment | Yes | Always returns BucketOwner |
| GetBucketTagging | Yes | |
| PutBucketTagging | Yes | |
| DeleteBucketTagging | Yes | |
| GetBucketVersioning | Yes | See [S3 Object Versioning](./S3-Object-Versioning.md) |
| PutBucketVersioning | Yes | |
| GetObjectLockConfiguration | Yes | See [S3 Object Lock and Retention](./S3-Object-Lock-and-Retention.md) |
| PutObjectLockConfiguration | Yes | |
| GetPublicAccessBlock | Yes | |
| PutPublicAccessBlock | Yes | |
| DeletePublicAccessBlock | Yes | |
| GetBucketAccelerateConfiguration | Yes | Always returns `Suspended` |
| GetBucketAnalyticsConfiguration | Yes | Stub: returns `NoSuchConfiguration` |
| ListBucketAnalyticsConfigurations | Yes | Stub: returns an empty list |
| GetBucketIntelligentTieringConfiguration | Yes | Stub: returns `NoSuchConfiguration` |
| ListBucketIntelligentTieringConfigurations | Yes | Stub: returns an empty list |
| GetBucketInventoryConfiguration | Yes | Stub: returns `NoSuchConfiguration` |
| ListBucketInventoryConfigurations | Yes | Stub: returns an empty list |
| GetBucketLogging | Yes | Always returns an empty `BucketLoggingStatus` |
| GetBucketMetricsConfiguration | Yes | Stub: returns `NoSuchConfiguration` |
| ListBucketMetricsConfigurations | Yes | Stub: returns an empty list |
| GetBucketPolicyStatus | Yes | Computes `IsPublic` from the bucket policy |
| PutBucketRequestPayment | Yes | Accepts only `Payer=BucketOwner` |
| PutBucketAccelerateConfiguration | No | |
| PutBucketAnalyticsConfiguration | No | |
| DeleteBucketAnalyticsConfiguration | No | |
| PutBucketIntelligentTieringConfiguration | No | |
| DeleteBucketIntelligentTieringConfiguration | No | |
| PutBucketInventoryConfiguration | No | |
| DeleteBucketInventoryConfiguration | No | |
| PutBucketLogging | No | |
| PutBucketMetricsConfiguration | No | |
| DeleteBucketMetricsConfiguration | No | |
| GetBucketNotificationConfiguration | No | |
| PutBucketNotificationConfiguration | No | |
| GetBucketReplication | No | |
| PutBucketReplication | No | |
| DeleteBucketReplication | No | |
| GetBucketWebsite | No | |
| PutBucketWebsite | No | |
| DeleteBucketWebsite | No | |

## Object Operations

| API Operation | Supported | Notes |
|---|---|---|
| CopyObject | Yes | Supports version ID, encryption, metadata directive |
| DeleteObject | Yes | Supports version ID; also deletes folders |
| DeleteObjects | Yes | Multi-object delete |
| GetObject | Yes | Supports range requests, conditional headers, SSE, user metadata |
| GetObjectAcl | Yes | |
| GetObjectAttributes | Yes | |
| GetObjectLegalHold | Yes | See [S3 Object Lock and Retention](./S3-Object-Lock-and-Retention.md) |
| GetObjectRetention | Yes | |
| GetObjectTagging | Yes | |
| HeadObject | Yes | Returns user metadata, encryption info |
| ListObjects | Yes | V1 (legacy) |
| ListObjectsV2 | Yes | |
| ListObjectVersions | Yes | See [S3 Object Versioning](./S3-Object-Versioning.md) |
| PostObject | Yes | Browser-based form uploads via POST policy |
| PutObject | Yes | Supports SSE, user metadata (`x-amz-meta-*`), conditional headers |
| PutObjectAcl | Yes | |
| PutObjectLegalHold | Yes | |
| PutObjectRetention | Yes | |
| PutObjectTagging | Yes | |
| DeleteObjectTagging | Yes | |
| GetObjectTorrent | No | |
| RenameObject | Yes | Atomic metadata-only move; unversioned buckets only. See [S3 RenameObject](./S3-RenameObject.md) |
| RestoreObject | No | |
| SelectObjectContent | No | |
| WriteGetObjectResponse | No | S3 Object Lambda |

## Multipart Upload Operations

| API Operation | Supported | Notes |
|---|---|---|
| CreateMultipartUpload | Yes | IAM action: `s3:CreateMultipartUpload` |
| UploadPart | Yes | IAM action: `s3:UploadPart` |
| UploadPartCopy | Yes | |
| CompleteMultipartUpload | Yes | IAM action: `s3:CompleteMultipartUpload` |
| AbortMultipartUpload | Yes | IAM action: `s3:AbortMultipartUpload` |
| ListMultipartUploads | Yes | IAM action: `s3:ListBucketMultipartUploads` |
| ListParts | Yes | IAM action: `s3:ListMultipartUploadParts` |

All multipart operations are implicitly allowed when `s3:PutObject` is granted. See [S3 Bucket Policies#multipart-upload-permission-inheritance](./S3-Bucket-Policies.md#multipart-upload-permission-inheritance).

## Additional APIs

SeaweedFS also implements these related AWS service APIs on the same S3 endpoint:

| Service | Operations | Documentation |
|---|---|---|
| Security Token Service (STS) | AssumeRole, AssumeRoleWithWebIdentity, AssumeRoleWithLDAPIdentity, GetFederationToken, GetCallerIdentity | [OIDC Integration](./OIDC-Integration.md) |
| IAM API | User, policy, access key, and group management | [Amazon IAM API](./Amazon-IAM-API.md), [AWS IAM CLI](./AWS-IAM-CLI.md) |
| S3 Tables | Table bucket, namespace, and table management (Apache Iceberg) | [S3 Table Bucket](./S3-Table-Bucket.md) |

## SeaweedFS Extensions

These are SeaweedFS-specific S3 subresources, not part of the AWS S3 API. They use the same S3 endpoint and SigV4 authentication but are not callable by standard AWS tools (`aws s3api`, `s3cmd`, `rclone`). Use any SigV4-capable HTTP client.

| Subresource | Operations | IAM Permission | Documentation |
|---|---|---|---|
| `?seaweedfs-quota` | `PUT /{bucket}?seaweedfs-quota`, `GET /{bucket}?seaweedfs-quota` | `s3:PutBucketQuota`, `s3:GetBucketQuota` | [S3 Bucket Quota](./S3-Bucket-Quota.md) |

# Feature Differences

| Feature | SeaweedFS | Amazon S3 |
|---|---|---|
| Multi byte ranges reads | Yes | No |
| DeleteObject deletes a folder | Yes | No |
| Same path for both a file and a folder | No | Yes |
| Allows more than "/" as a delimiter | No | Yes |
| Object Versioning | Yes | Yes |
| MFA Delete for versioning | No | Yes |
| Server-Side Encryption (SSE-KMS) | Yes | Yes |
| Server-Side Encryption (SSE-C) | Yes | Yes |
| Server-Side Encryption (SSE-S3) | Yes | Yes |
| KMS Providers (Multi-cloud) | Yes | No |
| Conditional Headers (All operations) | Yes | Yes |
| Range requests with SSE | Yes | Yes |
| Presigned URLs | Yes | Yes |

## Empty Folders

SeaweedFS has directories while AWS S3 only has objects with "fake" directories. In AWS S3, if the last file is deleted in a directory, the directory will disappear also.

To be consistent with AWS S3, SeaweedFS automatically cleans up empty folders asynchronously after file deletions.

# Related Pages

**Configuration & Authentication**
- [S3 Configuration](./S3-Configuration.md) — Overview of all configuration options
- [S3 Credentials](./S3-Credentials.md) — Access key and identity management
- [OIDC Integration](./OIDC-Integration.md) — OIDC, STS, and role-based access
- [Amazon IAM API](./Amazon-IAM-API.md) / [AWS IAM CLI](./AWS-IAM-CLI.md) — IAM API operations
- [Security Configuration](./Security-Configuration.md) — mTLS and JWT between S3 gateway and filer

**Security & Policies**
- [S3 Bucket Policies](./S3-Bucket-Policies.md) — IAM-style policies with condition operators
- [S3 Policy Conditions](./S3-Policy-Conditions.md) — Condition key reference
- [S3 Policy Variables](./S3-Policy-Variables.md) — Policy variable substitution
- [S3 Object Lock and Retention](./S3-Object-Lock-and-Retention.md) — Object lock, retention, legal hold
- [S3 Object Versioning](./S3-Object-Versioning.md) — Version management

**Encryption**
- [Server-Side Encryption](./Server-Side-Encryption.md) — SSE overview
- [Server-Side Encryption SSE-KMS](./Server-Side-Encryption-SSE-KMS.md) — AWS KMS, Google Cloud KMS, OpenBao/Vault
- [Server-Side Encryption SSE-C](./Server-Side-Encryption-SSE-C.md) — Customer-provided keys

**Features**
- [S3 Conditional Operations](./S3-Conditional-Operations.md) — If-Match, If-None-Match, If-Modified-Since, If-Unmodified-Since
- [S3 RenameObject](./S3-RenameObject.md) — Atomic metadata-only object rename
- [S3 CORS](./S3-CORS.md) — Cross-Origin Resource Sharing
- [S3 Bucket Quota](./S3-Bucket-Quota.md) — Storage quota management
- [S3 Rate Limiting](./S3-Rate-Limiting.md) — Request rate limiting
- [S3 API Audit log](./S3-API-Audit-log.md) — Audit logging

**S3 Tables & Iceberg**
- [S3 Table Bucket](./S3-Table-Bucket.md) — S3 Tables API
- [SeaweedFS Iceberg Catalog](./SeaweedFS-Iceberg-Catalog.md) — Apache Iceberg REST catalog
- [Iceberg Table Maintenance](./Iceberg-Table-Maintenance.md) — Table maintenance operations
- [S3 Tables Security](./S3-Tables-Security.md) — Table bucket security

**Deployment & Operations**
- [S3 Nginx Proxy](./S3-Nginx-Proxy.md) — Reverse proxy and X-Forwarded-* header support
- [Docker Compose for S3](./Docker-Compose-for-S3.md) — Docker deployment
- [S3 API Benchmark](./S3-API-Benchmark.md) — Performance benchmarking
- [S3 API FAQ](./S3-API-FAQ.md) — Frequently asked questions

**Client Tools**
- [AWS CLI with SeaweedFS](./AWS-CLI-with-SeaweedFS.md) — AWS CLI usage, presigned URLs
- [s3cmd with SeaweedFS](./s3cmd-with-SeaweedFS.md)
- [rclone with SeaweedFS](./rclone-with-SeaweedFS.md)
- [restic with SeaweedFS](./restic-with-SeaweedFS.md)
- [nodejs with Seaweed S3](./nodejs-with-Seaweed-S3.md)
