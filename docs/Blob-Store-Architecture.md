---
id: Blob-Store-Architecture
title: "Blob Store Architecture"
sidebar_label: "Blob Store Architecture"
---

The blob store is the bottom layer of SeaweedFS: master servers and volume servers. Everything else, the [Filer](./Directories-and-Files.md), the [S3 API](./Amazon-S3-API.md), [FUSE Mount](./FUSE-Mount.md), and the [S3 Table Bucket](./S3-Table-Bucket.md) catalogs, is built on top of it. You can also use it directly as a key-to-blob store, which is what this page walks through first, before explaining how the master assigns and locates volumes.

## Using the blob store directly

By default, the master node runs on port 9333, and the volume nodes run on port 8080.
Let's start one master node, and two volume nodes on port 8080 and 8081. Ideally, they should be started from different machines. We'll use localhost as an example.

SeaweedFS uses HTTP REST operations to read, write, and delete. The responses are in JSON or JSONP format.

### Start Master Server

```
> ./weed master
```

### Start Volume Servers

```
> weed volume -dir="/tmp/data1" -max=5  -master="localhost:9333" -port=8080 &
> weed volume -dir="/tmp/data2" -max=10 -master="localhost:9333" -port=8081 &
```

### Write A Blob

A blob, also referred as a needle, a chunk, or mistakenly as a file, is just a byte array. It can have attributes, such as name, mime type, create or update time, etc. But basically it is just a byte array of a relatively small size, such as 2 MB ~ 64 MB. The size is not fixed.

To upload a blob: first, send a HTTP POST, PUT, or GET request to `/dir/assign` to get an `fid` and a volume server URL:

```
> curl http://localhost:9333/dir/assign
{"count":1,"fid":"3,01637037d6","url":"127.0.0.1:8080","publicUrl":"localhost:8080"}
```

Second, to store the blob content, send a HTTP multi-part POST request to `url + '/' + fid` from the response:

```
> curl -F file=@/home/chris/myphoto.jpg http://127.0.0.1:8080/3,01637037d6
{"name":"myphoto.jpg","size":43234,"eTag":"1cc0118e"}
```

To update, send another POST request with updated blob content.

For deletion, send an HTTP DELETE request to the same `url + '/' + fid` URL:

```
> curl -X DELETE http://127.0.0.1:8080/3,01637037d6
```

### Save Blob Id

Now, you can save the `fid`, 3,01637037d6 in this case, to a database field.

The number 3 at the start represents a volume id. After the comma, it's one file key, 01, and a file cookie, 637037d6.

The volume id is an unsigned 32-bit integer. The file key is an unsigned 64-bit integer. The file cookie is an unsigned 32-bit integer, used to prevent URL guessing.

The file key and file cookie are both coded in hex. You can store the &lt;volume id, file key, file cookie&gt; tuple in your own format, or simply store the `fid` as a string.

If stored as a string, in theory, you would need 8+1+16+8=33 bytes. A char(33) would be enough, if not more than enough, since most uses will not need 2^32 volumes.

If space is really a concern, you can store the file id in the binary format. You would need one 4-byte integer for volume id, 8-byte long number for file key, and a 4-byte integer for the file cookie. So 16 bytes are more than enough.

### Read a Blob

Here is an example of how to render the URL.

First look up the volume server's URLs by the file's volumeId:

```
> curl http://localhost:9333/dir/lookup?volumeId=3
{"volumeId":"3","locations":[{"publicUrl":"localhost:8080","url":"localhost:8080"}]}
```

Since (usually) there are not too many volume servers, and volumes don't move often, you can cache the results most of the time. Depending on the replication type, one volume can have multiple replica locations. Just randomly pick one location to read.

Now you can take the public URL, render the URL or directly read from the volume server via URL:

```
 http://localhost:8080/3,01637037d6.jpg
```

Notice we add a file extension ".jpg" here. It's optional and just one way for the client to specify the file content type.

If you want a nicer URL, you can use one of these alternative URL formats:

```
 http://localhost:8080/3/01637037d6/my_preferred_name.jpg
 http://localhost:8080/3/01637037d6.jpg
 http://localhost:8080/3,01637037d6.jpg
 http://localhost:8080/3/01637037d6
 http://localhost:8080/3,01637037d6
```

If you want to get a scaled version of an image, you can add some params:

```
http://localhost:8080/3/01637037d6.jpg?height=200&width=200
http://localhost:8080/3/01637037d6.jpg?height=200&width=200&mode=fit
http://localhost:8080/3/01637037d6.jpg?height=200&width=200&mode=fill
```

### Rack-Aware and Data Center-Aware Replication

SeaweedFS applies the replication strategy at a volume level. So, when you are getting a blob id, you can specify the replication strategy. For example:

```
curl http://localhost:9333/dir/assign?replication=001
```

The replication parameter options are:

