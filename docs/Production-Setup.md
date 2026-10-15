---
id: Production-Setup
title: "Production Setup"
sidebar_label: "Production Setup"
---

A robust production setup requires more configuration -- and care -- than the
[Getting Started](./Getting-Started.md) guide. There are multiple layers of components. Please follow
the steps to set them up from bottom up, one by one.

* Set up object storage
  * Set up Masters
  * Add volume servers
* Set up file storage
  * Choose filer store
  * Setup Filer

And then, choose the component you want to set up
* Set up S3
* Set up FUSE mount
* Cluster Maintenance

## Prerequisites

Make sure the ports are open. By default

| server | http port | gRPC port |
| -------- | ------ | ------ |
| Master | 9333 | 19333 |
| Volume | 8080 | 18080 |
| Filer | 8888 | 18888 |
| S3 | 8333 | |

If you have multi-homed servers (many IP addresses and interfaces),
ensure SeaweedFS uses the correct IP for cluster communication. Append
`-ip=xx.xx.xx.xx` to specify the appropriate address. 

If you wish to use a different IP address for user-facing services, then 
set `-ip.bind=yy.yy.yy.yy` as well.

### For single node setup

You can just use `weed server -filer -s3 -ip=xx.xx.xx.xx`, to have one master,
one volume server, one filer, and one S3 API server running. 

It is better to have several volumes running on one machine, so that if one
volume is compacting, the other volumes can still serve read and write requests.
The default volume size is 30GB. So if your server does not have multiple 30GB
empty spaces, you need to reduce the volume size.

```
weed server -filer -s3 -ip=xx.xx.xx.xx -volume.max=0 -master.volumeSizeLimitMB=1024
```

# Set up object storage

## Set up Masters

### One master is fine

If there are 2 machines, it is not possible to achieve consensus. Just do not bother to set up multiple masters. 

Even for large clusters, it is totally fine to have one single master. The load on master is very light. It is unlikely to go down. You can always just restart it since it only has soft states collected from volume servers.

### Set up masters

OK. Your CTO just wants multiple masters. To do so, see [Failover Master Server](./Failover-Master-Server.md) for details.

Assuming your machine has a directory: `/data/seaweedfs`. Run these on 3 machines with ip addresses as ip1, ip2, ip3.

```
weed master -mdir=/data/seaweedfs/master -peers=ip1:9333,ip2:9333,ip3:9333 -ip=ip1
weed master -mdir=/data/seaweedfs/master -peers=ip1:9333,ip2:9333,ip3:9333 -ip=ip2
weed master -mdir=/data/seaweedfs/master -peers=ip1:9333,ip2:9333,ip3:9333 -ip=ip3
```

Additional notes:
* Depending on the available disk space on each volume server, the master may need
to reduce maximum volume size, e.g., add `-volumeSizeLimitMB=1024`. This will ensure
each volume server has several volumes.

* Since it is for production, you may also want to add `-metrics.address=&lt;Prometheus gateway address&gt;`. See [System Metrics](./System-Metrics.md).

### Add volume servers

Adding volume servers is easy. Actually this is much easier than most other systems.
If you do not specify `-max=0` then the number of volumes is limited to 8. You can
specify a non-zero value, if you wish to explicitly manage your disk space.

* **For machine with one disk to use**

Run this to setup:
```
weed volume -master=ip1:9333,ip2:9333,ip3:9333 -dataCenter=dc1 -rack=rack1 -dir=/data/seaweedfs/volume -ip=xxx.xxx.xxx.xxx -max=0
```

* **For machine with multiple disks**

Configure the `-dir` to be comma separated directory list, and set `-max` for corresponding directories, assuming the `/data/seaweedfs/volume[x]` are on different disks. 
```
weed volume -master=ip1:9333,ip2:9333,ip3:9333 -dataCenter=dc1 -rack=rack1 -ip=xxx.xxx.xxx.xxx -dir=/data/seaweedfs/volume1,/data/seaweedfs/volume2,/data/seaweedfs/volume3 -max=0,0,0
```
Do not use multiple directories on the same disk. The automatic volume count limit will double count the capacity.

* **For machine with multiple disks**

You can also create multiple volume servers on different ports. It could be easier for changing disks.
```
weed volume -master=ip1:9333,ip2:9333,ip3:9333 -dataCenter=dc1 -rack=rack1 -dir=/data/seaweedfs/volume1 -ip=xxx.xxx.xxx.xxx -max=0 -port=8081
weed volume -master=ip1:9333,ip2:9333,ip3:9333 -dataCenter=dc1 -rack=rack1 -dir=/data/seaweedfs/volume2 -ip=xxx.xxx.xxx.xxx -max=0 -port=8082
weed volume -master=ip1:9333,ip2:9333,ip3:9333 -dataCenter=dc1 -rack=rack1 -dir=/data/seaweedfs/volume3 -ip=xxx.xxx.xxx.xxx -max=0 -port=8083

```

