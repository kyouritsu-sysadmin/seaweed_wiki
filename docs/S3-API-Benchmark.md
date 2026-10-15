---
id: S3-API-Benchmark
title: "S3 API Benchmark"
sidebar_label: "S3 API Benchmark"
---

# Test setup

Here are some tests on one single computer. However, if you need more performance, you can add `filer` and `s3` to linearly increase total throughput.

# Test with Warp
https://github.com/minio/warp

Warp is a more complete test suite. It needs identity access management. So you would need to configure authentication info with `weed s3 -conf=...` or `weed filer -s3 -s3.conf=...`. See https://github.com/seaweedfs/seaweedfs/wiki/Amazon-S3-API#authentication

Here is the results from my local laptop written to an external SSD via USB 3.1:

```
$ warp mixed --host localhost:8333 --access-key some_access_key1 --secret-key some_secret_key1 --duration=1m --obj.size 1024B --concurrent 4
warp: Benchmark data written to "warp-mixed-2021-07-20[010604]-28pi.csv.zst"
Mixed operations.
Operation: DELETE, 10%, Concurrency: 4, Duration: 59s.
 * Throughput: 578.41 obj/s

Operation: GET, 45%, Concurrency: 4, Duration: 59s.
 * Throughput: 2.54 MiB/s, 2602.54 obj/s

Operation: PUT, 15%, Concurrency: 4, Duration: 59s.
 * Throughput: 0.85 MiB/s, 867.63 obj/s

Operation: STAT, 30%, Concurrency: 4, Duration: 59s.
 * Throughput: 1735.03 obj/s

Cluster Total: 3.39 MiB/s, 5783.74 obj/s
warp: Cleanup Done.

$ warp mixed --host localhost:8333 --access-key some_access_key1 --secret-key some_secret_key1 --duration=1m --obj.size 102400B --concurrent 4
warp: Benchmark data written to "warp-mixed-2021-07-20[010749]-xFIM.csv.zst"
Mixed operations.
Operation: DELETE, 10%, Concurrency: 4, Duration: 59s.
 * Throughput: 344.99 obj/s

Operation: GET, 45%, Concurrency: 4, Duration: 59s.
 * Throughput: 151.59 MiB/s, 1552.25 obj/s

Operation: PUT, 15%, Concurrency: 4, Duration: 59s.
 * Throughput: 50.54 MiB/s, 517.49 obj/s

Operation: STAT, 30%, Concurrency: 4, Duration: 59s.
 * Throughput: 1034.85 obj/s

Cluster Total: 202.13 MiB/s, 3449.58 obj/s
warp: Cleanup Done.

```

# Another test with warp

Here is a user-provided `run-warp.sh` file.
```
#!/bin/bash -e

if [[ "$#" -lt 1 ]]
then
  echo "Usage: $0 count [options]"
  exit 1
fi

COUNT="$1"
shift

COUNTER=0
while [  $COUNTER -lt $COUNT ]; do
    let COUNTER=COUNTER+1
    warp client "127.0.0.1:576${COUNTER}" \
      1> warp-client-"${COUNTER}".out \
      2> warp-client-"${COUNTER}".err &
done

sleep 5

warp "$@" \
  --host "localhost:8333" \
  --access-key "some_access_key1" --secret-key "some_secret_key1" \
  --bucket warp-"${COUNTER}-$(date +%s)" \
  --warp-client=127.0.0.1:576{1...$COUNT} \
  1> warp.out \
  2> warp.err

```

Start the warp this way:
```
./run-warp.sh 4 list --concurrent 5 --objects 100000 --obj.size=4KiB --duration 60s
```

Here is the result:
```
warp: Benchmark data written to "warp-remote-2020-11-29[165701]-gsYs.csv.zst"

Operation: PUT
* Average: 15.35 MiB/s, 3929.68 obj/s

Throughput, split into 101 x 1s:
 * Fastest: 17.1MiB/s, 4387.13 obj/s
 * 50% Median: 15.8MiB/s, 4045.38 obj/s
 * Slowest: 12.8MiB/s, 3280.82 obj/s

```

# Test with Hotsauce S3 Benchmark
Found this https://github.com/markhpc/hsbench tool which seems easy to use.


Here are my results on my laptop. 

