---
id: Filer-Stores
title: "Filer Stores"
sidebar_label: "Filer Stores"
---

### Comparing Storage Options

The Filer Store persists all file metadata and directory information.

| Filer Store Name | Lookup | number of entries in a folder | Scalability | Directory Renaming | TTL | [Fast Bucket Deletion](https://github.com/seaweedfs/seaweedfs/wiki/S3-API-FAQ#how-to-speed-up-bucket-deletion) |Note |
| ---------------- | -- | -- | -- | -- | -- | -- | -- |
| memory       | O(1)   | limited by memory | Local, Fast                | | Yes| | for testing only, no persistent storage |
| leveldb      | O(logN)| unlimited | Local, Very Fast               | | Yes| | Default, fairly scalable |
| leveldb2     | O(logN)| unlimited | Local, Very Fast               | | Yes| | Similar to leveldb, part of the lookup key is 128bit MD5 instead of the long full file path |
| leveldb3     | O(logN)| unlimited | Local, Very Fast               | | Yes| Yes| Similar to leveldb2, separate leveldb instance for each bucket |
| RocksDB      | O(logN)| unlimited | Local, Very Fast               | | Native| | Default, fairly scalable. Need to manually build. |
| Sqlite       | O(logN)| unlimited | Local, Very Fast               |Atomic| Yes | Yes | Default, fairly scalable, Stream backup. Need to manually build. |
| Mongodb      | O(logN)| unlimited | Local or Distributed, Fast     | | Yes| | Easy to manage |
| Arangodb     | O(logN)| unlimited | Local or Distributed, Fast     | | Native| Yes | Easy to manage; Scalable |
| YDB          | O(logN)| unlimited | Local or Distributed, Fast     |Atomic| Native| Yes | Easy to manage; True elastic Scalability; High Availability. Need to manually build. |
| [Redis2](https://github.com/seaweedfs/seaweedfs/wiki/Filer-Redis-Setup)| O(1)   | limited   | Local or Distributed, Fastest  ||Native| | one directory's children are stored in one key~value entry |
| [Redis3](https://github.com/seaweedfs/seaweedfs/wiki/Filer-Redis-Setup)| O(1)   | unlimited   | Local or Distributed, Fastest  ||Native| | one directory's children are spread into multiple key~value entries |
| Cassandra    | O(logN)| unlimited | Local or Distributed, Very Fast||Native| |                |
| MySql        | O(logN)| unlimited | Local or Distributed, Fast     |Atomic| Yes| | Easy to manage |
| MySql2       | O(logN)| unlimited | Local or Distributed, Fast    |Atomic| Yes| Yes| Easy to manage |
| Postgres     | O(logN)| unlimited | Local or Distributed, Fast     |Atomic| Yes| | Easy to manage |
| Postgres2    | O(logN)| unlimited | Local or Distributed, Fast    |Atomic| Yes| Yes| Easy to manage |
| MemSql       | O(logN)| unlimited | Distributed, Fast     |Atomic| Yes| Yes| Scalable |
| TiDB         | O(logN)| unlimited | Distributed, Fast     |Atomic| Yes| Yes| Scalable |
| CockroachDB  | O(logN)| unlimited | Distributed, Fast     |Atomic| Yes| Yes| Scalable |
| YugabyteDB   | O(logN)| unlimited | Distributed, Fast     |Atomic| Yes| Yes| Scalable |
| Etcd         | O(logN)| unlimited | Distributed, 10,000 writes/sec     || Yes| | No SPOF. High Availability. Limited Capacity.|
| ElasticSearch| O(logN)| unlimited | Distributed, Fast     || Yes| | Scalable, Searchable. Need to manually build. |
| HBase        | O(logN)| unlimited | Distributed, Fast     | | Native| | Scalable |
| TiKV         | O(logN)| unlimited | Distributed, Fast     |Atomic|Yes| Yes| Scalable. High Availability. Need to manually build. |
| Tarantool    | O(logN)| unlimited | Local or Distributed, Fast ||Yes|| Scalable. High Availability. Need to manually build. |

#### Switching between different Stores
It is easy to switch between different filer stores.  
This is useful if you started with embedded DB and want to move to distributed one or in reverse.

For example:
```sh

# make sure you don't create or modify files in filer before this to maintain consistency of metadata
# save current filer meta data to local disk

$ weed shell
> fs.cd /
> fs.meta.save
...
total 65 directories, 292 files
meta data for http://localhost:8888/ is saved to localhost-8888-20190417-005421.meta
> exit

# you can turn off old filer if you have metadata saved to file
# now switch to a new filer, and load the previously saved metadata
$ weed shell
> fs.meta.load localhost-8888-20190417-005421.meta
...
total 65 directories, 292 files
localhost-8888-20190417-005421.meta is loaded to http://localhost:8888/

# optionally, you can use concurrency to speed up the meta load process
# -concurrency=N specifies the number of parallel meta load operations to filer
# caution: this may not work correctly with some databases like Redis

# $ weed shell
# > fs.meta.load -concurrency=1 localhost-8888-20190417-005421.meta
```

### Extending Storage Options

For any new storage option, please implement the FilerStore interface. It should be fairly straight forward to implement. Welcome to contribute back.
