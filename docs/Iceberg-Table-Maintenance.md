---
id: Iceberg-Table-Maintenance
title: "Iceberg Table Maintenance"
sidebar_label: "Iceberg Table Maintenance"
---

# Iceberg Table Maintenance

## Introduction

SeaweedFS includes an automated **Iceberg table maintenance** worker that keeps [S3 Table Buckets](./S3-Table-Bucket.md) healthy. Over time, Iceberg tables accumulate small data files, stale snapshots, orphaned files, and fragmented manifests. Left unchecked, this degrades query performance and wastes storage.

The maintenance worker runs four operations in the recommended Iceberg order:

1. **Compact** -- merge small Parquet data files into larger ones
2. **Expire Snapshots** -- remove old snapshots and their unreferenced files
3. **Remove Orphans** -- delete files on disk that no snapshot references
4. **Rewrite Manifests** -- consolidate many small manifest files into fewer large ones

The worker integrates with the [Worker](./Worker.md) framework: an admin server schedules detection scans, the worker proposes tables that need attention, and the admin assigns execution jobs.

## Prerequisites

- A running SeaweedFS cluster with S3 Table Bucket support enabled
- At least one `weed worker` instance with `iceberg_maintenance` in its job types
- Tables created via the [S3 Tables API](./S3-Table-Bucket-Commands.md) or the [Iceberg REST Catalog](./SeaweedFS-Iceberg-Catalog.md)

## Enabling Maintenance

Iceberg maintenance is **disabled by default**. Enable it through the admin UI or API:

1. Navigate to **Admin UI > Job Types > Iceberg Maintenance**
2. Toggle **Enabled** to on
3. Configure detection interval, scope filters, and worker thresholds

Or start a worker with the job type included (it is in the default set):

```bash
# Default: includes iceberg_maintenance along with other job types
weed worker -admin=localhost:23646

# Explicitly specify job types
weed worker -admin=localhost:23646 -jobType=iceberg_maintenance
```

## Operations

### 1. Compact Data Files

Compaction merges many small Parquet files within the same partition into fewer, larger files. This reduces the number of file opens during queries and improves I/O throughput.

#### How It Works

1. Read the current snapshot's manifest list; separate data manifests from delete manifests
2. Group small data files (below `target_file_size_mb`) by **partition spec ID + partition key** so files from different specs are never mixed
3. Filter groups to those with at least `min_input_files` entries
4. If `apply_deletes` is enabled and delete manifests exist, collect position deletes and equality deletes from all delete manifest entries
5. For each group (bin), read all source Parquet files, filter out deleted rows (position deletes via binary search, equality deletes via hash set lookup), and merge remaining rows into a single output file
6. Write one manifest per partition spec with ADDED entries (merged files), DELETED entries (originals), and EXISTING entries (untouched files)
7. Carry forward delete manifests if any non-compacted data files remain; drop them if all data files were compacted (deletes fully consumed)
8. Commit a new snapshot via optimistic concurrency

#### Before / After: Unpartitioned Table

**Before** -- 6 small files totaling 53 MB:

```
data/
  file-001.parquet   (10 MB)
  file-002.parquet    (5 MB)
  file-003.parquet    (8 MB)
  file-004.parquet   (12 MB)
  file-005.parquet    (3 MB)
  file-006.parquet   (15 MB)
metadata/
  v1.metadata.json
  snap-100.avro           <- manifest list (1 snapshot)
  manifest-100.avro       <- manifest (6 entries)
```

**After** -- 1 merged file:

```
data/
  file-001..006.parquet   <- still on disk until orphan removal
  compact-100-<ts>-0.parquet  (53 MB, new merged file)
metadata/
  v1.metadata.json
  v2-<nonce>.metadata.json    <- new metadata
  snap-<ts>.avro              <- new manifest list (2 snapshots)
  compact-<ts>.avro           <- new manifest:
                                   1 ADDED   (merged file)
                                   6 DELETED (originals)
```

The original data files remain on disk. They become unreferenced after `expire_snapshots` drops the old snapshot, and are cleaned up by `remove_orphans`.

#### Before / After: Partitioned Table

**Before** -- `region=us` has 5 small files, `region=eu` has only 2:

