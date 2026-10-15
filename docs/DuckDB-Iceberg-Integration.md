---
id: DuckDB-Iceberg-Integration
title: "DuckDB Iceberg Integration"
sidebar_label: "DuckDB Iceberg Integration"
---

# DuckDB Iceberg Integration

DuckDB can query Iceberg tables stored in SeaweedFS using the [Iceberg extension](https://duckdb.org/docs/extensions/iceberg.html) and the built-in Iceberg REST Catalog.

## Prerequisites

- SeaweedFS running with the Iceberg REST Catalog enabled (port `8181` by default)
- A table bucket created via `weed shell` or the S3 Tables API
- DuckDB v1.1.0+ with the Iceberg extension

## Quick Start

### 1. Start SeaweedFS with credentials and a table bucket

`weed mini` is fully configurable via environment variables — credentials become an admin S3 identity, and `S3_TABLE_BUCKET` pre-creates the Iceberg table bucket. No IAM config file or `weed shell` step needed:

```bash
export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
export S3_TABLE_BUCKET=my-catalog

weed mini -dir ~/data
```

This brings up:
- Iceberg REST Catalog on `http://localhost:8181`
- S3 endpoint on `http://localhost:8333`
- An admin S3 identity using the AWS env vars above (used as DuckDB's `CLIENT_ID` / `CLIENT_SECRET`)
- Table bucket `my-catalog` pre-created

`S3_TABLE_BUCKET` (or the `-tableBucket` flag) accepts a comma-separated list (`my-catalog,other-catalog`); existing buckets are left alone. `S3_BUCKET` / `-bucket` does the same for plain (non-table) buckets.

### 2. Connect DuckDB

```sql
INSTALL iceberg;
LOAD iceberg;

-- Iceberg catalog secret (OAuth2 against the REST Catalog).
-- CLIENT_ID / CLIENT_SECRET must match the AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY exported above.
CREATE SECRET iceberg_secret (
    TYPE ICEBERG,
    ENDPOINT 'http://localhost:8181',
    CLIENT_ID 'AKIAIOSFODNN7EXAMPLE',
    CLIENT_SECRET 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
);

-- S3 secret for reading data files. Same credentials.
CREATE SECRET s3_secret (
    TYPE S3,
    KEY_ID 'AKIAIOSFODNN7EXAMPLE',
    SECRET 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
    ENDPOINT 'localhost:8333',
    URL_STYLE 'path',
    USE_SSL false
);
```

## Authentication

SeaweedFS supports OAuth2 `client_credentials` flow for the Iceberg REST Catalog, which is what DuckDB uses. Your S3 access key and secret key are used as the `CLIENT_ID` and `CLIENT_SECRET`.

When DuckDB creates an Iceberg secret, it automatically:
1. Posts to `POST /v1/oauth/tokens` with your credentials
2. Receives a bearer token
3. Uses the bearer token for all subsequent catalog requests

### With IAM Credentials

When `weed mini` is started with `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` exported (or with `-s3.config=iam.json` for richer multi-identity setups), the `CLIENT_ID` / `CLIENT_SECRET` passed to `CREATE SECRET` must match a registered access key / secret key pair. The catalog rejects unknown credentials with `401 invalid_client`.

### Anonymous Access (Development)

When SeaweedFS runs without IAM configuration (e.g., `weed mini` with no `-s3.config`), you can connect without credentials. DuckDB still requires the `CLIENT_ID` and `CLIENT_SECRET` fields, but any non-empty values will work:

```sql
CREATE SECRET (
    TYPE ICEBERG,
    ENDPOINT 'http://localhost:8181',
    CLIENT_ID 'admin',
    CLIENT_SECRET 'admin'
);
```

## Scoping Secrets to a Catalog

Use the `SCOPE` parameter to bind a secret to a specific table bucket:

```sql
CREATE SECRET iceberg_secret (
    TYPE ICEBERG,
    ENDPOINT 'http://localhost:8181',
    CLIENT_ID 'your-access-key',
    CLIENT_SECRET 'your-secret-key',
    SCOPE 's3://my-catalog/'
);

CREATE SECRET s3_secret (
    TYPE S3,
    KEY_ID 'your-access-key',
    SECRET 'your-secret-key',
    ENDPOINT 'localhost:8333',
    URL_STYLE 'path',
    USE_SSL false,
    SCOPE 's3://my-catalog/'
);
```

## Querying Tables

Once secrets are configured, you can query Iceberg tables:

```sql
-- Scan an Iceberg table by its S3 path
SELECT * FROM iceberg_scan('s3://my-catalog/my-namespace/my-table');

-- With metadata path
SELECT * FROM iceberg_scan('s3://my-catalog/my-namespace/my-table/metadata/v1.metadata.json');
```

## "Attaching" the catalog

Once secrets are configured, it is possible to attach the catalog for direct access:

```sql
ATTACH 's3://my-catalog' AS my_catalog(
  TYPE iceberg,
  SECRET iceberg_secret,
  ENDPOINT 'http://localhost:8181',
  READ_ONLY false
);

SELECT * FROM my_catalog.my-namespace.my-table;

INSERT INTO my_catalog.my-namespace.my-table VALUES (...);
```

Note that remote catalogs are mounted read-only by default, so if you need to be able to modify things, you need the `READ_ONLY false`. If you only need to read, no need to add the `READ_ONLY false`.

## Configuration Reference

| Parameter | Description | Default |
|-----------|-------------|---------|
| Iceberg REST port | `--port.iceberg` (standalone) or `-s3.port.iceberg` (mini) | `8181` |
| S3 port | `--port` (standalone) or `-s3.port` (mini) | `8333` |
| Disable Iceberg | Set port to `0` | Enabled |

## Troubleshooting

### "HTTP NotFound_404" on `/v1/oauth/tokens`

Upgrade SeaweedFS. The OAuth2 token endpoint was added to support DuckDB's authentication flow.

### "access denied" when creating secrets

Ensure your `CLIENT_ID` and `CLIENT_SECRET` match a valid IAM identity configured in SeaweedFS. Check your `-s3.config` file.

### DuckDB can connect but cannot read data

Make sure you have an S3 secret configured in addition to the Iceberg secret. The Iceberg secret handles catalog operations (listing namespaces, table metadata), while the S3 secret is needed for reading the actual Parquet data files.

```sql
-- Both secrets are needed:
-- 1. ICEBERG secret -> talks to the catalog API on port 8181
-- 2. S3 secret -> reads data files from S3 on port 8333
```

## See Also

- [SeaweedFS Iceberg Catalog](./SeaweedFS-Iceberg-Catalog.md) - Architecture and Spark/Trino integration
- [S3 Table Bucket](./S3-Table-Bucket.md) - Managing table buckets
- [S3 Tables Security](./S3-Tables-Security.md) - IAM policies for table access
