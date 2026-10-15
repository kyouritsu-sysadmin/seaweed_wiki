---
id: Independent-Benchmarks
title: "Independent Benchmarks"
sidebar_label: "Independent Benchmarks"
---

Please submit independent benchmarks here. They will be re-organized to the right wiki place later.

# A talk comparing SeaweedFS with Minio.

https://github.com/miku/haystack

```
we used minio as a KVS with an S3 API and inserts got very slow after around 80-100M keys (it probably was the ext fs)
we looked for alternatives, that could be deployed quickly, found seeweedfs, tested it and deployed it
```

# Comparing with MooseFS

https://github.com/moosefs/moosefs/issues/370


I've decided to compare MooseFS performance to SeaweedFS in regards to small files.
I've copied all 30 million small files to SeaweedFS and then measured time taken by rsync to copy small files to empty 100GB SSD. It took 874 minutes (14h 34m) to fill the SSD with small files from MooseFS while it took 356 minutes (3h 56m) to fill the SSD from SeaweedFS.

SeaweedFS accomplished the task roughly 2.5 times faster than MooseFS but there is a catch: I've placed small files to SSD-backed chunkservers while SeaweedFS had the data on rotational HDDs. That's a serious evidence of efficient design when one can demonstrate 2+ times better performance on HDD versus SSD, isn't it?

# A SeaweedFS introduction in Chinese
https://github.com/bingoohuang/blog/issues/57

# Benchmark SeaweedFS as a GlusterFS replacement
https://github.com/seaweedfs/seaweedfs/wiki/Benchmark-SeaweedFS-as-a-GlusterFS-replacement

# Benchmark Object Stores
https://it-notes.dragas.net/2025/11/06/self-hosting-your-mastodon-media-with-seaweedfs/
