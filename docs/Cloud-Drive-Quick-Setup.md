---
id: Cloud-Drive-Quick-Setup
title: "Cloud Drive Quick Setup"
sidebar_label: "Cloud Drive Quick Setup"
---

To users not familiar with SeaweedFS, there seems many things to learn.
But for SeaweedFS Cloud Drive, the setup is easy.

# Setup a simple SeaweedFS cluster

To use Cloud Drive, a simple SeaweedFS cluster without HA is fine. The cloud storage is a backup copy already.

Since very likely you may want to use S3, the following will include S3 setup.

Run this to have a SeaweedFS cluster:
```
  $ weed server -s3
```

## Setup S3 credentials
Start a `weed shell`
```
$ weed shell
master: localhost:9333 filer: localhost:8888
> s3.configure -h
> s3.configure -user me -access_key=any -secret_key=any -buckets=bucket1 -actions=Read,Write,List,Tagging,Adminf
```

# Configure Remote Storage

This step will configure a remote storage and how to access it.

The following command created a remote storage named "s5". 

In `weed shell`:
```
> remote.configure -h
# For non AWS S3 vendors
> remote.configure -name=s5 -type=s3 -s3.access_key=xxx -s3.secret_key=yyy -s3.endpoint=http://localhost:8333
{
  "type": "s3",
  "name": "s5",
  "s3AccessKey": "any",
  "s3SecretKey": "***",
  "s3Region": "us-east-2",
  "s3Endpoint": "http://localhost:8333"
}
# For AWS S3
> remote.configure -name=s5 -type=s3 -s3.access_key=xxx -s3.secret_key=yyy -s3.region=us-east-2
> remote.configure
{
  "type": "s3",
  "name": "s5",
  "s3AccessKey": "any",
  "s3SecretKey": "***",
  "s3Region": "us-east-2"
}
# For aliyun OSS
> remote.configure -name=s5 -type=aliyun -aliyun.access_key=xxx -aliyun.secret_key=yyy -aliyun.endpoint=http://oss-cn-wulanchabu-internal.aliyuncs.com -aliyun.region=oss-cn-wulanchabu  -s3.storage_class=STANDARD -s3.support_tagging=false
```

# Mount Remote Storage

The remote storage can be mounted to any directory. Here we mounted to the local `bucket1`:
```
> remote.mount -dir=/buckets/bucket1 -remote=s5/bucketxxx -nonempty
> remote.mount -dir=/buckets/bucket1 -remote=s5/bucketxxx/path/to/dir -nonempty
```
If any errors, go back to `remote.configure` and make sure everything is correct.

# Test the setup

Right now you can already try to read or write to folder `/buckets/bucket1`.
The read may feel a bit slow since it needs to download first. 

# Setup write back

This is needed only if you want local changes go back to the remote storage. 

For this example, just start one process as this:
```
$ weed filer.remote.sync -dir=/buckets/bucket1
```

This command will continuously write back changes of this mounted directory to the cloud storage.

This command is designed to run as a background process. It can be paused by `ctl+c`. It can also try to re-connect to filer if disconnected.

# Setup cache and uncache process

Since only metadata are pulled and there are no file content cache, reading remote files are somewhat slow.

You may want to cache all or some of the files, to make sure the first read is always fast.
You may want to uncache a group of files, to save some local storage.

These cache or uncache jobs can vary wildly. Here are some examples:

```
# cache a whole folder
> remote.cache -dir=/buckets/bucket1/a/b/c  
# cache all parquet files
> remote.cache -dir=/buckets/bucket1 -include=*.parquet 
# cache file size between 1024 and 10240 byte
> remote.cache -dir=/buckets/bucket1 -minSize=1024 -maxSize=10240

# uncache file size older than 3600 seconds
> remote.uncache -dir=/buckets/bucket1 -maxAge=3600
# uncache file size more than 10240 bytes
> remote.uncache -dir=/buckets/bucket1 -minSize=10240

```

These jobs can be setup as scheduled cron jobs.

# Detect Cloud Data Updates

If the cloud storage has other processes writing to it, the mounted folder needs to know the new files.
You can setup cron jobs to run `remote.meta.sync` regularly.

```
> remote.meta.sync -h
> remote.meta.sync -dir=/buckets/bucket1

```


