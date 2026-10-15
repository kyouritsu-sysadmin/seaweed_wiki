---
id: Data-Structure-for-Large-Files
title: "Data Structure for Large Files"
sidebar_label: "Data Structure for Large Files"
---

# Small files vs Large files

What are considered small files and what are large files? It does not have a clear answer as CPU/memory/network/disk/... are all constantly improving over time.

# Small Files

In SeaweedFS, the small files are defined as any file that can be saved in one chunk of data. The chunk size limit is not a fixed number, but flexible according to the hardware or the requirements. It can be anywhere ranging from 1MB ~ 10MB or a bit higher. 

We will assume it is 8MB for following discussion.

# Medium Files

For larger files, usually the files are split into chunks. Each chunk info is referenced by a SeaweedFS file id. With a few additional data, such as offset, size, encryption, compression, the chunk info will be about 40 bytes uncompressed.

A reasonable key value store can store about 1000 ~ 10000 pieces of chunk info, which is about 40KB ~ 400KB.

Since each chunk is about 8MB, these 1000~10000 pieces of chunk info can address files up to 8GB ~ 80GB in size efficiently.

# Super Large File

For even larger files, the meta data, which is the list of chunk info, can grow big. One 800GB file can have a 4MB meta data. This would not scale.

SeaweedFS adds a manifest chunk to hold 1000 pieces of chunk info. This manifest chunk is stored together with the raw data on volume servers, which greatly reduces the storage load on key value stores and also reduces the access time.

For example, one super large file with 1000 manifest chunks is still 400KB in meta data in the key value store, but it can address a file of 8MB * 1000 * 1000 = 8TB in size.

The 8TB for one file is not a real limit, but only used for this discussion. However, if you have the need for files more than 8TB, please prepare some consulting fee and we will help you. :) Or you probably should already split the large files into smaller files.

## Note

This manifest chunk can also be easily implemented recursively, which can leads to even larger file size limit. But there are a few reasons of not going there:

* The recursion leads to multi-level of indirection, and make the access time unpredictable. SeaweedFS tries to minimize this as much as possible.
* The size limit is already very high. It is way beyond what most common use cases would ever need. We will add the recursion later when really necessary.
