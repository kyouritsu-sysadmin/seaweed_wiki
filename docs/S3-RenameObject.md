---
id: S3-RenameObject
title: "S3 RenameObject"
sidebar_label: "S3 RenameObject"
---

# S3 RenameObject

SeaweedFS supports the S3 `RenameObject` API: rename an object within a
bucket in one atomic, metadata-only operation. AWS offers this API only on
directory buckets (S3 Express One Zone); SeaweedFS provides it on regular
buckets.

Available since version 4.42.

## How It Works

The rename is executed by the filer as an atomic metadata move. The
object's data is never read or rewritten, so renaming a 1 TB object costs
the same as renaming a 1 KB one, and the ETag, tags, user metadata, and
encryption metadata all travel unchanged.

Both keys are write-locked for the duration of the operation, and all
precondition headers are evaluated under those locks, so a conditional
rename is atomic cluster-wide — the same guarantee as
[S3 Conditional Operations](./S3-Conditional-Operations.md).

## Request

```
PUT /{bucket}/{destination-key}?renameObject
x-amz-rename-source: {source-key}
```

The `x-amz-rename-source` value can be a bare key (`old-name.txt`) or
bucket-qualified (`mybucket/old-name.txt`), with or without a leading
slash — AWS's own examples use both forms. The value is read as a literal
key first; only when no such object exists and the value starts with the
request's own bucket name is it re-read as `bucket/key`. Cross-bucket
renames are not supported: the source bucket is always the request's
bucket.

With the AWS CLI:

```bash
aws --endpoint-url http://localhost:8333 s3api rename-object \
  --bucket mybucket \
  --key new-name.txt \
  --rename-source mybucket/old-name.txt
```

Or as a raw request:

```bash
curl -X PUT -H "x-amz-rename-source: old-name.txt" \
  "http://localhost:8333/mybucket/new-name.txt?renameObject"
```

## Conditional Headers

Like `CopyObject`, a rename can carry conditions for both ends of the
operation independently.

The source is conditioned with rename-source headers:

| Header | Type |
|--------|------|
| `x-amz-rename-source-if-match` | ETag |
| `x-amz-rename-source-if-none-match` | ETag |
| `x-amz-rename-source-if-modified-since` | RFC 1123 date |
| `x-amz-rename-source-if-unmodified-since` | RFC 1123 date |

The destination is conditioned with the four standard headers
(`If-Match`, `If-None-Match`, `If-Modified-Since`,
`If-Unmodified-Since`). The most useful one: an existing destination
object is silently replaced, as with `PutObject`, so send
`If-None-Match: *` to make the rename fail with `PreconditionFailed`
instead of overwriting.

```bash
curl -X PUT \
  -H "x-amz-rename-source: old-name.txt" \
  -H "If-None-Match: *" \
  "http://localhost:8333/mybucket/new-name.txt?renameObject"
```

## Restrictions

* **Unversioned buckets only.** A bucket with versioning enabled or
  suspended — including any bucket with Object Lock, which implies
  versioning — returns `501 NotImplemented`. This matches AWS, where
  RenameObject exists only on directory buckets, which cannot be
  versioned.
* **Objects only.** A key with a trailing slash names a directory, and
  renaming one would move a whole subtree; both ends reject it. An object
  whose key is also a prefix of other keys (a "directory object") cannot
  be renamed either.
* **Source read + delete permission.** The caller needs write permission
  on the destination (it is the request URL), plus read and delete
  permission on the source, since the rename both reads the object and
  removes its old key.
* **No idempotency replay.** `x-amz-client-token` is accepted — AWS SDKs
  fill it in automatically — but retrying a rename that already succeeded
  returns `NoSuchKey`, because the source is gone.

## Errors

| Condition | Error |
|---|---|
| Source object does not exist | `NoSuchKey` (404) |
| Bucket is versioned | `NotImplemented` (501) |
| Destination same as source | `InvalidRequest` (400) |
| Missing or empty `x-amz-rename-source` | `InvalidArgument` (400) |
| A directory exists at the destination key | `ExistingObjectIsDirectory` (409) |
| A precondition failed | `PreconditionFailed` (412) |