```
data/
  region=us/part-001.parquet  (20 MB)
  region=us/part-002.parquet  (15 MB)
  region=us/part-003.parquet  (10 MB)
  region=us/part-004.parquet  (25 MB)
  region=us/part-005.parquet  (18 MB)
  region=eu/part-006.parquet   (5 MB)
  region=eu/part-007.parquet   (8 MB)
```

**After** -- only `region=us` is compacted (5 >= `min_input_files`), `region=eu` is untouched (2 &lt; 5):

```
data/
  region=us/part-001..005.parquet  <- marked DELETED in manifest
  region=eu/part-006.parquet       <- EXISTING (carried forward)
  region=eu/part-007.parquet       <- EXISTING (carried forward)
  compact-100-<ts>-0.parquet       <- merged US data (88 MB)
```

#### Before / After: Oversized Bin (Split)

When a partition group exceeds `target_file_size_bytes`, it is split into sub-bins:

**Before** -- 20 small files in one partition, totaling 600 MB (target = 256 MB):

**After** -- split into multiple output files:

```
compact-...-0.parquet  (~250 MB, files 1-8)
compact-...-1.parquet  (~240 MB, files 9-15)
(files 16-20 left alone if fewer than min_input_files)
```

#### Delete Handling

When `apply_deletes` is enabled (the default), compaction applies both **position deletes** and **equality deletes** during the merge:

- **Position deletes**: the delete file contains `file_path` + `pos` columns indicating specific rows to remove. Paths are normalized so absolute S3 URLs and relative paths match correctly.
- **Equality deletes**: the delete file specifies equality field IDs and column values. Rows matching those values are filtered out. Different delete files may use different equality columns — deletes are grouped by field ID set.

After compaction, delete manifests whose referenced data files were all compacted are dropped (deletes fully consumed). If any data files remain uncompacted, delete manifests are carried forward.

Set `apply_deletes=false` to revert to the previous behavior of skipping tables with delete manifests.

#### Skip Conditions

A table whose recorded format is not `ICEBERG` is skipped by every job here,
before any metadata is read. This matters more than it sounds: a Lance table
registered through the Iceberg REST adapter keeps its fragments under `data/`,
where they are unreferenced by any Iceberg snapshot by construction, and orphan
cleanup would otherwise delete them. See [SeaweedFS Lance Catalog](./SeaweedFS-Lance-Catalog.md) for the
catalog that serves those tables properly.

| Condition | Result |
|:---|:---|
| All files >= `target_file_size_mb` | `"no files eligible for compaction"` |
| No partition has >= `min_input_files` small files | `"no files eligible for compaction"` |
| Delete manifests present and `apply_deletes=false` | `"compaction skipped: delete manifests present and apply_deletes is disabled"` |
| No current snapshot | `"no current snapshot"` |

---

### 2. Expire Snapshots

Removes old snapshots from table metadata and deletes files that are no longer referenced by any remaining snapshot.

#### How It Works

1. Sort snapshots by timestamp (newest first)
2. The current snapshot is **always kept**
3. A snapshot a branch or tag points at is **always kept**, however old it is
4. Keep the newest `max_snapshots_to_keep` snapshots regardless of age
5. Among the rest, expire those older than `snapshot_retention_hours`
6. Snapshots within the retention window are kept even if they exceed the count
7. Commit new metadata with expired snapshots removed
8. Delete files exclusively referenced by expired snapshots (best-effort)

#### Branches and Tags

A named ref pins its snapshot: expiring it would drop the ref with it, and then
delete the files it pointed at, so tags used for time travel and write-audit-publish
branches survive maintenance no matter how far past retention they are.

A branch may also carry its own retention, and those override the worker for the
ancestors behind its head:

| Ref property | Effect |
|---|---|
| `min-snapshots-to-keep` | keeps that many snapshots back from the branch head |
| `max-snapshot-age-ms` | keeps ancestors newer than this age |

A table's own `history.expire.max-snapshot-age-ms` and
`history.expire.min-snapshots-to-keep` properties set the table-wide window and
take precedence over the worker config; the per-ref values above refine it for
one branch.

If a tag or branch appears while a maintenance run is planning, the run is
abandoned and re-planned on the next cycle rather than committing a plan made
before the ref existed.

