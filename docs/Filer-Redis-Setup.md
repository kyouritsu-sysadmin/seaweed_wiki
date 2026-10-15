---
id: Filer-Redis-Setup
title: "Filer Redis Setup"
sidebar_label: "Filer Redis Setup"
---

Currently there are two Redis implementations, i.g., `redis2` and `redis3`. What is the difference?

# Storing directory list

Since Redis is a key-value store, the directory list could not be efficiently iterated by scanning the keys. So the directory list is stored as a [sorted set](https://redis.io/topics/data-types#sorted-sets) in `redis2`:
```
 <directory_path>: <sorted set of names>
```

The sorted set in Redis is fairly efficient. Storing 100K ~ 1 million entries is still fairly fast. In most of the cases, it should work very well with large directories.

# Super Large Directories

In some cases, the directory may have 10s of millions or billions of files or sub directories. The directory list would be too big to fit into one Redis entry in one Redis instance. For `redis2`, you can specify which folder is super large, and avoid storing this fat list of names, but giving up the capability to list a directory.

This is where `redis3` can help. The internal data structure is:

```
 <directory_path>: <skip list>
 <skip list item 1>: <sorted set of 1 million names>
 <skip list item 2>: <sorted set of 1 million names>
 ...
```
The directory list is stored as a skip list, and the child names are spread into the list items. This prevents each directory entry from being too large and slower to access. Skip list has `O(log(N))` access time. With each sorted set storing 1 million names, it should scale very well to billions of files in one directory.

Compared to `redis2`, there are extra Redis operations to maintain this list:
* Adding or deleting needs one additional lock operation.
* Updating an entry needs to takes `O(log(N))` times to access the skip list item first.

One Redis operation costs about 25 microseconds. The extra Redis operations cost about 4 Redis round trips when running with 1 million items. The cost is relatively small compared to the whole file creation/update/deletion process. 

# Note
The file read operation is still just one Redis operation, since it does not need to read the list of other directory items.