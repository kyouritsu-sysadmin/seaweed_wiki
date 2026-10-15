---
id: S3-Lifecycle-Recipes
title: "S3 Lifecycle Recipes"
sidebar_label: "S3 Lifecycle Recipes"
---

# S3 Lifecycle — Recipes

Worked, end-to-end configurations for the common lifecycle scenarios, each with how to apply it and how to confirm it ran. For the feature reference and validation rules see [S3 Lifecycle](./S3-Lifecycle.md); for config knobs see the [Operator Guide](./S3-Lifecycle-Operator-Guide.md).

All examples use the AWS CLI against the S3 endpoint. Set it once:

```bash
export S3_ENDPOINT=http://localhost:8333
```

Each rule needs a `Status` and a `Filter` (use `{}` to match the whole bucket). The CLI accepts the JSON shown here; the bytes on the wire are the equivalent `LifecycleConfiguration` XML.

## Verifying any rule

Two independent signals tell you a rule worked:

1. **The dispatch counter advances.** Each delete increments `SeaweedFS_s3_lifecycle_dispatch_total{bucket,kind,outcome}`. A successful expiry shows up as `outcome="DONE"`. The `kind` label is one of:

   | `kind` | Set by |
   |---|---|
   | `expiration_days` | `Expiration.Days` |
   | `expiration_date` | `Expiration.Date` |
   | `noncurrent_days` | `NoncurrentVersionExpiration.NoncurrentDays` |
   | `newer_noncurrent` | `NoncurrentVersionExpiration.NewerNoncurrentVersions` (stand-alone) |
   | `abort_mpu` | `AbortIncompleteMultipartUpload` |
   | `expired_delete_marker` | `Expiration.ExpiredObjectDeleteMarker` |

   ```promql
   sum by (kind, outcome) (SeaweedFS_s3_lifecycle_dispatch_total{bucket="my-bucket"})
   ```

2. **The object is gone.** `aws s3api head-object` returns `404`, or `list-object-versions` no longer shows the version.

**Timing.** Replay-eligible rules (`Expiration.Days`, `NoncurrentDays`, `AbortIncompleteMultipartUpload`) fire on the next worker pass. Version-list-aware rules (`Expiration.Date`, `NewerNoncurrentVersions`, `ExpiredObjectDeleteMarker`) fire on the next walker pass — additionally up to one `walker_interval_minutes` window. With the default daily schedule, budget up to 24h. To check a rule immediately without waiting, drive the worker by hand with `s3.lifecycle.run-shard` (see the [Operator Guide](./S3-Lifecycle-Operator-Guide.md#verifying-a-rule-is-working)).

## Expire objects under a prefix

Delete everything under `logs/` 30 days after it was written.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3api put-bucket-lifecycle-configuration \
  --bucket my-bucket \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "expire-logs-30d",
      "Status": "Enabled",
      "Filter": { "Prefix": "logs/" },
      "Expiration": { "Days": 30 }
    }]
  }'
```

Replay path (`kind="expiration_days"`). The 30-day clock starts at the object's latest-version PUT. On a versioned bucket this writes a delete marker rather than removing data — pair it with the cleanup recipes below.

Verify:

```bash
aws --endpoint-url "$S3_ENDPOINT" s3api head-object --bucket my-bucket --key logs/old.log
# expected: An error occurred (404)
```

## Abort incomplete multipart uploads

Reclaim parts from uploads that were started but never completed, 7 days after initiation.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3api put-bucket-lifecycle-configuration \
  --bucket my-bucket \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "abort-stuck-mpu",
      "Status": "Enabled",
      "Filter": {},
      "AbortIncompleteMultipartUpload": { "DaysAfterInitiation": 7 }
    }]
  }'
```

Replay path (`kind="abort_mpu"`). The clock starts at the `CreateMultipartUpload` time. Safe to run on every bucket — it only touches in-flight uploads, never completed objects.

Verify:

```bash
aws --endpoint-url "$S3_ENDPOINT" s3api list-multipart-uploads --bucket my-bucket
# expected: no Uploads older than 7 days
```

## Expire objects by tag

Delete objects tagged `temp=true`, one day after write, regardless of prefix.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3api put-bucket-lifecycle-configuration \
  --bucket my-bucket \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "expire-temp-tagged",
      "Status": "Enabled",
      "Filter": { "Tag": { "Key": "temp", "Value": "true" } },
      "Expiration": { "Days": 1 }
    }]
  }'
```

Replay path. The tag is read from the live object at evaluation time, so re-tagging an object changes whether it matches. (This mutability is also why the [TTL fast path](./S3-Lifecycle-vs-Volume-TTL.md#the-ttl-fast-path-opt-in) refuses to stamp tag-filtered rules.)

## Expire only large objects

Combine predicates with `And`. Here: delete objects under `tmp/` that are larger than 5 MiB.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3api put-bucket-lifecycle-configuration \
  --bucket my-bucket \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "expire-large-tmp",
      "Status": "Enabled",
      "Filter": {
        "And": {
          "Prefix": "tmp/",
          "ObjectSizeGreaterThan": 5242880
        }
      },
      "Expiration": { "Days": 7 }
    }]
  }'
```

