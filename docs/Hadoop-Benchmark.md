---
id: Hadoop-Benchmark
title: "Hadoop Benchmark"
sidebar_label: "Hadoop Benchmark"
---

# Setup Hadoop Benchmark

Here are my steps. First, checkout the hadoop 3.4.1 binary, untar, and cd in to the hadoop directory.
```
wget https://downloads.apache.org/hadoop/common/hadoop-3.4.1/hadoop-3.4.1.tar.gz
tar xvf hadoop-3.4.1.tar.gz
cd hadoop-3.4.1
```

Modify the file `./etc/hadoop/core-site.xml`

```
<configuration>
    <property>
        <name>fs.seaweedfs.impl</name>
        <value>seaweed.hdfs.SeaweedFileSystem</value>
    </property>
    <property>
        <name>fs.defaultFS</name>
        <value>seaweedfs://localhost:8888</value>
    </property>
    <property>
       <name>fs.AbstractFileSystem.seaweedfs.impl</name>
       <value>seaweed.hdfs.SeaweedAbstractFileSystem</value>
    </property>
</configuration>
```

Then get the seaweedfs hadoop client jar.

```
cd share/hadoop/common/lib/
wget https://repo1.maven.org/maven2/com/seaweedfs/seaweedfs-hadoop3-client/4.38/seaweedfs-hadoop3-client-4.38.jar
cd ../../../..
```

# TestDFSIO Benchmark

The TestDFSIO benchmark is used for measuring I/O (read/write) performance.

**However, the generated data to write is all zero. SeaweedFS automatically compress this kind of data. So this is not scientific for now.**

## TestDFSIO write tests
Start the TestDFSIO write tests:

```
bin/hadoop jar ./share/hadoop/mapreduce/hadoop-mapreduce-client-jobclient-3.4.1-tests.jar TestDFSIO -write -nrFiles 4 -size 64MB -bufferSize 8388608 -resFile /tmp/TestDFSIOwrite.txt

...
INFO fs.TestDFSIO: ----- TestDFSIO ----- : write
INFO fs.TestDFSIO:             Date & time: Wed Jul 08 00:45:01 PDT 2026
INFO fs.TestDFSIO:         Number of files: 4
INFO fs.TestDFSIO:  Total MBytes processed: 256
INFO fs.TestDFSIO:       Throughput mb/sec: 605.2
INFO fs.TestDFSIO:  Average IO rate mb/sec: 633.27
INFO fs.TestDFSIO:   IO rate std deviation: 130.3
INFO fs.TestDFSIO:      Test exec time sec: 1.32
```

## TestDFSIO read tests

Start the TestDFSIO read tests:

```
bin/hadoop jar ./share/hadoop/mapreduce/hadoop-mapreduce-client-jobclient-3.4.1-tests.jar TestDFSIO -read -nrFiles 4 -size 64MB -bufferSize 8388608 -resFile /tmp/TestDFSIOread.txt

...

INFO fs.TestDFSIO: ----- TestDFSIO ----- : read
INFO fs.TestDFSIO:             Date & time: Wed Jul 08 00:45:10 PDT 2026
INFO fs.TestDFSIO:         Number of files: 4
INFO fs.TestDFSIO:  Total MBytes processed: 256
INFO fs.TestDFSIO:       Throughput mb/sec: 1174.31
INFO fs.TestDFSIO:  Average IO rate mb/sec: 1226.51
INFO fs.TestDFSIO:   IO rate std deviation: 227.6
INFO fs.TestDFSIO:      Test exec time sec: 1.28
```

Clean up the benchmark data when done:

```
bin/hadoop jar ./share/hadoop/mapreduce/hadoop-mapreduce-client-jobclient-3.4.1-tests.jar TestDFSIO -clean
```

# Independent Benchmarks

## Sugon (中科曙光)
To test the performance of HDFS and SeaweedFS, we did a comparison by running 4 common spark operators, such as `count`, `group by`, `join` and `write`, for `group by` and `join` , there is a  `count` followed to act.

The basic configuration information of cluster is as follows: 

- HDFS：
  + Node number: 25
  + Total disks: 36disk  *  25node = 900disk
  + Disk capacity: 3.7T SATA
  + Total disk capacity: 3.19PB
  + Replication: 5

- SeaweedFS:

  + Node number: 6（3+3 rack）
  + Disk capacity: 3.7T SATA
  + Cluster max volume: 21500
  + Total disk capacity: 799TB
  + Replication policy: 010

Here are the details and results of our test. At the beginning of the test, we put our data to  both HDFS and SeaweedFS.  The amount of the data is 100 million records, and stored in 200 parquet files. The size of each parquet file is about 89 MB. We ran spark on yarn with 20 executors. In spark, we got two DataFrames by reading parquet from HDFS and HCFS separately, then executed `count`, `group by` and `join`  by 100 times , and `write` by 10 times, on each DataFrame.

As for `count`,  SeaweedFS's advantage  is obvious. The average time of the DataFrame from HDFS is 4.05 seconds, while SeaweedFS is only 0.659. Following is the result:

| Summary | HDFS  | SeaweedFS  |
| ------- | ----- | ----- |
| Count   | 100   | 100   |
| Mean    | 4.050 | 0.659 |
| Stddev  | 0.264 | 0.941 |
| Min     | 3.678 | 0.392 |
| Max     | 5.692 | 9.688 |



As for `write`, we wrote the DataFrame from HDFS to SeaweedFS, and  wrote the DataFrame from HCFS to SeaweedFS. Following is the result:

| Summary | HDFS    | SeaweedFS    |
| ------- | ------- | ------- |
| Count   | 10      | 10      |
| Mean    | 234.279 | 232.078 |
| Stddev  | 26.823  | 12.652  |
| Min     | 216.931 | 214.349 |
| Max     | 307.330 | 252.375 |



As for `group by`, following is the result:

| Summary | HDFS   | SeaweedFS   |
| ------- | ------ | ------ |
| Count   | 100    | 100    |
| Mean    | 14.121 | 12.515 |
| Stddev  | 1.972  | 1.255  |
| Min     | 12.879 | 11.322 |
| Max     | 32.296 | 22.573 |



As for `join`, every DataFrame join with itself on one column. Following is the result:

| Summary | HDFS   | SeaweedFS   |
| ------- | ------ | ------ |
| Count   | 100    | 100    |
| Mean    | 25.684 | 23.897 |
| Stddev  | 0.934  | 1.381  |
| Min     | 24.006 | 22.275 |
| Max     | 30.991 | 30.279 |
