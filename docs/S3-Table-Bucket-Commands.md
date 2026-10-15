---
id: S3-Table-Bucket-Commands
title: "S3 Table Bucket Commands"
sidebar_label: "S3 Table Bucket Commands"
---

SeaweedFS supports the S3 Tables API, providing a way to manage table-based data structures with AWS S3 compatibility. This guide provides commands to test the S3 Tables features in SeaweedFS.

## Configuration

### Prerequisites

For AWS CLI and curl commands, configure your environment variables:

```bash
export S3_ENDPOINT=http://localhost:8333
export AWS_ACCESS_KEY_ID=any
export AWS_SECRET_ACCESS_KEY=any
export AWS_DEFAULT_REGION=us-east-1
```

> [!NOTE]
> The `s3tables` service is a relatively new AWS service. Ensure your AWS CLI is up to date (v2.17+ recommended). If `aws s3tables` is not available, use the `curl` commands provided below.

---

## 1. Table Bucket Operations

### Create Table Bucket
**AWS CLI:**
```bash
aws s3tables create-table-bucket --endpoint-url $S3_ENDPOINT --name my-test-bucket
```

**curl:**
```bash
curl -X POST $S3_ENDPOINT/ \
  -H "X-Amz-Target: S3Tables.CreateTableBucket" \
  -H "Content-Type: application/x-amz-json-1.1" \
  -d '{"name": "my-test-bucket"}'
```

> [!NOTE]
> A table bucket holds **one table format**. `format` is a SeaweedFS extension to
> `CreateTableBucket` and accepts `ICEBERG` (the default, and what AWS S3 Tables
> serves) or `LANCE`. Creating a table of another format in a declared bucket is
> refused with 409.
>
> ```bash
> curl -X POST $S3_ENDPOINT/ \
>   -H "X-Amz-Target: S3Tables.CreateTableBucket" \
>   -H "Content-Type: application/x-amz-json-1.1" \
>   -d '{"name": "vectors", "format": "LANCE"}'
> ```
>
> From the shell: `s3tables.bucket -create -name vectors -format LANCE -account 000000000000`
>
> At startup: `weed mini -tableBucket=vectors:LANCE` pre-creates buckets before
> anything connects, each entry `name[:FORMAT]` with an unsuffixed name meaning
> ICEBERG. The same list can come from `S3_TABLE_BUCKET`.
>
> Buckets created before this field existed carry no declaration and keep
> accepting either format. See [SeaweedFS Lance Catalog](./SeaweedFS-Lance-Catalog.md).

---

### List Table Buckets
**AWS CLI:**
```bash
aws s3tables list-table-buckets --endpoint-url $S3_ENDPOINT
```

**curl:**
```bash
curl -X POST $S3_ENDPOINT/ \
  -H "X-Amz-Target: S3Tables.ListTableBuckets" \
  -H "Content-Type: application/x-amz-json-1.1" \
  -d '{}'
```

---

### Get Table Bucket
**AWS CLI:**
```bash
aws s3tables get-table-bucket --endpoint-url $S3_ENDPOINT --table-bucket-arn arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket
```

**curl:**
```bash
curl -X POST $S3_ENDPOINT/ \
  -H "X-Amz-Target: S3Tables.GetTableBucket" \
  -H "Content-Type: application/x-amz-json-1.1" \
  -d '{"tableBucketARN": "arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket"}'
```

---

## 2. Namespace Operations

### Create Namespace
**AWS CLI:**
```bash
aws s3tables create-namespace --endpoint-url $S3_ENDPOINT --table-bucket-arn arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket --namespace my_namespace
```

**curl:**
```bash
curl -X POST $S3_ENDPOINT/ \
  -H "X-Amz-Target: S3Tables.CreateNamespace" \
  -H "Content-Type: application/x-amz-json-1.1" \
  -d '{
    "tableBucketARN": "arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket",
    "namespace": ["my_namespace"]
  }'
```

---

### List Namespaces
**AWS CLI:**
```bash
aws s3tables list-namespaces --endpoint-url $S3_ENDPOINT --table-bucket-arn arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket
```