#### Before / After

**Before** -- table with 8 snapshots, `max_snapshots_to_keep=5`, `snapshot_retention_hours=168` (7 days):

```
Snapshots (newest first):
  snap-8  (current, 1 hour ago)    <- always kept
  snap-7  (2 days ago)             <- kept (within budget)
  snap-6  (3 days ago)             <- kept (within budget)
  snap-5  (5 days ago)             <- kept (within budget)
  snap-4  (6 days ago)             <- kept (within budget, count=5)
  snap-3  (8 days ago)             <- EXPIRED (beyond budget + retention)
  snap-2  (10 days ago)            <- EXPIRED
  snap-1  (14 days ago)            <- EXPIRED
```

**After**:

```
Snapshots:
  snap-8  (current)
  snap-7
  snap-6
  snap-5
  snap-4

Deleted: manifest lists, manifests, and data files
         exclusively referenced by snap-1, snap-2, snap-3
```

Result: `"expired 3 snapshot(s), deleted 12 unreferenced file(s)"`

---

### 3. Remove Orphans

Deletes files in the table's `metadata/` and `data/` directories that are not referenced by any snapshot. This catches files left behind by failed writes, interrupted compactions, or other incomplete operations.

#### How It Works

1. Collect all file paths referenced by all snapshots (manifest lists, manifests, data files) plus the active metadata file and previous metadata log entries
2. Walk the `metadata/` and `data/` directories on the filer
3. For each file not in the reference set:
   - Skip if the file is newer than `orphan_older_than_hours` (safety window)
   - Skip if the file has no attributes (unknown age)
   - Delete the file

#### Before / After

**Before** -- table directory has leftover files from a failed compaction and an old metadata version:

```
metadata/
  v1.metadata.json         <- referenced (previous metadata log)
  v2-<nonce>.metadata.json <- referenced (current)
  snap-100.avro            <- referenced
  compact-failed.avro      <- NOT referenced, 4 days old
  v0.metadata.json         <- NOT referenced, 10 days old
data/
  file-001.parquet         <- referenced
  compact-orphan.parquet   <- NOT referenced, 5 days old
  temp-upload.parquet      <- NOT referenced, 1 hour old
```

**After** (with `orphan_older_than_hours=72`):

```
Deleted:
  metadata/compact-failed.avro    (4 days > 72h)
  metadata/v0.metadata.json       (10 days > 72h)
  data/compact-orphan.parquet     (5 days > 72h)

Kept:
  data/temp-upload.parquet        (1 hour < 72h safety window)
```

Result: `"removed 3 orphan file(s)"`

---

### 4. Rewrite Manifests

Consolidates many small manifest files into fewer large ones. When a table accumulates many manifests (from frequent small commits), query engines must open each one to plan scans. Rewriting reduces this overhead.

#### How It Works

1. Read all data manifests from the current snapshot's manifest list
2. Skip if manifest count is below `min_input_files`
3. Group manifest entries by partition spec ID (for spec-evolved tables, one output manifest per spec)
4. Write merged manifest(s) containing all entries
5. Carry forward any delete manifests unchanged
6. Write a new manifest list and commit a new snapshot

#### Before / After

**Before** -- 12 small manifests from frequent commits:

```
metadata/
  manifest-001.avro   (50 entries)
  manifest-002.avro   (10 entries)
  manifest-003.avro    (5 entries)
  ...
  manifest-012.avro    (8 entries)
  snap-500.avro        <- manifest list pointing to 12 manifests
```

**After** -- 1 merged manifest:

```
metadata/
  merged-<ts>-spec0-<ts>.avro  (all entries combined)
  snap-<ts>-<ts>.avro          <- new manifest list (1 manifest)
```

Result: `"rewrote 12 manifests into 1 (320 entries)"`

#### Skip Conditions

| Condition | Result |
|:---|:---|
| Data manifest count &lt; `min_manifests_to_rewrite` | `"only N data manifests, below threshold of M"` |
| No current snapshot | `"no current snapshot"` |
| No data entries | `"no data entries to rewrite"` |

## Configuration Reference

### Admin Config (Scope Filters)

