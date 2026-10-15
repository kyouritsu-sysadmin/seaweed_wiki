---
id: Filer-Commands-and-Operations
title: "Filer Commands and Operations"
sidebar_label: "Filer Commands and Operations"
---

Filer is similar to common file systems and people may ask for similar tools.

## Copy to Filer

`weed filer.copy` can copy one or a list of files or directories to filer.

```
// copy all go files under current directory to filer's /github/ folder.
// The directory structure is copied also.
> weed filer.copy -include *.go . http://localhost:8888/github/
...
Copy ./unmaintained/change_replication/change_replication.go => http://localhost:8888/github/./unmaintained/change_replication/change_replication.go
Copy ./unmaintained/fix_dat/fix_dat.go => http://localhost:8888/github/./unmaintained/fix_dat/fix_dat.go
Copy ./unmaintained/see_idx/see_idx.go => http://localhost:8888/github/./unmaintained/see_idx/see_idx.go
Copy ./weed/command/backup.go => http://localhost:8888/github/./weed/command/backup.go
Copy ./weed/command/benchmark.go => http://localhost:8888/github/./weed/command/benchmark.go
Copy ./weed/command/command.go => http://localhost:8888/github/./weed/command/command.go
Copy ./weed/command/compact.go => http://localhost:8888/github/./weed/command/compact.go
...
```

The above `weed copy` command is very efficient. It will contact the master server for a fileId, and submit the file content to volume servers, then just create the entry on filer. Also, the file copying will also split large files into chunks automatically.

This put very little loads on filer and the master server. Data is only transmitted between the local machine and the volume server.

## Copy files within Filer

SeaweedFS also supports copying files within the filer using the HTTP API. This is useful for creating backups, duplicates, or templates without downloading and re-uploading files.

### HTTP API Copy

```bash
# Copy a file to a new location
curl -X POST 'http://localhost:8888/path/to/destination?cp.from=/path/to/source'

# Copy with automatic name resolution
curl -X POST 'http://localhost:8888/backup/?cp.from=/important/config.json'
# Creates: /backup/config.json
```

**Features:**
- **Efficient**: Server-side copy without client data transfer
- **Independent chunks**: Creates new chunk copies (not shared references)
- **Atomic operation**: Either succeeds completely or fails with no partial state
- **Preserves metadata**: File attributes, timestamps, and permissions maintained

**Comparison of copy methods:**

| Method | Use Case | Data Transfer | Performance |
| ------ | -------- | ------------- | ----------- |
| `weed filer.copy` | Local files → Filer | Client → Volume Server | Good for initial uploads |
| `cp.from` HTTP API | File → File within Filer | Volume Server → Volume Server | Excellent for server-side copies |

For more details, see the [Filer Server API documentation](./Filer-Server-API.md#copy-files).

## Register a file on Filer

As mentioned above, the (path, fileId, fileSize) can be registered on filer with this gRPC call.

    filer_pb.SeaweedFilerClient.CreateEntry()

The code example can be found in filer_copy.go file.
