---
id: Structured-Data-Lake-with-SMQ-and-SQL
title: "Structured Data Lake with SMQ and SQL"
sidebar_label: "Structured Data Lake with SMQ and SQL"
---

# Structured Data Lake with SMQ and SQL

SeaweedFS + Seaweed Message Queue (SMQ) gives you a unified pipeline: produce structured messages, process them in real time, and query the same data with SQL. Whether producers speak Kafka or a simple pub/sub gRPC API, they both write schematized messages into the same data lake.

## Core ideas

- Schematized messages can be queried directly with SQL (no ETL required)
- SMQ brokers are computation-only nodes and scale linearly with demand
- Structured data is written as messages and can be queried in real time
- Together, SeaweedFS + SMQ form a data lake for structured data (hot streams + Parquet)

## Ingestion paths

Two equivalent ways to ingest structured messages:

- Kafka clients → [Kafka to Kafka Gateway to SMQ to SQL](./Kafka-to-Kafka-Gateway-to-SMQ-to-SQL.md)
- Pub/Sub clients → [Pub-Sub to SMQ to SQL](./Pub-Sub-to-SMQ-to-SQL.md)

Both end up with the same outcomes: live streams for subscribers and Parquet files in SeaweedFS for SQL engines.

## Architecture

```
Producers (Kafka or Pub/Sub)  ==>  SMQ Brokers  ==>  Subscribers (real-time)
                                        \
                                         +--> SeaweedFS (Parquet) ==> SQL Engines
```

## Querying the lake

Point your SQL engines at the Parquet paths:

- Trino/Presto
- Spark SQL
- DuckDB
- ClickHouse (file table engines)

Examples are available in the ingestion pages.

## Operate at scale

- Scale SMQ brokers horizontally; they are stateless computation nodes
- Storage is disaggregated (SeaweedFS) for durable, efficient Parquet files

## Learn more

- Messaging basics: [Seaweed Message Queue](./Seaweed-Message-Queue.md)
- PostgreSQL-compatible server: [PostgreSQL-compatible Server weed db](./PostgreSQL-compatible-Server-weed-db.md)
- Kafka ingestion: [Kafka to Kafka Gateway to SMQ to SQL](./Kafka-to-Kafka-Gateway-to-SMQ-to-SQL.md)
- Pub/Sub ingestion: [Pub-Sub to SMQ to SQL](./Pub-Sub-to-SMQ-to-SQL.md)


