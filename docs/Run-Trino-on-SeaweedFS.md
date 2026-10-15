---
id: Run-Trino-on-SeaweedFS
title: "Run Trino on SeaweedFS"
sidebar_label: "Run Trino on SeaweedFS"
---

# Run Trino on SeaweedFS

Trino (the maintained successor to Presto) queries data stored on
SeaweedFS through its Hive connector. The mechanism changed in current Trino: the `hive-hadoop2`
connector was renamed to `hive`, and the Hadoop FileSystem path is now opt-in
through `fs.hadoop.enabled`.

Two storage paths work, both verified with Trino 475, Eclipse Temurin JDK 23,
and `seaweedfs-hadoop3-client-4.38.jar`:

- **A. HCFS** - the Hive connector talks to the filer directly through the
  `seaweedfs-hadoop3-client` jar (`seaweedfs://` URIs).
- **B. S3 gateway** - the Hive connector talks to SeaweedFS's S3 gateway with
  Trino's built-in S3 filesystem (`s3://` URIs). Simpler: no extra jar, no
  `core-site.xml`.

JDK note: Trino 475 is the last release that runs on JDK 23. Trino 476+ needs
JDK 24 and 479+ needs JDK 25. Use the JDK your Trino version requires; the config
below is otherwise the same.

## Metastore

The Hive connector needs a metastore. This guide uses Trino's built-in file
metastore (`hive.metastore=file`), which stores table metadata as files beside
the data, so there is no separate service to run. For production, run a
standalone Hive Metastore and set `hive.metastore=thrift` instead.

## Trino base config

`etc/node.properties`:
```
node.environment=test
node.id=trino-1
node.data-dir=/opt/trino/data
```

`etc/config.properties` (single node coordinator, 8080 is the Trino port):
```
coordinator=true
node-scheduler.include-coordinator=true
http-server.http.port=8080
discovery.uri=http://localhost:8080
```

`etc/jvm.config` (the last two flags are required on JDK 23/24):
```
-server
-Xmx3G
-XX:InitialRAMPercentage=60
-XX:MaxRAMPercentage=60
-XX:+ExitOnOutOfMemoryError
-XX:+HeapDumpOnOutOfMemoryError
-XX:-OmitStackTraceInFastThrow
-Djdk.attach.allowAttachSelf=true
-Dfile.encoding=UTF-8
--sun-misc-unsafe-memory-access=allow
--enable-native-access=ALL-UNNAMED
```

## A. HCFS with seaweedfs-hadoop3-client

1. Put the client jar on the Hive connector classpath:
```
cp seaweedfs-hadoop3-client-4.38.jar /opt/trino/plugin/hive/hdfs/
```

2. `etc/catalog/core-site.xml`:
```
<configuration>
    <property>
        <name>fs.seaweedfs.impl</name>
        <value>seaweed.hdfs.SeaweedFileSystem</value>
    </property>
    <property>
        <name>fs.AbstractFileSystem.seaweedfs.impl</name>
        <value>seaweed.hdfs.SeaweedAbstractFileSystem</value>
    </property>
    <property>
        <name>fs.seaweed.buffer.size</name>
        <value>4194304</value>
    </property>
</configuration>
```

3. `etc/catalog/seaweedfs.properties` (8888 is the filer port):
```
connector.name=hive
hive.metastore=file
hive.metastore.catalog.dir=seaweedfs://localhost:8888/trino/warehouse
fs.hadoop.enabled=true
hive.config.resources=/opt/trino/etc/catalog/core-site.xml
```

`fs.hadoop.enabled=true` is required: current Trino uses native object-storage
filesystems by default and only loads a Hadoop FileSystem implementation
(SeaweedFS's) when this is set. The file metastore creates
`seaweedfs://localhost:8888/trino/warehouse` on demand, so no directory needs
to be precreated.

## B. S3 gateway with native S3

1. Run SeaweedFS with the S3 gateway and one identity with credentials:
```
weed server -dir=/data -filer -s3 -s3.config=s3config.json
```
`s3config.json`:
```
{
  "identities": [
    {
      "name": "trino",
      "credentials": [
        { "accessKey": "trinokey", "secretKey": "trinosecret" }
      ],
      "actions": ["Admin", "Read", "Write", "List", "Tagging"]
    }
  ]
}
```
Create a bucket for the warehouse (8333 is the S3 gateway port):
```
AWS_ACCESS_KEY_ID=trinokey AWS_SECRET_ACCESS_KEY=trinosecret \
  aws --endpoint-url http://localhost:8333 s3 mb s3://warehouse
```

2. `etc/catalog/seaweedfs.properties`:
```
connector.name=hive
hive.metastore=file
hive.metastore.catalog.dir=s3://warehouse/
fs.native-s3.enabled=true
s3.endpoint=http://localhost:8333
s3.region=us-east-1
s3.path-style-access=true
s3.aws-access-key=trinokey
s3.aws-secret-key=trinosecret
```
No jar and no `core-site.xml` are needed for this path.

## Run a query

Start Trino and connect with the Trino CLI:
```
bin/launcher start
trino --server http://localhost:8080 --catalog seaweedfs
```
```
trino> CREATE SCHEMA seaweedfs.demo;
CREATE SCHEMA
trino> CREATE TABLE seaweedfs.demo.boshen (name varchar);
CREATE TABLE
trino> INSERT INTO seaweedfs.demo.boshen VALUES ('alice'), ('bob'), ('carol');
INSERT: 3 rows
trino> SELECT * FROM seaweedfs.demo.boshen ORDER BY name;
 name
-------
 alice
 bob
 carol
(3 rows)
```

## Confirm the data is on SeaweedFS

The table is stored as ORC under the metastore catalog directory.

HCFS - list the table directory on the filer:
```
curl -H "Accept: application/json" \
  http://localhost:8888/trino/warehouse/demo/boshen/
```

S3 - list the bucket:
```
AWS_ACCESS_KEY_ID=trinokey AWS_SECRET_ACCESS_KEY=trinosecret \
  aws --endpoint-url http://localhost:8333 s3 ls s3://warehouse/demo/boshen/ --recursive
```

Either way you will see the ORC data file, named like
`20260708_080447_00007_4q5f3_&lt;uuid&gt;`, next to the `.trinoSchema` metadata the
file metastore wrote. The data file begins and ends with the `ORC` magic bytes.