```
000: no replication
001: replicate once on the same rack
010: replicate once on a different rack, but same data center
100: replicate once on a different data center
200: replicate twice on two different data center
110: replicate once on a different rack, and once on a different data center
```

More details about replication can be found in [Replication](./Replication.md).

You can also set the default replication strategy when starting the master server.

### Allocate Blob Key on Specific Data Center

Volume servers can be started with a specific data center name:

```
 weed volume -dir=/tmp/1 -port=8080 -dataCenter=dc1
 weed volume -dir=/tmp/2 -port=8081 -dataCenter=dc2
```

When requesting a blob key, an optional "dataCenter" parameter can limit the assigned volume to the specific data center. For example, this specifies that the assigned volume should be limited to 'dc1':

```
 http://localhost:9333/dir/assign?dataCenter=dc1
```

### Other Features

* [No Single Point of Failure](./Failover-Master-Server.md)
* [Insert with your own keys](./Optimization.md#insert-with-your-own-keys)
* [Chunking large files](./Optimization.md#upload-large-files)
* [Collection as a Simple Name Space](./Optimization.md#collection-as-a-simple-name-space)

The full HTTP surface is in [Master Server API](./Master-Server-API.md) and [Volume Server API](./Volume-Server-API.md).

## How the master and volume servers work

Usually distributed file systems split each file into chunks. A central server keeps a mapping of filenames to chunks, and also which chunks each chunk server has.

The main drawback is that the central server can't handle many small files efficiently, and since all read requests need to go through the central master, so it might not scale well for many concurrent users.

Instead of managing chunks, SeaweedFS manages data volumes in the master server. Each data volume is 32GB in size, and can hold a lot of blobs. And each storage node can have many data volumes. So the master node only needs to store the metadata about the volumes, which is a fairly small amount of data and is generally stable.

The actual blob metadata, which are the blob volume, offset, and size, is stored in each volume on volume servers. Since each volume server only manages metadata of blobs on its own disk, with only 16 bytes for each blob, all access can read the metadata just from memory and only needs one disk operation to actually read file data.

For comparison, consider that an xfs inode structure in Linux is 536 bytes.

### Master Server and Volume Server

The architecture is fairly simple. The actual data is stored in volumes on storage nodes. One volume server can have multiple volumes, and can both support read and write access with basic authentication.

All volumes are managed by a master server. The master server contains the volume id to volume server mapping. This is fairly static information, and can be easily cached.

On each write request, the master server also generates a file key, which is a growing 64-bit unsigned integer. Since write requests are not generally as frequent as read requests, one master server should be able to handle the concurrency well.

### Write and Read files

When a client sends a write request, the master server returns (volume id, file key, file cookie, volume node URL) for the blob. The client then contacts the volume node and POSTs the blob content.

When a client needs to read a blob based on (volume id, file key, file cookie), it asks the master server by the volume id for the (volume node URL, volume node public URL), or retrieves this from a cache. Then the client can GET the content, or just render the URL on web pages and let browsers fetch the content.

### Saving memory

All blob metadata stored on a volume server is readable from memory without disk access. Each file takes just a 16-byte map entry of &lt;64bit key, 32bit offset, 32bit size&gt;. Of course, each map entry has its own space cost for the map. But usually the disk space runs out before the memory does.

### Tiered Storage to the cloud

The local volume servers are much faster, while cloud storages have elastic capacity and are actually more cost-efficient if not accessed often (usually free to upload, but relatively costly to access). With the append-only structure and O(1) access time, SeaweedFS can take advantage of both local and cloud storage by offloading the warm data to the cloud.

Usually hot data are fresh and warm data are old. SeaweedFS puts the newly created volumes on local servers, and optionally upload the older volumes on the cloud. If the older data are accessed less often, this literally gives you unlimited capacity with limited local servers, and still fast for new data.

With the O(1) access time, the network latency cost is kept at minimum.

If the hot/warm data is split as 20/80, with 20 servers, you can achieve storage capacity of 100 servers. That's a cost saving of 80%! Or you can repurpose the 80 servers to store new data also, and get 5X storage throughput.

See [Cloud Tier](./Cloud-Tier.md) for the setup.

### The Filer on top

Built on top of the blob store, the SeaweedFS Filer adds directory structure to create a file system. The directory structure is an interface that is implemented in many key-value stores or databases, see [Filer Stores](./Filer-Stores.md).

The content of a file is mapped to one or many blobs, distributed to multiple volumes on multiple volume servers.

## Disks

### Hard Drive Performance

When testing read performance on SeaweedFS, it basically becomes a performance test of your hard drive's random read speed. Hard drives usually get 100MB/s~200MB/s.

### Solid State Disk

To modify or delete small files, SSD must delete a whole block at a time, and move content in existing blocks to a new block. SSD is fast when brand new, but will get fragmented over time and you have to garbage collect, compacting blocks. SeaweedFS is friendly to SSD since it is append-only. Deletion and compaction are done on volume level in the background, not slowing reading and not causing fragmentation.
