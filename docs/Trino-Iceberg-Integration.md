---
id: Trino-Iceberg-Integration
title: "Trino Iceberg Integration"
sidebar_label: "Trino Iceberg Integration"
---

# Trino Iceberg Integration

Trino connects to SeaweedFS Iceberg tables using the `iceberg` connector with the `rest` catalog type and SigV4 authentication.

## Prerequisites

- Trino 4xx+ with the Iceberg connector
- SeaweedFS started as shown in [Setup](#setup) below

## Setup

Start `weed mini` with credentials and a pre-created table bucket via environment variables:

```bash
export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
export S3_TABLE_BUCKET=my-table-bucket

weed mini -dir ~/data
```

This brings up the Iceberg REST Catalog on `http://localhost:8181`, the S3 endpoint on `http://localhost:8333`, an admin S3 identity using the AWS env vars (used as Trino's SigV4 credentials below), and the table bucket `my-table-bucket` pre-created.

## Configuration

Create a catalog properties file at `etc/catalog/iceberg.properties`:

```properties
connector.name=iceberg
iceberg.catalog.type=rest
iceberg.rest-catalog.uri=http://localhost:8181
iceberg.rest-catalog.warehouse=s3://my-table-bucket

# File format
iceberg.file-format=PARQUET
iceberg.unique-table-location=true

# SigV4 authentication for the REST catalog
iceberg.rest-catalog.security=SIGV4

# S3 FileIO configuration
fs.native-s3.enabled=true
s3.endpoint=http://localhost:8333
s3.path-style-access=true
s3.signer-type=AwsS3V4Signer
s3.aws-access-key=AKIAIOSFODNN7EXAMPLE
s3.aws-secret-key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
s3.region=us-east-1
```

### Recommended: `iceberg.unique-table-location=true`

Keep Trino's default `iceberg.unique-table-location=true` (already shown in the configuration above). With it enabled, each new table is created at a unique path `s3://&lt;bucket&gt;/&lt;namespace&gt;/&lt;tableName&gt;-&lt;UUID&gt;/`. The UUID suffix gives you three operational properties worth keeping:

- **Orphan-resistant `DROP` + `CREATE`** — if a `DROP TABLE` cleanup partially fails (filer error, crash mid-cleanup), a fresh `CREATE TABLE` with the same name lands at a new path and is not blocked or polluted by leftover files.
- **Crash-safe aborted creates** — a `CREATE TABLE` that wrote partial state but failed to commit leaves debris under one UUID; the retry uses a new UUID and proceeds cleanly.
- **Defense-in-depth against client-side empty-location pre-flight checks** — Trino runs `listFiles(&lt;location&gt;).hasNext()` before commit, and so do some other engines. With unique paths the check sees a fresh empty directory regardless of any historical state at the deterministic name.

If you prefer the cleaner `s3://&lt;bucket&gt;/&lt;namespace&gt;/&lt;tableName&gt;/` layout (one directory per table, no `&lt;tableName&gt;-&lt;UUID&gt;/` sibling), setting `iceberg.unique-table-location=false` is safe against SeaweedFS — you give up the resistance properties above. Pick whichever trade-off fits your operational model.

### Multi-Level Namespaces

To use nested namespaces (e.g., `db.schema`), add:

```properties
iceberg.rest-catalog.nested-namespace-enabled=true
```

## Example SQL

### Schema Operations

```sql
-- Create a schema (maps to an Iceberg namespace)
CREATE SCHEMA IF NOT EXISTS iceberg.my_namespace;

-- List schemas
SHOW SCHEMAS FROM iceberg;
```

### Table Operations

```sql
-- Create a table
CREATE TABLE iceberg.my_namespace.events (
    id INTEGER,
    event VARCHAR,
    ts TIMESTAMP(6)
) WITH (
    format = 'PARQUET'
);

-- Insert data
INSERT INTO iceberg.my_namespace.events VALUES
    (1, 'click', TIMESTAMP '2024-01-15 10:30:00'),
    (2, 'view', TIMESTAMP '2024-01-15 11:00:00');

-- Query
SELECT * FROM iceberg.my_namespace.events;

-- Inspect data files
SELECT file_path FROM iceberg.my_namespace."events$files" LIMIT 5;
```

### Multi-Level Namespace Example

```sql
CREATE SCHEMA IF NOT EXISTS iceberg."analytics.web";

CREATE TABLE iceberg."analytics.web".pageviews (
    id INTEGER,
    url VARCHAR,
    ts TIMESTAMP(6)
) WITH (
    format = 'PARQUET'
);
```

## Anonymous Access

When SeaweedFS runs without IAM, remove the SigV4 and credential properties:

```properties
connector.name=iceberg
iceberg.catalog.type=rest
iceberg.rest-catalog.uri=http://localhost:8181
iceberg.rest-catalog.warehouse=s3://my-table-bucket

fs.native-s3.enabled=true
s3.endpoint=http://localhost:8333
s3.path-style-access=true
s3.region=us-east-1
```

## See Also

- [SeaweedFS Iceberg Catalog](./SeaweedFS-Iceberg-Catalog.md) - Architecture and concepts
- [S3 Table Bucket](./S3-Table-Bucket.md) - Managing table buckets
