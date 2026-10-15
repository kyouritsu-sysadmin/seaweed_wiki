---
id: S3-Conditional-Operations
title: "S3 Conditional Operations"
sidebar_label: "S3 Conditional Operations"
---

# S3 Conditional Operations

SeaweedFS supports AWS S3-compatible conditional headers for safe concurrent
access patterns, optimistic locking, and efficient conditional operations.

**The conditional check and the write are atomic — cluster-wide.** The
precondition is evaluated against the live object and the write is applied
under the same lock, on the filer that owns the key in the cluster's hash
ring. Two clients racing an `If-Match` update never both succeed, regardless
of which filer each one talks to. See
[Filer Operation Serialization](./Filer-Operation-Serialization.md) for the underlying primitive
(`ObjectTransaction`) and how it stays correct across filer restarts and
ring changes.

## Supported Conditional Headers

These conditions act on the **target object** (the object being read or
written). All four are supported on GET, HEAD, PUT, POST
(`CompleteMultipartUpload`), and COPY. DELETE supports only `If-Match`.

| Header | Type | Applies to | Special values |
|--------|------|------------|----------------|
| `If-Match` | ETag | GET, HEAD, PUT, POST, COPY, **DELETE** | `*` matches any existing object; comma-separated ETag list is honored |
| `If-None-Match` | ETag | GET, HEAD, PUT, POST, COPY | `*` matches only when the object does **not** exist (compare-and-create); comma-separated ETag list is honored |
| `If-Modified-Since` | RFC 1123 date | GET, HEAD, PUT, POST, COPY | — |
| `If-Unmodified-Since` | RFC 1123 date | GET, HEAD, PUT, POST, COPY | — |

### Copy-source conditionals

`CopyObject` and `UploadPartCopy` accept a second set of headers that
condition on the **source** object. They are independent of the four
standard headers above (which condition on the destination), so a single
copy request can carry conditions for both ends.

| Header | Type |
|--------|------|
| `x-amz-copy-source-if-match` | ETag |
| `x-amz-copy-source-if-none-match` | ETag |
| `x-amz-copy-source-if-modified-since` | RFC 1123 date |
| `x-amz-copy-source-if-unmodified-since` | RFC 1123 date |

### Evaluation order