**curl:**
```bash
curl -X POST $S3_ENDPOINT/ \
  -H "X-Amz-Target: S3Tables.ListNamespaces" \
  -H "Content-Type: application/x-amz-json-1.1" \
  -d '{"tableBucketARN": "arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket"}'
```

---

## 3. Table Operations

### Create Table (Iceberg)
**AWS CLI:**
```bash
aws s3tables create-table --endpoint-url $S3_ENDPOINT --table-bucket-arn arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket --namespace my_namespace --name my_table --format ICEBERG
```

**curl:**
```bash
curl -X POST $S3_ENDPOINT/ \
  -H "X-Amz-Target: S3Tables.CreateTable" \
  -H "Content-Type: application/x-amz-json-1.1" \
  -d '{
    "tableBucketARN": "arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket",
    "namespace": ["my_namespace"],
    "name": "my_table",
    "format": "ICEBERG"
  }'
```

---

### List Tables
**AWS CLI:**
```bash
aws s3tables list-tables --endpoint-url $S3_ENDPOINT --table-bucket-arn arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket --namespace my_namespace
```

**curl:**
```bash
curl -X POST $S3_ENDPOINT/ \
  -H "X-Amz-Target: S3Tables.ListTables" \
  -H "Content-Type: application/x-amz-json-1.1" \
  -d '{
    "tableBucketARN": "arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket",
    "namespace": ["my_namespace"]
  }'
```

---

## 4. Policy and Tagging

### Put Table Bucket Policy
**AWS CLI:**
```bash
aws s3tables put-table-bucket-policy --endpoint-url $S3_ENDPOINT \
  --table-bucket-arn arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket \
  --resource-policy "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":\"*\",\"Action\":\"s3tables:*\",\"Resource\":\"*\"}]}"
```

**curl:**
```bash
curl -X POST $S3_ENDPOINT/ \
  -H "X-Amz-Target: S3Tables.PutTableBucketPolicy" \
  -H "Content-Type: application/x-amz-json-1.1" \
  -d '{
    "tableBucketARN": "arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket",
    "resourcePolicy": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":\"*\",\"Action\":\"s3tables:*\",\"Resource\":\"*\"}]}"
  }'
```

### Get Table Bucket Policy
**AWS CLI:**
```bash
aws s3tables get-table-bucket-policy --endpoint-url $S3_ENDPOINT \
  --table-bucket-arn arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket
```

**curl:**
```bash
curl -X POST $S3_ENDPOINT/ \
  -H "X-Amz-Target: S3Tables.GetTableBucketPolicy" \
  -H "Content-Type: application/x-amz-json-1.1" \
  -d '{"tableBucketARN": "arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket"}'
```

### Tag Resource
**AWS CLI:**
```bash
aws s3tables tag-resource --endpoint-url $S3_ENDPOINT \
  --resource-arn arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket \
  --tags Environment=test,Owner=admin
```

**curl:**
```bash
curl -X POST $S3_ENDPOINT/ \
  -H "X-Amz-Target: S3Tables.TagResource" \
  -H "Content-Type: application/x-amz-json-1.1" \
  -d '{
    "resourceArn": "arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket",
    "tags": {"Environment": "test", "Owner": "admin"}
  }'
```

### List Tags
**AWS CLI:**
```bash
aws s3tables list-tags-for-resource --endpoint-url $S3_ENDPOINT \
  --resource-arn arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket
```

**curl:**
```bash
curl -X POST $S3_ENDPOINT/ \
  -H "X-Amz-Target: S3Tables.ListTagsForResource" \
  -H "Content-Type: application/x-amz-json-1.1" \
  -d '{"resourceArn": "arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket"}'
```

## 5. Maintenance Configuration

Compaction and snapshot management are configured per table; unreferenced file
removal is configured on the table bucket. See
[Iceberg Table Maintenance](./Iceberg-Table-Maintenance.md) for what the worker does
with these settings, and for the table properties that take precedence over them.

