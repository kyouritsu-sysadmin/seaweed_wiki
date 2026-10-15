---
id: Gateway-to-Remote-Object-Storage
title: "Gateway to Remote Object Storage"
sidebar_label: "Gateway to Remote Object Storage"
---

# Intro

The [Mount Remote Storage](./Mount-Remote-Storage.md) feature can mount one folder in a remote object store bucket. 

However, 
* You may have multiple buckets in one or more cloud storages. 
* You may want to create new buckets or remove old buckets. 

How to synchronize them automatically?

# Design of Gateway to Remote Object Store

![SeaweedFS Gateway to RemoteObjectStorage](https://raw.githubusercontent.com/seaweedfs/seaweedfs/master/note/SeaweedFS_Gateway_RemoteObjectStore.png)

The `weed filer.remote.gateway -createBucketAt=cloud1` process can mirror local changes to remote object storage, i.e.:

* Local new buckets will be automatically mounted to the remote storage specified in `-createBucketAt`
* Local deleted buckets will be automatically deleted in its remote storage.
* All local changes under the mounted buckets are uploaded to its remote storage.

# Assumption

One or more cloud storages have been configured following [Configure Remote Storage](./Configure-Remote-Storage.md) .

# Setup Steps

## 1. (Optional) Mount all existing remote buckets as local buckets

If there are some existing buckets, run this to mount all of them as local buckets and synchronize their metadata to the local SeaweedFS cluster.

```
# in "weed shell"
> remote.mount.buckets -remote=cloud1 -apply
```

## 2. Upload local changes in `/buckets`

Start a `weed filer.remote.gateway` and let it run continuously.

If new buckets are created locally, this will also automatically create new buckets in the specified remote storage.

It is OK to pause it, and resume.
It is also OK to change the `-createBucketAt=xxx` value to a different one, since it only affects new bucket creation.

```
$ weed filer.remote.gateway -createBucketAt=cloud1
synchronize /buckets, default new bucket creation in cloud1 ...
```

In some cloud storage vendor, the bucket names need to be unique. To address this, run it with `-createBucketWithRandomSuffix` option.
It will create buckets with name as `localBucketName-xxxx`, appending a random number as the suffix.
```
$ weed filer.remote.gateway -createBucketAt=cloud1 -createBucketWithRandomSuffix
```



## 3. (Optional) Cache or uncache

Run these commands as needed to speed up access or to release disk spaces.

The basic implementation mechanism is the same as other mounted folders.
You may need to create a cronjob to run it periodically.

```
# in "weed shell"

# cache all pdf files in all mounted buckets
> remote.cache -include=*.pdf

# cache all pdf files in a bucket
> remote.cache -dir=/buckets/some-bucket -include=*.pdf

# uncache all files older than 1 hour and larger than 10KB
> remote.uncache -minAge=3600 -minSize=10240
```
