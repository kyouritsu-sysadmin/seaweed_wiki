---
id: Dremio-Iceberg-Integration
title: "Dremio Iceberg Integration"
sidebar_label: "Dremio Iceberg Integration"
---

# Dremio Iceberg Integration

Dremio connects to SeaweedFS Iceberg tables using a `RESTCATALOG` source that points to the SeaweedFS Iceberg REST Catalog. Authentication to S3 uses standard access/secret keys; Dremio reaches the data layer over the S3A filesystem.

This page reflects the integration verified by the [Dremio OSS 25.2.0 catalog test](https://github.com/seaweedfs/seaweedfs/tree/master/test/s3tables/catalog_dremio).

## Prerequisites

- Dremio OSS 25.2.0 or later with the experimental REST catalog plugin enabled
- SeaweedFS started as shown in [Setup](#setup) below

In Dremio OSS 25.2 the Iceberg REST catalog source is gated behind a support key. Pass it to the JVM via `DREMIO_JAVA_EXTRA_OPTS`:

```bash
DREMIO_JAVA_EXTRA_OPTS="-Ddremio.debug.sysopt.plugins.restcatalog.enabled=true"
```

## Setup

Start `weed mini` with credentials and a pre-created table bucket via environment variables:

```bash
export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
export S3_TABLE_BUCKET=my-table-bucket

weed mini -dir ~/data
```

This brings up the Iceberg REST Catalog on `http://localhost:8181`, the S3 endpoint on `http://localhost:8333`, an admin S3 identity using the AWS env vars (used as the Dremio source's S3 credentials below), and the table bucket `my-table-bucket` pre-created.

## Configuration

Iceberg REST catalog sources in Dremio are not configured through `dremio.conf`. After Dremio is up, register the source by `POST`ing to `/api/v3/catalog`:

```bash
curl -X POST http://localhost:9047/api/v3/catalog \
  -H "Authorization: _dremio$DREMIO_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "entityType": "source",
    "name": "iceberg",
    "type": "RESTCATALOG",
    "config": {
      "restEndpointUri": "http://host.docker.internal:8181",
      "enableAsync": true,
      "isCachingEnabled": false,
      "maxCacheSpacePct": 100,
      "isRecursiveAllowedNamespaces": true,
      "propertyList": [
        {"name": "warehouse", "value": "s3://my-table-bucket"},
        {"name": "scope", "value": "PRINCIPAL_ROLE:ALL"},
        {"name": "fs.s3a.aws.credentials.provider", "value": "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider"},
        {"name": "fs.s3a.endpoint", "value": "host.docker.internal:8333"},
        {"name": "fs.s3a.path.style.access", "value": "true"},
        {"name": "fs.s3a.connection.ssl.enabled", "value": "false"},
        {"name": "fs.s3a.endpoint.region", "value": "us-east-1"},
        {"name": "dremio.s3.compat", "value": "true"},
        {"name": "dremio.s3.region", "value": "us-east-1"},
        {"name": "dremio.bucket.discovery.enabled", "value": "false"},
        {"name": "fs.s3a.audit.enabled", "value": "false"},
        {"name": "fs.s3a.create.file-status-check", "value": "false"}
      ],
      "secretPropertyList": [
        {"name": "fs.s3a.access.key", "value": "AKIAIOSFODNN7EXAMPLE"},
        {"name": "fs.s3a.secret.key", "value": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"},
        {"name": "credential", "value": "AKIAIOSFODNN7EXAMPLE:wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"}
      ]
    }
  }'
```

Key settings:

- `restEndpointUri` points at the SeaweedFS Iceberg REST Catalog (default `:8181`).
- `warehouse` is `s3://&lt;table-bucket-name&gt;`. SeaweedFS maps this to the bucket of the same name.
- `dremio.s3.compat=true` and `dremio.bucket.discovery.enabled=false` are required for non-AWS S3 endpoints.
- `fs.s3a.path.style.access=true` and `fs.s3a.connection.ssl.enabled=false` match a typical local SeaweedFS deployment.

If Dremio runs in a container and SeaweedFS runs on the host, use `host.docker.internal` (with `--add-host host.docker.internal:host-gateway` on Linux).

## Example SQL

Dremio submits SQL through `/api/v3/sql`, which returns a job ID; poll `/api/v3/job/&lt;id&gt;` for completion and fetch rows from `/api/v3/job/&lt;id&gt;/results`.

The integration test exercises the read path against tables produced by the SeaweedFS REST catalog and populated by PyIceberg (and by extension any other Iceberg writer such as Spark or Trino):

```sql
SELECT * FROM iceberg.my_namespace.events;
SELECT COUNT(*) FROM iceberg.my_namespace.events;
```

Write paths from Dremio (`CREATE TABLE`, `INSERT`) are not exercised by the SeaweedFS test suite as of Dremio OSS 25.2.0. Treat Dremio primarily as a reader against tables produced by Spark, Trino, or other writers.

## Multi-Level Namespaces

SeaweedFS exposes multi-level Iceberg namespaces (e.g. `analytics.web`) through dot-separated namespace names in REST catalog calls. Dremio surfaces them as nested folders under the source. The Dremio integration test exercises this path; no extra source configuration is required beyond `isRecursiveAllowedNamespaces: true` shown above.

## Anonymous Access

When SeaweedFS runs without IAM (e.g. `weed mini` with no `-s3.config`), the REST catalog accepts unsigned requests. The Dremio source still needs S3 credentials for the data path, so leave `fs.s3a.access.key` / `fs.s3a.secret.key` set; SeaweedFS accepts any value when IAM is disabled.

## See Also

- [SeaweedFS Iceberg Catalog](./SeaweedFS-Iceberg-Catalog.md) - Architecture and concepts
- [S3 Table Bucket](./S3-Table-Bucket.md) - Managing table buckets
- [Dremio integration test](https://github.com/seaweedfs/seaweedfs/tree/master/test/s3tables/catalog_dremio) - End-to-end reference
