---
id: Optimization-for-Many-Small-Buckets
title: "Optimization for Many Small Buckets"
sidebar_label: "Optimization for Many Small Buckets"
---

When using SeaweedFS with the S3 API, each S3 bucket maps to a separate **collection**, and each collection maintains its own set of volumes. With default settings, this can lead to excessive resource consumption when you have many small buckets.

## The Problem

With defaults:
- **Volume size limit**: 30 GB (`-volumeSizeLimitMB=30000`)
- **Volume growth count**: 7 volumes pre-created per collection (for `000` replication)

So each new bucket triggers creation of up to 7 volumes of 30 GB each. For 1,000 buckets, that could mean 7,000 volumes — each consuming file descriptors, memory for indexes, and compaction overhead — even if each bucket only stores a few megabytes of data.

## Recommended Settings

### 1. Reduce Volume Size Limit

Lower `-volumeSizeLimitMB` on the master server so volumes fill up and seal faster, reducing wasted space per bucket:

```
weed master -volumeSizeLimitMB=1000
```

Choose a value proportional to the expected data per bucket. If most buckets hold less than 100 MB, even `-volumeSizeLimitMB=100` may be appropriate.

### 2. Reduce Volume Growth Count

By default, SeaweedFS pre-creates 7 volumes at once for each collection with no replication. Reduce this to 1 in `master.toml`:

```toml
[master.volume_growth]
copy_1 = 1
copy_2 = 1
copy_3 = 1
copy_other = 1
```

This is the single most impactful change for many-bucket workloads. With 1,000 buckets, this reduces the volume count from ~7,000 to ~1,000.

Generate a template config with:
```bash
weed scaffold -config=master
```

### 3. Keep Volume Preallocate Disabled

When `-volumePreallocate=true`, each volume reserves its full `volumeSizeLimitMB` on disk immediately. For many small buckets, keep it at the default (`false`):

```
weed master -volumePreallocate=false
```

### 4. Use LevelDB Index

With many volumes, the memory cost of in-memory indexes adds up (roughly 20 bytes per file per volume). Use LevelDB to reduce memory consumption:

```
weed volume -index=leveldb
```

See [Optimization](./Optimization.md) for details on LevelDB index flavors.

## Design Considerations

Even with optimized settings, thousands of buckets means thousands of collections and volumes. Each volume has operational costs:

| Resource | Impact |
|----------|--------|
| File descriptors | Each volume opens `.dat` and `.idx` files |
| Memory | Index data per volume (in-memory mode) |
| Compaction | Vacuuming runs per volume |
| Startup time | More volumes = slower volume server startup |

If your application allows it, consolidating objects into fewer buckets (using key prefixes like `tenant1/`, `tenant2/` for logical separation) is more efficient than thousands of separate buckets. But if the architecture requires many buckets, the settings above will significantly reduce resource consumption.

## Example Configuration

For a workload with ~3,000 small buckets, each holding under 1 GB:

**Master server:**
```
weed master -volumeSizeLimitMB=512 -volumePreallocate=false
```

**master.toml:**
```toml
[master.volume_growth]
copy_1 = 1
copy_2 = 1
copy_3 = 1
copy_other = 1
```

**Volume server:**
```
weed volume -index=leveldb
```

## See Also

* [Optimization](./Optimization.md)
* [Volume Management](./Volume-Management.md)
* [Amazon S3 API](./Amazon-S3-API.md)
