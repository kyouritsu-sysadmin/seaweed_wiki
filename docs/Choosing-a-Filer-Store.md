---
id: Choosing-a-Filer-Store
title: "Choosing a Filer Store"
sidebar_label: "Choosing a Filer Store"
---

Here is a list of common questions about choosing a filer store.

## Cassandra vs ScyllaDB vs others

Cassandra and ScyllaDB are distributed, having native support for TTL.

The data structure is the same for Cassandra and ScyllaDB. If a directory has too many updates, there would be corresponding number of tombstones if the SSTable compaction did not kick in. Too many tombstones would slow down the queries.

This happened in one user where “/tmp” folder is used as a staging folder for all uploaded files, the read operations becomes slower and slower for this folder. Changing to redis with [Path-Specific-Filer-Store](./Path-Specific-Filer-Store.md) for this folder resolved this performance issue.

