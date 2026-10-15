---
id: Migrate-to-Filer-Store
title: "Migrate to Filer Store"
sidebar_label: "Migrate to Filer Store"
---

If there are already a lot of files, how to move them to the SeaweedFS the most efficient way?

### 1. Setup Filer
1. create a filer.toml file, see the output of "weed scaffold -config=filer"
1. choose and setup a filer data store. It is OK to just pick one and use it. You can always switch later.
3. start the filer
> Example: `weed filer -master=localhost:9333`

### 2. Mount
* If you want to copy files via OS-provided copy command, start the "weed mount"
> Example: `weed mount -filer=localhost:8888 -dir=/some/dir`

### 3. Copy Files
The easiest way is just to use the OS-provided copy command from the command line. However, usually it is single-threaded.

The most efficient way is to use "weed filer.copy". It is multi-threaded and bypasses the FUSE layer.
> Example: `weed filer.copy file_or_dir1 [file_or_dir2 file_or_dir3] http://localhost:8888/path/to/a/folder/`