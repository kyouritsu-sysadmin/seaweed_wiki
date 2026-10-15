---
id: Cloud-Tier
title: "Cloud Tier"
sidebar_label: "Cloud Tier"
---

## Motivation

> NOTE: SeaweedFS provides **two mechanisms** to use cloud storage:
>  1) [SeaweedFS Cloud Drive](https://github.com/seaweedfs/seaweedfs/wiki/Cloud-Drive-Benefits)
>     - in this case, you can **mount** an S3 bucket to the Seaweedfs file system (in the filer), and access the remote files
>       through SeaweedFS. Effectively, SeaweedFS caches the files from the cloud storage.
>     - In this mode, the file structure in cloud store is exactly matching the SeaweedFS structure - so every
>       file in SeaweedFS will also become a file in the cloud storage provider.
>     - This is useful in case you want to use the files inside the cloud provider's infrastructure.
>     - However, this does **not support file encryption** in any way (obviously), as the files are put to Cloud Storage as is.
>  2) **Tiered Storage with Cloud Tier** (**&lt;== You are here**)
>     - In this mode, seaweedFS **moves full volume files to the cloud storage provider**, so files which are 1 GB (in our case) big.
>     - This mode supports [Filer Data Encryption](https://github.com/seaweedfs/seaweedfs/wiki/Filer-Data-Encryption) transparently.
>     - The chunk files uploaded to the cloud provider are not usable outside of SeaweedFS.



Cloud storage is an ideal place to backup warm data. Its storage is scalable, and cost is usually low compared to on-premise storage servers. Uploading to the cloud is usually free. However, usually the cloud storage access is not free and slow. 

SeaweedFS is fast. However, its capacity is limited by available number of volume servers. 

One good way is to combine SeaweedFS' fast local access speed with the cloud storage's elastic capacity.

Assuming hot data is 20% and warm data is 80%. We can move the warm data to the cloud storage. The access for the warm data will be slower, but this can free up 80% servers, or repurpose them for faster local access, instead of just storing warm data with little access. All of this is transparent to SeaweedFS users.

With fixed number of servers, this transparent cloud integration literally gives SeaweedFS unlimited capacity, in addition to its fast speed. Just add more local SeaweedFS volume servers to increase the throughput. 

## Design
If one volume is tiered to the cloud, 
* The volume is marked as readonly.
* The index file is still local
* The `.dat` file is moved to the cloud. 
* The same O(1) disk read is applied to the remote file. When requesting a file entry, a single range request retrieves the entry's content.

## Benefits

Compared to direct S3 storage, this is both faster and cheaper!

* Cheaper!
  * Reduce the API access cost to almost nothing, which is often forgotten at first, but will hit your wallet unexpectedly after you go all-in with S3.
  * Use lower cost storage tiers.
  * Compression
* Faster!
  * Local access for recent data, skipping one internet trip.
  * Access old data from S3 with O(1) http call.

## Usage
1. Use `weed scaffold -config=master` to generate `master.toml`, tweak it, and start master server with the `master.toml`.
1. Use `volume.tier.upload` in `weed shell` to move volumes to the cloud.
1. Use `volume.tier.download` in `weed shell` to move volumes to the local cluster.
1. Use `volume.tier.compact` in `weed shell` to reclaim space from deleted files on the cloud.

## Configuring Storage Backend

The following storage backends are currently supported:
- S3
- Rclone

### S3

Multiple S3 buckets are supported. Usually you just need to configure one backend.

```
# The storage backends are configured on the master, inside master.toml
[storage.backend]
	[storage.backend.s3.default]
	enabled = true
	aws_access_key_id     = ""     # if empty, loads from the shared credentials file (~/.aws/credentials).
	aws_secret_access_key = ""     # if empty, loads from the shared credentials file (~/.aws/credentials).
	region = "us-west-1"
	bucket = "one_bucket"          # an existing bucket
	storage_class = "STANDARD_IA"

	[storage.backend.s3.name2]
	enabled = true
	aws_access_key_id     = ""     # if empty, loads from the shared credentials file (~/.aws/credentials).
	aws_secret_access_key = ""     # if empty, loads from the shared credentials file (~/.aws/credentials).
	region = "us-west-2"
	bucket = "one_bucket_two"          # an existing bucket
        force_path_style = "false"     # The default value is true. If you are using Alibaba Cloud OSS (path style is no longer supported), please set it to false.
	storage_class = "STANDARD_IA"

```

### Rclone

> NOTE: Since version 3.60 the rclone backend is removed
> in standard builds to reduce size for common use cases. Use the `_full` weed binary.

Here's an example of a configuration for an Rclone storage backend:

```
[storage.backend]
	[storage.backend.rclone.default]
	enabled = true
	remote_name = "my-onedrive"
	key_template = "SeaweedFS/{{ slice . 0 2 }}/{{ slice . 2 4 }}/{{ slice . 4 }}"  # optional
```

Where `my-remote` must correspond to what's configured in `~/.config/rclone/rclone.conf`:
```
[my-onedrive]
type = onedrive
...
```

The optional `key_template` property makes it possible to choose how the individual volume files are eventually named in the storage backend.  
The template has to follow the [text/template](https://pkg.go.dev/text/template) syntax, where `.` is a UUID string representing the volume ID.  
In this example, files would be named as such in OneDrive:
```
SeaweedFS/
  5f/
    e5/
      03d8-0aba-4e42-b1c8-6116bf862f71
```

### Configuration

After changing the master config, you need to **restart the volume servers** so that they pull the updated configuration
from the master. If you forget to do this, you'll get an error message about no storage backends being configured.

After this is configured, you can use this command to upload the .dat file content to the cloud.

```
// move the volume 37.dat to the s3 cloud
volume.tier.upload -dest=s3 -collection=benchmark -volumeId=37
// or
volume.tier.upload -dest=s3.default -collection=benchmark -volumeId=37
// if for any reason you want to move the volume to a different bucket
volume.tier.upload -dest=s3.name2 -collection=benchmark -volumeId=37

```

## Compacting Cloud Tier Volumes

When files are deleted from cloud-tiered volumes, the space on the remote storage is not automatically reclaimed. Over time this can cause cloud storage usage to grow indefinitely despite deletions. Use `volume.tier.compact` to reclaim this space.

The command automates the process of downloading the volume data, compacting it locally to remove deleted entries, and re-uploading the compacted data back to the cloud.

```
// compact a specific remote volume
volume.tier.compact -volumeId=37

// compact all remote volumes in a collection with >20% garbage
volume.tier.compact -collection=mybucket -garbageThreshold=0.2

// compact all remote volumes across all collections
volume.tier.compact -collection=".*" -garbageThreshold=0.3
```

The `-garbageThreshold` flag (default `0.3`) controls the minimum ratio of deleted data before compaction is triggered. Volumes below this threshold are skipped.

To run this periodically, add `volume.tier.compact -collection=".*" -garbageThreshold=0.3` to the admin script plugin worker, or use a cron job:
```
echo "lock;volume.tier.compact -collection=\".*\" -garbageThreshold=0.3;unlock" | weed shell
```

**Note:** Compaction temporarily requires enough local disk space to hold the volume's `.dat` file during the download and compaction steps.

## Automated Tiering

Add `volume.tier.upload -dest s3 -fullPercent=95 -quietFor=1h` to the admin script plugin worker configuration via the admin UI at `/plugin`. The admin script worker handles locking automatically, so you do not need explicit `lock`/`unlock` commands.

```bash
# Start admin server and worker
weed admin -master=localhost:9333
weed worker -admin=localhost:23646
```

Or you can run the `weed shell` periodically in some cron job:
```
echo "lock;volume.tier.upload -dest s3 -fullPercent=95 -quietFor=1h;unlock" | weed shell
```

> **Legacy note:** Previously, this was configured in `master.toml` under `[master.maintenance]`. That mechanism is skipped when an admin server is connected. New deployments should use the admin script plugin worker instead. See [Migrate Maintenance Scripts to Admin Script Plugin](./Migrate-Maintenance-Scripts-to-Admin-Script-Plugin.md) for details.
