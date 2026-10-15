---
id: FAQ
title: "FAQ"
sidebar_label: "FAQ"
---

### How many volumes do I need?

The SeaweedFS volume here is different from common storage volume.
| SeaweedFS Volume | Common Volume |
| --- | --- |
| A disk file | A disk |

The following is all about SeaweedFS volumes.

SeaweedFS assumes there are many SeaweedFS volumes. Data placement, replication, collection, disk type, S3 buckets, TTL, CSI mount, etc, are all based on volumes. So if the error is `no free volumes left`, please add more volumes.

Specifically, 
* A different replication would need a different set of volumes.
* A different collection would need a different set of volumes.
* A different TTL would need a different set of volumes.
* A different disk type would need a different set of volumes.
* A different S3 bucket is mapped to a collection, would need a different set of volumes. 
* A CSI mount is automatically mapped to a bucket, which needs a few volumes.

The default volume size is 30GB, and default to 8 volumes. Very likely you would need to customize a bit. Either through reducing the volume size in `weed master -volumeSizeLimitMB=xxx`, or increasing the `weed volume -max=xxx` value.

`-volumePreallocate` will preallocate disk spaces to volumes. These disk spaces are "taken" by the assigned volume, and could not be used by other volumes, even though the "df" command would report them as "free" if the volumes are not full.

SeaweedFS also assumes there is a default disk type, which is either empty or `"hdd"`. If all your disk type is `"ssd"`, you should leave the disk type as empty since the disk type basically is just a tag to group the volumes.

### Metadata Event Logs with All-SSD Clusters

**Q: I am seeing errors or cannot find a disk type when writing metadata event logs on my all-SSD cluster. What should I do?**

If your cluster consists entirely of SSDs (with no HDDs), you may encounter issues where the system fails to find a suitable disk type for writing metadata event logs. This happens because by default it is looking for a disk type as empty or hdd.

**Solution:**
In your configuration, simply leave all disk types empty. This is the recommended approach for homogenous clusters.

