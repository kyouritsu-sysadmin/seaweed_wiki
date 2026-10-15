---
id: Cache-Remote-Storage
title: "Cache Remote Storage"
sidebar_label: "Cache Remote Storage"
---

After [Mount Remote Storage](./Mount-Remote-Storage.md), you can already read or write files in the mounted directory.

However, sometimes you want to have a command to warm up the file content directly, instead of lazy cache.

And sometimes you may want to reduce local storage usage, to `uncache` the file content.

## Cache Mounted File Content
In `weed shell`, checkout `remote.cache` and `remote.uncache`:

```
> help remote.cache
  remote.cache	# cache the file content for mounted directories or files

	# assume a remote storage is configured to name "s3_1"
	remote.configure -name=s3_1 -type=s3 -s3.access_key=xxx -s3.secret_key=yyy
	# mount and pull one bucket
	remote.mount -dir=xxx -remote=s3_1/bucket

	# after mount, run one of these command to cache the content of the files
	remote.cache                     # cache on all mounted directories
	remote.cache -dir=/xxx
	remote.cache -dir=/xxx/some/sub/dir
	remote.cache -dir=/xxx/some/sub/dir -include=*.pdf
	remote.cache -dir=/xxx/some/sub/dir -exclude=*.txt
	remote.cache -maxSize=1024000    # cache files smaller than 100K
	remote.cache -maxAge=3600        # cache files less than 1 hour old

	This is designed to run regularly. So you can add it to some cronjob.
	If a file is already synchronized with the remote copy, the file will be skipped to avoid unnecessary copy.

	The actual data copying goes through volume severs in parallel.

> help remote.uncache
  remote.uncache	# keep the metadata but remote cache the file content for mounted directories or files

	This is designed to run regularly. So you can add it to some cronjob.
	If a file is not synchronized with the remote copy, the file will be skipped to avoid loss of data.

	remote.uncache                     # uncache on all mounted directories
	remote.uncache -dir=/xxx
	remote.uncache -dir=/xxx/some/sub/dir
	remote.uncache -dir=/xxx/some/sub/dir -include=*.pdf
	remote.uncache -dir=/xxx/some/sub/dir -exclude=*.txt
	remote.uncache -minSize=1024000    # uncache files larger than 100K
	remote.uncache -minAge=3600        # uncache files older than 1 hour

```

## Note

If you want some more flexibility to decide which file to cache or uncache, please help to send a PR.