These control **which tables** the detection scan considers. Set via the Admin UI under the Iceberg Maintenance job type.

| Parameter | Default | Description |
|:---|:---|:---|
| `bucket_filter` | *(blank = all)* | Comma-separated wildcard patterns for table bucket names (`*` and `?` supported) |
| `namespace_filter` | *(blank = all)* | Comma-separated wildcard patterns for namespaces |
| `table_filter` | *(blank = all)* | Comma-separated wildcard patterns for table names |

**Examples:**

```
bucket_filter:    prod-*, staging-*
namespace_filter: analytics, events-*
table_filter:     clicks, orders-*
```

### Where Settings Come From

A table's effective settings are resolved from three places, most specific first:

1. **The table's own Iceberg properties.** What every engine already writes, and what wins by default.
2. **The maintenance configuration** set through `PutTableMaintenanceConfiguration` (per table) or `PutTableBucketMaintenanceConfiguration` (per bucket).
3. **The worker config below**, which is the cluster-wide default.

These Iceberg table properties override the worker config:

| Property | Overrides | Iceberg default |
|:---|:---|:---|
| `write.target-file-size-bytes` | `target_file_size_mb` | 512 MiB |
| `write.delete.target-file-size-bytes` | `delete_target_file_size_mb` | 64 MiB |
| `history.expire.max-snapshot-age-ms` | `snapshot_retention_hours` | 5 days |
| `history.expire.min-snapshots-to-keep` | `max_snapshots_to_keep` | 1 |

Properties win because the compactor has to agree with whoever writes the files: a writer honouring `write.target-file-size-bytes` and a compactor rewriting to a different size would rewrite each other's output forever. Set `table_properties_override` to `false` to invert this and make the maintenance configuration authoritative.

A malformed, zero or negative property is logged and ignored, so a misconfigured table falls back to the worker config rather than stopping its own maintenance.

**Enablement is not part of this.** Iceberg has no property meaning "do not compact this table", so a maintenance configuration with `"status": "disabled"` removes that type's operations outright and no property re-enables them. See [Maintenance Configuration API](#maintenance-configuration-api).

### Worker Config (Thresholds)

These control **how** maintenance operations behave, wherever a table does not say otherwise. Set via the Admin UI or passed as worker config values.

| Parameter | Default | Description |
|:---|:---|:---|
| `snapshot_retention_hours` | `168` (7 days) | Expire snapshots older than this |
| `max_snapshots_to_keep` | `5` | Always keep at least this many newest snapshots |
| `orphan_older_than_hours` | `72` (3 days) | Safety window: only delete orphans older than this |
| `target_file_size_mb` | `256` (MB) | Files smaller than this are compaction candidates |
| `min_input_files` | `5` | Minimum small files in a partition to trigger compaction |
| `apply_deletes` | `true` | When true, compaction applies position and equality deletes to data files. When false, tables with delete manifests are skipped |
| `min_manifests_to_rewrite` | `5` | Minimum manifests before rewriting is triggered |
| `max_commit_retries` | `5` | Max optimistic concurrency retries on version conflict |
| `operations` | `all` | Comma-separated list of operations, or `all` |
| `rewrite_strategy` | `binpack` | `binpack` keeps the existing row order; `sort` rewrites each bin using the table sort order; `auto` sorts tables that declare one and bin-packs the rest |
| `table_properties_override` | `true` | Let a table's own Iceberg properties override this config and its maintenance configuration |

### Operations Selection

The `operations` parameter controls which operations run and in what order. Operations always execute in canonical order regardless of the order specified:

```
compact -> expire_snapshots -> remove_orphans -> rewrite_manifests
```

**Examples:**

```
operations: all                              # run everything (default)
operations: expire_snapshots,remove_orphans  # snapshots + cleanup only
operations: compact                          # compaction only
```

### Admin Runtime Defaults

| Setting | Default | Description |
|:---|:---|:---|
| Enabled | `false` | Must be explicitly enabled |
| Detection interval | `3600s` (1 hour) | How often the worker scans for tables needing maintenance |
| Detection timeout | `300s` | Max time for a detection scan |
| Max jobs per detection | `100` | Cap on proposals per scan |
| Global execution concurrency | `4` | Cluster-wide parallel maintenance jobs |
| Per-worker execution concurrency | `2` | Parallel jobs per worker instance |
| Job max runtime | `3600s` (1 hour) | Timeout for a single maintenance job |
| Retry limit | `1` | Scheduler-level retries for failed jobs |

