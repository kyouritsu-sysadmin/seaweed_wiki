---
id: Spark-Lance-Integration
title: "Spark Lance Integration"
sidebar_label: "Spark Lance Integration"
---

# Spark Lance Integration

Spark reads and writes Lance tables in a SeaweedFS table bucket through the
[Lance Spark connector](https://lance.org/integrations/spark/config/), pointed at
the [SeaweedFS Lance Catalog](./SeaweedFS-Lance-Catalog.md).

Verified against Spark 3.5.1 and `org.lance:lance-spark-bundle-3.5_2.12:0.7.1` by
the integration suite in `test/s3tables/catalog_spark_lance/`.

## Prerequisites

- SeaweedFS with the Lance Namespace enabled: `weed server -s3 -s3.port.lance=9101`
- A table bucket declared `LANCE`, made either from the shell:

  ```bash
  weed shell
  > s3tables.bucket -create -name vectors -format LANCE -account 000000000000
  ```

  or at startup, with `weed mini -tableBucket=vectors:LANCE`.

## Configuration

### PySpark

```python
from pyspark.sql import SparkSession

spark = (SparkSession.builder
    .appName("SeaweedFS Lance")
    .config("spark.jars.packages", "org.lance:lance-spark-bundle-3.5_2.12:0.7.1")
    .config("spark.sql.catalog.lance", "org.lance.spark.LanceNamespaceSparkCatalog")
    .config("spark.sql.catalog.lance.impl", "rest")
    .config("spark.sql.catalog.lance.uri", "http://localhost:9101")
    .config("spark.sql.catalog.lance.storage.aws_endpoint", "http://localhost:8333")
    .config("spark.sql.catalog.lance.storage.allow_http", "true")
    .config("spark.sql.catalog.lance.storage.aws_access_key_id", "…")
    .config("spark.sql.catalog.lance.storage.aws_secret_access_key", "…")
    .config("spark.sql.catalog.lance.storage.aws_region", "us-east-1")
    .getOrCreate())
```

Pick the bundle that matches your Spark and Scala version — `lance-spark-bundle-3.4_2.12`,
`-3.5_2.12`, `-3.5_2.13`, `-4.0_2.13` and others are published under `org.lance`.

### The `storage.` prefix

Everything under `spark.sql.catalog.&lt;name&gt;.storage.` is handed to lance as
object_store options, so these are **object_store's key names**
(`aws_endpoint`, `aws_access_key_id`, `allow_http`) rather than Spark's `s3a`
ones. Getting this wrong is the usual reason a table lists but will not read.

Credentials belong there because a gateway without STS configured vends an
endpoint and a region but no credentials of its own. With
`-s3.iceberg.credentialRole` set, the namespace vends real ones and the client
does not need static keys — see [SeaweedFS Lance Catalog](./SeaweedFS-Lance-Catalog.md).

## Example SQL

A table bucket is the first level of the namespace path, so a table is addressed
as `&lt;catalog&gt;.&lt;bucket&gt;.&lt;namespace&gt;.<table>`:

```sql
CREATE NAMESPACE IF NOT EXISTS lance.`vectors`.ml;

CREATE TABLE lance.`vectors`.ml.embeddings (
    id BIGINT,
    title STRING,
    vector ARRAY<FLOAT>
) USING lance;

INSERT INTO lance.`vectors`.ml.embeddings VALUES
    (1, 'one', array(1.0f, 2.0f, 3.0f)),
    (2, 'two', array(2.0f, 3.0f, 4.0f));

SELECT count(*) FROM lance.`vectors`.ml.embeddings;
SELECT id, title FROM lance.`vectors`.ml.embeddings WHERE id >= 2 ORDER BY id;
```

Backticks around the bucket name are needed when it contains a hyphen.

## What to expect

- **`CREATE TABLE` works.** The connector declares the table through the catalog
  and writes the data itself; it does not push Arrow data at the server, which
  is the operation SeaweedFS answers `Unsupported` for.
- **`SHOW TABLES` returns namespace identifiers**, not bare Spark names:

  ```
  SHOW TABLES IN lance.`vectors`.ml
  -> vectors$ml$embeddings
  ```

- **Repeated writes are fine.** A second `INSERT` is the one that fails on a
  store that cannot order commits; SeaweedFS evaluates Lance's conditional PUT
  atomically at the object's owner filer, so it does not.

## Without Spark

The same tables open in [LanceDB Integration](./LanceDB-Integration.md), in pylance, or straight off
their location with no catalog at all.

## See also

- [SeaweedFS Lance Catalog](./SeaweedFS-Lance-Catalog.md)
- [LanceDB Integration](./LanceDB-Integration.md)
- [Lance Maintenance Worker](./Lance-Maintenance-Worker.md)
- [Spark Iceberg Integration](./Spark-Iceberg-Integration.md)
