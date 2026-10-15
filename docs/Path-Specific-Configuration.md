---
id: Path-Specific-Configuration
title: "Path Specific Configuration"
sidebar_label: "Path Specific Configuration"
---

## Requirements
Clients writing to SeaweedFS can configure most storage options, such as Collection, Replication, TTL, etc. However, you may want to configure these storage options on the filer side.

For example, an administrator can create a `/scratch/` directory, configured so that anything written to it is automatically given a 7-day TTL. This directory could be used to store things like CI build artifacts, and it would naturally roll off old files without any intervention.

This could also be used to implement a system-wide "trash can" (e.g. all deletes move objects to the trash and apply a TTL to them).

## How it works

On filer, there is one special file, `/etc/seaweedfs/filer.conf`. It has all the path-specific configurations.

> **NOTE**: The file `/etc/seaweedfs/filer.conf` is NOT stored in the host file system, but **inside SeaweedFS**. This way, all
> path-specific configuration is synchronized across all replicated filers.

All filers will read this configuration and apply the storage option based on the write target file path.

## How to configure

Here is an example of using `weed shell`. You can also write the `/etc/seaweedfs/filer.conf` file directly. All filers will reload this file if it is changed.

```
$ weed shell

# fs.configure will display current filer.conf content
> fs.configure
{

}

# add a location specific collection setting
> fs.configure -locationPrefix=/tests/ -collection=special
{
  "locations": [
    {
      "locationPrefix": "/tests/",
      "collection": "special"
    }
  ]
}

# save the above setting
> fs.configure -locationPrefix=/tests/ -collection=special -apply
{
  "locations": [
    {
      "locationPrefix": "/tests/",
      "collection": "special"
    }
  ]
}

# delete the above setting and save to the filer
> fs.configure -locationPrefix=/tests/ -delete -apply
{

}
```

# Options

For any path, you can configure
* Disk type `[hdd|ssd|&lt;tag&gt;]`
* Fsync
* Volume Growth Count
* Collection
* Replication
* TTL
* Data Center
* Rack
* Data Node

```
# see more options
> fs.configure -h
Usage of fs.configure:
  -apply
        update and apply filer configuration
  -collection string
        assign writes to this collection
  -dataCenter string
        assign writes to this dataCenter
  -dataNode string
        assign writes to this dataNode
  -delete
        delete the configuration by locationPrefix
  -disk string
        [hdd|ssd|<tag>] hard drive or solid state drive or any tag
  -fsync
        fsync for the writes
  -locationPrefix string
        path prefix, required to update the path-specific configuration
  -rack string
        assign writes to this rack
  -readOnly
        disable writes
  -replication string
        assign writes with this replication
  -ttl string
        assign writes with this ttl
  -volumeGrowthCount int
        the number of physical volumes to add if no writable volumes
  -worm
    	write-once-read-many, written files are readonly

```

## What is NOT included

The storage options are applied during write time.

So if a file is created and then moved to the configured path, the storage option would not take effect.
