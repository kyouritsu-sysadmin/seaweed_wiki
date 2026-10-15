---
id: Filer-Change-Data-Capture
title: "Filer Change Data Capture"
sidebar_label: "Filer Change Data Capture"
---

Is it too much a dream to have something similar to [inotify](https://man7.org/linux/man-pages/man7/inotify.7.html) in a distributed file system? Not really!

Actually SeaweedFS can give you more!

# Experience it first

You can continuously watch the SeaweedFS meta data changes. Let's also filter with `jq` and see only the new files created using this command:
```bash
weed filer.meta.tail -timeAgo=3h | jq .eventNotification.newEntry
```

which will return:

```json
{
  "name": "abc.png",
  "chunks": [
    {
      "size": "941248",
      "mtime": "1611297248363702000",
      "eTag": "2848d811982973ffda34cf8c8599e3f6",
      "fid": {
        "volumeId": 23,
        "fileKey": "155320",
        "cookie": 2256694723
      }
    }
  ],
  "attributes": {
    "fileSize": "941248",
    "mtime": "1611297248",
    "fileMode": 432,
    "uid": 502,
    "gid": 20,
    "crtime": "1611297248",
    "mime": "image/png",
    "replication": "000",
    "md5": "KEjYEZgpc//aNM+MhZnj9g=="
  }
}
\\ the rest has been truncated for brevity
```

See the help:

```console
$ weed filer.meta.tail -h
Example: weed filer.meta.tail [-filer=localhost:8888] [-target=/]
Default Usage:
  -es string
    	comma-separated elastic servers http://<host:port>
  -es.index string
    	ES index name (default "seaweedfs")
  -filer string
    	filer hostname:port (default "localhost:8888")
  -pathPrefix string
    	path to a folder or file, or common prefix for the folders or files on filer (default "/")
  -pattern string
    	full path or just filename pattern, ex: "/home/?opher", "*.pdf", see https://golang.org/pkg/path/filepath/#Match
  -timeAgo duration
    	start time before now. "300ms", "1.5h" or "2h45m". Valid time units are "ns", "us" (or "µs"), "ms", "s", "m", "h"
Description:
  See recent changes on a filer.

```

If configured Elastic Search server names, the meta data will be sent to Elastic Search
```console
$ weed filer.meta.tail -es=http://localhost:9200
```

# How it works?

The `weed filer.meta.tail` code is nothing fancy. It is calls a gRPC stream API to subscribe to all meta data changes and simply print out the meta data.

The gRPC API has several important use cases within SeaweedFS:
* Replicate data to other SeaweedFS clusters in `weed filer.sync`.
* Replicate meta data to other filers if not sharing the same filer meta store.
* Replicate meta data to `weed mount` asynchronously.

The gRPC API is also open to public and can support many other languages. 

# Example

Here is an example [ExampleWatchFileChanges.java](https://github.com/seaweedfs/seaweedfs/blob/master/other/java/examples/src/main/java/com/seaweedfs/examples/ExampleWatchFileChanges.java), in Java:

https://github.com/seaweedfs/seaweedfs/tree/master/other/java/examples/src/main/java/com/seaweedfs/examples

To subscribe the meta data changes:
| Parameter   | Meaning | 
| -- | -- |
| prefix | A path prefix. Watch any directory or file with this path prefix |
| clientName | A client name, just for logging |
| sinceNs |  A timestamp in nano seconds. Watch changes from this timestamp. You can rewind the time. |

Basically there are four types of events to handle:
| Type   | Directory | NewEntry | OldEntry | NewParentPath |
| -------| -------| -------| -------| -------|
| Create | exists | exists | null | equal to Directory |
| Update | exists | exists | exists | equal to Directory |
| Delete | exists | null | exists | equal to Directory |
| Rename | exists | exists | exists | not equal to Directory |

# Other Languages

This is based on Filer gRPC API. You should be able to easily implement it in your own language.

https://github.com/seaweedfs/seaweedfs/blob/master/weed/pb/filer.proto#L52

A Golang example:
https://github.com/tuxmart/seawolf

# Possible Use Cases

This is basically stream processing or event processing for files. The possible use cases are all up to your imagination.

* Detect new image or video files. Add versions with different resolutions.
* A **distributed configuration distribution**: stores configuration files under a folder. Detect the configuration changes and reload. 
* A **job queue**: upload files to a folder, and processing new files as soon as possible, and delete the processed files.
* Do-it-yourself **Data Replication or Backup**.
* **Batch processing**: streaming data is cool, but sometimes batching is more efficient. To combine streaming and batching, you can put one batch of new data as a file and trigger the batch processing on that file.
* Folder size statistics and monitoring.
