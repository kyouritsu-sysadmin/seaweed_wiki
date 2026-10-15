---
id: SeaweedFS-Lance-Catalog
title: "SeaweedFS Lance Catalog"
sidebar_label: "SeaweedFS Lance Catalog"
---

# SeaweedFS Lance Catalog

SeaweedFS provides a built-in [Lance Namespace](https://lancedb.github.io/lance-namespace/) REST catalog, beside the [SeaweedFS Iceberg Catalog](./SeaweedFS-Iceberg-Catalog.md) and over the same table buckets.

[Lance](https://lancedb.com) is a columnar format built for multimodal and vector data: random access is orders of magnitude faster than Parquet, and a dataset carries its own vector and scalar indices.

## Architecture

- **Lance Namespace API**: a dedicated port (default `9101`)
- **S3 data access**: the S3 port (default `8333`)
- **Authentication**: the same SigV4 identities as the rest of the S3 stack, with optional credential vending

A **table bucket is a catalog**, exactly as it is for Iceberg. Which protocol serves it depends on the format the bucket declares.

| Format | Served by | Default port |
|--------|-----------|--------------|
| `ICEBERG` | Iceberg REST Catalog | 8181 |
| `LANCE` | Lance Namespace API | 9101 |

Identifiers are lists, joined on the wire by `$` (configurable per request), and map onto what already exists:

```
["vectors"]                        -> table bucket "vectors"
["vectors", "ml"]                  -> namespace "ml" in that bucket
["vectors", "ml", "embeddings"]    -> table "embeddings"
```

The root (`/v1/namespace/%24/list`, or just the delimiter) lists table buckets.

## Quick Start

### 1. Start SeaweedFS

```bash
weed server -s3 -s3.port.lance=9101
```

or `weed mini`, which starts the Lance namespace along with everything else.

### 2. Create a Lance table bucket

Two ways, depending on whether the cluster is already running.

**From the shell**, against a running cluster:

```bash
weed shell
> s3tables.bucket -create -name vectors -format LANCE -account 000000000000
```

**At startup**, with `weed mini -tableBucket`, which pre-creates buckets before
anything connects. Each entry is `name[:FORMAT]`, and an unsuffixed name means
`ICEBERG`:

```bash
weed mini -tableBucket=vectors:LANCE

# several at once, in either format
weed mini -tableBucket=warehouse,vectors:LANCE
```

The same list can come from the `S3_TABLE_BUCKET` environment variable, which is
how the Docker images take it.

mini will not create a bucket in a format it does not serve — a `:LANCE` entry
with the Lance namespace disabled is skipped with a warning rather than made
unreachable — so keep `-s3.port.lance` enabled (it is, by default).

A bucket holds one format. Declaring `LANCE` means the catalog refuses an Iceberg table in it, and the reverse. Buckets created before formats were declared carry none and keep accepting either.

### 3. Use it

```python
import lance, lance_namespace as ln

ns = ln.connect("rest", {"uri": "http://localhost:9101"})
ns.create_namespace(ln.CreateNamespaceRequest(id=["vectors", "ml"]))

declared = ns.declare_table(ln.DeclareTableRequest(id=["vectors", "ml", "embeddings"]))
lance.write_dataset(table, declared.location, storage_options=declared.storage_options)
```

See [LanceDB Integration](./LanceDB-Integration.md) and [Spark Lance Integration](./Spark-Lance-Integration.md) for the same thing
through those clients.

## What the catalog serves

| Operation | Route | Notes |
|-----------|-------|-------|
| Create / list / describe / drop / exists namespace | `/v1/namespace/{id}/…` | root lists table buckets |
| List tables | `GET /v1/namespace/{id}/table/list` | |
| List every table | `GET /v1/table` | across the catalog |
| Declare table | `POST /v1/table/{id}/declare` | reserves the name, returns the location |
| Describe table | `POST /v1/table/{id}/describe` | location, and credentials on request |
| Register / deregister | `POST /v1/table/{id}/register`, `/deregister` | see below |
| Drop / rename | `POST /v1/table/{id}/drop`, `/rename` | |

Everything else — `create`, `insert`, `query`, `count_rows`, index, tag, branch and version operations — answers the spec's `Unsupported` (HTTP 501). Those carry Arrow data and would mean reading and writing the Lance file format inside the gateway, which is not implemented. Clients do the reading and writing themselves against the location the catalog hands back, which is the split the format is designed for.

`managed_versioning` is `false` and will stay false: a Lance commit is a conditional PUT, and SeaweedFS answers `If-None-Match: *` atomically at the object's owner filer, so the dataset can own its own version history.

### Deregister is not a drop

`deregister` hides a table from the catalog and **keeps the data**. `drop` removes both. A deregistered table can be brought back with `register`, or read straight off its location by any client.

## Credential vending

The Lance spec carries this in the protocol. Ask for it on a describe:

```python
described = ns.describe_table(ln.DescribeTableRequest(
    id=["vectors", "ml", "embeddings"], vend_credentials=True))

dataset = lance.dataset(described.location, storage_options=described.storage_options)
```

The response's `storage_options` carry object_store's own key names — `aws_access_key_id`, `aws_secret_access_key`, `aws_session_token`, `aws_region`, `aws_endpoint`, `allow_http` — plus `expires_at_millis`. It reuses the same STS path as the Iceberg catalog; configure it with `-s3.iceberg.credentialRole`.

Without STS configured, the namespace vends an endpoint and a region but **no credentials**, and the client must bring its own. See [LanceDB Integration](./LanceDB-Integration.md) for what that looks like in practice.

## The catalog is optional

Tables are laid out so that a namespace prefix is also a valid Lance directory:

```python
lance.dataset("s3://vectors/ml/embeddings", storage_options=opts)
```

opens the same data with no catalog in the path. duckdb, pandas, Polars and DataFusion do not speak the namespace protocol; this is what keeps them able to read your tables.

## Maintenance

A Lance table needs upkeep that no Iceberg worker can do — in particular, rows written after an index was built are not covered by it, so a vector search silently misses them. The worker ships in the SeaweedFS image (`docker run chrislusf/seaweedfs worker-rust --admin admin:23646`) and on each release; see [Lance Maintenance Worker](./Lance-Maintenance-Worker.md).

## Admin UI

Table buckets show the format they hold and the endpoint that serves them. For a Lance table, the schema, row count and version history come from a maintenance worker rather than from the gateway, which cannot read the format; sample rows are fetched from a worker when the page is opened. Both are labelled with which worker answered and when.

## See also

- [LanceDB Integration](./LanceDB-Integration.md)
- [Spark Lance Integration](./Spark-Lance-Integration.md)
- [DuckDB Lance Integration](./DuckDB-Lance-Integration.md)
- [Lance Maintenance Worker](./Lance-Maintenance-Worker.md)
- [S3 Table Bucket](./S3-Table-Bucket.md)
- [SeaweedFS Iceberg Catalog](./SeaweedFS-Iceberg-Catalog.md)
