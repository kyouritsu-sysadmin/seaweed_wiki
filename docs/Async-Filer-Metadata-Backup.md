---
id: Async-Filer-Metadata-Backup
title: "Async Filer Metadata Backup"
sidebar_label: "Async Filer Metadata Backup"
---

It is desirable to have a copy of the filer metadata. However, it is not always easy to setup replications for filer metadata store:
* The store does support stream replication.
* The store is embedded leveldb, RocksDB, etc.
* It is just complicated.

# Async filer metadata backup to a different store

We can continuously backup filer metadata to a different store, without running a filer instance.
```
         Metadata Changes
 Filer --------------------> `weed filer.meta.backup` ---> A backup store(LevelDB/RocksDB/
                                                                        Mysql/Postgres/
                                                                        Redis/Cassanra/...)
```
Just need to configure the backup store the same way as `filer.toml`.

`weed filer.meta.backup` can be stopped and resumed. The metadata backup progress is tracked in the backup store itself. So you can pause/resume any time.

It is worth noting that the backup store can be different from the source filer store. E.g., you can use a cheaper on disk LevelDB as a remote store to backup Redis.

```
         Metadata Changes
 Filer --------------------> `weed filer.meta.backup` ---> A backup store(LevelDB)
on Redis

```

You can even do this:

```
         Metadata Changes                                                           sqlite streaming  
 Filer --------------------> `weed filer.meta.backup` ---> A backup store(Sqlite)  ------------------> S3
on Redis

```