```
benchmark$  hsbench -a accesstoken -s secret -z 4K -d 10 -t 10 -b 10 -u http://localhost:8333 -m "cxipgldx" -bp "hsbench-"
2020/11/17 20:05:51 Hotsauce S3 Benchmark Version 0.1
2020/11/17 20:05:51 Parameters:
2020/11/17 20:05:51 url=http://localhost:8333
2020/11/17 20:05:51 object_prefix=
2020/11/17 20:05:51 bucket_prefix=hsbench-
2020/11/17 20:05:51 region=us-east-1
2020/11/17 20:05:51 modes=cxipgldx
2020/11/17 20:05:51 output=
2020/11/17 20:05:51 json_output=
2020/11/17 20:05:51 max_keys=1000
2020/11/17 20:05:51 object_count=-1
2020/11/17 20:05:51 bucket_count=10
2020/11/17 20:05:51 duration=10
2020/11/17 20:05:51 threads=10
2020/11/17 20:05:51 loops=1
2020/11/17 20:05:51 size=4K
2020/11/17 20:05:51 interval=1.000000
2020/11/17 20:05:51 Running Loop 0 BUCKET CLEAR TEST
2020/11/17 20:05:51 Loop: 0, Int: TOTAL, Dur(s): 0.0, Mode: BCLR, Ops: 0, MB/s: 0.00, IO/s: 0, Lat(ms): [ min: 0.0, avg: 0.0, 99%: 0.0, max: 0.0 ], Slowdowns: 0
2020/11/17 20:05:51 Running Loop 0 BUCKET DELETE TEST
2020/11/17 20:05:51 Loop: 0, Int: TOTAL, Dur(s): 0.0, Mode: BDEL, Ops: 0, MB/s: 0.00, IO/s: 0, Lat(ms): [ min: 0.0, avg: 0.0, 99%: 0.0, max: 0.0 ], Slowdowns: 0
2020/11/17 20:05:51 Running Loop 0 BUCKET INIT TEST
2020/11/17 20:05:51 Loop: 0, Int: TOTAL, Dur(s): 0.0, Mode: BINIT, Ops: 10, MB/s: 0.00, IO/s: 3166, Lat(ms): [ min: 1.8, avg: 2.7, 99%: 3.0, max: 3.0 ], Slowdowns: 0
2020/11/17 20:05:51 Running Loop 0 OBJECT PUT TEST
2020/11/17 20:05:52 Loop: 0, Int: 0, Dur(s): 1.0, Mode: PUT, Ops: 3641, MB/s: 14.22, IO/s: 3641, Lat(ms): [ min: 1.4, avg: 2.7, 99%: 7.3, max: 91.6 ], Slowdowns: 0
2020/11/17 20:05:53 Loop: 0, Int: 1, Dur(s): 1.0, Mode: PUT, Ops: 3986, MB/s: 15.57, IO/s: 3986, Lat(ms): [ min: 1.4, avg: 2.5, 99%: 5.6, max: 24.9 ], Slowdowns: 0
2020/11/17 20:05:54 Loop: 0, Int: 2, Dur(s): 1.0, Mode: PUT, Ops: 4091, MB/s: 15.98, IO/s: 4091, Lat(ms): [ min: 1.4, avg: 2.4, 99%: 5.4, max: 20.0 ], Slowdowns: 0
2020/11/17 20:05:55 Loop: 0, Int: 3, Dur(s): 1.0, Mode: PUT, Ops: 4011, MB/s: 15.67, IO/s: 4011, Lat(ms): [ min: 1.4, avg: 2.5, 99%: 5.6, max: 20.6 ], Slowdowns: 0
2020/11/17 20:05:56 Loop: 0, Int: 4, Dur(s): 1.0, Mode: PUT, Ops: 4145, MB/s: 16.19, IO/s: 4145, Lat(ms): [ min: 1.1, avg: 2.4, 99%: 5.8, max: 19.3 ], Slowdowns: 0
2020/11/17 20:05:57 Loop: 0, Int: 5, Dur(s): 1.0, Mode: PUT, Ops: 3648, MB/s: 14.25, IO/s: 3648, Lat(ms): [ min: 1.2, avg: 2.7, 99%: 7.4, max: 22.5 ], Slowdowns: 0
2020/11/17 20:05:58 Loop: 0, Int: 6, Dur(s): 1.0, Mode: PUT, Ops: 2978, MB/s: 11.63, IO/s: 2978, Lat(ms): [ min: 1.4, avg: 3.4, 99%: 9.8, max: 45.6 ], Slowdowns: 0
2020/11/17 20:05:59 Loop: 0, Int: 7, Dur(s): 1.0, Mode: PUT, Ops: 3287, MB/s: 12.84, IO/s: 3287, Lat(ms): [ min: 1.5, avg: 3.0, 99%: 9.0, max: 23.7 ], Slowdowns: 0
2020/11/17 20:06:00 Loop: 0, Int: 8, Dur(s): 1.0, Mode: PUT, Ops: 3201, MB/s: 12.50, IO/s: 3201, Lat(ms): [ min: 1.6, avg: 3.1, 99%: 8.4, max: 20.7 ], Slowdowns: 0
2020/11/17 20:06:01 Loop: 0, Int: 9, Dur(s): 1.0, Mode: PUT, Ops: 3317, MB/s: 12.96, IO/s: 3317, Lat(ms): [ min: 1.4, avg: 3.0, 99%: 8.0, max: 20.1 ], Slowdowns: 0
2020/11/17 20:06:01 Loop: 0, Int: TOTAL, Dur(s): 10.0, Mode: PUT, Ops: 36315, MB/s: 14.18, IO/s: 3631, Lat(ms): [ min: 1.1, avg: 2.7, 99%: 7.2, max: 91.6 ], Slowdowns: 0
2020/11/17 20:06:01 Running Loop 0 OBJECT GET TEST
2020/11/17 20:06:02 Loop: 0, Int: 0, Dur(s): 1.0, Mode: GET, Ops: 3724, MB/s: 14.55, IO/s: 3724, Lat(ms): [ min: 1.3, avg: 2.6, 99%: 4.9, max: 19.3 ], Slowdowns: 0
2020/11/17 20:06:03 Loop: 0, Int: 1, Dur(s): 1.0, Mode: GET, Ops: 4236, MB/s: 16.55, IO/s: 4236, Lat(ms): [ min: 1.0, avg: 2.3, 99%: 4.0, max: 24.3 ], Slowdowns: 0
2020/11/17 20:06:04 Loop: 0, Int: 2, Dur(s): 1.0, Mode: GET, Ops: 4303, MB/s: 16.81, IO/s: 4303, Lat(ms): [ min: 1.0, avg: 2.3, 99%: 4.0, max: 33.6 ], Slowdowns: 0
2020/11/17 20:06:05 Loop: 0, Int: 3, Dur(s): 1.0, Mode: GET, Ops: 4613, MB/s: 18.02, IO/s: 4613, Lat(ms): [ min: 1.2, avg: 2.1, 99%: 3.5, max: 25.9 ], Slowdowns: 0
2020/11/17 20:06:06 Loop: 0, Int: 4, Dur(s): 1.0, Mode: GET, Ops: 4461, MB/s: 17.43, IO/s: 4461, Lat(ms): [ min: 1.2, avg: 2.2, 99%: 3.1, max: 32.7 ], Slowdowns: 0
2020/11/17 20:06:07 Loop: 0, Int: 5, Dur(s): 1.0, Mode: GET, Ops: 4169, MB/s: 16.29, IO/s: 4169, Lat(ms): [ min: 1.0, avg: 2.4, 99%: 4.2, max: 27.5 ], Slowdowns: 0
2020/11/17 20:06:08 Loop: 0, Int: 6, Dur(s): 1.0, Mode: GET, Ops: 4121, MB/s: 16.10, IO/s: 4121, Lat(ms): [ min: 1.1, avg: 2.4, 99%: 3.7, max: 5.7 ], Slowdowns: 0
2020/11/17 20:06:09 Loop: 0, Int: 7, Dur(s): 1.0, Mode: GET, Ops: 3300, MB/s: 12.89, IO/s: 3300, Lat(ms): [ min: 1.4, avg: 3.0, 99%: 4.5, max: 8.8 ], Slowdowns: 0
2020/11/17 20:06:10 Loop: 0, Int: TOTAL, Dur(s): 9.0, Mode: GET, Ops: 36315, MB/s: 15.77, IO/s: 4038, Lat(ms): [ min: 1.0, avg: 2.4, 99%: 4.1, max: 33.6 ], Slowdowns: 0
2020/11/17 20:06:10 Running Loop 0 BUCKET LIST TEST
2020/11/17 20:06:10 Loop: 0, Int: TOTAL, Dur(s): 0.3, Mode: LIST, Ops: 40, MB/s: 0.00, IO/s: 133, Lat(ms): [ min: 45.5, avg: 73.1, 99%: 93.6, max: 93.6 ], Slowdowns: 0
2020/11/17 20:06:10 Running Loop 0 OBJECT DELETE TEST
2020/11/17 20:06:11 Loop: 0, Int: 0, Dur(s): 1.0, Mode: DEL, Ops: 5388, MB/s: 21.05, IO/s: 5388, Lat(ms): [ min: 0.7, avg: 1.8, 99%: 4.5, max: 99.4 ], Slowdowns: 0
2020/11/17 20:06:12 Loop: 0, Int: 1, Dur(s): 1.0, Mode: DEL, Ops: 6375, MB/s: 24.90, IO/s: 6375, Lat(ms): [ min: 0.8, avg: 1.6, 99%: 3.0, max: 8.6 ], Slowdowns: 0
2020/11/17 20:06:13 Loop: 0, Int: 2, Dur(s): 1.0, Mode: DEL, Ops: 3709, MB/s: 14.49, IO/s: 3709, Lat(ms): [ min: 0.8, avg: 2.7, 99%: 12.1, max: 17.1 ], Slowdowns: 0
2020/11/17 20:06:14 Loop: 0, Int: 3, Dur(s): 1.0, Mode: DEL, Ops: 1495, MB/s: 5.84, IO/s: 1495, Lat(ms): [ min: 0.8, avg: 6.7, 99%: 14.5, max: 17.9 ], Slowdowns: 0
2020/11/17 20:06:15 Loop: 0, Int: 4, Dur(s): 1.0, Mode: DEL, Ops: 1437, MB/s: 5.61, IO/s: 1437, Lat(ms): [ min: 0.9, avg: 7.0, 99%: 15.6, max: 17.7 ], Slowdowns: 0
2020/11/17 20:06:16 Loop: 0, Int: 5, Dur(s): 1.0, Mode: DEL, Ops: 1360, MB/s: 5.31, IO/s: 1360, Lat(ms): [ min: 0.9, avg: 7.3, 99%: 15.8, max: 25.9 ], Slowdowns: 0
2020/11/17 20:06:18 Loop: 0, Int: 6, Dur(s): 1.0, Mode: DEL, Ops: 1289, MB/s: 5.04, IO/s: 1289, Lat(ms): [ min: 0.8, avg: 7.4, 99%: 17.6, max: 29.5 ], Slowdowns: 0
2020/11/17 20:06:18 Loop: 0, Int: 7, Dur(s): 1.0, Mode: DEL, Ops: 313, MB/s: 1.22, IO/s: 313, Lat(ms): [ min: 0.8, avg: 33.1, 99%: 822.3, max: 823.5 ], Slowdowns: 0
2020/11/17 20:06:19 Loop: 0, Int: 8, Dur(s): 1.0, Mode: DEL, Ops: 1320, MB/s: 5.16, IO/s: 1320, Lat(ms): [ min: 1.0, avg: 7.6, 99%: 16.9, max: 19.6 ], Slowdowns: 0
2020/11/17 20:06:20 Loop: 0, Int: 9, Dur(s): 1.0, Mode: DEL, Ops: 1270, MB/s: 4.96, IO/s: 1270, Lat(ms): [ min: 1.0, avg: 7.9, 99%: 19.5, max: 29.7 ], Slowdowns: 0
2020/11/17 20:06:20 Loop: 0, Int: TOTAL, Dur(s): 10.0, Mode: DEL, Ops: 23966, MB/s: 9.36, IO/s: 2396, Lat(ms): [ min: 0.7, avg: 4.2, 99%: 15.3, max: 823.5 ], Slowdowns: 0
2020/11/17 20:06:20 Running Loop 0 BUCKET DELETE TEST
2020/11/17 20:06:21 Loop: 0, Int: TOTAL, Dur(s): 0.4, Mode: BDEL, Ops: 10, MB/s: 0.00, IO/s: 24, Lat(ms): [ min: 371.6, avg: 407.9, 99%: 421.6, max: 421.6 ], Slowdowns: 0
benchmark$
```
