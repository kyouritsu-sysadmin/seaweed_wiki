---
id: Filer-as-a-Key-Large-Value-Store
title: "Filer as a Key Large Value Store"
sidebar_label: "Filer as a Key Large Value Store"
---

# Key-Large-Value Store

Usually a distributed file system is considered slow but with large capacity, while a distributed key-value store is not advised to store large binary objects.

What about a key value system that can store small and large objects with almost unlimited capacity?

It is true that key-value stores are limited by the storage capacity. As the data size grows, KV stores usually get slower due to more IO cost. For example, Cassandra needs to compact its log-structured-merge tree periodically, when all key and value data are sorted, merged, and persisted to disk multiple times. The larger data size can only slow down the operations.

We can store the large value data outside of KV stores, and only store the reference in KV stores. 

With SeaweedFS, a large value can be stored as a chunk on volume servers and can be referenced by a 16-byte chunk id. In addition, the smaller values can be stored directly in KV stores, saving one network hop. So you can get an efficient KV store with almost unlimited size, while still have the same access speed for small values and reasonable speed for larger values.

## How to do it?

There are two tricks:
* Usually the entries are in one folder. You can configure for [Super Large Directories](./Super-Large-Directories.md). It will avoid the additional work to maintain the file list in the large folder.
* Optionally configure to store small values in filer store. E.g., `weed filer -saveToFilerLimit=1024` will store values less than 1KB to filer store itself. Accessing these small entries are basically no difference than accessing the underlying key-value stores directly.

## AWS S3 is a poor key-value store

Using AWS S3 as a key-value store is tempting due to its unlimited capacity. However, AWS S3 has no SLA for its access latency since there are a lot of noisy neighbors.

What is more, the API cost is a big concern. AWS S3 seems cheap for storage, but for small objects which requires frequent access, the API cost can quickly add up at $0.005 for 1 thousand PUT/DELETE requests.

If we need to test with 1 million objects:
  * 1 million write operations cost $5, or $150/month for 12 operations/second in production.
  * Another $5 to clean up the 1 million test objects.

So not only it is fairly slow, but also it is expensive to use S3 as a key-value store.

# Benchmark with YCSB as a Key-Value store

[Yahoo! Cloud Serving Benchmark(YCSB)](https://github.com/brianfrankcooper/YCSB) is a framework for evaluating the performance of different “key-value” and “cloud” serving stores.

### SeaweedFS Benefits
The databases usually is much more expensive than SeaweedFS for the same capacity. It would be nice to to quickly store and access files with unlimited disk space, and only store a file name in the main database.

SeaweedFS has no additional costs for API access. For example, it is a fixed monthly cost if running on EC2 instances. You do not need to worry about unmanageable API costs.

And SeaweedFS can offload less-accessed data to S3 with [Cloud Tier](./Cloud-Tier.md), so it literally has unlimited storage space.

### SeaweedFS on YCSB

SeaweedFS has been added to YCSB https://github.com/brianfrankcooper/YCSB/tree/master/seaweedfs

To run SeaweedFS benchmark with YCSB, just checkout the repo, and run
```
./bin/ycsb load seaweedfs -p seaweed.filerHost=localhost -p seaweed.filerPort=8888 -p seaweed.folder=/ycsb \
    -p fieldlength=10 -p fieldcount=20 -p recordcount=1000000 -p threadcount=4 -P workloads/workloada
```

Here is my result on my macbook. Separating SeaweedFS into multiple dedicated instances and run the YCSB client on a separate machine will have better numbers. 

Of course, the numbers depend on too many factors, e.g., disk, memory, cpu, network, data size, concurrency, etc. I would like you to share your real results with your actual setups.

```
[OVERALL], RunTime(ms), 557512
[OVERALL], Throughput(ops/sec), 1793.6833646630027
[TOTAL_GCS_PS_Scavenge], Count, 1213
[TOTAL_GC_TIME_PS_Scavenge], Time(ms), 3201
[TOTAL_GC_TIME_%_PS_Scavenge], Time(%), 0.5741580450286272
[TOTAL_GCS_PS_MarkSweep], Count, 1
[TOTAL_GC_TIME_PS_MarkSweep], Time(ms), 24
[TOTAL_GC_TIME_%_PS_MarkSweep], Time(%), 0.0043048400751912064
[TOTAL_GCs], Count, 1214
[TOTAL_GC_TIME], Time(ms), 3225
[TOTAL_GC_TIME_%], Time(%), 0.5784628851038185
[CLEANUP], Operations, 4
[CLEANUP], AverageLatency(us), 1.75
[CLEANUP], MinLatency(us), 0
[CLEANUP], MaxLatency(us), 5
[CLEANUP], 95thPercentileLatency(us), 5
[CLEANUP], 99thPercentileLatency(us), 5
[INSERT], Operations, 1000000
[INSERT], AverageLatency(us), 2221.879515
[INSERT], MinLatency(us), 929
[INSERT], MaxLatency(us), 623615
[INSERT], 95thPercentileLatency(us), 3347
[INSERT], 99thPercentileLatency(us), 6311
[INSERT], Return=OK, 1000000
```