### Put Table Maintenance Configuration
**AWS CLI:**
```bash
aws s3tables put-table-maintenance-configuration --endpoint-url $S3_ENDPOINT \
  --table-bucket-arn arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket \
  --namespace my_namespace \
  --name my_table \
  --type icebergCompaction \
  --value '{"status":"enabled","settings":{"icebergCompaction":{"targetFileSizeMB":512,"strategy":"auto"}}}'
```

**curl:**
```bash
curl -X PUT "$S3_ENDPOINT/tables/arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket/my_namespace/my_table/maintenance/icebergCompaction" \
  -H "Content-Type: application/json" \
  -d '{
    "value": {
      "status": "enabled",
      "settings": {"icebergCompaction": {"targetFileSizeMB": 512, "strategy": "auto"}}
    }
  }'
```

Turn a maintenance type off for a table:

```bash
aws s3tables put-table-maintenance-configuration --endpoint-url $S3_ENDPOINT \
  --table-bucket-arn arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket \
  --namespace my_namespace \
  --name my_table \
  --type icebergSnapshotManagement \
  --value '{"status":"disabled"}'
```

### Get Table Maintenance Configuration
**AWS CLI:**
```bash
aws s3tables get-table-maintenance-configuration --endpoint-url $S3_ENDPOINT \
  --table-bucket-arn arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket \
  --namespace my_namespace \
  --name my_table
```

A table that has never been configured returns an empty configuration; the
effective values then come from the worker config.

### Get Table Maintenance Job Status
**AWS CLI:**
```bash
aws s3tables get-table-maintenance-job-status --endpoint-url $S3_ENDPOINT \
  --table-bucket-arn arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket \
  --namespace my_namespace \
  --name my_table
```

Each job type reports `Not_Yet_Run`, `Successful`, `Failed` or `Disabled`, with
the time of the last run.

### Put Table Bucket Maintenance Configuration
**AWS CLI:**
```bash
aws s3tables put-table-bucket-maintenance-configuration --endpoint-url $S3_ENDPOINT \
  --table-bucket-arn arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket \
  --type icebergUnreferencedFileRemoval \
  --value '{"status":"enabled","settings":{"icebergUnreferencedFileRemoval":{"unreferencedDays":3,"nonCurrentDays":10}}}'
```

A file is deleted once it is older than `unreferencedDays` **plus**
`nonCurrentDays` — thirteen days here.

### Get Table Bucket Maintenance Configuration
**AWS CLI:**
```bash
aws s3tables get-table-bucket-maintenance-configuration --endpoint-url $S3_ENDPOINT \
  --table-bucket-arn arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket
```

---

## Cleanup

### Delete Table
**AWS CLI:**
```bash
aws s3tables delete-table --endpoint-url $S3_ENDPOINT \
  --table-bucket-arn arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket \
  --namespace my_namespace \
  --name my_table
```

**curl:**
```bash
curl -X POST $S3_ENDPOINT/ \
  -H "X-Amz-Target: S3Tables.DeleteTable" \
  -H "Content-Type: application/x-amz-json-1.1" \
  -d '{
    "tableBucketARN": "arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket",
    "namespace": ["my_namespace"],
    "name": "my_table"
  }'
```

### Delete Namespace
**AWS CLI:**
```bash
aws s3tables delete-namespace --endpoint-url $S3_ENDPOINT \
  --table-bucket-arn arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket \
  --namespace my_namespace
```

**curl:**
```bash
curl -X POST $S3_ENDPOINT/ \
  -H "X-Amz-Target: S3Tables.DeleteNamespace" \
  -H "Content-Type: application/x-amz-json-1.1" \
  -d '{
    "tableBucketARN": "arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket",
    "namespace": ["my_namespace"]
  }'
```

### Delete Table Bucket
**AWS CLI:**
```bash
aws s3tables delete-table-bucket --endpoint-url $S3_ENDPOINT \
  --table-bucket-arn arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket
```

**curl:**
```bash
curl -X POST $S3_ENDPOINT/ \
  -H "X-Amz-Target: S3Tables.DeleteTableBucket" \
  -H "Content-Type: application/x-amz-json-1.1" \
  -d '{"tableBucketARN": "arn:aws:s3tables:us-east-1:000000000000:bucket/my-test-bucket"}'
```
