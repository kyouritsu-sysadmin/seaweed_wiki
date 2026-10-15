---
id: Iceberg-REST-Catalog-API
title: "Iceberg REST Catalog API"
sidebar_label: "Iceberg REST Catalog API"
---

SeaweedFS implements the [Iceberg REST Catalog API](https://github.com/apache/iceberg/blob/main/open-api/rest-catalog-open-api.yaml), so any Iceberg REST client (Spark, Trino, PyIceberg, iceberg-go, DuckDB, Dremio, RisingWave, Doris) can manage namespaces, tables, and views directly against SeaweedFS while data and metadata files live in SeaweedFS S3 buckets.

For setup, authentication, and client integrations, see [SeaweedFS Iceberg Catalog](./SeaweedFS-Iceberg-Catalog.md).

# Endpoint

The catalog listens on its own port (default `8181`, set with `-s3.port.iceberg`). A catalog is a table bucket; address it either by URL prefix (`/v1/{bucket}/...`) or with `?warehouse=s3://{bucket}/`. With neither, requests default to the bucket named `warehouse`. See [SeaweedFS Iceberg Catalog](./SeaweedFS-Iceberg-Catalog.md) for the bucket relationship.

# Supported APIs

The tables below list the Iceberg REST Catalog operations and their support status, using the operation names from the REST catalog OpenAPI spec.

## Configuration and OAuth

| API Operation | Method & Path | Supported | Notes |
|---|---|---|---|
| GetConfig | `GET /v1/config` | Yes | Echoes `overrides.prefix` for a `?warehouse=` query |
| GetToken | `POST /v1/oauth/tokens` | Yes | `client_credentials` grant; S3 access/secret key as client id/secret |

## Namespace

| API Operation | Method & Path | Supported | Notes |
|---|---|---|---|
| ListNamespaces | `GET /v1/{prefix}/namespaces` | Yes | `parent` and pagination supported |
| CreateNamespace | `POST /v1/{prefix}/namespaces` | Yes | |
| LoadNamespaceMetadata | `GET /v1/{prefix}/namespaces/{ns}` | Yes | |
| NamespaceExists | `HEAD /v1/{prefix}/namespaces/{ns}` | Yes | |
| DropNamespace | `DELETE /v1/{prefix}/namespaces/{ns}` | Yes | Rejects a non-empty namespace |
| UpdateNamespaceProperties | `POST /v1/{prefix}/namespaces/{ns}/properties` | Yes | Returns the removed/updated/missing summary |

## Table

| API Operation | Method & Path | Supported | Notes |
|---|---|---|---|
| ListTables | `GET /v1/{prefix}/namespaces/{ns}/tables` | Yes | |
| CreateTable | `POST /v1/{prefix}/namespaces/{ns}/tables` | Yes | Includes stage-create |
| LoadTable | `GET /v1/{prefix}/namespaces/{ns}/tables/{table}` | Yes | Vends S3 FileIO config so clients read data files directly; `?snapshots=refs` returns only the snapshots refs point at |
| TableExists | `HEAD /v1/{prefix}/namespaces/{ns}/tables/{table}` | Yes | |
| UpdateTable | `POST /v1/{prefix}/namespaces/{ns}/tables/{table}` | Yes | Commit with assert-* requirements |
| DropTable | `DELETE /v1/{prefix}/namespaces/{ns}/tables/{table}` | Yes | |
| RegisterTable | `POST /v1/{prefix}/namespaces/{ns}/register` | Yes | Registers an existing `metadata.json` location |
| RenameTable | `POST /v1/{prefix}/tables/rename` | Yes | Catalog-only; data and metadata files do not move |
| ReportMetrics | `POST /v1/{prefix}/namespaces/{ns}/tables/{table}/metrics` | Yes | Accepted and discarded; the catalog keeps no metrics store |
| LoadCredentials | `GET /v1/{prefix}/namespaces/{ns}/tables/{table}/credentials` | No | Credentials come back on LoadTable instead, see [S3 Tables Security](./S3-Tables-Security.md) |
| PlanTableScan / FetchScanTasks | `.../tables/{table}/plan` | No | Server-side scan planning |

## View

| API Operation | Method & Path | Supported | Notes |
|---|---|---|---|
| ListViews | `GET /v1/{prefix}/namespaces/{ns}/views` | Yes | |
| CreateView | `POST /v1/{prefix}/namespaces/{ns}/views` | Yes | |
| LoadView | `GET /v1/{prefix}/namespaces/{ns}/views/{view}` | Yes | |
| ViewExists | `HEAD /v1/{prefix}/namespaces/{ns}/views/{view}` | Yes | |
| ReplaceView | `POST /v1/{prefix}/namespaces/{ns}/views/{view}` | Yes | Commit with assert-view-uuid requirements |
| DropView | `DELETE /v1/{prefix}/namespaces/{ns}/views/{view}` | Yes | |
| RenameView | `POST /v1/{prefix}/views/rename` | Yes | Catalog-only, like RenameTable |

## Transaction

| API Operation | Method & Path | Supported | Notes |
|---|---|---|---|
| CommitTransaction | `POST /v1/{prefix}/transactions/commit` | Yes | Multi-table commit; requirements validated together, applied best-effort (not crash-atomic) |

# Notes

- **Naming**: namespace and table/view names use the S3 Tables charset — lowercase `a-z`, `0-9`, `_` and `-`, starting and ending alphanumeric. Names with other characters (uppercase, dots) are rejected with `400 BadRequestException`.
- **Table and view names share a namespace**: a name is unique across both within a namespace.
- **Metadata storage**: the catalog entry is a pointer; the Iceberg `metadata.json` is an object at `s3://{bucket}/{ns}/{table}/metadata/vN.metadata.json`. A commit writes a new metadata file and flips the pointer.
- **Concurrent commits**: the metadata file is written exclusively and the pointer is flipped conditionally, so two engines committing from the same base cannot lose each other's snapshot. The loser retries against the winner's metadata and, out of attempts, gets `409 CommitFailedException` — which Iceberg clients handle by re-reading and retrying. A commit that finds its `vN.metadata.json` name taken stages under `vN-{uuid}.metadata.json`.

# See Also

- [SeaweedFS Iceberg Catalog](./SeaweedFS-Iceberg-Catalog.md)
- [Iceberg Table Maintenance](./Iceberg-Table-Maintenance.md)