## Maintenance Configuration API

Five S3 Tables actions configure maintenance per table or per table bucket, and report what the last run did. They are reachable through the AWS CLI and SDKs at their published REST paths.

| Action | Scope | Types |
|:---|:---|:---|
| `PutTableMaintenanceConfiguration` | Table | `icebergCompaction`, `icebergSnapshotManagement` |
| `GetTableMaintenanceConfiguration` | Table | |
| `GetTableMaintenanceJobStatus` | Table | |
| `PutTableBucketMaintenanceConfiguration` | Table bucket | `icebergUnreferencedFileRemoval` |
| `GetTableBucketMaintenanceConfiguration` | Table bucket | |

### Settings

Every numeric setting is an integer between 1 and 2147483647. Values outside that range are rejected rather than stored and then ignored.

| Type | Setting | Effect |
|:---|:---|:---|
| `icebergCompaction` | `targetFileSizeMB` | Files smaller than this are compaction candidates |
| `icebergCompaction` | `strategy` | `auto`, `binpack` or `sort` |
| `icebergSnapshotManagement` | `minSnapshotsToKeep` | Always keep at least this many newest snapshots |
| `icebergSnapshotManagement` | `maxSnapshotAgeHours` | Expire snapshots older than this |
| `icebergUnreferencedFileRemoval` | `unreferencedDays` | Days a file must be unreferenced before it counts as non-current |
| `icebergUnreferencedFileRemoval` | `nonCurrentDays` | Further days before a non-current file is deleted |

Orphan removal deletes in one step rather than marking files non-current first, so a file is deleted once it is older than `unreferencedDays` **plus** `nonCurrentDays`. A `3`/`10` configuration deletes on day thirteen.

### Disabling maintenance

```bash
aws s3tables put-table-maintenance-configuration \
  --table-bucket-arn arn:aws:s3tables:us-east-1:000000000000:bucket/analytics \
  --namespace sales --name orders \
  --type icebergSnapshotManagement \
  --value '{"status":"disabled"}' \
  --endpoint-url http://localhost:8333
```

A disabled type stops running for that table immediately. This is the one control no table property can override.

### Setting a target file size

```bash
aws s3tables put-table-maintenance-configuration \
  --table-bucket-arn arn:aws:s3tables:us-east-1:000000000000:bucket/analytics \
  --namespace sales --name orders \
  --type icebergCompaction \
  --value '{"status":"enabled","settings":{"icebergCompaction":{"targetFileSizeMB":512,"strategy":"auto"}}}' \
  --endpoint-url http://localhost:8333
```

Remember that `write.target-file-size-bytes` on the table beats this unless `table_properties_override` is `false`.

### Reading job status

```bash
aws s3tables get-table-maintenance-job-status \
  --table-bucket-arn arn:aws:s3tables:us-east-1:000000000000:bucket/analytics \
  --namespace sales --name orders \
  --endpoint-url http://localhost:8333
```

Every job type is reported as `Not_Yet_Run`, `Successful`, `Failed` or `Disabled`, with the timestamp of the last run and a failure message where there is one. Manifest rewriting and delete-file rewriting have no AWS equivalent and are reported under `icebergCompaction`.

### Differences from AWS

- `GetTableMaintenanceConfiguration` returns an empty configuration for a table that has never been configured, rather than synthesising defaults. The effective values come from the worker config, which this API cannot express.
- Job status is last-run only. There is no retained history behind it.
- The `z-order` compaction strategy is rejected, because the worker cannot produce that layout and accepting it would mean storing one strategy and running another.
- Disabling `icebergCompaction` also stops manifest and delete-file rewriting, since those ride with it.

## Execution Order

Operations execute in a fixed order that follows Iceberg best practices:

```
compact -> expire_snapshots -> remove_orphans -> rewrite_manifests
```

This order matters because:

