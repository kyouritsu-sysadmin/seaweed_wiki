---
id: Replication
title: "Replication"
sidebar_label: "Replication"
---

Replication is a cornerstone of modern storage systems such as SeaweedFS, ensuring that data remains accessible, durable, and consistent across various scenarios, from routine access to disaster recovery. Here’s why replication is critical for any storage system, especially in environments managed by sysadmins:

### High Availability

Replication guarantees that data is not confined to a single location or device. By distributing copies across different servers, racks or data centers, it ensures that if one part of the system fails, the data remains accessible from another location. This is crucial for businesses that rely on continuous data availability to serve their customers around the clock. _investigate what availability SWFS provides_

### Data Durability

Data is an invaluable asset for any organization. Replication enhances data durability, safeguarding against data loss that could occur due to hardware failures, human errors, or natural disasters. By maintaining multiple copies of data, it significantly reduces the risk of losing critical information, ensuring that businesses can recover quickly even in the face of unexpected events.  SeaweedFS provides configurable replication to match your durability requirements.

### Disaster Recovery

In the event of a catastrophic failure, such as a data center outage, replication is the backbone of disaster recovery strategies. It enables organizations to switch to a replicated site where data remains intact and operations can continue with minimal downtime. This capability is vital for maintaining business continuity and minimizing the impact of disasters on operations and reputation.  SeaweedFS can be configured to ensure copies are stored in different locations, including multiple data centers and third party storage provides.

### Load Balancing

Replication also helps distribute the workload across multiple servers, improving performance and reducing latency for users. By allowing data to be served from multiple points, it can balance the load more effectively, ensuring smoother user experiences and more efficient use of resources. _Investigate load balancing options._

### Data Consistency

In distributed systems, keeping data consistent across different locations is a challenge. Replication strategies, especially those that include synchronous replication, help ensure that all copies of the data are up-to-date and consistent. This is crucial for applications that rely on real-time data accuracy, such as financial transactions and inventory management.

SeaweedFS provides write consistency by ensuring writes are confirmed on multiple volumes (see below), and reduces the complexity of consistent erasure coding by generating the [erasure coded data asynchronously](./Erasure-Coding-for-warm-storage.md).

### Scalability

As data grows, replication facilitates scalability. It allows systems to expand horizontally by adding more replicas to handle increased load and data volume. This scalability is essential for organizations that expect to grow and need a storage solution that can grow with them without compromising performance or reliability.

In summary, replication is not just a feature but a fundamental aspect of a resilient storage infrastructure. It provides a safety net against data loss, enhances system performance, and supports seamless scalability. For sysadmins, understanding and implementing effective replication strategies is key to managing a robust, reliable, and efficient storage environment.

# Configuration

The replication control is done at the volume level, controlled by various flags.  Typically a default replication is set at the master, or the filer, and this choice is propagated to the volumes.  Volume replication can also be set directly, though this is less useful.  When data is written, the write operation does not complete until replication is confirmed on all volumes.

SeaweedFS does not rebalance or ensure the actual replication matches the set level under normal operation.  If any replica is missing, there is no automatic repair. This is to prevent over replication due to transient volume sever failures or disconnections.  Instead fixing replication is done through the weed shell (see `volume.fix.replication`).  Typically this is done periodically with a script.  Likewise, under normal operation read failures are simply passed on to the client application and require an out of band process to recover.   A partially unavailable volume becomes read-only and any new writes will instead go to a different volume (-replication set).

# replication string

SeaweedFS uses a 3 digit string to specify the replication policy corresponding to (data center)(rack)(volume server) _check if this is actually by `-dir`, or server_  The total number of copies is 1 + sum(digits), so 205 would correspond to 1+2+5 = 8 copies of the data and require 8x storage space compared to the original source data.  Because SeaweedFS uses checksums, it can detect when a volume is corrupted (typically lost due to an unreadable drive, but sometimes through bitrot), 205 replication would provide resilience against 7 concurrent failures, and if the local data center were destroy, still maintain two copies elsewhere.

High redundancy factors require large overhead for storage, by using [Erasure-Coding-for-warm-storage](./Erasure-Coding-for-warm-storage.md) SeaweedFS can provide resiliency without a high storage cost.

# Good practices

## Disk failure

If a drive fails (_how to detect?_) it is often the case that aggressive replication will cause other drives to fail (this is amplified by the fact that often drives are bought at the same time and have similar number of operating hours).  As a result it is good practice to minimise the reads, and especially the writes, to other drives in similar condition.  New drives can be added, volumes on older drives can be marked as read-only, replication can be performed with `-doDelete=false` to avoid unnecessary writes to critical drives.

