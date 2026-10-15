---
id: SeaweedFS-Java-Client
title: "SeaweedFS Java Client"
sidebar_label: "SeaweedFS Java Client"
---

There are a few external Java libraries available. But actually SeaweedFS already supports Hadoop compatible file system. There are Java code already working with SeaweedFS.

Here is an SeaweedFS Java API implementation refactored out of the existing code.

https://github.com/seaweedfs/seaweedfs/tree/master/other/java/examples/src/main/java/com/seaweedfs/examples

# Build Java Client Jar

```
$cd $GOPATH/src/github.com/seaweedfs/seaweedfs/other/java/client
$ mvn install
```

Gradle
```gradle
implementation 'com.seaweedfs:seaweedfs-client:4.38'
```

Maven
```xml
<dependency>
  <groupId>com.seaweedfs</groupId>
  <artifactId>seaweedfs-client</artifactId>
  <version>4.38</version>
</dependency>
```
Or you can download the latest version from MavenCentral

https://central.sonatype.com/artifact/com.seaweedfs/seaweedfs-client

## Features

Implemented APIs for file system storage. The blob storage APIs is not included.

* **Efficient Read Write Path** read and write directly to the volume servers, and only use filer servers for meta data. If you use http to read or write directly via filer, the data still needs to go through filer, which is less efficient.
* **Monitor Filesystem Events** You can watch all meta data changes recursively under any folder. Common `inotify` only support watch for events under one folder, and not recursively. 
* **Read Ahead** When reading large files and processing the current chunk, the next chunk will be pre-fetched.

## Note

When creating a `FilerClient` object, the port `18888` in the example is the default gRPC port.
When starting filer, `weed filer -port=8888`, the port 8888 is default http port.
 
```
  FilerClient filerClient = new FilerClient("localhost", 18888);
```

## Read File

```
  FilerClient filerClient = new FilerClient("localhost", 18888);
  SeaweedInputStream seaweedInputStream = new SeaweedInputStream(filerClient, "/test.zip");
  // next, you can use seaweedInputStream as a normal InputStream
```

## Write File

```
  FilerClient filerClient = new FilerClient("localhost", 18888);
  SeaweedOutputStream seaweedOutputStream = new SeaweedOutputStream(filerClient, "/test/"+filename);
  // next, you can use seaweedOutputStream as a normal OutputStream
```

## Write File with Replication

You can specify replication level when writing files. SeaweedFS uses a replication string format: a 3-digit string representing (data center)(rack)(volume server) copies.

```
  FilerClient filerClient = new FilerClient("localhost", 18888);
  // Create output stream with replication (e.g., "001" = 1 copy, "002" = 2 copies, "011" = 1 data center + 1 rack copy, etc.)
  SeaweedOutputStream seaweedOutputStream = new SeaweedOutputStream(filerClient, "/test/"+filename, "002");
  // next, you can use seaweedOutputStream as a normal OutputStream
```

Or set replication after creation:

```
  FilerClient filerClient = new FilerClient("localhost", 18888);
  SeaweedOutputStream seaweedOutputStream = new SeaweedOutputStream(filerClient, "/test/"+filename);
  seaweedOutputStream.setReplication("001"); // Set 2 copies replication
  // next, you can use seaweedOutputStream as a normal OutputStream
```

Common replication values:
- `""` (empty string): Use SeaweedFS filer's default replication
- `"000"`: No replication (1 copy)
- `"001"`: 1 additional copy (2 total)
- `"002"`: 2 additional copies (3 total) 
- `"011"`: 1 data center + 1 rack copy (3 total)
- `"020"`: 2 rack copies (3 total)

## Watch file changes

This API streams meta data changes. 

The following is one implementation. It just watch the folder "/buckets" and all the meta data changes under the folder and all sub folders recursively. A bit more code, but should be powerful and simple to use.

```
        FilerClient filerClient = new FilerClient("localhost", 18888);

        long sinceNs = (System.currentTimeMillis() - 3600 * 1000) * 1000000L;

        Iterator<FilerProto.SubscribeMetadataResponse> watch = filerClient.watch(
                "/buckets",
                "exampleClientName",
                sinceNs
        );

        System.out.println("Connected to filer, subscribing from " + new Date());

        while (watch.hasNext()) {
            FilerProto.SubscribeMetadataResponse event = watch.next();
            FilerProto.EventNotification notification = event.getEventNotification();
            if (!event.getDirectory().equals(notification.getNewParentPath())) {
                // move an entry to a new directory, possibly with a new name
                if (notification.hasOldEntry() && notification.hasNewEntry()) {
                    System.out.println("moved " + event.getDirectory() + "/" + notification.getOldEntry().getName() + " to " + notification.getNewParentPath() + "/" + notification.getNewEntry().getName());
                } else {
                    System.out.println("this should not happen.");
                }
            } else if (notification.hasNewEntry() && !notification.hasOldEntry()) {
                System.out.println("created entry " + event.getDirectory() + "/" + notification.getNewEntry().getName());
            } else if (!notification.hasNewEntry() && notification.hasOldEntry()) {
                System.out.println("deleted entry " + event.getDirectory() + "/" + notification.getOldEntry().getName());
            } else if (notification.hasNewEntry() && notification.hasOldEntry()) {
                System.out.println("updated entry " + event.getDirectory() + "/" + notification.getNewEntry().getName());
            }
        }
```

## Standard file manipulation

You can also use this API for standard file manipulation: directory listing, file touch, folder creation, file deletion, and recursive folder deletion.

```
  FilerClient filerClient = new FilerClient("localhost", 18888);

  List<FilerProto.Entry> entries = filerClient.listEntries("/");

  for (FilerProto.Entry entry : entries) {
      System.out.println(entry.toString());
  }

  filerClient.mkdirs("/new_folder", 0755);
  filerClient.touch("/new_folder/new_empty_file", 0755);
  filerClient.touch("/new_folder/new_empty_file2", 0755);
  filerClient.rm("/new_folder/new_empty_file", false, true);
  filerClient.rm("/new_folder", true, true);

```

## Advanced Usage
Sometimes you may need to go deeper. For example, change modification time `mtime`.

```
  // load existing entry
  FilerProto.Entry entry = filerClient.lookupEntry("/some/dir","entryName");

  // change the attribute
  FilerProto.Entry.Builder entryBuilder = FilerProto.Entry.newBuilder(entry);
  FilerProto.FuseAttributes.Builder attrBuilder = FilerProto.FuseAttributes.newBuilder(entry.getAttributes());
  attrBuilder.setMtime(...)

  // save the new entry
  entryBuilder.setAttributes(attrBuilder);
  filerClient.updateEntry("/some/dir", entryBuilder.build());
```
