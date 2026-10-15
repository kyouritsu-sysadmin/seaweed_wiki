---
id: Mount-Remote-Storage
title: "Mount Remote Storage"
sidebar_label: "Mount Remote Storage"
---

After [Configure Remote Storage](./Configure-Remote-Storage.md), you will get a storage name `cloud1`.

## Mount a Remote Storage
Now you can run `remote.mount` in `weed shell`:
```
> remote.mount -h
Usage of remote.mount:
  -dir string
    	a directory in filer
  -nonempty
    	allows the mounting over a non-empty directory
  -remote string
    	a directory in remote storage, ex. <storageName>/<bucket>/path/to/dir
  -metadataStrategy string
    	lazy: skip upfront metadata pull; eager: full metadata pull (default "eager")
  -listingCacheTTL int
    	seconds to cache remote directory listings (0 = disabled)

> help remote.mount
  remote.mount	# mount remote storage and pull its metadata

	# assume a remote storage is configured to name "s3_1"
	remote.configure -name=cloud1 -type=s3 -s3.access_key=xyz -s3.secret_key=yyy

	# mount and pull one bucket (eager metadata pull, the default)
	remote.mount -dir=/xxx -remote=cloud1/bucket
	# mount and pull one directory in the bucket
	remote.mount -dir=/xxx -remote=cloud1/bucket/dir1

	# lazy mount: skip upfront metadata pull, fetch on demand
	remote.mount -dir=/xxx -remote=cloud1/bucket -metadataStrategy=lazy
	# lazy mount with on-demand directory listing cached for 5 minutes
	remote.mount -dir=/xxx -remote=cloud1/bucket -metadataStrategy=lazy -listingCacheTTL=300

	# after mount, start a separate process to write updates to remote storage
	weed filer.remote.sync -filer=<filerHost>:<filerPort> -dir=/xxx

```

With `remote.mount`, you can mount one bucket or any directory in the bucket.

## Metadata Strategies

Two flags control how metadata is handled:

- **`-metadataStrategy`**: `eager` (default) pulls all metadata at mount time; `lazy` skips the upfront pull and fetches file metadata on first access.
- **`-listingCacheTTL`**: `0` (default) disables on-demand directory listing; `>0` enables automatic directory listing from remote, cached for the specified number of seconds.

These flags can be combined. Here are all four combinations:

### Combination Reference

| `-metadataStrategy` | `-listingCacheTTL` | Mount command | Behavior |
|---|---|---|---|
| `eager` | `0` | `remote.mount -dir=/xxx -remote=cloud1/bucket` | **Full upfront pull.** All metadata is downloaded at mount time. Listings and file access are instant. Use `remote.meta.sync` to refresh stale data. |
| `eager` | `>0` | `remote.mount -dir=/xxx -remote=cloud1/bucket -listingCacheTTL=300` | **Full upfront pull + auto-refreshing listings.** Same as eager, but directory listings automatically refresh from remote after the TTL expires. Keeps listings up-to-date when remote data changes over time without manual `remote.meta.sync`. |
| `lazy` | `0` | `remote.mount -dir=/xxx -remote=cloud1/bucket -metadataStrategy=lazy` | **Fully on-demand.** No upfront cost. File metadata is fetched on first access (stat, read). Directory listings are empty until files are accessed individually. Best for very large buckets where you access specific files by known paths. |
| `lazy` | `>0` | `remote.mount -dir=/xxx -remote=cloud1/bucket -metadataStrategy=lazy -listingCacheTTL=300` | **On-demand files + auto-populating listings.** No upfront cost. Directory listings automatically fetch from remote and cache for the TTL. Individual files are also fetchable on demand. Best for large buckets where you need both `ls` and direct file access without upfront cost. |

### Comparison

| | Eager | Eager + TTL | Lazy | Lazy + TTL |
|---|---|---|---|---|
| **Mount time** | Slow (pulls all metadata) | Slow (pulls all metadata) | Instant | Instant |
| **`ls` / `ListObjects`** | Instant (local) | Instant, auto-refreshes | Empty | Auto-fetched from remote |
| **File stat/read** | Instant (local) | Instant (local) | First access fetches | First access fetches |
| **Stale listings** | Manual `remote.meta.sync` | Auto-refreshed per TTL | N/A (empty) | Auto-refreshed per TTL |
| **Remote API calls** | Only at mount + sync | Mount + periodic listing | Per file access | Per file access + periodic listing |
| **Best for** | Small/medium buckets | Buckets with external writes | Sparse access by known path | Large buckets, general use |

`remote.unmount` will drop all local metadata and cached file content.

### Repeatedly Update Metadata

For eager mounts without `-listingCacheTTL`, the data on the cloud may change and local metadata becomes stale. To `unmount` first and `mount` again can work but is costly, since all data has to be cached again.

To refresh the metadata changes, you can run this on the mounted directory or any sub directories, e.g.:
```
	remote.meta.sync -dir=/xxx
	remote.meta.sync -dir=/xxx/sub/dir
```
This will update local metadata accordingly and still keep file contents that are not changed.

If the data on the cloud changes often, you can create a cronjob to run it. Or you can add this command to the admin scripts defined in `master.toml`, to run it regularly.

With `-listingCacheTTL`, directory listings refresh automatically, reducing the need for manual `remote.meta.sync`.

## Write Back Changes to Remote Storage

The filer does not push to remote on its own. Local changes — creates, updates, and deletes inside the mounted directory — only reach the remote bucket if you opt in to one of the write-back paths below. If neither is running, the mount behaves as a read-only cache.

### Read-Only Mount (Remote → Local Only)

