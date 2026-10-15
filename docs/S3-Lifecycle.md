---
id: S3-Lifecycle
title: "S3 Lifecycle"
sidebar_label: "S3 Lifecycle"
---

# S3 Lifecycle

SeaweedFS implements the S3 `PutBucketLifecycleConfiguration` API. Configured rules are evaluated and enforced by a worker that runs as a scheduled job and exits when each pass completes.

This page is the operator-facing entry point. Developers and architecture readers should see [`weed/s3api/s3lifecycle/DESIGN.md`](https://github.com/seaweedfs/seaweedfs/blob/master/weed/s3api/s3lifecycle/DESIGN.md).

## Supported features

| Feature | Status | Notes |
|---|---|---|
| `Expiration.Days` | Yes | Latest-version PUT clock |
| `Expiration.Date` | Yes | Walker path; fires once date is reached |
| `Expiration.ExpiredObjectDeleteMarker` | Yes | Walker path; sibling-aware |
| `NoncurrentVersionExpiration.NoncurrentDays` | Yes | Clock starts at the demoting PUT, not the entry's own mtime |
| `NoncurrentVersionExpiration.NewerNoncurrentVersions` | Yes | Walker path; version-list aware |
| `AbortIncompleteMultipartUpload.DaysAfterInitiation` | Yes | |
| `Filter.Prefix` | Yes | |
| `Filter.Tag` | Yes | |
| `Filter.ObjectSizeGreaterThan` / `ObjectSizeLessThan` | Yes | |
| `Filter.And` (composite) | Yes | |
| `Transition` / `NoncurrentVersionTransition` | Rejected | SeaweedFS doesn't model storage class tiers. A `PUT` whose enabled rules contain either is rejected with `NotImplemented` — the config is not stored. See [Limits and validation](#limits-and-validation). |

## API endpoints

```text
PUT    /{bucket}?lifecycle   # PutBucketLifecycleConfiguration
GET    /{bucket}?lifecycle   # GetBucketLifecycleConfiguration
DELETE /{bucket}?lifecycle   # DeleteBucketLifecycle
```

The CLI examples below are the convenient way to drive these. The PUT body on the wire is XML — the same `LifecycleConfiguration` document AWS uses:

```xml
<LifecycleConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <Rule>
    <ID>expire-logs</ID>
    <Status>Enabled</Status>
    <Filter>
      <And>
        <Prefix>logs/</Prefix>
        <Tag><Key>class</Key><Value>temp</Value></Tag>
        <ObjectSizeGreaterThan>4096</ObjectSizeGreaterThan>
      </And>
    </Filter>
    <Expiration><Days>30</Days></Expiration>
    <NoncurrentVersionExpiration>
      <NoncurrentDays>7</NoncurrentDays>
      <NewerNoncurrentVersions>3</NewerNoncurrentVersions>
    </NoncurrentVersionExpiration>
    <AbortIncompleteMultipartUpload>
      <DaysAfterInitiation>7</DaysAfterInitiation>
    </AbortIncompleteMultipartUpload>
  </Rule>
</LifecycleConfiguration>
```

Unknown elements are skipped on decode. `Filter` with a single `Prefix` (or a single `Tag`) needs no `And` wrapper; `And` is only required when combining more than one predicate. The stored XML is returned verbatim by `GET` — SeaweedFS does not rewrite or canonicalize it.

## Limits and validation

The `PUT` handler validates the whole document before touching any state, so a rejected config never half-applies:

| Condition | Result |
|---|---|
| Body larger than **1 MiB** | `EntityTooLarge` |
| Body not valid lifecycle XML | `MalformedXML` |
| An **enabled** rule contains `Transition` or `NoncurrentVersionTransition` | `NotImplemented` (whole config rejected) |
| Filer / backing-store error | `InternalError` |
| `GET` when no lifecycle is configured | `NoSuchLifecycleConfiguration` |

Notes:

- Only **enabled** rules are checked for transitions — a `Disabled` rule carrying a `Transition` is ignored rather than rejected, matching how a disabled rule is otherwise inert.
- There is no enforced cap on the number of rules, rule-ID length, or tag count beyond the 1 MiB document size.
- `GET` has a legacy fallback: if a bucket has no lifecycle XML but does have directory TTLs configured via `fs.configure -ttl` (see [S3 Lifecycle vs Volume TTL](./S3-Lifecycle-vs-Volume-TTL.md)), `GET` synthesizes `Expiration.Days` rules from those TTLs instead of returning `NoSuchLifecycleConfiguration`.

## Example: AWS CLI

```bash
# Set lifecycle configuration
aws s3api put-bucket-lifecycle-configuration \
  --endpoint-url http://localhost:8333 \
  --bucket my-bucket \
  --lifecycle-configuration '{
    "Rules": [
      {
        "ID": "expire-old",
        "Status": "Enabled",
        "Filter": { "Prefix": "" },
        "Expiration": { "Days": 90 },
        "NoncurrentVersionExpiration": { "NoncurrentDays": 30 },
        "AbortIncompleteMultipartUpload": { "DaysAfterInitiation": 7 }
      }
    ]
  }'

# Get lifecycle configuration
aws s3api get-bucket-lifecycle-configuration \
  --endpoint-url http://localhost:8333 \
  --bucket my-bucket

# Delete lifecycle configuration
aws s3api delete-bucket-lifecycle \
  --endpoint-url http://localhost:8333 \
  --bucket my-bucket
```

## Example: Terraform

```hcl
resource "aws_s3_bucket_lifecycle_configuration" "example" {
  bucket = aws_s3_bucket.example.id

  rule {
    id     = "expire-logs"
    status = "Enabled"

    filter {
      prefix = "logs/"
    }

    expiration {
      days = 30
    }

    noncurrent_version_expiration {
      noncurrent_days           = 7
      newer_noncurrent_versions = 2
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}
```

## How it works

The lifecycle worker is a scheduled job (default daily). Each invocation:

1. Reads bucket lifecycle XML from each bucket's metadata.
2. Compiles rules into a per-shard partition (replay-eligible vs. walker-bound).
3. Subscribes to the filer meta-log — one stream covering all 16 shards in this worker process.
4. For replay-eligible actions (`ExpirationDays`, `NoncurrentDays`, `AbortMPU`), checks each event's DueTime and dispatches `LifecycleDelete` if elapsed.
5. For walker-bound rules (`ExpirationDate`, `ExpiredObjectDeleteMarker`, `NewerNoncurrent`, or anything promoted to scan-only), iterates the bucket and evaluates each entry against current state.
6. Persists per-shard cursors so the next pass resumes where this one left off.

The worker exits when the pass is done. The admin scheduler invokes it on a daily cadence by default; operators can change that via the standard plugin scheduler config.

### Timing

Expiration is not event-time accurate. The lag from the triggering PUT to the actual delete is bounded by the worker invocation cadence (default 24h) plus, for walker-only rules, up to one `walker_interval_minutes` window. Budget for "up to a day," not seconds.

`Days` count in 24-hour units from the relevant clock (the latest-version PUT for `Expiration.Days`, the demoting PUT for `NoncurrentDays`, the MPU initiation for `AbortIncompleteMultipartUpload`). The AWS CLI and SDKs reject `Days &lt; 1` client-side, so one day is the smallest window you'll set through them. SeaweedFS does **not** validate this server-side — a raw `PUT` with `Days` set to `0` (or omitted) is stored and returned as-is, but the rule compiles to a no-op and deletes nothing. The in-repo integration tests compile with a build tag that shortens one "day" to 10 seconds so a full lifecycle can be exercised in CI; released binaries always use 24 hours.

## Versioning integration

Lifecycle rules interact with [S3 Object Versioning](./S3-Object-Versioning.md):

- **`NoncurrentVersionExpiration`** only applies to versioned buckets. Non-current versions are deleted after `NoncurrentDays` days since they were superseded (the demoting PUT's TsNs, not the version's own mtime). `NewerNoncurrentVersions` retains the N newest non-current versions.
- **`ExpiredObjectDeleteMarker`** removes delete markers that are the sole remaining version of an object (no non-current versions behind them).
- **`Expiration.Days`** on a versioned bucket creates a delete marker when the current version expires; it does not permanently delete the object.

## Disk reclamation and the TTL fast path

By default the worker deletes objects individually and disk is freed later by [volume vacuum](./Volume-Management.md). For high-churn, non-versioned buckets with a fixed `Expiration.Days` retention, an opt-in **TTL fast path** stamps the expiry as a volume TTL at write time, so disk is reclaimed by dropping the whole volume and the worker only removes the metadata entry. It is off by default and applies only to non-versioned, non-Object-Lock buckets with prefix/size `Expiration.Days` rules; everything else falls back to the worker automatically.

```text
weed shell -master <host:port>
> s3.bucket.lifecycle.fastpath -name my-bucket            # show current state
> s3.bucket.lifecycle.fastpath -name my-bucket -enable
> s3.bucket.lifecycle.fastpath -name my-bucket -disable
```

Trade-offs and when to choose it are covered in [S3 Lifecycle vs Volume TTL](./S3-Lifecycle-vs-Volume-TTL.md).

## Quick references

- **[Recipes](./S3-Lifecycle-Recipes.md)** — copy-paste configs for the common scenarios, with how to verify each
- **[Operator Guide](./S3-Lifecycle-Operator-Guide.md)** — config knobs, defaults, when to change each
- **[Monitoring](./S3-Lifecycle-Monitoring.md)** — Prometheus metrics, heartbeat log line, what a healthy run looks like
- **[Troubleshooting](./S3-Lifecycle-Troubleshooting.md)** — stuck cursor, missing deletes, head-of-line blocking
- **[Architecture](./S3-Lifecycle-Architecture.md)** — high-level overview of the worker, engine, and dispatch path
