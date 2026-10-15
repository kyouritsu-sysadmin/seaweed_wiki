---
id: Tiered-Storage
title: "Tiered Storage"
sidebar_label: "Tiered Storage"
---

All read and write operation for volume data is O(1) disk seek. However, there are fast, slow, and remote storages. 
Since data that are hot, warm, and cold, it would be cost-efficient to place data accordingly. SeaweedFS supports tiered storage, where you can place data to customizable disk types, and provides ways to move data to different tiers.

```

  => NVME      => SATA SSD => Fast HDD => Slow HDD => Cloud

  => Critical  => Hot      => Less Hot => Warm     => Cold

```

# Speed up volume index

To write any data, the volume index needs to append one entry. To read any data, the volume index lookup is required. The volume index can be in memory mode or an LevelDB instance. The amount of index content is small while it is accessed frequently. 

You can run `weed volume -dir.idx=/fast/disk/dir` or `weed server -volume.dir.idx=/fast/disk/dir` to ensure the volume index is located on a fast disk, e.g., a fast SSD mount.

If the volume server already has some existing data, you can just stop the volume server, move the `.idx` files to the index folder, and restart the volume server.

# SSD & HDD Volume Disk Types

If the volume data also needs fast access, you can create them on fast disks.

For example, one volume server can have two disks with two kinds of disk types:
```
weed volume -max=10000 -disk=hdd,ssd -port=8080 -dir=/large_data,/fast_data -compactionMBps=40  -minFreeSpacePercent=7
```

Please notice the `-disk=hdd,ssd` and `-dir=/large_data,/fast_data`.

Then you can create with `fs.configure` a path specific setting and set buckets/collections that start with (example)  "ssd_" to be allocated to the ssd, and all other collection will be created on the hdd. you can also create specific bucket name.

Example (within the weed shell):
```
fs.configure -locationPrefix=/buckets/ssd_ -disk=ssd -apply
```

https://github.com/seaweedfs/seaweedfs/wiki/Path-Specific-Configuration

# Custom Tags

Custom Tags are supported for the disk types. Besides the default `hdd` and `ssd`, you can use any lower-cased tags, such as `ssd1`, `hdd2`, `nvme`, `raid6`, etc.

Same as the default disk types, you can place the data by custom disk types.
```
fs.configure -locationPrefix=/buckets/fast_ -disk=nvme -apply
```

You can also schedule admin scripts to move volumes from one tier to another tier. See below about `volume.tier.move`.

## Change Volume Disk Type

When `volume.balance` or `volume.fix.replication`, the volume disk type would not change.

### Change by `volume.tier.move`
`volume.tier.move` in `weed shell` can be used to change the disk type for one whole collection.
```
volume.tier.move -fromDiskType=hdd -toDiskType=ssd -quietFor=1s -fullPercent=0.001 -collection=benchmark -force
```

#### Alter replication settings of moved volumes
the `-toReplication` feature can be used to alter the replication settings for the newly moved volumes via the `volume.tier.move` command.
```
volume.tier.move -fromDiskType=hdd -toDiskType=ssd -quietFor=1s -fullPercent=0.001 -collection=benchmark -toReplication 100 -force
```

### Change by `volume.move`
`volume.move` in `weed shell` can be used to move across volume servers:
```
volume.move -source <source volume server host:port> -target <target volume server host:port> -volumeId <volume id> -disk [hdd|ssd|<tag>]
```

### Manually move volume files
For now, if you only want to change the disk type of a volume, and the volume server is not running, you can simply move the volume data from ssd directory to hdd directory, or vice versa.
