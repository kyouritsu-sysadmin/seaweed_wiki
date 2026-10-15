---
id: Erasure-Coding-for-warm-storage
title: "Erasure Coding for warm storage"
sidebar_label: "Erasure Coding for warm storage"
---

This erasure coding implementation took some ideas from [f4: Facebook’s Warm BLOB Storage System](https://www.usenix.org/system/files/conference/osdi14/osdi14-paper-muralidhar.pdf), without its high hardware requirements.

Usually data is hot when it is fresh, and are accessed very often. SeaweedFS normal volumes tries hard to minimize the disk operations, but it comes with a cost of loading indexes in memory. 

However, data can become warm or cold after a period of time. They are accessed much less often. The high cost of memory is not cost-efficient for warm storage. To store them more efficiently, you can "seal" the data and enable erasure coding (EC).

## Benefit
* **Storage Efficiency**: SeaweedFS implemented RS(10,4), which allows loss of 4 shards of data with 1.4x data size. Compared to replicating data 5 times to achieve the same robustness, it saves 3.6x disk space.
* **Fast Read Speed**: SeaweedFS uses continuous 1GB block layout with 1MB block sizes for edge cases, optimized for both small file reads and storage efficiency.
* **Optimized for Small Files**: there are no file size requirement for EC to be effective.
* **High Availability**: If up to 4 shards are down, the data is still accessible with reasonable speed.
* **Memory Efficiency** Minimum memory usage. The volume server does not load index data into memory.
* **Fast Startup** Startup time is much shorter by skip loading index data into memory.
* **Rack-Aware** data placement to minimize impact of volume server and rack failures.
* **Disk-Aware** data placement to ensure shards are distributed across different physical disks within a server, protecting against individual disk failures in JBOD setups.
* **Flexible Server Layout** There are no minimum number of servers, or racks. SeaweedFS manages erasure coding data via volumes. If the number of servers is less than 4, EC can protect against hard drive failures. If the number of servers is greater than or equal to 4, EC can protect against server failures. If the number of racks is greater than 4, EC can protect against rack failures.

The downside:
* If some EC shards are missing, fetching data on those shards would be slower.
* Re-construct missing EC shards would require transmitting whole volume data.
* Only deletion is supported. Update is not supported.
* Compaction would require converting back to normal volumes first.

Side Note:
* The 10+4 configuration is the default for the open source version.
* The SeaweedFS Enterprise version supports custom EC ratios.

## Architecture
SeaweedFS implemented 10.4 Reed-Solomon Erasure Coding (EC). The large volumes are split into chunks of 1GB, and every 10 data chunks are also encoded into 4 parity chunks. So a 30 GB data volume will be encoded into 14 EC shards, each shard is of size 3 GB and has 3 EC blocks.

Since the data is split into 1GB chunks, usually one small file is contained in one shard, or possibly two shards in edge cases. So most reads still only cost O(1) disk read.

For smaller volumes less than 10GB, and for edge cases, the volume is split into smaller 1MB chunks. 

The 14 EC shards should be spread into disks, volume servers and racks as evenly as possible, to protect against the hardware failure caused data loss.

## How to enable it?

Erasure coding is handled by the **`erasure_coding` plugin worker**. Start the admin server and a worker:

```bash
weed admin -master=localhost:9333
weed worker -admin=localhost:23646
```

The `erasure_coding` plugin worker automatically detects volumes that are candidates for EC encoding and executes the encoding. It is enabled by default and configurable from the admin UI at `/plugin`. If you are migrating from `master.toml` maintenance scripts, see [Migrate Maintenance Scripts to Admin Script Plugin](./Migrate-Maintenance-Scripts-to-Admin-Script-Plugin.md).

### Detection Thresholds

The worker detects volumes eligible for EC encoding based on configurable thresholds:

| Setting | Default | Description |
|---------|---------|-------------|
| Fullness Ratio | 0.8 (80%) | Minimum volume fullness ratio to trigger encoding |
| Quiet Period | 300s (5 min) | Volume must be unmodified for at least this long |
| Minimum Size | 30 MB | Only volumes larger than this are considered |
| Collection Filter | (all) | Optionally restrict to a specific collection |

Detection runs every 5 minutes by default. These settings can be adjusted in the admin UI.

### How it works

The worker scans the cluster topology, identifies volumes meeting the thresholds above, and proposes EC encoding jobs. The admin server deduplicates proposals and dispatches them to available workers for execution.

If the volume is replicated, only one copy will be erasure encoded. All the original copies will be purged after a successful erasure encoding.

Note: One collection can contain both normal volumes and erasure coded volumes, with write requests going to normal volumes.

### Data Repair
If disks fail or servers fail, some data shards are lost. With erasure coding, we can recover the lost data shards from the remaining data shards.

The data repair happens for the whole volume, instead of one small file at a time. It is much more efficient and fast to reconstruct the missing data shards than processing each file individually.

### Detecting silent corruption (bitrot)

Data repair recovers *lost* shards, but a shard that is still present can rot silently on disk. Cold parity shards are especially exposed because they are never read during normal serving. An optional per-volume checksum sidecar (`.ecsum`) lets `ec.scrub -mode checksum` detect such corruption and lets the rebuild path refuse to consume unverified bytes. See [EC Bitrot Detection](./EC-Bitrot-Detection.md).

### EC data balancing
With servers added or removed, some data shards may not be laid out optimally. For example, one volume's 5 data shards could be on the same server. If that server goes down, the volume would be unrepairable or part of the data is lost permanently.

The default admin script includes `ec.balance -apply` which spreads EC shards evenly to minimize data loss risk.

EC shard re-balancing happens in three steps:

  1. Duplicate EC shards for the same volume + server are deleted.
  2. EC shards are balanced across volumes for all racks.
  3. EC shards are balanced across volumes for individual racks.

Destination volume/racks for EC shards are selected based on capacity, favoring those with less preexisting shards in order to ensure an uniform distribution. Additionally, EC shards selection obey default [replica placement settings](./Replication.md#the-meaning-of-replication-type) for the master server.

## How the read works?
When all data shards are online, the read for one file key are assigned to one volume server (A) that has at least one data shard for the volume. Server A will read its copy of index file, and locate the volume server (B), and read from server B for the file key.

For example, one read request for 3,0144448888 will:
1. Ask master server to locate the EC shards for volume 3, which is usually a list of volume servers.
2. The read client can randomly pick one of the returned volume servers, A.
3. Server A will read its local index file, find the right volume server B that has the file content. Sometimes it may have to contact additional servers if the file is split between multiple blocks. But usually the data shard has 1GB block size. So this does not happen often.

In normal operations, there are usually one extra network hop compared to normal volume reads.

In case of missing data shards or read failures from server B, server A will try to collect as many pieces of data as possible from the remaining servers, and reconstruct the requested data.

## Read Performance

For this test, I started 4 volume servers. With each volume divided into 14 shards, each server will host 3 or 4 volumes. If one volume server is down, the data will still be readable and repairable.

Here are the benchmark numbers by `weed benchmark -master localhost:9334 -n 102040 -collection=t -write=true`
```
------------ Randomly Reading Benchmark ----------
Completed 30822 of 102040 requests, 30.2% 30815.7/s 31.0MB/s
Completed 62311 of 102040 requests, 61.1% 31478.1/s 31.7MB/s
Completed 94190 of 102040 requests, 92.3% 31894.3/s 32.1MB/s

Concurrency Level:      16
Time taken for tests:   3.246 seconds
Complete requests:      102040
Failed requests:        0
Total transferred:      107698394 bytes
Requests per second:    31435.64 [#/sec]
Transfer rate:          32401.20 [Kbytes/sec]

Connection Times (ms)
              min      avg        max      std
Total:        0.1      0.4       40.5      0.5

Percentage of the requests served within a certain time (ms)
   50%      0.3 ms
   66%      0.4 ms
   75%      0.5 ms
   90%      0.6 ms
   95%      0.9 ms
   98%      1.3 ms
   99%      1.8 ms
  100%     40.5 ms
```

Then I force to erasure encode the volumes by `ec.encode -collection t -quietFor 1s -fullPercent=0.001`

Here is the normal EC read performance by `weed benchmark -master localhost:9334 -n 102040 -collection=t -write=false`. 

You may need to run it twice because of some one-time read for the volume version. The EC read performance is about half of the normal volume read performance, because of the extra network hop.

```
------------ Randomly Reading Benchmark ----------
Completed 14077 of 102040 requests, 13.8% 14046.8/s 14.1MB/s
Completed 28261 of 102040 requests, 27.7% 14184.1/s 14.3MB/s
Completed 42580 of 102040 requests, 41.7% 14348.0/s 14.4MB/s
Completed 56617 of 102040 requests, 55.5% 14008.5/s 14.1MB/s
Completed 70513 of 102040 requests, 69.1% 13896.0/s 14.0MB/s
Completed 84264 of 102040 requests, 82.6% 13751.1/s 13.8MB/s
Completed 97858 of 102040 requests, 95.9% 13623.1/s 13.7MB/s

Concurrency Level:      16
Time taken for tests:   7.306 seconds
Complete requests:      102040
Failed requests:        0
Total transferred:      107699432 bytes
Requests per second:    13966.69 [#/sec]
Transfer rate:          14395.82 [Kbytes/sec]

Connection Times (ms)
              min      avg        max      std
Total:        0.1      1.1       24.9      0.7

Percentage of the requests served within a certain time (ms)
   50%      1.0 ms
   66%      1.2 ms
   75%      1.3 ms
   80%      1.4 ms
   90%      1.7 ms
   95%      2.1 ms
   98%      2.8 ms
   99%      3.4 ms
  100%     24.9 ms
```

Now let's stop one of the 4 servers. There will be 3 or 4 shards missing, out of the total 14 shards. It is still readable. But the read speed is slower because the volume server needs to contact all other servers to reconstruct the missing data.

```
------------ Randomly Reading Benchmark ----------
Completed 9458 of 102040 requests, 9.3% 9456.8/s 9.5MB/s
Completed 19216 of 102040 requests, 18.8% 9758.1/s 9.8MB/s
Completed 28837 of 102040 requests, 28.3% 9620.1/s 9.7MB/s
Completed 38221 of 102040 requests, 37.5% 9385.6/s 9.4MB/s
Completed 47410 of 102040 requests, 46.5% 9177.2/s 9.2MB/s
Completed 56586 of 102040 requests, 55.5% 9186.0/s 9.2MB/s
Completed 66274 of 102040 requests, 64.9% 9679.4/s 9.7MB/s
Completed 75385 of 102040 requests, 73.9% 9120.8/s 9.2MB/s
Completed 84028 of 102040 requests, 82.3% 8643.3/s 8.7MB/s
Completed 92447 of 102040 requests, 90.6% 8416.7/s 8.5MB/s
Completed 100831 of 102040 requests, 98.8% 8386.2/s 8.4MB/s

Concurrency Level:      16
Time taken for tests:   11.149 seconds
Complete requests:      102040
Failed requests:        0
Total transferred:      107702392 bytes
Requests per second:    9152.52 [#/sec]
Transfer rate:          9433.99 [Kbytes/sec]

Connection Times (ms)
              min      avg        max      std
Total:        0.1      1.7       40.1      1.6

Percentage of the requests served within a certain time (ms)
   50%      1.2 ms
   66%      1.7 ms
   75%      2.1 ms
   80%      2.4 ms
   90%      3.5 ms
   95%      4.6 ms
   98%      6.4 ms
   99%      7.7 ms
  100%     40.1 ms
```