2.  **Path-Specific Configuration:** If you cannot leave the disk types empty for any specific reason, you can enforce the disk type using the [path-specific filer configuration](https://github.com/seaweedfs/seaweedfs/wiki/Filer-Store-Replication#path-specific-filer-configuration).

    Example using `weed shell` to configure the metadata log path:
    ```bash
    # Start the weed shell
    weed shell
    
    # Configure the metadata event log path to use SSD (or another disk type)
    # The default path for system logs is /topics/.system/log
    fs.configure -locationPrefix=/topics/.system/log -disk=ssd -apply
    ```

### How do I pre-allocate one or more volumes?

To pre-allocate volumes, send a request to the Master server. For example:

```shell
# To create more volumes in a given data center
curl "http://localhost:9333/vol/grow?dataCenter=000&count=4" # returns {"count":4}
# To create more volumes on a given rack
curl "http://localhost:9333/vol/grow?rack=example-rack&count=4" # returns {"count":4}
# To create more volumes on a given volume server
curl "http://localhost:9333/vol/grow?dataNode=example-node&count=4" # returns {"count":4}
```

See the [Master Server API documentation](https://github.com/seaweedfs/seaweedfs/wiki/Master-Server-API#pre-allocate-volumes) for full details (and more ways to choose replication).

### How to access the server dashboard?
SeaweedFS has web dashboards for its different services:

* Master server dashboards can be accessed on `http://hostname:port` in a web browser.
  For example: `http://localhost:9333`.
* Volume server dashboards can be accessed on `http://hostname:port/ui/index.html`.
  For example: `http://localhost:8080/ui/index.html`

Also see [#275](https://github.com/seaweedfs/seaweedfs/issues/275).

### Does it support xxx language?
If using `weed filer`, just send one HTTP POST to write, or one HTTP GET to read.

If using SeaweedFS for block storage, you may try to reuse some existing libraries.

The internal management APIs are in gRPC. You can generate the language bindings for your own purpose.

### Does it support FUSE?
Yes.

### My data is safe? What about bit-rot protection? Is there any encryption?

* **SSD friendly**: SeaweedFS data is all append-only and create less stress to the disks, especially SSDs with a limited number of write cycles. SeaweedFS can maximumly reduce writes to the same SSD cell, thus increase its lifespan.

* **Bitrot Protection**: Entries on volume servers are CRC checked for any possible changes on server side and accessible via Etag. For Filer and S3 APIs, the files can also be checked via MD5 Etag by clients.

* **Replication**: Each file can have its own replication strategy. Erasure encoding not only saves space, but also can tolerate loss of 4 shards of data.

* **Encryption**: Filer can run in AES256 encryption mode, with the encryption keys stored in filer meta data store. So the volume server can safely run anywhere, remote or on cloud. See [Filer Data Encryption](./Filer-Data-Encryption.md)

* **Secure Connection**: Between all the components, i.e., master, volume server, filer, and clients, SSL/TLS can be enabled for all the communications. JWT can be enabled to securely allow any client to upload data to volume servers. See [Security Overview](./Security-Overview.md)

* **Access Control**: For [Amazon S3 API](./Amazon-S3-API.md), the credentials can be checked and access control can be enforced. 

### How is it optimized for small files? How small is small files?

Optimization for small files is actually optimization for large amount of files. The file size does not matter. 

Filer server would automatically chunk the files if necessary.

### Does it support large files, e.g., 500M ~ 10G?
Large file will be automatically split into chunks, in `weed filer`, `weed mount`, `weed filer.copy`, etc, with options to set the chunk size.

TB level files also work.  The meta data size is linear to the number of file chunks. So keep the file chunk size larger will reduce the meta data size.

Another level of indirection can be added later for unlimited file size. Let me know if you are interested.

### How many volumes to configure for one volume server?

Just do not over configure the number of volumes. Keep the total size smaller than your available disk size.
It is also important to leave some disk space for a couple of volume size, so that the compaction can run.

### Volume server consumes too much memory?

If one volume has large number of small files, the memory usage would be high in order to keep each entry in memory or in leveldb.

To reduce memory usage, one way is to convert the older volumes into [Erasure-Coded volumes](https://github.com/seaweedfs/seaweedfs/wiki/Erasure-Coding-for-warm-storage), which are read only. The volume server can will sort the index and store it as a sorted index file (with extension `.sdx`). So looking up one entry costs a binary search within the sorted index file, instead of O(1) memory lookup.

### How to configure volumes larger than 30GB?

Before 1.29, the maximum volume size is limited to 30GB. However, with recent larger disks, one 8TB hard drive can hold 200+ volumes. The large amount of volumes introduces unnecessary work load for master.

Since 1.29, there are separate builds, with `_large_disk` in the file names:
* darwin_amd64_large_disk.tar.gz
* linux_amd64_large_disk.tar.gz
* windows_amd64_large_disk.zip

These builds are not compatible with normal 30GB versions. The `large disk` version uses 17 bytes for each file entry, while previously each file entry needs 16 bytes.

To upgrade to `large disk` version,
* remove `*.idx` files
* use the large-disk version, run `weed fix` to re-generate the `*.idx` files
* start master with a larger volume size limit
* start volume servers, with reasonable maximum number of volumes

### What's the difference between `large_disk` and `large_disk_full`?

- **`large_disk`**: Normal volumes are limited to 30GB each. This `large_disk` build enables support for volumes larger than 30GB (the `5BytesOffset` flag). It uses 17 bytes per file entry instead of 16 bytes, allowing volume sizes up to 8TB. 

- **`large_disk_full`**: This build includes everything in `large_disk`, PLUS additional filer store backend integrations:
  - **elastic** - Elasticsearch filer store
  - **gocdk** - Go Cloud Development Kit support (for cloud storage backends)
  - **rclone** - Rclone integration for remote storage
  - **sqlite** - SQLite filer store
  - **tarantool** - Tarantool filer store
  - **tikv** - TiKV filer store
  - **ydb** - YDB (Yandex Database) filer store

  This build is only available for `linux/amd64` due to build complexity.

**Which one should I use?**

- Use the **standard (no suffix)** build if your total storage needs are under 30GB per volume and you don't need extra backends.
- Use **`_large_disk`** if you need larger volumes (>30GB each) but don't need the extra filer store backends.
- Use **`_full`** if you need extra filer store backends but don't need large volumes.
- Use **`_large_disk_full`** if you need both large volumes AND extra filer store backends.
- Use **`_large_disk_rocksdb`** if you specifically need RocksDB as a filer store with large disk support.

**Important:** The `large_disk` versions are NOT compatible with standard 30GB versions. You cannot mix them in the same cluster. See the section above for migration instructions.

### How large should I configure the volumes?

If the system has lots of updates or deletions, it is better to keep the volume size small to reduce compaction load.

If the system is mostly readonly and running `large disk` version, it is ok to keep the volume size large.

There are situations that needs more volumes:
* In SeaweedFS S3 API, each bucket will use a few volumes. So more buckets needs more volumes.
* When using different collection, TTL or replication types, each `&lt;collection, TTL, replication&gt;` combination will need a few volumes.

### Why my 010 replicated volume files have different size?

The volumes are consistent, but not necessarily the same size or the same number of files. This could be due to these reasons:

* If some files are written only to some but not all of the replicas, the writes are considered failed (A best-effort attempt will try to delete the written files).
* The compaction may not happen at exactly the same time.

### Why files are deleted by disk spaces are not released?

The disk spaces are released when volume is vacuumed. By default, the vacuum only happens when garbage is more than 30%.

You can use `weed shell` to run `volume.vacuum -garbageThreshold=0.0001` to trigger the vacuum.

```
$ weed shell
master: localhost:9333 filer: localhost:8888
> lock
> volume.vacuum -h
Usage of volume.vacuum:
  -garbageThreshold float
    	vacuum when garbage is more than this limit (default 0.3)
>
```

### How to store large logs?

The log files are usually very large. Use `weed filer` to store them. 

Usually the logs are collected during a long period of time span. Let's say each day's log is about a manageable 128MB. You can store each day's log via "weed filer" under "/logs/" folder. For example:

    /logs/2015-01-01.log
    /logs/2015-01-02.log
    /logs/2015-01-03.log
    /logs/2015-01-04.log

## gRPC Ports
gRPC can be derived from the `-port` number and adding 10000 on top of it, i.g., `-port=8080` means gRPC port is `18080`.

If you **must** have custom gRPC ports, you can specify a custom gRPC port when `master`, `volume server` or `filer` starts. And for all the other places referencing `master` and `filer`, you also need to specify in this format:
```
 <host>:<port>.<grpcPort>
```
For example:
```
 weed master -port=9333 -port.grpc=9444
 weed volume -port=8080 -port.grpc=8444 -master=localhost:9333.9444
 weed filer  -port=8888 -port.grpc=9999 -master=localhost:9333.9444
 weed shell -filer=localhst:8888.9999 -master=localhost:9333.9444
 weed mount -dir=mm -filer=localhst:8888.9999
```

## Support ipv6?

Yes. A common error is when binding a link-scoped ipv6 address without a proper scope. This will cause `connect: invalid argument`.

Note that the `-ip` and `-ip.bind` have different format, e.g.:

```
# invalid
-ip="[fe80::4c3:3cff:fe4f:7e0b]" -ip.bind="[fe80::4c3:3cff:fe4f:7e0b]"

# valid
-ip="[fe80::4c3:3cff:fe4f:7e0b]" -ip.bind="[fe80::4c3:3cff:fe4f:7e0b%eth0]"
```

## Mount Filer
### weed mount error after restarting

If you mount SeaweedFS filer on MacOS, sometimes when restarting "weed mount -dir xxx", you may see this error:

> mount helper error: mount_osxfuse: mount point xxx is itself on a OSXFUSE volume

To fix this, do mount:

    $ mount
    /dev/disk1s1 on / (apfs, local, journaled)
    devfs on /dev (devfs, local, nobrowse)
    /dev/disk1s4 on /private/var/vm (apfs, local, noexec, journaled, noatime, nobrowse)
    map -hosts on /net (autofs, nosuid, automounted, nobrowse)
    map auto_home on /home (autofs, automounted, nobrowse)
    map -fstab on /Network/Servers (autofs, automounted, nobrowse)
    /dev/disk2 on /Volumes/FUSE for macOS (hfs, local, nodev, nosuid, read-only, noowners, quarantine, mounted by chris)
    weed@osxfuse0 on /Users/chris/tmp/mm (osxfuse, local, nodev, nosuid, synchronous, mounted by chris)

The last line shows the folder that already mounted something. Need to unmount it first.

    $ umount weed@osxfuse0


That should be it!

## Upgrade
### How to change from 30GB version to large volume 8000G version?
These two versions can not be mixed together.

To change to a different version, you will need to manually copy the `.dat` files, and run `weed fix` to regenerate `.idx` files.

### How to upgrade from release 1.xx to a.yy
Unless special notes, all upgrade will be backward compatible and ensure no data loss. There could be CLI tweaks. But in general, just test the CLI and make sure it can run.
