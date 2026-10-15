---
id: DuckDB-Lance-Integration
title: "DuckDB Lance Integration"
sidebar_label: "DuckDB Lance Integration"
---

# DuckDB Lance Integration

DuckDB's [`lance` core extension](https://duckdb.org/docs/stable/core_extensions/lance.html)
reads Lance tables out of a SeaweedFS table bucket **over S3, without the
catalog**. That works because a table bucket's layout is a valid Lance dataset
directory — see [SeaweedFS Lance Catalog](./SeaweedFS-Lance-Catalog.md).

Verified against DuckDB 1.5.5 by the integration suite in
`test/s3tables/catalog_duckdb_lance/`.

## Setup

```sql
INSTALL lance;
LOAD lance;

CREATE SECRET seaweedfs (
    TYPE lance,
    ACCESS_KEY_ID '…',
    SECRET_ACCESS_KEY '…',
    REGION 'us-east-1',
    ENDPOINT 'http://localhost:8333',
    ALLOW_HTTP true,
    VIRTUAL_HOSTED_STYLE_REQUEST false
);
```

Those are object_store's key names, the same ones the namespace vends in
`storage_options`.

## Reading a table

A table created through the catalog lives at `s3://&lt;bucket&gt;/&lt;namespace&gt;/<table>`:

```sql
SELECT count(*) FROM __lance_scan('s3://vectors/ml/embeddings');

SELECT id, title
FROM __lance_scan('s3://vectors/ml/embeddings')
WHERE id < 5;

SELECT id
FROM lance_vector_search('s3://vectors/ml/embeddings', 'vector',
                         [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0], k := 3);
```

## Why `__lance_scan` and not `FROM 's3://…'`

DuckDB's replacement scan — the ergonomic `SELECT * FROM 's3://…'` form —
recognises a Lance dataset **by a `.lance` path suffix**. Tables created through
this catalog do not have one, deliberately: the catalog entry *is* the dataset
directory, a table name may not contain a dot, and a suffix would leak into ARNs
and bucket policies.

```sql
-- a dataset written to a .lance path: recognised
SELECT count(*) FROM 's3://vectors/ml/exported.lance';

-- a table created through the catalog: not recognised
SELECT count(*) FROM 's3://vectors/ml/embeddings';   -- Catalog Error
SELECT count(*) FROM __lance_scan('s3://vectors/ml/embeddings');  -- works
```

## Known limitation

`ATTACH 's3://bucket/namespace' AS ns (TYPE lance)` — the directory-namespace
form in the extension's own documentation — fails in DuckDB 1.5.5 with
`Cannot launch in-memory database in read-only mode`, whatever options are
passed. Use the scan functions above.

## See also

- [SeaweedFS Lance Catalog](./SeaweedFS-Lance-Catalog.md)
- [LanceDB Integration](./LanceDB-Integration.md)
- [Spark Lance Integration](./Spark-Lance-Integration.md)
- [DuckDB Iceberg Integration](./DuckDB-Iceberg-Integration.md)
