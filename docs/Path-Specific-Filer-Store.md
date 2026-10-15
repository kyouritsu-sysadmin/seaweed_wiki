---
id: Path-Specific-Filer-Store
title: "Path Specific Filer Store"
sidebar_label: "Path Specific Filer Store"
---

If your meta data size keeps growing and one filer store can not handle, you can still scale your system with path-specific filer stores.

# Why this is needed?

In most cases, you would just need to setup one filer store.

However, there are some examples that one filer store is not enough:

* A portion of the data is critical. It needs strong consistency and is ok with high latency.
* With too many updates in a directory, the Cassandra with LSM tree becomes slower with too many tombstones. You may want to use Redis for that directory.
* One filer store can not handle the total amount of files. We can add more file stores for big directories to ensure linear scalability.
* One directory operations are hot. Having a separate store can physically isolate from and avoid impact to other directories.

# How to add path-specific filer stores?

Run `weed scaffold -config=filer`, there is an example:
```
##########################
##########################
# To add path-specific filer store:
#
# 1. Add a name following the store type separated by a dot ".". E.g., cassandra.tmp
# 2. Add a location configuraiton. E.g., location = "/tmp/"
# 3. Copy and customize all other configurations.
#     Make sure they are not the same if using the same store type!
# 4. Set enabled to true
#
# The following is just using redis as an example
##########################
[redis2.tmp]
enabled = false
location = "/tmp/"
address  = "localhost:6379"
password = ""
database = 0
```

You can add multiple path-specific filer stores. 

# How does it work?

When any request comes in, the directory is matched to all locations with customized filer stores. The matching is efficient and there are no limits in terms of the number of path-specific filer stores. The matched filer store is used to handle the metadata reads and writes.

This only works for new data or new updates. Existing data for old directories will become `lost` or invisible. So only apply this to new directories.

# Data Storage

The directory path stored in the path-specific filer store has the `location` prefix trimmed and persists to the store. For example, if `location = "/my/home/"`, the file `/my/home/tmp/file.txt` will only store as "/tmp/file.txt". When reading back, the prefix will be transparently added back.

This trimming saves some storage, but that is not the purpose. This means the path-specific filer store is portable. It can later change `location` to another directory, or even another filer.

# What still works?

This can not be applied to existing directories. Besides this requirement, all other meta data operations are almost transparent to this configuration change. For example,

* The renaming works across filer stores.
* The metadata exports and imports still works.
* The cross-cluster replication still works.