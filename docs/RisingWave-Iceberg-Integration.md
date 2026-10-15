---
id: RisingWave-Iceberg-Integration
title: "RisingWave Iceberg Integration"
sidebar_label: "RisingWave Iceberg Integration"
---

# RisingWave Iceberg Integration

RisingWave can read from and write to SeaweedFS Iceberg tables using the `iceberg` connector with the REST catalog type.

## Prerequisites

- RisingWave v2.5.0+ with Iceberg connector support
- SeaweedFS started as shown in [Setup](#setup) below

## Setup

Start `weed mini` with credentials and a pre-created table bucket via environment variables:

```bash
export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
export S3_TABLE_BUCKET=my-table-bucket

weed mini -dir ~/data
```

This brings up the Iceberg REST Catalog on `http://localhost:8181`, the S3 endpoint on `http://localhost:8333`, an admin S3 identity using the AWS env vars (used as RisingWave's `s3.access.key` / `s3.secret.key` below), and the table bucket `my-table-bucket` pre-created.

## Reading from Iceberg (Source)

Create a source to read an existing Iceberg table:

```sql
CREATE SOURCE my_source WITH (
    connector = 'iceberg',
    catalog.type = 'rest',
    catalog.uri = 'http://localhost:8181',
    catalog.name = 'default',
    database.name = 'my_namespace',
    table.name = 'my_table',
    warehouse.path = 's3://my-table-bucket',
    s3.endpoint = 'http://localhost:8333',
    s3.region = 'us-east-1',
    s3.access.key = 'AKIAIOSFODNN7EXAMPLE',
    s3.secret.key = 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
    s3.path.style.access = 'true',
    catalog.rest.sigv4_enabled = 'true',
    catalog.rest.signing_region = 'us-east-1',
    catalog.rest.signing_name = 's3'
);
```

Query the source:

```sql
SELECT * FROM my_source ORDER BY id;
```

## Writing to Iceberg (Sink)

### Append-Only Sink

Stream data from a RisingWave table to an Iceberg table in append-only mode:

```sql
-- Create a RisingWave table
CREATE TABLE events (id INT, event VARCHAR);

-- Create an append-only Iceberg sink
CREATE SINK events_sink FROM events
WITH (
    connector = 'iceberg',
    catalog.type = 'rest',
    catalog.uri = 'http://localhost:8181',
    catalog.name = 'default',
    database.name = 'my_namespace',
    table.name = 'events',
    warehouse.path = 's3://my-table-bucket',
    s3.endpoint = 'http://localhost:8333',
    s3.region = 'us-east-1',
    s3.access.key = 'AKIAIOSFODNN7EXAMPLE',
    s3.secret.key = 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
    s3.path.style.access = 'true',
    catalog.rest.sigv4_enabled = 'true',
    catalog.rest.signing_region = 'us-east-1',
    catalog.rest.signing_name = 's3',
    type = 'append-only',
    force_append_only = 'true'
);

-- Insert data (will be streamed to Iceberg)
INSERT INTO events VALUES (1, 'click'), (2, 'view');
FLUSH;
```

### Upsert Sink

For tables with a primary key, use upsert mode to propagate updates and deletes:

```sql
CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR);

CREATE SINK users_sink FROM users
WITH (
    connector = 'iceberg',
    catalog.type = 'rest',
    catalog.uri = 'http://localhost:8181',
    catalog.name = 'default',
    database.name = 'my_namespace',
    table.name = 'users',
    warehouse.path = 's3://my-table-bucket',
    s3.endpoint = 'http://localhost:8333',
    s3.region = 'us-east-1',
    s3.access.key = 'AKIAIOSFODNN7EXAMPLE',
    s3.secret.key = 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
    s3.path.style.access = 'true',
    catalog.rest.sigv4_enabled = 'true',
    catalog.rest.signing_region = 'us-east-1',
    catalog.rest.signing_name = 's3',
    type = 'upsert',
    primary_key = 'id'
);

-- These operations are streamed to Iceberg
INSERT INTO users VALUES (1, 'Alice'), (2, 'Bob');
FLUSH;
UPDATE users SET name = 'Charles' WHERE id = 1;
DELETE FROM users WHERE id = 2;
FLUSH;
```

## Configuration Reference

| Parameter | Description |
|-----------|-------------|
| `catalog.type` | Must be `rest` |
| `catalog.uri` | Iceberg REST Catalog URL (default `http://localhost:8181`) |
| `catalog.name` | Catalog name (use `default`) |
| `database.name` | Iceberg namespace name |
| `table.name` | Iceberg table name |
| `warehouse.path` | S3 path to the table bucket (e.g., `s3://my-bucket`) |
| `s3.endpoint` | SeaweedFS S3 endpoint (default `http://localhost:8333`) |
| `s3.path.style.access` | Must be `true` for SeaweedFS |
| `catalog.rest.sigv4_enabled` | Enable SigV4 auth (`true` when IAM is configured) |
| `catalog.rest.signing_name` | Signing service name (`s3`) |
| `type` | Sink type: `append-only` or `upsert` |
| `primary_key` | Required for upsert sinks |

## See Also

- [SeaweedFS Iceberg Catalog](./SeaweedFS-Iceberg-Catalog.md) - Architecture and concepts
- [S3 Table Bucket](./S3-Table-Bucket.md) - Managing table buckets
