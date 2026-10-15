---
id: Spark-Iceberg-Integration
title: "Spark Iceberg Integration"
sidebar_label: "Spark Iceberg Integration"
---

# Spark Iceberg Integration

Apache Spark connects to SeaweedFS Iceberg tables using the Iceberg Spark runtime with the `rest` catalog type and SigV4 authentication.

## Prerequisites

- Spark 3.5+ with Iceberg packages
- SeaweedFS started as shown in [Setup](#setup) below

Required packages:
- `org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2` (match your Spark version)
- `org.apache.iceberg:iceberg-aws-bundle:1.5.2`

## Setup

Start `weed mini` with credentials and a pre-created table bucket via environment variables:

```bash
export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
export S3_TABLE_BUCKET=my-table-bucket

weed mini -dir ~/data
```

This brings up the Iceberg REST Catalog on `http://localhost:8181`, the S3 endpoint on `http://localhost:8333`, an admin S3 identity using the AWS env vars (used as Spark's SigV4 credentials below), and the table bucket `my-table-bucket` pre-created.

## Configuration

### PySpark

```python
from pyspark.sql import SparkSession

spark = (SparkSession.builder
    .appName("SeaweedFS Iceberg")
    .config("spark.jars.packages",
            "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2,"
            "org.apache.iceberg:iceberg-aws-bundle:1.5.2")
    .config("spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
    .config("spark.sql.catalog.iceberg",
            "org.apache.iceberg.spark.SparkCatalog")
    .config("spark.sql.catalog.iceberg.type", "rest")
    .config("spark.sql.catalog.iceberg.uri", "http://localhost:8181")
    # SigV4 authentication
    .config("spark.sql.catalog.iceberg.rest.auth.type", "sigv4")
    .config("spark.sql.catalog.iceberg.rest.sigv4-enabled", "true")
    .config("spark.sql.catalog.iceberg.rest.signing-name", "s3")
    .config("spark.sql.catalog.iceberg.rest.access-key-id", "AKIAIOSFODNN7EXAMPLE")
    .config("spark.sql.catalog.iceberg.rest.secret-access-key", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
    # S3 FileIO
    .config("spark.sql.catalog.iceberg.io-impl",
            "org.apache.iceberg.aws.s3.S3FileIO")
    .config("spark.sql.catalog.iceberg.s3.endpoint", "http://localhost:8333")
    .config("spark.sql.catalog.iceberg.s3.region", "us-east-1")
    .config("spark.sql.catalog.iceberg.s3.access-key", "AKIAIOSFODNN7EXAMPLE")
    .config("spark.sql.catalog.iceberg.s3.secret-key", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
    .config("spark.sql.catalog.iceberg.s3.path-style-access", "true")
    .getOrCreate()
)
```

### spark-sql CLI

```bash
spark-sql \
    --packages "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2,org.apache.iceberg:iceberg-aws-bundle:1.5.2" \
    --conf "spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions" \
    --conf "spark.sql.defaultCatalog=iceberg" \
    --conf "spark.sql.catalog.iceberg=org.apache.iceberg.spark.SparkCatalog" \
    --conf "spark.sql.catalog.iceberg.type=rest" \
    --conf "spark.sql.catalog.iceberg.uri=http://localhost:8181" \
    --conf "spark.sql.catalog.iceberg.io-impl=org.apache.iceberg.aws.s3.S3FileIO" \
    --conf "spark.sql.catalog.iceberg.s3.endpoint=http://localhost:8333" \
    --conf "spark.sql.catalog.iceberg.s3.path-style-access=true" \
    --conf "spark.sql.catalog.iceberg.s3.access-key=AKIAIOSFODNN7EXAMPLE" \
    --conf "spark.sql.catalog.iceberg.s3.secret-key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" \
    --conf "spark.sql.catalog.iceberg.rest.sigv4-enabled=true" \
    --conf "spark.sql.catalog.iceberg.rest.signing-name=s3"
```

## Example SQL

### Namespace and Table Operations

```sql
-- Create a namespace
CREATE NAMESPACE iceberg.my_namespace;

-- Create a table
CREATE TABLE iceberg.my_namespace.users (
    id INT,
    name STRING,
    age INT
) USING iceberg;

-- Insert data
INSERT INTO iceberg.my_namespace.users VALUES
    (1, 'Alice', 30),
    (2, 'Bob', 25),
    (3, 'Charlie', 35);

-- Query
SELECT * FROM iceberg.my_namespace.users;
SELECT COUNT(*) FROM iceberg.my_namespace.users;

-- Update and delete
UPDATE iceberg.my_namespace.users SET age = 31 WHERE id = 1;
DELETE FROM iceberg.my_namespace.users WHERE id = 3;
```

### Multi-Level Namespaces

```sql
CREATE NAMESPACE iceberg.analytics;
CREATE NAMESPACE iceberg.analytics.web;

CREATE TABLE iceberg.analytics.web.pageviews (
    id INT,
    url STRING,
    ts TIMESTAMP
) USING iceberg;
```

### Time Travel

```sql
-- Query a table at a specific point in time
SELECT COUNT(*) FROM iceberg.my_namespace.users
    TIMESTAMP AS OF '2024-01-15 10:30:00';
```

## Anonymous Access

When SeaweedFS runs without IAM, disable SigV4:

```python
spark = (SparkSession.builder
    .config("spark.sql.catalog.iceberg.type", "rest")
    .config("spark.sql.catalog.iceberg.uri", "http://localhost:8181")
    .config("spark.sql.catalog.iceberg.rest.sigv4-enabled", "false")
    .config("spark.sql.catalog.iceberg.io-impl",
            "org.apache.iceberg.aws.s3.S3FileIO")
    .config("spark.sql.catalog.iceberg.s3.endpoint", "http://localhost:8333")
    .config("spark.sql.catalog.iceberg.s3.path-style-access", "true")
    # ... other standard configs
    .getOrCreate()
)
```

## See Also

- [SeaweedFS Iceberg Catalog](./SeaweedFS-Iceberg-Catalog.md) - Architecture and concepts
- [S3 Table Bucket](./S3-Table-Bucket.md) - Managing table buckets
- [run Spark on SeaweedFS](./run-Spark-on-SeaweedFS.md) - Spark with SeaweedFS HDFS connector (non-Iceberg)
