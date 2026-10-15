---
id: Doris-Iceberg-Integration
title: "Doris Iceberg Integration"
sidebar_label: "Doris Iceberg Integration"
---

# Apache Doris Iceberg Integration

Apache Doris connects to SeaweedFS Iceberg tables using an external catalog of `type=iceberg` and `iceberg.catalog.type=rest`. Authentication to the REST catalog uses OAuth2 client credentials via the standard Iceberg `credential` property; data files are read directly from S3 using `s3.access_key` / `s3.secret_key`.

This page reflects the integration verified by the [Apache Doris all-in-one 2.1.0 catalog test](https://github.com/seaweedfs/seaweedfs/tree/master/test/s3tables/catalog_doris).

## Prerequisites

- Apache Doris 2.1.0 or later (the all-in-one Docker image works for local testing)
- A MySQL-protocol client (`mysql` CLI or any Go/Java/Python MySQL driver) — Doris speaks MySQL on port `9030`
- SeaweedFS started as shown in [Setup](#setup) below

## Setup

Start `weed mini` with credentials and a pre-created table bucket via environment variables:

```bash
export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
export S3_TABLE_BUCKET=my-table-bucket

weed mini -dir ~/data
```

This brings up the Iceberg REST Catalog on `http://localhost:8181`, the S3 endpoint on `http://localhost:8333`, an admin S3 identity using the AWS env vars (used as Doris's `credential` and `s3.*` keys below), and the table bucket `my-table-bucket` pre-created.

If Doris runs in a container and SeaweedFS runs on the host, use `host.docker.internal` (with `--add-host host.docker.internal:host-gateway` on Linux) in the URLs below.

## Configuration

Doris external catalogs are registered with `CREATE CATALOG`. Connect with any MySQL client and run:

```sql
CREATE CATALOG iceberg_catalog PROPERTIES (
    "type" = "iceberg",
    "iceberg.catalog.type" = "rest",
    "uri" = "http://localhost:8181",
    "warehouse" = "s3://my-table-bucket",
    "credential" = "AKIAIOSFODNN7EXAMPLE:wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "s3.endpoint" = "http://localhost:8333",
    "s3.access_key" = "AKIAIOSFODNN7EXAMPLE",
    "s3.secret_key" = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "s3.region" = "us-east-1",
    "use_path_style" = "true"
);
```

Key settings:

- `uri` points at the SeaweedFS Iceberg REST Catalog (default `:8181`).
- `warehouse` is `s3://&lt;table-bucket-name&gt;`. SeaweedFS maps this to the bucket of the same name.
- `credential` is the Iceberg-standard OAuth2 client credentials in `client_id:client_secret` form. Doris's REST client exchanges this for a bearer token at `&lt;uri&gt;/v1/oauth/tokens` using the `client_credentials` grant.
- `s3.endpoint`, `s3.access_key`, `s3.secret_key`, `s3.region` are used by the BE workers to read parquet files directly from S3.
- `use_path_style=true` is required for SeaweedFS's path-style S3.

If you change tables outside of Doris (e.g. via Spark, Trino, or PyIceberg), refresh the catalog so the new metadata is picked up:

```sql
REFRESH CATALOG iceberg_catalog;
```

## Example SQL

### Browse the catalog

```sql
-- List all catalogs registered on this Doris cluster
SHOW CATALOGS;

-- Switch into the Iceberg catalog and list namespaces
SWITCH iceberg_catalog;
SHOW DATABASES;

-- List tables in a namespace
SHOW TABLES FROM iceberg_catalog.my_namespace;
```

### Read tables

```sql
-- Three-part identifier: catalog.namespace.table
SELECT * FROM iceberg_catalog.my_namespace.events;
SELECT COUNT(*) FROM iceberg_catalog.my_namespace.events;

-- Identifiers with hyphens or special characters need backticks
SELECT * FROM iceberg_catalog.`my-ns`.`my-table`;
```

The integration test exercises catalog discovery (`SHOW CATALOGS` / `SHOW DATABASES` / `SHOW TABLES`), schema parsing (column-name projection on `id, label`), `SELECT COUNT(*)` against an empty table, and reading three rows that were written by a PyIceberg writer before Doris connected. This validates both the metadata path and the parquet read path.

Write paths from Doris (`CREATE TABLE`, `INSERT INTO`) against an Iceberg REST catalog are not exercised by the SeaweedFS test suite. Treat Doris primarily as a reader against tables produced by Spark, Trino, or other writers.

## Anonymous Access

When SeaweedFS runs without IAM (e.g. `weed mini` with no `-s3.config`), the REST catalog accepts unsigned requests. Drop `credential` from the catalog properties and leave the `s3.*` keys set — SeaweedFS accepts any value when IAM is disabled:

```sql
CREATE CATALOG iceberg_catalog PROPERTIES (
    "type" = "iceberg",
    "iceberg.catalog.type" = "rest",
    "uri" = "http://localhost:8181",
    "warehouse" = "s3://my-table-bucket",
    "s3.endpoint" = "http://localhost:8333",
    "s3.access_key" = "any",
    "s3.secret_key" = "any",
    "s3.region" = "us-east-1",
    "use_path_style" = "true"
);
```

## See Also

- [SeaweedFS Iceberg Catalog](./SeaweedFS-Iceberg-Catalog.md) - Architecture and concepts
- [S3 Table Bucket](./S3-Table-Bucket.md) - Managing table buckets
- [Doris integration test](https://github.com/seaweedfs/seaweedfs/tree/master/test/s3tables/catalog_doris) - End-to-end reference