Per [RFC 7232 §6](https://datatracker.ietf.org/doc/html/rfc7232#section-6)
and AWS S3, the conditions are evaluated in this order; later conditions
are skipped when an earlier one is present:

1. `If-Match`
2. `If-Unmodified-Since` — ignored if `If-Match` is present
   ([RFC 7232 §3.4](https://datatracker.ietf.org/doc/html/rfc7232#section-3.4))
3. `If-None-Match`
4. `If-Modified-Since` — ignored if `If-None-Match` is present
   ([RFC 7232 §3.3](https://datatracker.ietf.org/doc/html/rfc7232#section-3.3))

### Not supported

* `If-Range`. A `Range` request without `If-Range` works normally; there is
  no header to fall back to a full-object response when the source has
  changed.

## HTTP Examples

### Conditional GET (Caching)

```bash
# First, get the object and note its ETag
curl -I "http://localhost:8333/mybucket/myfile.txt"
# Response: ETag: "d41d8cd98f00b204e9800998ecf8427e"

# Conditional GET - only download if object changed
curl -H "If-None-Match: \"d41d8cd98f00b204e9800998ecf8427e\"" \
  "http://localhost:8333/mybucket/myfile.txt"
```

### Conditional PUT (Optimistic Locking)

```bash
# Safe update - only modify if object hasn't changed
curl -X PUT -H "If-Match: \"d41d8cd98f00b204e9800998ecf8427e\"" \
  -H "Content-Type: text/plain" \
  --data "Updated content" \
  "http://localhost:8333/mybucket/myfile.txt"

# Prevent overwrites - only create if object doesn't exist
curl -X PUT -H "If-None-Match: *" \
  -H "Content-Type: text/plain" \
  --data "New file content" \
  "http://localhost:8333/mybucket/newfile.txt"
```

### If-Modified-Since

```bash
# Only download if modified after specific date
curl -H "If-Modified-Since: Wed, 15 Jan 2024 10:00:00 GMT" \
  "http://localhost:8333/mybucket/log-file.txt"
```

### If-Unmodified-Since

```bash
# Update only if not modified since last read
curl -X PUT \
  -H "If-Unmodified-Since: Wed, 15 Jan 2024 10:00:00 GMT" \
  -H "Content-Type: text/plain" \
  --data "Updated content" \
  "http://localhost:8333/mybucket/document.txt"
```

### Copy Operations

```bash
# Copy only if source object hasn't changed
curl -X PUT \
  -H "x-amz-copy-source: /source-bucket/source-file.txt" \
  -H "x-amz-copy-source-if-match: \"source-etag\"" \
  "http://localhost:8333/dest-bucket/dest-file.txt"

# Same copy, but also refuse to overwrite the destination
curl -X PUT \
  -H "x-amz-copy-source: /source-bucket/source-file.txt" \
  -H "x-amz-copy-source-if-match: \"source-etag\"" \
  -H "If-None-Match: *" \
  "http://localhost:8333/dest-bucket/dest-file.txt"
```

### Conditional DELETE

```bash
# Delete only if the object's ETag still matches what we read
curl -X DELETE \
  -H "If-Match: \"d41d8cd98f00b204e9800998ecf8427e\"" \
  "http://localhost:8333/mybucket/myfile.txt"
```

DELETE supports `If-Match` only; the other three conditional headers are
ignored on DELETE per the AWS S3 spec.

## HTTP Status Codes

| Status Code | When | Meaning |
|-------------|------|---------|
| **200 OK** | All conditions met | Operation succeeded normally |
| **304 Not Modified** | GET/HEAD with `If-None-Match` match, or `If-Modified-Since` not exceeded | Object unchanged; response carries the ETag header but no body |
| **400 Invalid Request** | `If-Modified-Since` or `If-Unmodified-Since` is not a valid RFC 1123 date | Header is malformed |
| **412 Precondition Failed** | Any other failed condition (all writes; GET/HEAD with `If-Match` mismatch or `If-Unmodified-Since` exceeded) | Operation blocked by condition |

## Atomicity and concurrency

The contract is the same as AWS S3: a successful `PUT` with a precondition
header means the precondition held *at the moment the write was applied*,
not merely at some earlier read. The two cases worth calling out:

* **`If-None-Match: "*"` (compare-and-create).** At most one of any number
  of concurrent `PUT`s for the same key succeeds; the rest return
  `412 Precondition Failed`. Use this as a primitive for distributed
  leader election, exclusive file creation, or idempotent uploads.
* **`If-Match: "&lt;etag&gt;"` (optimistic concurrency).** A read-modify-write
  cycle that fails with `412` means another writer changed the object
  between your read and your write. Retry against the new ETag.

How it stays correct across a multi-filer cluster:

1. The S3 gateway forwards each write to a filer. That filer issues a
   single `ObjectTransaction` RPC describing the precondition plus the
   mutations (e.g. write the object + flip the version pointer + delete
   the prior null-version entry).
2. The transaction is routed by key to the *owner* filer for that object
   — the same filer for every concurrent writer of the same key,
   regardless of which gateway or filer they entered through.
3. The owner takes an exclusive per-path lock for the key's lifetime of
   the transaction, evaluates the precondition against the current
   metadata, and applies the mutations under that lock. The whole
   sequence is one RPC; there is no caller-held distributed lock that
   can leak on a slow or crashed client.
4. During filer membership changes, the same routing primitive applies a
   cooling-window dual-read and a warm-up period so a new owner never
   serves a write whose precondition it cannot yet verify. The
   precondition guarantee survives ring changes.

The detailed mechanism is in [Filer Operation Serialization](./Filer-Operation-Serialization.md). The same
primitive also powers cross-mount POSIX advisory locks; see
[Distributed POSIX Locks](./Distributed-POSIX-Locks.md).

## Related Documentation

- [Amazon S3 API](./Amazon-S3-API.md)
- [S3 Object Versioning](./S3-Object-Versioning.md)
- [S3 Object Lock and Retention](./S3-Object-Lock-and-Retention.md)
- [Filer Operation Serialization](./Filer-Operation-Serialization.md)
- [Distributed POSIX Locks](./Distributed-POSIX-Locks.md)