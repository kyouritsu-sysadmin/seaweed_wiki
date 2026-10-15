---
id: SeaweedFS-Iceberg-Catalog
title: "SeaweedFS Iceberg Catalog"
sidebar_label: "SeaweedFS Iceberg Catalog"
---

# SeaweedFS Iceberg Catalog

SeaweedFS provides a built-in Iceberg REST Catalog that can be used with popular analytics engines.

## Architecture

The SeaweedFS S3 Tables feature implements the **Iceberg REST Catalog API**. This allows clients to talk directly to SeaweedFS to manage Iceberg namespaces and tables, while the underlying data files (Parquet, Avro, Metadata JSON) are stored in SeaweedFS S3 buckets.

- **Iceberg REST Catalog**: Available on a dedicated port (default `8181`)
- **S3 Data Access**: Available on the S3 port (default `8333`)
- **Authentication**: SigV4 (Spark, Trino, RisingWave), OAuth2 (DuckDB, Doris), or unsigned REST + S3 access keys (Dremio)

## Catalog and Bucket Relationship

In SeaweedFS, an **Iceberg Catalog** corresponds 1:1 with a **Table Bucket**.

- When you configure a client with a URI prefix like `http://localhost:8181/v1/my-catalog/`, SeaweedFS maps requests to the bucket named `my-catalog`.
- If no catalog/prefix is provided in the URL (e.g., `http://localhost:8181/v1/`), it defaults to using a bucket named `warehouse`.

This architecture allows you to manage multiple independent Iceberg catalogs on the same SeaweedFS cluster simply by creating multiple buckets.

## Quick Start

### 1. Start SeaweedFS

```bash
weed mini
```

This starts:
- S3 API on port `8333`
- Iceberg REST Catalog on port `8181`

### 2. Create a Table Bucket

```bash
weed shell
> s3tables.bucket -create -name my-catalog
```

### 3. Connect Your Query Engine

See the integration guide for your engine below.

## Client Integrations

| Engine | Auth Method | Guide |
|--------|------------|-------|
| **Apache Spark** | SigV4 | [Spark Iceberg Integration](./Spark-Iceberg-Integration.md) |
| **Trino** | SigV4 | [Trino Iceberg Integration](./Trino-Iceberg-Integration.md) |
| **Dremio** | S3 access keys (REST source) | [Dremio Iceberg Integration](./Dremio-Iceberg-Integration.md) |
| **DuckDB** | OAuth2 | [DuckDB Iceberg Integration](./DuckDB-Iceberg-Integration.md) |
| **Apache Doris** | OAuth2 | [Doris Iceberg Integration](./Doris-Iceberg-Integration.md) |
| **RisingWave** | SigV4 | [RisingWave Iceberg Integration](./RisingWave-Iceberg-Integration.md) |
| **Lakekeeper** | STS + SigV4 | [Lakekeeper Iceberg Integration](./Lakekeeper-Iceberg-Integration.md) |

## Metadata Storage

SeaweedFS stores Iceberg metadata using a hybrid approach to maximize performance and compatibility:

### Namespaces
Namespace metadata (creation time, properties) is stored as **Extended Attributes (xattrs)** on the directory corresponding to the namespace in the Filer.
- This ensures lightweight namespace operations.
- The directory structure in the Filer mirrors the namespace hierarchy.

### Tables
Table metadata follows the standard Iceberg V2 specification:
- **Metadata Location**: Stored in the `metadata/` subdirectory of the table.
- **Data Location**: Stored in the `data/` subdirectory.
- **Format**:
    - `vN.metadata.json`: The table metadata file.
    - `snap-*.avro`: Snapshot manifest lists.
    - `*.avro`: Manifest files.
    - `*.parquet`: Data files.

## Authentication and Authorization

### Authentication Methods

SeaweedFS supports two authentication methods for the Iceberg REST Catalog:

**SigV4 (Spark, Trino, RisingWave)** — Clients sign each request using AWS Signature Version 4. This is the standard method used by most Iceberg-compatible engines.

**OAuth2 (DuckDB, Doris)** — Clients exchange S3 credentials for a bearer token via `POST /v1/oauth/tokens` using the `client_credentials` grant type. The S3 access key is used as `client_id` and the secret key as `client_secret`.

### Credential Vending

Engines that expect the catalog to hand out storage credentials, rather than
being configured with S3 keys of their own, send:

```
X-Iceberg-Access-Delegation: vended-credentials
```

Vending is off until a role is named:

```
weed server -s3 -s3.iceberg.credentialRole=arn:aws:iam::role/IcebergTableAccess             -s3.iceberg.credentialDurationSeconds=3600
```

The catalog then assumes that role for the caller and returns temporary
credentials in the LoadTable response `config` (`s3.access-key-id`,
`s3.secret-access-key`, `s3.session-token`) and in `storage-credentials`. The
session is scoped by policy to that one table's prefix plus the bucket listing
needed to resolve it, so a credential vended for one table cannot read, write,
or enumerate another.

The role's trust policy decides who may assume it — that is the control point,
and the role needs advanced IAM (`-s3.iam.config`) configured. Requested
durations must be between 900 and 43200 seconds.

Without a role configured, the catalog vends nothing and returns no S3 endpoint
to a client that asked for delegation, so it keeps using the credentials it was
configured with rather than falling back to unsigned requests.

### Authorization (IAM)
Permissions are managed via **S3 Bucket Policies** applied to the Table Bucket.
- You can define granular permissions for `CreateNamespace`, `CreateTable`, `WriteTable`, etc.
- Example Policy to allow read-only access:
  ```json
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "s3tables:ListNamespaces",
          "s3tables:GetTable",
          "s3tables:ListTables"
        ],
        "Resource": "arn:aws:s3tables:region:account:bucket/my-catalog/*"
      }
    ]
  }
  ```

### Anonymous Access (Development)

If SeaweedFS is running without IAM configuration (e.g., `weed mini` with no `-s3.config`), the Iceberg Catalog allows anonymous access by default. This is useful for local development and testing. See each integration page for anonymous configuration details.

## Configuration Reference

| Parameter | CLI Flag | Default |
|-----------|----------|---------|
| Iceberg REST port | `-s3.port.iceberg` (mini) / `--port.iceberg` (standalone) | `8181` |
| S3 port | `-s3.port` (mini) / `--port` (standalone) | `8333` |
| Disable Iceberg | Set port to `0` | Enabled |
| IAM config | `-s3.config` | None (anonymous) |

## See Also

- [Iceberg REST Catalog API](./Iceberg-REST-Catalog-API.md) - Supported REST Catalog operations
- [S3 Table Bucket](./S3-Table-Bucket.md) - Creating and managing table buckets
- [S3 Tables Security](./S3-Tables-Security.md) - IAM policies for table access
- [S3 Table Bucket Commands](./S3-Table-Bucket-Commands.md) - `weed shell` commands
- [Iceberg Table Maintenance](./Iceberg-Table-Maintenance.md) - Compaction and cleanup