If the remote bucket is the source of truth and the filer is just a cache, do not run `weed filer.remote.sync` and do not run `remote.copy.local`. With neither push path enabled, deleting a file from the filer only drops the local cache entry; the upstream blob is untouched and the metadata will reappear on the next `remote.meta.sync`.

A typical read-only setup combines a pull command, a warm-up command, and an evict command — all one-way from the remote's perspective:

| Concern | Command | Direction |
|---|---|---|
| Pick up new files added to the bucket out-of-band | `remote.meta.sync -dir=/xxx` (cron) | Remote → Local (metadata only) |
| Pre-warm hot files locally | `remote.cache -dir=/xxx -include=...` | Remote → Local (data) |
| Reclaim local disk on cold files | `remote.uncache -dir=/xxx -minAge=...` | Local-only (remote untouched) |

If `-listingCacheTTL` is set on `remote.mount`, listings refresh automatically and `remote.meta.sync` is rarely needed.

### Option 1: Continuous Sync with `weed filer.remote.sync`

For **continuous, real-time synchronization**, start a separate process `weed filer.remote.sync -dir=xxx`. This process will listen to filer change events and write any changes back to the remote storage automatically.

```
weed filer.remote.sync -filer=<filerHost>:<filerPort> -dir=xxx
```

The process is designed to be worry-free. It should automatically resume if stopped, and can reconnect automatically.

**Use this when:**
- You need real-time synchronization of all changes
- Files are being continuously created, modified, or deleted
- You want automatic background synchronization

### Option 2: On-Demand Sync with `remote.copy.local`

For **on-demand, batch synchronization** of local-only files, use the `remote.copy.local` command in `weed shell`. This is useful for one-time or scheduled backups.

**Use this when:**
- You have existing local files that were never synced to remote
- You deleted filer logs and need to re-sync existing files
- You want to run periodic batch backups via cron
- You need fine-grained control over which files to sync (using filters)


## Copy Local-Only Files to Remote

The `remote.copy.local` command synchronizes local-only files to remote storage. This is useful when you have files that were created locally and need to be backed up to remote storage.

```
> help remote.copy.local
  remote.copy.local	# copy local-only files to remote storage for mounted directories

	# copy all local-only files in a mounted directory to remote
	remote.copy.local -dir=/xxx

	# copy with filters
	remote.copy.local -dir=/xxx/some/sub/dir -include=*.pdf
	remote.copy.local -dir=/xxx/some/sub/dir -exclude=*.txt
	remote.copy.local -minSize=1024000    # copy files larger than 100K
	remote.copy.local -maxSize=10240000   # copy files smaller than 10MB

	# force update even if remote file exists
	remote.copy.local -dir=/xxx -forceUpdate=true

	# delete extraneous files from remote storage (files that do not exist locally), similar to rsync --delete
	remote.copy.local -dir=/xxx -delete

	# dry run to see what would be copied
	remote.copy.local -dir=/xxx -dryRun=true

	This command only copies files that don't have remote entries yet.
	Files that are already synchronized with remote storage are skipped.

	The actual data copying goes through volume servers in parallel.
```

## Command Comparison

Here's a comprehensive comparison of remote storage synchronization and caching commands:

### Global Command Comparison

| Feature | `weed filer.remote.sync` | `remote.copy.local` | `remote.meta.sync` | `remote.cache` | `remote.uncache` |
|---------|-------------------------|---------------------|--------------------|----------------|------------------|
| **Type** | Long-running daemon | Shell command (batch) | Shell command (batch) | Shell command (batch) | Shell command (batch) |
| **Purpose** | Continuous sync (Local → Remote) | Backup local-only files (Local → Remote) | Refresh local index from remote (metadata only) | Download to local cache (Remote → Local) | Free up local storage (Local → Delete) |
| **Data Flow** | Local → Remote (metadata + data) | Local → Remote | Remote → Local (metadata only) | Remote → Local | Local-only (remote untouched) |
| **Trigger** | Automatic (file events) | Manual / Cron | Manual / Cron | Manual / Cron | Manual / Cron |
| **File Scope** | All changes | Local-only files | All files in dir | Files on remote | Cached files |
| **Filters** | None (syncs all) | Yes (`include`/`exclude`) | No | Yes (`include`/`exclude`) | Yes (`include`/`exclude`) |
| **Force** | Automatic | `-forceUpdate` | N/A | N/A | N/A |
| **Dry Run** | No | `-dryRun` | No | `-dryRun` | `-dryRun` |
| **Use Case** | Active writes, consistency | Backups, recovery | Detect external uploads to bucket | Warm-up, pre-fetching | Save disk space |



### Typical Workflow

1. **Mount remote storage**: `remote.mount -dir=/buckets/mybucket -remote=s3_1/bucket`
2. **Start continuous sync** (optional): `weed filer.remote.sync -filer=localhost:8888 -dir=/buckets/mybucket`
3. **Create local files**: Write files directly to `/buckets/mybucket/`
4. **Batch backup** (if not using filer.remote.sync): `remote.copy.local -dir=/buckets/mybucket`
5. **Free up space**: `remote.uncache -dir=/buckets/mybucket -minSize=10240000`
6. **Warm up cache**: `remote.cache -dir=/buckets/mybucket -include=*.pdf`


## Unmount a Remote Storage

Similarly, running `remote.unmount -dir=xxx` can unmount a remote storage. However, this means all cached data and metadata will be deleted.
And if `weed filer.remote.sync -filer=&lt;filerHost&gt;:&lt;filerPort&gt; -dir=xxx` was not run, the local updates have not been uploaded to the remote storage, so these local updates will be lost.

The `weed filer.remote.sync` will stop as soon as it sees the directory is unmounted. So the local deletion will not propagate back to the cloud, avoiding possible data loss.

