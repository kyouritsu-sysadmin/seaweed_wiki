---
id: S3-Lifecycle-vs-Volume-TTL
title: "S3 Lifecycle vs Volume TTL"
sidebar_label: "S3 Lifecycle vs Volume TTL"
---

# S3 Lifecycle vs Volume TTL

SeaweedFS has two independent ways to make objects expire. Both read as "delete after N days," but they reclaim disk and react to policy changes differently. Choosing the wrong one is the usual cause of "expiration ran but disk was never freed."

## At a glance

| | Volume TTL | S3 Lifecycle (default) |
|---|---|---|
| Set by | `fs.configure -ttl`, `assign?ttl=` | `PutBucketLifecycleConfiguration` |
| Granularity | whole TTL volume | per object |
| Reclaims disk | drops the whole volume once its newest file expires | per-object delete, then volume vacuum |
| Honors a later policy change | No — clock baked in at write time | Yes — worker re-evaluates current rules each pass |
| Versioned buckets | not version-aware (expires as a unit) | full S3 semantics (delete markers, noncurrent) |
| Object Lock aware | No | Yes — locked objects skipped |
| Latency | volume-expiry granularity | worker cadence (default up to 24h) |

The core difference: **volume TTL is decided once, at write time, for a whole volume. S3 lifecycle is a policy the worker re-checks on every pass, per object.**

## Volume TTL

A file's TTL is tied to its *volume*. Files sharing a TTL land in the same volumes, and the volume server drops a whole volume once its newest file expires — no per-file delete, no vacuum. Set it per directory with `fs.configure -ttl 20d`, or per write with `assign?ttl=`.

Cheap to reclaim, but not S3-aware: no delete markers, no per-object rules, no Object Lock, and space is freed only when the *entire* volume ages out. See [Store file with a Time To Live](./Store-file-with-a-Time-To-Live.md).

## S3 lifecycle (default)

`PutBucketLifecycleConfiguration` rules are run by the lifecycle worker. It deletes objects individually, honoring the *current* policy, and vacuum reclaims the space. On versioned buckets it follows full S3 semantics and skips objects under retention or legal hold.

The rule set, and how versioning interacts with it (delete markers, `NoncurrentVersionExpiration`, `ExpiredObjectDeleteMarker`), are documented on [S3 Lifecycle](./S3-Lifecycle.md#versioning-integration); config knobs are in the [Operator Guide](./S3-Lifecycle-Operator-Guide.md).

## The TTL fast path (opt-in)

This bridges the two. When enabled on a bucket, an `Expiration.Days` rule is stamped as a volume TTL at write time — so disk is reclaimed by dropping the volume, and the worker only removes the metadata entry (no per-chunk deletes).

It is **off by default** because a volume TTL can't be taken back:

- Change or remove the rule later, and objects already written still expire on the old schedule. The default worker path re-reads the policy and adjusts.
- Dead bytes stay in a TTL volume — showing zero deleted bytes — until the whole volume ages out. That is the classic "lifecycle ran but disk wasn't reclaimed" symptom.

When on, it applies only to non-versioned, non-Object-Lock buckets with prefix/size `Expiration.Days` rules; everything else falls back to the worker automatically.

```text
weed shell -master <host:port>
> s3.bucket.lifecycle.fastpath -name my-bucket            # show
> s3.bucket.lifecycle.fastpath -name my-bucket -enable
> s3.bucket.lifecycle.fastpath -name my-bucket -disable
```

The setting lives in bucket metadata, reaches every S3 server without a restart, and affects only future writes.

## Which should I use?

- **Default lifecycle (fast path off)** — if you use versioning or Object Lock, or might change the policy later. Correct S3 behavior; space reclaimed by vacuum.
- **Fast path on**, or a **dedicated TTL collection** (`fs.configure -ttl`) — for high-churn, non-versioned data with a fixed retention, where you want the cheapest reclamation and accept that the per-object TTL is final.

## See also

[S3 Lifecycle](./S3-Lifecycle.md) · [S3 Lifecycle Operator Guide](./S3-Lifecycle-Operator-Guide.md) · [Store file with a Time To Live](./Store-file-with-a-Time-To-Live.md) · [S3 Object Versioning](./S3-Object-Versioning.md) · [S3 Object Lock and Retention](./S3-Object-Lock-and-Retention.md)
