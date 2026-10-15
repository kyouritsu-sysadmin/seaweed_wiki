---
id: run-Spark-on-SeaweedFS
title: "run Spark on SeaweedFS"
sidebar_label: "run Spark on SeaweedFS"
---

# Installation for Spark
Follow instructions on spark doc: 
* https://spark.apache.org/docs/latest/configuration.html#inheriting-hadoop-cluster-configuration
* https://spark.apache.org/docs/latest/configuration.html#custom-hadoophive-configuration

Tested with Spark 4.0.3 (`spark-4.0.3-bin-hadoop3`, Scala 2.13, bundled Hadoop 3.4.1) on JDK 17. Spark 4.0.x requires Java 17+. The same steps work with Spark 3.5.x on JDK 17.

## installation inheriting from Hadoop cluster configuration

Inheriting from Hadoop cluster configuration should be the easiest way. 

To make these files visible to Spark, set HADOOP_CONF_DIR in $SPARK_HOME/conf/spark-env.sh to a location containing the configuration file `core-site.xml`, usually `/etc/hadoop/conf`

## installation not inheriting from Hadoop cluster configuration

Copy the seaweedfs-hadoop3-client-4.38.jar to all executor machines.

Add the following to spark/conf/spark-defaults.conf on every node running Spark
```
spark.driver.extraClassPath=/path/to/seaweedfs-hadoop3-client-4.38.jar
spark.executor.extraClassPath=/path/to/seaweedfs-hadoop3-client-4.38.jar
spark.hadoop.fs.seaweedfs.impl=seaweed.hdfs.SeaweedFileSystem
spark.hadoop.fs.AbstractFileSystem.seaweedfs.impl=seaweed.hdfs.SeaweedAbstractFileSystem
```
`fs.AbstractFileSystem.seaweedfs.impl` is required on Hadoop 3.x.

And modify the configuration at runtime:

```
./bin/spark-submit \
  --name "My app" \
  --master local[4] \
  --conf spark.eventLog.enabled=false \
  --conf spark.hadoop.fs.seaweedfs.impl=seaweed.hdfs.SeaweedFileSystem \
  --conf spark.hadoop.fs.AbstractFileSystem.seaweedfs.impl=seaweed.hdfs.SeaweedAbstractFileSystem \
  --conf spark.hadoop.fs.defaultFS=seaweedfs://localhost:8888 \
  --jars /path/to/seaweedfs-hadoop3-client-4.38.jar \
  myApp.jar
```

# Example

Put the client jar on the classpath and point Spark at the filer. Start a filer first (`weed filer`), then:

```
$ bin/spark-shell \
  --master 'local[2]' \
  --conf spark.driver.extraClassPath=/path/to/seaweedfs-hadoop3-client-4.38.jar \
  --conf spark.executor.extraClassPath=/path/to/seaweedfs-hadoop3-client-4.38.jar \
  --conf spark.hadoop.fs.seaweedfs.impl=seaweed.hdfs.SeaweedFileSystem \
  --conf spark.hadoop.fs.AbstractFileSystem.seaweedfs.impl=seaweed.hdfs.SeaweedAbstractFileSystem
...
Welcome to
      ____              __
     / __/__  ___ _____/ /__
    _\ \/ _ \/ _ `/ __/  '_/
   /___/ .__/\_,_/_/ /_/\_\   version 4.0.3
      /_/

Using Scala version 2.13.16 (OpenJDK 64-Bit Server VM, Java 17.0.19)

scala> val df = Seq((1,"alice"),(2,"bob"),(3,"carol"),(4,"dave")).toDF("id","name")
scala> df.write.mode("overwrite").parquet("seaweedfs://localhost:8888/spark-test/people")
scala> val back = spark.read.parquet("seaweedfs://localhost:8888/spark-test/people")
scala> back.count()
res: Long = 4
scala> back.orderBy("id").show(false)
+---+-----+
|id |name |
+---+-----+
|1  |alice|
|2  |bob  |
|3  |carol|
|4  |dave |
+---+-----+
```

The write lands under `/spark-test/people/` on the filer as `_SUCCESS` plus the snappy parquet part files. The path prefix `spark-test` is created on write, no need to pre-create it.

# A Full Example
Here is a local example switching everything to SeaweedFS. In the `$SPARK_HOME/conf/spark-defaults.conf` file,

  1. `spark-defaults.conf`
```
spark.master=local[*]

spark.hadoop.fs.seaweedfs.impl=seaweed.hdfs.SeaweedFileSystem
spark.hadoop.fs.AbstractFileSystem.seaweedfs.impl=seaweed.hdfs.SeaweedAbstractFileSystem
spark.hadoop.fs.defaultFS=seaweedfs://localhost:8888

spark.driver.extraClassPath=/path/to/seaweedfs-hadoop3-client-4.38.jar
spark.executor.extraClassPath=/path/to/seaweedfs-hadoop3-client-4.38.jar

spark.eventLog.enabled=true
spark.eventLog.dir=seaweedfs://localhost:8888/spark-history/
spark.history.fs.logDirectory=seaweedfs://localhost:8888/spark-history/
```
  2. Run a spark shell. Event logs are written to SeaweedFS under `/spark-history/`.
```
$ bin/spark-shell
...
Welcome to
      ____              __
     / __/__  ___ _____/ /__
    _\ \/ _ \/ _ `/ __/  '_/
   /___/ .__/\_,_/_/ /_/\_\   version 4.0.3
      /_/

Using Scala version 2.13.16 (OpenJDK 64-Bit Server VM, Java 17.0.19)
Spark session available as 'spark'.

scala> sc.parallelize(1 to 100).sum
res0: Double = 5050.0
```
