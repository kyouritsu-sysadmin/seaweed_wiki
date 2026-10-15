---
id: LanceDB-Integration
title: "LanceDB Integration"
sidebar_label: "LanceDB Integration"
---

# LanceDB Integration

[LanceDB](https://lancedb.com) connects to the [SeaweedFS Lance Catalog](./SeaweedFS-Lance-Catalog.md) over the Lance Namespace REST protocol, so a SeaweedFS table bucket works as a LanceDB catalog with no other service in the way.

Verified against `lancedb 0.37.1`, `lance-namespace 0.8.6` and `pylance 10.0.0` by the integration suite in `test/s3tables/catalog_lancedb/`.

## 1. Start SeaweedFS

```bash
weed server -dir=/data -s3 -s3.port.lance=9101
```

## 2. Create a Lance table bucket

```bash
weed shell
> s3tables.bucket -create -name vectors -format LANCE -account 000000000000
```

Or pre-create it at startup, which is one line instead of two:

```bash
weed mini -tableBucket=vectors:LANCE
```

## 3. Connect

```python
import lancedb

db = lancedb.connect_namespace(
    "rest",
    {"uri": "http://localhost:9101"},
    storage_options={
        "aws_endpoint": "http://localhost:8333",
        "allow_http": "true",
        "aws_access_key_id": "...",
        "aws_secret_access_key": "...",
        "aws_region": "us-east-1",
    },
)
```

`connect_namespace` takes the properties dict as `Dict[str, str]`; `storage_options` is a separate keyword argument, and passing it inside the properties fails with `'dict' object is not an instance of 'str'`.

## 4. Use it

A table bucket is the first level of the namespace path, so `namespace_path` is `[bucket, namespace]`:

```python
# create - LanceDB declares the table through the catalog and writes the data
table = db.create_table(
    "embeddings", data=rows, namespace_path=["vectors", "ml"])

# list
db.table_names(namespace_path=["vectors", "ml"])
# -> ['vectors$ml$embeddings']

# open and query
table = db.open_table("embeddings", namespace_path=["vectors", "ml"])
table.count_rows()
table.search([0.1] * 8).limit(5).to_list()
table.search().where("id < 5").limit(10).to_list()

# index
table.create_index(metric="l2", vector_column_name="vector",
                   index_type="IVF_PQ", num_partitions=1, num_sub_vectors=4)
```

## Credentials

**This is the one that catches people.** A gateway without STS configured vends `storage_options` carrying an endpoint and a region but no credentials, and LanceDB uses what the namespace vends on some paths — so a client configured only through `connect_namespace(storage_options=...)` can still end up with none, failing inside lance with:

```
Failed to get AWS credentials: CredentialsNotLoaded(... "no providers in chain provided credentials")
```

Two ways out, and you can use both:

1. **Configure credential vending** so the namespace hands out real, scoped, expiring credentials:

   ```bash
   weed server -s3 -s3.port.lance=9101 -s3.iceberg.credentialRole=arn:aws:iam::…:role/…
   ```

2. **Give the client credentials the ordinary way**, in the environment, so lance's provider chain finds them whichever path is taken:

   ```bash
   export AWS_ACCESS_KEY_ID=… AWS_SECRET_ACCESS_KEY=…
   export AWS_ENDPOINT_URL=http://localhost:8333
   export AWS_ALLOW_HTTP=true
   ```

## What is not served

`create_table` works because LanceDB declares through the catalog and writes the data itself. Asking LanceDB to push the operation to the server instead —

```python
lancedb.connect_namespace(..., namespace_client_pushdown_operations=["CreateTable"])
```

— calls the namespace's own `CreateTable`, which carries Arrow data and is not implemented here; see [SeaweedFS Lance Catalog](./SeaweedFS-Lance-Catalog.md) for the full list. The client falls back to declare-and-write, so the table still lands.

## Without the catalog

The same dataset opens by URI, which is worth knowing before you build anything that assumes the catalog is always reachable:

```python
import lance
lance.dataset("s3://vectors/ml/embeddings", storage_options=opts)
```

## See also

- [SeaweedFS Lance Catalog](./SeaweedFS-Lance-Catalog.md)
- [Spark Lance Integration](./Spark-Lance-Integration.md)
- [DuckDB Lance Integration](./DuckDB-Lance-Integration.md)
- [Lance Maintenance Worker](./Lance-Maintenance-Worker.md) — compaction, index optimization, version cleanup