## debugging replication problems

_important section, needs work_

## manual volume management

SeaweedFS is quite forgiving of the placement of the volume files.  Volume files can be moved onto other storage using, for example, `rsync`, and a volume server pointing at the new location will pick up these volumes on restart.  If a separate dir.idx is provided, the corresponding index files (.ecx, *.ecj) may need to be moved into this directory.

# How to use

Basically, the way it works is:

1. start weed master, and optionally specify the default replication type

   ```bash
   # 001 means for each file a replica will be created in the same rack
   ./weed master -defaultReplication=001
   ```

2. start volume servers as this:

   ```bash
   ./weed volume -port=8081 -dir=/tmp/1 -max=100 -master="master_address:9333" -dataCenter=dc1 -rack=rack1
   ./weed volume -port=8082 -dir=/tmp/2 -max=100 -master="master_address:9333" -dataCenter=dc1 -rack=rack1
   ```
On another rack,
   ```bash
   ./weed volume -port=8081 -dir=/tmp/1 -max=100 -master="master_address:9333" -dataCenter=dc1 -rack=rack2
   ./weed volume -port=8082 -dir=/tmp/2 -max=100 -master="master_address:9333" -dataCenter=dc1 -rack=rack2
   ```

No change to Submitting, Reading, and Deleting files.

## The meaning of replication type

*Note: This subject to change.*

The replication type is defined by a 3 digit string as follows:

Column | Meaning
---|---
**x** | number of replica in other data centers
**y** | number of replica in other racks in the same data center
**z** | number of replica in other servers in the same rack

The replication string represents the additional number of copies of data that will be maintained by the seaweed cluster beyond the original data volume.  Data remains readable as long as at least on replica is accessible.  However, writes are permitted only if the number of replicas is achievable based on the replication configuration string.  The max value that can be specified is '255'. The total number of copies of this volume will be the sum of the digits + 1.  The original data is not counted.

Here are some possible replication configuration examples and what they mean:

Value | Meaning
---|---
000 | no replication, just one copy
001 | replicate once on the same rack
010 | replicate once on a different rack in the same data center
052 | replicate to five different racks within the same data center and two different volumes within the same rack
100 | replicate once on a different data center
200 | replicate twice on two other different data center
110 | replicate once on a different rack within the same data center and once on a different data center
... | ...
255 | replicate twice on two different data centers, five different racks and 5 different volumes servers with respect to where the original volume exists.

## Allocate File Key on specific data center

Now when requesting a file key, an optional "dataCenter" parameter can limit the assigned volume to the specific data center. For example, this specify

```bash
http://localhost:9333/dir/assign?dataCenter=dc1
```

## Write and Read

For consistent read and write, a quorum `W + R > N` is required. In SeaweedFS, `W = N` and `R = 1`.

In plain words, all the writes are strongly consistent and all N replica should be successful. If one of the replica fails to write, the whole write request will fail. This makes read request fast since it does not need to check and compare other replicas.

For failed write request, there might be some replicas written. These replica would be deleted. Since volumes are append only, the physical volume size may deviate over time.

### write-path

When a client do a write request, here follows the work-flow:
  1. a client sends a specific replication to the master in order to get assigned a fid
  2. the master receives the assign request, depending of the replication, it chooses volume servers that will handle them
  3. the client sends the write request to one of the volume servers and wait for the ACK
  4. the volume server persist the file and also replicated the file if needed.
  5. If everything is fine, the client get a OK response.

When a write is made to the filer, there is an additional step before step 1. and after 5. and the filer acts a client in the step 1 to 5.

## Fix replication

If one replica is missing, there are no automatic repair right away. This is to prevent over replication due to transient volume sever failures or disconnections. Instead, the volume will just become read-only. For any new writes, just assign a different file id to a different volume.

To repair the missing replicas, you can use `volume.fix.replication` in `weed shell`.

### Replicate without deleting
In certain circumstances—like adding/removing/altering replication settings of volumes or servers—the best strategy is to only repair under-replicated volumes and not delete any while working on volume and server modifications, in this situation use the flag `doDelete`: 

`volume.fix.replication -doDelete=false`

 After all replications and modifications are finished, desired replication consensus can then be obtained by running `volume.fix.replication` without the 'doDelete' flag.

## Change replication

In `weed shell`, you can change a volume replication setting via `volume.configure.replication`. After that, the volume will become readonly since the replication setting is not matched. You will also need to run `volume.fix.replication` to create missing replicas.