1. **Compact** creates a new snapshot with merged files and marks originals as deleted
2. **Expire Snapshots** drops old snapshots, making the original (now-deleted) files unreferenced
3. **Remove Orphans** cleans up unreferenced files from disk (including compaction leftovers)
4. **Rewrite Manifests** consolidates the manifests accumulated from compaction and other commits

If one operation fails, subsequent operations still attempt to run. The job reports partial success with per-operation results.

## Commit Protocol

All metadata-modifying operations (compact, expire_snapshots, rewrite_manifests) use an optimistic concurrency protocol:

1. **Read** current metadata from the table entry's xattr
2. **Plan** the changes (build new manifests, manifest lists, etc.)
3. **Write** new metadata file with a unique name (`v&lt;N&gt;-&lt;timestamp&gt;.metadata.json`)
4. **Compare-and-swap** the table entry's xattr: verify the stored `metadataVersion` matches what was read, then update atomically
5. On **version conflict**, clean up the staged metadata file and retry with exponential backoff (50ms, 100ms, 200ms, ... capped at 5s)

Each operation also includes a **stale-plan guard**: if the current snapshot has changed since planning began, the operation aborts rather than committing against outdated state.

## Detection

The detection scan runs periodically (default: hourly) and evaluates each table using metadata-only heuristics (no manifest reading):

- Snapshot count exceeds `max_snapshots_to_keep`
- Any snapshot is older than `snapshot_retention_hours`

Tables matching either condition are proposed as maintenance jobs. The actual operations then perform precise filtering (e.g., `expire_snapshots` checks both conditions together before expiring).

## Monitoring

Maintenance jobs report progress and results through the worker framework:

- **Activity events**: scan start, scan complete (with table count), per-operation start/complete
- **Progress updates**: percentage based on completed operations, with per-bin granularity during compaction
- **Job result summary**: per-operation outcomes joined by semicolons
- **Structured metrics**: per-operation metrics in `OutputValues` with dot-prefixed keys

Example result summary:
```
compact: compacted 15 files into 3 (across 3 bins);
expire_snapshots: expired 2 snapshot(s), deleted 8 unreferenced file(s);
remove_orphans: removed 4 orphan file(s);
rewrite_manifests: rewrote 7 manifests into 1 (120 entries)
```

### Structured Metrics

Each operation returns structured metrics in the job's `OutputValues` map, keyed with the operation name as prefix:

| Key | Description |
|:---|:---|
| `compact.files_merged` | Number of input files merged |
| `compact.files_written` | Number of output files produced |
| `compact.bins` | Number of compaction bins processed |
| `compact.duration_ms` | Time spent on compaction |
| `expire_snapshots.snapshots_expired` | Number of snapshots removed |
| `expire_snapshots.files_deleted` | Unreferenced files cleaned up |
| `expire_snapshots.duration_ms` | Time spent on expiration |
| `remove_orphans.orphans_removed` | Number of orphan files deleted |
| `remove_orphans.duration_ms` | Time spent on orphan removal |
| `rewrite_manifests.manifests_rewritten` | Number of data manifests consolidated |
| `rewrite_manifests.entries_total` | Total manifest entries in rewritten output |
| `rewrite_manifests.duration_ms` | Time spent on manifest rewriting |

## Limitations

- **Client-side CAS**: the compare-and-swap on metadata version is enforced client-side. Concurrent maintenance on the same table should be avoided (the deduplication key prevents this under normal scheduling).
- **Bucket-scoped file removal**: as in AWS, `icebergUnreferencedFileRemoval` is configured on the table bucket rather than per table.
- **Single filer per job**: detection tries each filer address in the cluster context until one connects, but each execution job uses the single filer address recorded in its proposal.

## See Also

- [S3 Table Bucket](./S3-Table-Bucket.md) -- Table bucket concepts and file layout
- [S3 Table Bucket Commands](./S3-Table-Bucket-Commands.md) -- CLI examples for creating and managing table buckets
- [SeaweedFS Iceberg Catalog](./SeaweedFS-Iceberg-Catalog.md) -- Using the Iceberg REST Catalog with Spark, Trino, Dremio, and other engines
- [S3 Tables Security](./S3-Tables-Security.md) -- IAM permissions for table buckets
- [Worker](./Worker.md) -- Worker framework overview
