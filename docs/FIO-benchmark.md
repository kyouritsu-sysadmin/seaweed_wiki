---
id: FIO-benchmark
title: "FIO benchmark"
sidebar_label: "FIO benchmark"
---

# FIO Benchmark

Here is the result of using tool [fio](https://github.com/axboe/fio) running on my personal laptop. Just for reference. Please benchmark with your own hardware.

* Hardware: Apple Silicon Mac (darwin/arm64), macFUSE.
* SeaweedFS version: `30GB 4.20` (built from master at commit `dfecd664f`).
* fio version: `fio-3.42`.
* Setup: `weed server -filer -s3 -dir=/tmp/swfs-bench/data` with `weed mount -filer=localhost:8888 -dir=/tmp/swfs-bench/mnt`.
* All six tests run back-to-back against the same mount.

# Prepare A file

Go to any mounted directory:

```
fio --randrepeat=1 --name=test --filename=fiotest --bs=128k --iodepth=1 --size=10G

```

# Random Read

Random Read with 4KB, 128KB and 2MB block sizes, with direct IO enabled.

```
$ fio --randrepeat=1 --name=test --filename=fiotest --bs=4k --iodepth=1 --readwrite=randread --size=10G -direct=1
test: (g=0): rw=randread, bs=(R) 4096B-4096B, (W) 4096B-4096B, (T) 4096B-4096B, ioengine=psync, iodepth=1
fio-3.42
Starting 1 process
test: (groupid=0, jobs=1): err= 0: pid=77069: Wed Apr 15 14:33:28 2026
  read: IOPS=5821, BW=22.7MiB/s (23.8MB/s)(10.0GiB/450279msec)
    clat (usec): min=14, max=53330, avg=171.40, stdev=94.52
     lat (usec): min=14, max=53330, avg=171.42, stdev=94.52
    clat percentiles (usec):
     |  1.00th=[   58],  5.00th=[   62], 10.00th=[   74], 20.00th=[  153],
     | 30.00th=[  163], 40.00th=[  167], 50.00th=[  172], 60.00th=[  178],
     | 70.00th=[  184], 80.00th=[  192], 90.00th=[  212], 95.00th=[  253],
     | 99.00th=[  338], 99.50th=[  400], 99.90th=[  652], 99.95th=[  881],
     | 99.99th=[ 2008]
   bw (  KiB/s): min= 9288, max=33407, per=100.00%, avg=23303.72, stdev=2442.70, samples=898
   iops        : min= 2322, max= 8351, avg=5825.82, stdev=610.68, samples=898
  lat (usec)   : 20=0.01%, 50=0.01%, 100=10.98%, 250=83.74%, 500=5.02%
  lat (usec)   : 750=0.16%, 1000=0.03%
  lat (msec)   : 2=0.03%, 4=0.01%, 10=0.01%, 20=0.01%, 50=0.01%
  lat (msec)   : 100=0.01%
  cpu          : usr=0.35%, sys=3.73%, ctx=2642999, majf=1, minf=16
  IO depths    : 1=100.0%, 2=0.0%, 4=0.0%, 8=0.0%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=2621440,0,0,0 short=0,0,0,0 dropped=0,0,0,0
     latency   : target=0.00ns, window=0.00ns, percentile=100.00%, depth=1

Run status group 0 (all jobs):
   READ: bw=22.7MiB/s (23.8MB/s), 22.7MiB/s-22.7MiB/s (23.8MB/s-23.8MB/s), io=10.0GiB (10.7GB), run=450279-450279msec


$ fio --randrepeat=1 --name=test --filename=fiotest --bs=128k --iodepth=1 --readwrite=randread --size=10G -direct=1
test: (g=0): rw=randread, bs=(R) 128KiB-128KiB, (W) 128KiB-128KiB, (T) 128KiB-128KiB, ioengine=psync, iodepth=1
fio-3.42
Starting 1 process
test: (groupid=0, jobs=1): err= 0: pid=98869: Wed Apr 15 14:33:55 2026
  read: IOPS=3063, BW=383MiB/s (402MB/s)(10.0GiB/26741msec)
    clat (usec): min=20, max=19500, avg=326.02, stdev=143.58
     lat (usec): min=20, max=19501, avg=326.05, stdev=143.59
    clat percentiles (usec):
     |  1.00th=[  112],  5.00th=[  141], 10.00th=[  255], 20.00th=[  281],
     | 30.00th=[  293], 40.00th=[  302], 50.00th=[  310], 60.00th=[  322],
     | 70.00th=[  343], 80.00th=[  375], 90.00th=[  416], 95.00th=[  469],
     | 99.00th=[  693], 99.50th=[  848], 99.90th=[ 1811], 99.95th=[ 2114],
     | 99.99th=[ 3130]
   bw (  KiB/s): min=338944, max=419072, per=100.00%, avg=392823.72, stdev=15668.15, samples=53
   iops        : min= 2648, max= 3274, avg=3068.62, stdev=122.38, samples=53
  lat (usec)   : 50=0.31%, 100=0.01%, 250=8.91%, 500=87.13%, 750=2.94%
  lat (usec)   : 1000=0.30%
  lat (msec)   : 2=0.32%, 4=0.06%, 10=0.01%, 20=0.01%
  cpu          : usr=0.17%, sys=2.61%, ctx=83580, majf=0, minf=18
  IO depths    : 1=100.0%, 2=0.0%, 4=0.0%, 8=0.0%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=81920,0,0,0 short=0,0,0,0 dropped=0,0,0,0
     latency   : target=0.00ns, window=0.00ns, percentile=100.00%, depth=1

Run status group 0 (all jobs):
   READ: bw=383MiB/s (402MB/s), 383MiB/s-383MiB/s (402MB/s-402MB/s), io=10.0GiB (10.7GB), run=26741-26741msec


$ fio --randrepeat=1 --name=test --filename=fiotest --bs=2m --iodepth=1 --readwrite=randread --size=10G -direct=1
test: (g=0): rw=randread, bs=(R) 2048KiB-2048KiB, (W) 2048KiB-2048KiB, (T) 2048KiB-2048KiB, ioengine=psync, iodepth=1
fio-3.42
Starting 1 process
test: (groupid=0, jobs=1): err= 0: pid=99986: Wed Apr 15 14:34:06 2026
  read: IOPS=456, BW=913MiB/s (958MB/s)(10.0GiB/11211msec)
    clat (usec): min=144, max=49606, avg=2187.28, stdev=1407.58
     lat (usec): min=144, max=49606, avg=2187.35, stdev=1407.59
    clat percentiles (usec):
     |  1.00th=[  180],  5.00th=[  210], 10.00th=[  273], 20.00th=[ 1139],
     | 30.00th=[ 1696], 40.00th=[ 1975], 50.00th=[ 2245], 60.00th=[ 2474],
     | 70.00th=[ 2671], 80.00th=[ 2999], 90.00th=[ 3392], 95.00th=[ 3851],
     | 99.00th=[ 5735], 99.50th=[ 6718], 99.90th=[ 8455], 99.95th=[15008],
     | 99.99th=[49546]
   bw (  KiB/s): min=585728, max=1277952, per=99.70%, avg=932541.86, stdev=161340.42, samples=22
   iops        : min=  286, max=  624, avg=455.05, stdev=78.68, samples=22
  lat (usec)   : 250=9.24%, 500=1.97%, 750=0.98%, 1000=3.38%
  lat (msec)   : 2=25.53%, 4=54.65%, 10=4.18%, 20=0.04%, 50=0.04%
  cpu          : usr=0.08%, sys=2.56%, ctx=11489, majf=0, minf=139
  IO depths    : 1=100.0%, 2=0.0%, 4=0.0%, 8=0.0%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=5120,0,0,0 short=0,0,0,0 dropped=0,0,0,0
     latency   : target=0.00ns, window=0.00ns, percentile=100.00%, depth=1

Run status group 0 (all jobs):
   READ: bw=913MiB/s (958MB/s), 913MiB/s-913MiB/s (958MB/s-958MB/s), io=10.0GiB (10.7GB), run=11211-11211msec

```



# Sequential Read

Sequential Read with 4KB, 128KB and 2MB block sizes.

```
$ fio --randrepeat=1 --name=test --filename=fiotest --bs=4k --iodepth=1 --readwrite=read --size=10G
test: (g=0): rw=read, bs=(R) 4096B-4096B, (W) 4096B-4096B, (T) 4096B-4096B, ioengine=psync, iodepth=1
fio-3.42
Starting 1 process
test: (groupid=0, jobs=1): err= 0: pid=947: Wed Apr 15 14:34:18 2026
  read: IOPS=394k, BW=1538MiB/s (1612MB/s)(10.0GiB/6659msec)
    clat (nsec): min=0, max=114751k, avg=2447.49, stdev=413885.84
     lat (nsec): min=0, max=114751k, avg=2465.25, stdev=413885.77
    clat percentiles (nsec):
     |  1.00th=[    0],  5.00th=[    0], 10.00th=[    0], 20.00th=[    0],
     | 30.00th=[    0], 40.00th=[    0], 50.00th=[    0], 60.00th=[ 1004],
     | 70.00th=[ 1004], 80.00th=[ 1004], 90.00th=[ 1004], 95.00th=[ 1004],
     | 99.00th=[ 1004], 99.50th=[ 2008], 99.90th=[21120], 99.95th=[22912],
     | 99.99th=[41216]
   bw (  MiB/s): min= 1243, max= 1836, per=99.60%, avg=1531.68, stdev=134.18, samples=13
   iops        : min=318278, max=470261, avg=392110.00, stdev=34350.53, samples=13
  lat (nsec)   : 2=51.72%
  lat (usec)   : 2=47.71%, 4=0.10%, 10=0.02%, 20=0.26%, 50=0.18%
  lat (usec)   : 100=0.01%, 250=0.01%, 500=0.01%, 750=0.01%, 1000=0.01%
  lat (msec)   : 2=0.01%, 4=0.01%, 10=0.01%, 50=0.01%, 100=0.01%
  lat (msec)   : 250=0.01%
  cpu          : usr=6.70%, sys=25.89%, ctx=24651, majf=0, minf=13
  IO depths    : 1=100.0%, 2=0.0%, 4=0.0%, 8=0.0%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=2621440,0,0,0 short=0,0,0,0 dropped=0,0,0,0
     latency   : target=0.00ns, window=0.00ns, percentile=100.00%, depth=1

Run status group 0 (all jobs):
   READ: bw=1538MiB/s (1612MB/s), 1538MiB/s-1538MiB/s (1612MB/s-1612MB/s), io=10.0GiB (10.7GB), run=6659-6659msec


$ fio --randrepeat=1 --name=test --filename=fiotest --bs=128k --iodepth=1 --readwrite=read --size=10G
test: (g=0): rw=read, bs=(R) 128KiB-128KiB, (W) 128KiB-128KiB, (T) 128KiB-128KiB, ioengine=psync, iodepth=1
fio-3.42
Starting 1 process
test: (groupid=0, jobs=1): err= 0: pid=1448: Wed Apr 15 14:34:24 2026
  read: IOPS=14.3k, BW=1790MiB/s (1877MB/s)(10.0GiB/5722msec)
    clat (usec): min=4, max=128818, avg=69.24, stdev=2373.84
     lat (usec): min=4, max=128818, avg=69.26, stdev=2373.84
    clat percentiles (usec):
     |  1.00th=[    8],  5.00th=[    8], 10.00th=[    8], 20.00th=[    8],
     | 30.00th=[    8], 40.00th=[    8], 50.00th=[    8], 60.00th=[    9],
     | 70.00th=[    9], 80.00th=[    9], 90.00th=[    9], 95.00th=[   10],
     | 99.00th=[   12], 99.50th=[   15], 99.90th=[   43], 99.95th=[88605],
     | 99.99th=[96994]
   bw (  MiB/s): min= 1524, max= 1920, per=99.33%, avg=1777.53, stdev=166.20, samples=11
   iops        : min=12192, max=15360, avg=14219.91, stdev=1329.51, samples=11
  lat (usec)   : 10=97.53%, 20=2.20%, 50=0.18%, 100=0.01%, 250=0.01%
  lat (usec)   : 500=0.01%
  lat (msec)   : 4=0.01%, 10=0.01%, 50=0.01%, 100=0.06%, 250=0.01%
  cpu          : usr=0.30%, sys=21.69%, ctx=12899, majf=0, minf=19
  IO depths    : 1=100.0%, 2=0.0%, 4=0.0%, 8=0.0%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=81920,0,0,0 short=0,0,0,0 dropped=0,0,0,0
     latency   : target=0.00ns, window=0.00ns, percentile=100.00%, depth=1

Run status group 0 (all jobs):
   READ: bw=1790MiB/s (1877MB/s), 1790MiB/s-1790MiB/s (1877MB/s-1877MB/s), io=10.0GiB (10.7GB), run=5722-5722msec


$ fio --randrepeat=1 --name=test --filename=fiotest --bs=2m --iodepth=1 --readwrite=read --size=10G
test: (g=0): rw=read, bs=(R) 2048KiB-2048KiB, (W) 2048KiB-2048KiB, (T) 2048KiB-2048KiB, ioengine=psync, iodepth=1
fio-3.42
Starting 1 process
test: (groupid=0, jobs=1): err= 0: pid=1932: Wed Apr 15 14:34:30 2026
  read: IOPS=1028, BW=2057MiB/s (2157MB/s)(10.0GiB/4979msec)
    clat (usec): min=101, max=92136, avg=959.57, stdev=7935.48
     lat (usec): min=101, max=92136, avg=959.60, stdev=7935.48
    clat percentiles (usec):
     |  1.00th=[  112],  5.00th=[  116], 10.00th=[  117], 20.00th=[  119],
     | 30.00th=[  120], 40.00th=[  122], 50.00th=[  125], 60.00th=[  129],
     | 70.00th=[  139], 80.00th=[  153], 90.00th=[  176], 95.00th=[  202],
     | 99.00th=[68682], 99.50th=[79168], 99.90th=[83362], 99.95th=[87557],
     | 99.99th=[91751]
   bw (  MiB/s): min= 1564, max= 2304, per=99.46%, avg=2045.61, stdev=263.06, samples=9
   iops        : min=  782, max= 1152, avg=1022.56, stdev=131.52, samples=9
  lat (usec)   : 250=97.60%, 500=1.17%, 750=0.02%
  lat (msec)   : 4=0.06%, 10=0.06%, 20=0.02%, 50=0.06%, 100=1.02%
  cpu          : usr=0.04%, sys=27.68%, ctx=13278, majf=0, minf=141
  IO depths    : 1=100.0%, 2=0.0%, 4=0.0%, 8=0.0%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=5120,0,0,0 short=0,0,0,0 dropped=0,0,0,0
     latency   : target=0.00ns, window=0.00ns, percentile=100.00%, depth=1

Run status group 0 (all jobs):
   READ: bw=2057MiB/s (2157MB/s), 2057MiB/s-2057MiB/s (2157MB/s-2157MB/s), io=10.0GiB (10.7GB), run=4979-4979msec

```

# Summary

| Test            | Block size | Bandwidth          | IOPS  |
|-----------------|------------|--------------------|-------|
| Random Read     | 4 KiB      | 22.7 MiB/s         | 5,821 |
| Random Read     | 128 KiB    | 383 MiB/s          | 3,063 |
| Random Read     | 2 MiB      | 913 MiB/s          | 456   |
| Sequential Read | 4 KiB      | 1538 MiB/s         | 394k  |
| Sequential Read | 128 KiB    | 1790 MiB/s         | 14.3k |
| Sequential Read | 2 MiB      | 2057 MiB/s         | 1,028 |
