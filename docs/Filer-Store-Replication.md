---
id: Filer-Store-Replication
title: "Filer Store Replication"
sidebar_label: "Filer Store Replication"
---

# Parallel filers with embedded filer store

If one filer is not enough, you can add more filers. This seems easy with shared filer stores, such as Redis, MySql, Postgres, Cassandra, HBase, etc.

But did you notice this also works for embedded filer stores, such as LevelDB, RocksDB, SQLite, etc?

How is it possible?

# Automatic Peer Discovery

When a filer starts up, it will report itself to the master. So the master knows all the filers. It will keep each filer updated about its peers (since version 2.77).

So when a filer was added or removed from the cluster, there is no configuration change needed. This makes rolling-restart much easier, and filer instances in Kubernetes can run in ReplicaSet instead of StatefulSet.

What's more, adding a fresh new filer will automatically synchronize the metadata with other filers. Resuming a paused filer will also resume the metadata synchronization from when it was stopped. Everything will/should just work!

Note however that using multiple replicated embedded filers is only eventually consistent. So using this setup behind a load-balancer might not work as expected, although this can be solved with load balancer configuration, such as hashing connections based on the `uploadId` GET query, or temporary sticky sessions to ensure the objects requested are available.

# Metadata synchronization

Knowing all the peers, one filer will keep its own metadata updated:

1. Aggregate filer meta data changes from peers
2. Replay filer meta data changes to local filer store, if it is an embedded store.

## Aggregate metadata updates

This is tightly related to FUSE Mount, which streams filer meta data changes from one filer. When using multiple filers but without peer file metadata updates, a FUSE mount can only see the changes applied to the connected filer. 

So aggregating metadata updates from its peers is required when the filers are using either shared or dedicated filer stores.

```
  FUSE mount <----> filer1 -- filer2
                       \       /
                        \     /
                         filer3
```

# Persist metadata changes to local embedded store

If the filer is running on embedded store, the metadata updates from its peers would be saved locally.

This basically synchronize the metadata across all the filer stores, where every filer store will have a full copy of all the metadata.

This also naturally replicated the filer store to achieve high availability for metadata.

# Example Topologies

* Multiple filers with leveldb stores

```
filer1(leveldb) <-> filer2(leveldb) <-> filer3(leveldb) 

```

* Two filers are fine. There is no requirements for number of filers.

```
filer1(leveldb) <-> filer2(leveldb)
```

* Two filers with different embedded stores are also fine. Of course, you will need a different `filer.toml`.

```
filer1(leveldb) <-> filer2(rocksdb)
```

* Two filers with one shared store instance are fine.

```
filer1(mysql) <-> filer2(mysql)
```

# Topologies Not Working!

* Two filers with a shared store and an embedded store are NOT fine.

This is because the `filer2` here will not attempt to persist `filer1` metadata updates to its mysql store.
```
filer1(leveldb) <--XX NOT WORKING XX---> filer2(mysql)
```

# How is it implemented?

Each filer has a local meta data change log. When starting, each filer will subscribe to meta data changes from its peers and apply to local filer store.

Each filer store will auto generate a unique `filer.store.id`. So for shared filer stores, such as mysql/postgres/redis, there is no need to setup peers because the `filer.store.id` will be the same.

The subscription will also periodically checkpoint the subscription progress, so the subscription can resume if either filer is restarted.

It is actually OK if you need to change filer IP or port. The replication can still resume as long as the filer store has the same content.

# Limitation

Multiple filers with local leveldb filer stores can work well. However, this layout does not work well with `weed filer.sync` cross data center replication as of now. This is because currently `weed filer.sync` use `filer.store.id` to identify data that needs to be replicated. Having multiple `filer.store.id` will confuse the `weed filer.sync`.
