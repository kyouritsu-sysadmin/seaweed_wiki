---
id: Filer-Metadata-Events
title: "Filer Metadata Events"
sidebar_label: "Filer Metadata Events"
---

On filer, there is a `/topics/.system/log` folder, it stores all filer metadata change events.

## Metadata Event Format
The events are stored in files organized by timestamp, `yyyy-MM-dd/hh-mm.segment`.

The events are encoded by protobuf, defined in https://github.com/seaweedfs/seaweedfs/blob/master/weed/pb/filer.proto . The related sections are:
```
service SeaweedFiler {
    rpc SubscribeMetadata (SubscribeMetadataRequest) returns (stream SubscribeMetadataResponse) {
    }
}

message SubscribeMetadataRequest {
    string client_name = 1;
    string path_prefix = 2;
    int64 since_ns = 3;
}
message SubscribeMetadataResponse {
    string directory = 1;
    EventNotification event_notification = 2;
    int64 ts_ns = 3;
}
message EventNotification {
    Entry old_entry = 1;
    Entry new_entry = 2;
    bool delete_chunks = 3;
    string new_parent_path = 4;
}
message LogEntry {
    int64 ts_ns = 1;
    int32 partition_key_hash = 2;
    bytes data = 3;
}

```

The ondisk file is a repeated bytes of the following format:
  1. 4 bytes of `LogEntry` size
  2. serialized `LogEntry`

The `LogEntry.data` stores serialized `SubscribeMetadataResponse`

## Read Metadata Events
The events can be read by any program as files. One example is here: https://github.com/seaweedfs/seaweedfs/blob/master/unmaintained/see_log_entry/see_log_entry.go

## Subscribe to Metadata

The protobuf definition also defined a RPC call, where you can subscribe to all metadata changes asynchronously.
This is how the `weed mount` can asynchronously get metadata updates from the filer, and avoid cross-wire metadata read operations to dramatically cut down operation latency.

```
service SeaweedFiler {
    rpc SubscribeMetadata (SubscribeMetadataRequest) returns (stream SubscribeMetadataResponse) {
    }
}

message SubscribeMetadataRequest {
    string client_name = 1;
    string path_prefix = 2;
    int64 since_ns = 3;
}
message SubscribeMetadataResponse {
    string directory = 1;
    EventNotification event_notification = 2;
    int64 ts_ns = 3;
}
```

This is similar to `inotify` in normal file system, but actually much more powerful. Usually `inotify` can only monitor one directory and its direct children, but SeaweedFS metadata subscription can monitor one directory and all its sub-directories and files.

This API also allows you to read from any point of time and replay all metadata events.

This API could be useful to build powerful event driven data processing pipelines. Please let me know if you have some great ideas or accomplishment!

### What kind of events it contains?

The `SubscribeMetadataResponse` contains `EventNotification`, which contains `old_entry` and `new_entry`. The following events can be derived:

* Create Event: `new_entry` is not null, and `old_entry` is null.
* Delete Event: `old_entry` is not null, and `new_entry` is null.
* Update Event: `old_entry` is not null, and `new_entry` is not null.
* Rename Event: similar to Update Event, but also need `SubscribeMetadataResponse.directory` and `EventNotification.new_parent_path`.

## Purging Metadata Logs
It is ok to delete the metadata logs. However, many features rely on these metadata events, such as:
* Async filer replication
* Sync metadata with `weed mount`
* Async filer metadata backup
* Filer backup

So better not to mess with the metadata logs, which should not take too much space. Just leave them there.