`And` is required whenever a filter has more than one predicate. Size bounds are strict: `ObjectSizeGreaterThan` matches objects *strictly larger* than the value, `ObjectSizeLessThan` *strictly smaller*. Set both to target a size band.

## Versioned bucket: keep the N newest versions

On a versioned bucket, retain the 5 most recent noncurrent versions and expire older noncurrent versions 30 days after they were superseded.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3api put-bucket-lifecycle-configuration \
  --bucket my-bucket \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "prune-noncurrent",
      "Status": "Enabled",
      "Filter": { "Prefix": "" },
      "NoncurrentVersionExpiration": {
        "NoncurrentDays": 30,
        "NewerNoncurrentVersions": 5
      }
    }]
  }'
```

A noncurrent version is removed only when **both** conditions hold: it is older than `NoncurrentDays` *and* there are at least `NewerNoncurrentVersions` newer noncurrent versions ahead of it. The five newest noncurrent versions are always kept, however old they get; everything behind them ages out at 30 days. The noncurrent clock starts at the PUT that demoted the version, not the version's own mtime.

Because the retain-N cap needs the full version list, this combination is evaluated on the walker pass, so it also waits up to one `walker_interval_minutes` window.

Use `NoncurrentDays` alone for a pure age policy, or `NewerNoncurrentVersions` alone for a pure count cap (keep exactly the N newest, no age requirement).

Verify:

```bash
aws --endpoint-url "$S3_ENDPOINT" s3api list-object-versions --bucket my-bucket --prefix my-key
# expected: at most 5 noncurrent versions remain
```

## Versioned bucket: clean up fully after deletes

A `DELETE` on a versioned bucket leaves a delete marker, and previous versions remain as noncurrent. To reclaim everything for deleted objects, use two rules — one to expire the old versions, one to remove the leftover delete marker once it is the only thing left:

```bash
aws --endpoint-url "$S3_ENDPOINT" s3api put-bucket-lifecycle-configuration \
  --bucket my-bucket \
  --lifecycle-configuration '{
    "Rules": [
      {
        "ID": "expire-noncurrent",
        "Status": "Enabled",
        "Filter": { "Prefix": "" },
        "NoncurrentVersionExpiration": { "NoncurrentDays": 30 }
      },
      {
        "ID": "expire-orphan-delete-markers",
        "Status": "Enabled",
        "Filter": { "Prefix": "" },
        "Expiration": { "ExpiredObjectDeleteMarker": true }
      }
    ]
  }'
```

`ExpiredObjectDeleteMarker` removes a delete marker only when it is the sole remaining version of the key (no noncurrent versions behind it). With the first rule clearing the noncurrent versions, the second eventually finds each delete marker orphaned and removes it. Both run on the walker pass.

## One-time cleanup at a fixed date

Delete everything under `archive/2024/` on a specific date, rather than relative to each object's age.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3api put-bucket-lifecycle-configuration \
  --bucket my-bucket \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "drop-2024-archive",
      "Status": "Enabled",
      "Filter": { "Prefix": "archive/2024/" },
      "Expiration": { "Date": "2026-07-01T00:00:00Z" }
    }]
  }'
```

Walker path (`kind="expiration_date"`). The rule fires on the first walker pass at or after the date; a date already in the past triggers on the next walk. Remove the rule afterward — it stays active and would expire anything later written under the prefix.

## A combined production config

Rules are independent and evaluated together, so one document can carry the whole policy for a bucket:

```bash
aws --endpoint-url "$S3_ENDPOINT" s3api put-bucket-lifecycle-configuration \
  --bucket my-bucket \
  --lifecycle-configuration '{
    "Rules": [
      {
        "ID": "expire-logs-30d",
        "Status": "Enabled",
        "Filter": { "Prefix": "logs/" },
        "Expiration": { "Days": 30 }
      },
      {
        "ID": "abort-stuck-mpu",
        "Status": "Enabled",
        "Filter": {},
        "AbortIncompleteMultipartUpload": { "DaysAfterInitiation": 7 }
      },
      {
        "ID": "prune-noncurrent",
        "Status": "Enabled",
        "Filter": { "Prefix": "" },
        "NoncurrentVersionExpiration": { "NoncurrentDays": 30, "NewerNoncurrentVersions": 5 }
      },
      {
        "ID": "expire-orphan-delete-markers",
        "Status": "Enabled",
        "Filter": { "Prefix": "" },
        "Expiration": { "ExpiredObjectDeleteMarker": true }
      }
    ]
  }'
```

`GET` returns the stored document verbatim. To temporarily disable a single rule without deleting it, set its `Status` to `Disabled` and re-`PUT`; the worker reads the change on its next pass.

## See also

[S3 Lifecycle](./S3-Lifecycle.md) · [S3 Lifecycle Operator Guide](./S3-Lifecycle-Operator-Guide.md) · [S3 Lifecycle Monitoring](./S3-Lifecycle-Monitoring.md) · [S3 Lifecycle Troubleshooting](./S3-Lifecycle-Troubleshooting.md) · [S3 Lifecycle vs Volume TTL](./S3-Lifecycle-vs-Volume-TTL.md) · [S3 Object Versioning](./S3-Object-Versioning.md)