Additional notes:
* If the disk space is huge and there will be a lot of volumes, configure `-index=leveldb` to reduce memory load.
* For busy volume servers, `-compactionMBps` can help to throttle the background jobs, e.g., compaction, balancing, encoding/decoding,etc.
* After adding volume servers, there will not be data rebalancing. It is generally not a good idea to actively rebalance data, which cost network bandwidth and slows down other servers. Data are written to new servers after new volumes are created on them. You can use `weed shell` and run `volume.balance -force` to manually balance them.
* Multiple volume servers on the same physical host count as separate servers for replication purposes. So if you have two physical hosts with multiple volume servers each, replication `001` (one replica in the same rack) does not guarantee that each copy will be stored on different physical hosts.

## Check the object store setup

Now the object store setup is completed. You can visit `http://&lt;master&gt;:9333/` to check it around.

* Ensure the Free volume count is not zero.
* Try to assign some file IDs to trigger a volume allocation. 

If you only use SeaweedFS object store, that is all.

# Set up file storage

## Choose filer store

If currently only one filer is needed, just use one filer with default filer store. It is very scalable.

You can always migrate to other scalable filer store by export and import the filer meta data. See [Filer Stores](./Filer-Stores.md)

Run `weed scaffold -config=filer` to generate an example `filer.toml` file. This file choose `leveldb2` as the filer store by default which stores file meta in local on disk. `leveldb2` only support one filer.

The filer store to choose depends on your requirements, your existing data stores, etc.

## Setup filer


```
weed filer -ip=xxx.xxx.xxx.xxx -master=ip1:9333,ip2:9333,ip3:9333 -dataCenter=dc1 -rack=rack1
```

Additional notes:
* Both `weed filer` and `weed master` has option `-defaultReplicaPlacement`. `weed master` uses it for the object store, while `weed filer` uses it for files. The `weed filer` setting will default to the value for `weed master`.
* `-encryptVolumeData` option is when you need to encrypt the data on volume servers. See [Filer Data Encryption](./Filer-Data-Encryption.md)

## Setup multiple filers

If using shared filer store, the filer itself is stateless. You can create multiple peer filers. The metadata and data are all shared. This is recommended for production.

# Additional components

## Setup S3 API

Follow [Amazon S3 API](./Amazon-S3-API.md) to generate a json config file, to assign accessKey and secretKey for different identities, and give read/write permissions to different buckets.

Start s3 together with filer. This avoids the setup for s3 to support multiple filers.

```
weed filer -s3 -s3.config=<config.json> -s3.port=8333
```

The endpoint is `http://&lt;s3_server_host&gt;:8333`.

### S3 Encryption at Rest (SSE-S3)

If your S3 clients use server-side encryption (`x-amz-server-side-encryption: AES256`), you **must** configure the Key Encryption Key (KEK) before starting the S3 API server. Without it, SSE-S3 requests will fail.

Add to `security.toml` (all S3 API servers in the cluster must use the same value):

```toml
[s3.sse]
# Option A: hex-encoded 256-bit key (generate with: openssl rand -hex 32)
kek = "a1b2c3d4..."

# Option B: any secret string (simpler, key is derived via HKDF)
key = "my-secret-passphrase"
```

Or via environment variables: `WEED_S3_SSE_KEK` / `WEED_S3_SSE_KEY`.

Store the value in your secrets manager. See [Server-Side-Encryption](./Server-Side-Encryption.md) for details and migration instructions.

## Set up FUSE mount

Run

`weed mount -filer=&lt;filer_host:filer_port&gt; -cacheCapacityMB=xxx -chunkSizeLimitMB=4 -dir=mount_point_dir`

* `-cacheCapacityMB` means file chunk read cache capacity in MB with tiered cache(memory + disk), default 0 which means chunk cache for read is disabled.
* `-chunkSizeLimitMB` local write buffer size, also chunk large file, default 2 MB.
* `-replication` is the replication level for each file. It overwrites replication settings on both filer and master.
* `-volumeServerAccess=[direct|publicUrl|filerProxy]` is used if master, volume server, and filer are inside a cluster, but `weed mount` is outside of the cluster. With this option set to `filerProxy`, only filer needs to be exposed to outside. All read write access to volume servers will be proxied by filer.

## Cluster Maintenance

In a cluster, volume servers can go down. But automatic rebalancing will be problematic. It can cause unexpected busy network activities. For example, the heartbeat of a volume server may come and go, causing an unnecessarily busy system. Currently recommended strategy is to keep the existing data readonly, and automatically add new writable volumes.

There are `volume.balance` and `volume.fix.replication` commands in `weed shell`. You can configure them to run during off hours.

See [Volume Management](./Volume-Management.md) for details.

## Other 
* Setup metrics, see [System Metrics](./System-Metrics.md)
* Setup security, see [Security Configuration](./Security-Configuration.md)
* If running out of in house machines
  * Enable [Erasure Coding for warm storage](./Erasure-Coding-for-warm-storage.md) to save replica spaces.
  * Move warm data to [Cloud Tier](./Cloud-Tier.md)
* Learn to use `weed shell`, to check the volume status, mount/unmount/move/balance/copy/delete a volume, fsck for the volume, erasure encoding/decoding, etc.