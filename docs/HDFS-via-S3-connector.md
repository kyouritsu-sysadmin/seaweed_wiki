---
id: HDFS-via-S3-connector
title: "HDFS via S3 connector"
sidebar_label: "HDFS via S3 connector"
---

Current recommended way for Hadoop to access SeaweedFS is via [SeaweedFS Hadoop Compatible File System](./Hadoop-Compatible-File-System.md), which is the most efficient way with the client directly accessing filer for metadata and accessing volume servers for file content.

However, the downside is that you need to add a SeaweedFS jar to classpath, and change some Hadoop settings.

# HDFS Access SeaweedFS via S3 connector

The S3A connector (`hadoop-aws`) points at the SeaweedFS S3 gateway. It ships with Hadoop distributions, so no SeaweedFS jar is needed.

Tested with Spark 4.0.3 (`spark-4.0.3-bin-hadoop3`, bundled Hadoop 3.4.1) on JDK 17. The `hadoop-aws` jar must match the Hadoop version bundled in Spark. For this build that is `hadoop-aws-3.4.1.jar` plus the AWS SDK v2 bundle `bundle-2.24.6.jar`, both found under `share/hadoop/tools/lib/` of a Hadoop 3.4.1 distribution.

## Configuration

Point S3A at the SeaweedFS S3 gateway (default port 8333):

```
fs.s3a.endpoint=http://localhost:8333
fs.s3a.path.style.access=true
fs.s3a.connection.ssl.enabled=false
```

Create the bucket before writing:

```
$ aws --endpoint-url http://localhost:8333 s3 mb s3://test
```

## Credentials

A SeaweedFS S3 gateway started without an identity config allows anonymous access. Use the anonymous provider:

```
fs.s3a.aws.credentials.provider=org.apache.hadoop.fs.s3a.AnonymousAWSCredentialsProvider
```

To require credentials, start the gateway with a static identity config, e.g. `s3.json`:

```
{
  "identities": [
    {
      "name": "spark",
      "credentials": [
        { "accessKey": "sparkkey", "secretKey": "sparksecret" }
      ],
      "actions": ["Admin", "Read", "Write", "List", "Tagging"]
    }
  ]
}
```
```
$ weed server -s3 -s3.config=s3.json ...
```
Then use the simple provider with those keys:

```
fs.s3a.aws.credentials.provider=org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider
fs.s3a.access.key=sparkkey
fs.s3a.secret.key=sparksecret
```

## Example

```
$ bin/spark-shell \
  --master 'local[2]' \
  --jars /path/to/hadoop-aws-3.4.1.jar,/path/to/bundle-2.24.6.jar \
  --conf spark.hadoop.fs.s3a.endpoint=http://localhost:8333 \
  --conf spark.hadoop.fs.s3a.path.style.access=true \
  --conf spark.hadoop.fs.s3a.connection.ssl.enabled=false \
  --conf spark.hadoop.fs.s3a.aws.credentials.provider=org.apache.hadoop.fs.s3a.AnonymousAWSCredentialsProvider
...
scala> val df = Seq((10,"x"),(20,"y"),(30,"z")).toDF("id","label")
scala> df.write.mode("overwrite").parquet("s3a://test/spark-s3a/data")
scala> val back = spark.read.parquet("s3a://test/spark-s3a/data")
scala> back.count()
res: Long = 3
scala> back.orderBy("id").show(false)
+---+-----+
|id |label|
+---+-----+
|10 |x    |
|20 |y    |
|30 |z    |
+---+-----+
```

The write lands in the bucket as `spark-s3a/data/_SUCCESS` plus the snappy parquet part files.

## Packaged spark job

Example `pom.xml` properties for a job compiled against Spark 4.0.3:

```
<properties>
    <maven.compiler.source>17</maven.compiler.source>
    <maven.compiler.target>17</maven.compiler.target>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    <scala.version>2.13.16</scala.version>
    <spark.version>4.0.3</spark.version>
    <hadoop.version>3.4.1</hadoop.version>
    <spark.pom.scope>compile</spark.pom.scope>
</properties>
```
And set the S3A configuration in your code:
```
SparkSession spark = SparkSession.builder()
    .master("local[*]")
    .config("spark.eventLog.enabled", "false")
    .appName("SparkDemoFromS3")
    .getOrCreate();
Configuration conf = spark.sparkContext().hadoopConfiguration();
conf.set("fs.s3a.endpoint", "http://localhost:8333");
conf.set("fs.s3a.path.style.access", "true");
conf.set("fs.s3a.connection.ssl.enabled", "false");
// anonymous access
conf.set("fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.AnonymousAWSCredentialsProvider");
// or, with a static identity:
// conf.set("fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider");
// conf.set("fs.s3a.access.key", "sparkkey");
// conf.set("fs.s3a.secret.key", "sparksecret");
Dataset<Row> df = spark.read().parquet("s3a://test/spark-s3a/data");
System.out.println(df.count());
df.write().mode("overwrite").parquet("s3a://test/testcc/t2");
```
