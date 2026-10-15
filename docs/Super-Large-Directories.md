---
id: Super-Large-Directories
title: "Super Large Directories"
sidebar_label: "Super Large Directories"
---

# Why need a super large directory?

This is actually a common case. For example, entity ids, such as user name, id, IP address, URLs, or UUID can be used as sub directory names. The number of entity ids could be very large. And under the sub directory, more unstructured data can be colocated together, such as user avatar, uploaded files, access logs, URL text, images, audio, video, etc.

You can manually translate the entity id to file id with a separate lookup, and use file id to access data. This is exactly what SeaweedFS does internally. This manual approach not only re-invents the wheel, but also would give up all the convenience from a file system, such as deeper directories. 

Assuming you are bootstrapping a startup with potentially millions of users, but currently only a few test accounts. You need to spend your time to really meet user requirements. You would not spend your time to design data structures and schemas for different cases to store customer data. Instead of optimizing early on, you can start with a folder for each account, and continue. SeaweedFS can make this simple approach future-proof.

# Why super large directory is challenging?

If one super large directory has way too many files or sub folders, the file listing itself can be a challenge.

For example, for Cassandra filer store, each entry has this schema:
```
  CREATE TABLE filemeta (
     directory varchar,
     name varchar,
     meta blob,
     PRIMARY KEY (directory, name)
  ) WITH CLUSTERING ORDER BY (name ASC);
```
The directory is the partitioning key. So the entries with the same directory is partitioned to the same data node. This is fine for most cases. However, if there are billions of direct child entries under one directory, the data node would not perform well.

We need a way to spread the data to all data nodes, without sacrificing too much. In a sense, we want SeaweedFS to be as efficient and scalable as a distributed key value store, while still using the familiar file system operations.

# How it works?

This is currently implemented in Cassandra and Redis. Super large directories sacrifices the directory listing functionality, to keep the directory scalable. As the directory entry names usually are user ids or UUIDs, the list are already stored in some other storage. Listing all child entries can be achieved by other approaches.

Only direct children of the super large directory can not be listed. For the deeper level directories, listing still works. For example, if `/home/users/` is configured as a super large directory, listing `/home/users/` would not work, but listing `/home/users/user1` and `/home/users/user1/books` still work.

```
  /home/users/user1/books/book1.txt
  /home/users/user1/books/book2.txt
```

## Cassandra Implementation
In Cassandra, for normal directories, data has primary key of `&lt;directory hash, name&gt;`, where the `directory hash` is the partitioning key. This data layout enables directory listing via range query with the directory hash as the prefix.

However, this means all the child entries are physically located in one Cassandra node. When the directory has billions of child entries, that Cassandra node will be overloaded.

So for large directories configured in Cassandra, SeaweedFS use the `&lt;full_path&gt;` as the partitioning key. So all child entries in that directory are evenly spread out to all Cassandra data nodes.

## Redis Implementation
In Redis, for normal directories, the list of child entries are stored in one key~value entry as `&lt;path, sorted_set_of_child_entry_names&gt;`. 

However, when the number of child entries becomes larger, it would be slower and slower to read and write to this key~value entry.

So for large directories configured in Redis, SeaweedFS skips this operation, so the list of child entries are not stored.

## The Downside

The consequences are:

* The directory listing for this folder is not supported.
* The filer meta data import and export for this folder is not supported. You can still do it for specific child folders though.
* Once this is configured, it can not be changed back easily. You will need to write code to iterate all sub entries for that.

# How to configure it?

In `filer.toml` for Cassandra/Redis, there is an option `superLargeDirectories`. For example, if you will have a lot of user data under `/home/users`

```
[cassandra2]
...
superLargeDirectories = [
  "/home/users",
]

```

This is assuming the `/home/user` is an empty folder. 

As you can see, it supports multiple super large directories. However, never change or remove the entries in `superLargeDirectories` or the data will be lost!

Note that with a path specific filer store, the `superLargeDirectories` path is relative to the path specific store root.  For example, if you wanted to make an entire S3 bucket have its own filer store and be a super large directory, you need to configure it like this:
```
 location = "/buckets/mybucket"
 superLargeDirectories = ["/"]
```
