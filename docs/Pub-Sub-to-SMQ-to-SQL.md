---
id: Pub-Sub-to-SMQ-to-SQL
title: "Pub Sub to SMQ to SQL"
sidebar_label: "Pub Sub to SMQ to SQL"
---

# Pub/Sub to SMQ to SQL: From Streams to Tables

Seaweed Message Queue (SMQ) bridges your live pub/sub streams and your analytical world. You publish structured messages, SMQ brokers stream them in real time, and at the same time SeaweedFS persists them into Parquet files so you can query with SQL engines later.

> New here? See the bigger picture: [Structured Data Lake with SMQ and SQL](./Structured-Data-Lake-with-SMQ-and-SQL.md).

## Why this matters

- Real-time and batch in one pipeline: stream to subscribers now, query with SQL later.
- Store once, use twice: messages land in Parquet (columnar, compressed), great for analytics.
- Stateless brokers, disaggregated storage: scale brokers independently of storage.

## Architecture at a glance

```
Publishers  =>  SMQ Agent (gRPC)  =>  SMQ Brokers  =>  Subscribers
                                 \
                                  +--> SeaweedFS (Parquet) => SQL Engines
```

- **Publish**: Send structured messages with a schema.
- **Stream**: Subscribers process messages with consumer groups and offsets.
- **Persist**: Messages are compacted/organized into Parquet files in SeaweedFS.
- **Query**: Point your SQL engines to the Parquet location.

## What you publish

Messages are structured records defined by a schema. SMQ validates these on publish and keeps ordering guarantees per key while enabling high concurrency via a sliding window.

## What you query

Parquet files written by SMQ are queryable by your favorite SQL engines:

- Trino/Presto
- Spark SQL
- DuckDB
- ClickHouse (via file table engines)

Point them to the Parquet path in SeaweedFS and query away.

## Quick start

1) Start a broker and an agent:

```bash
weed mq.broker -port=17777 -master=localhost:9333
weed mq.agent  -port=16777 -broker=localhost:17777
```

2) Define a schema and publish:

```go
type MyEvent struct {
    Key    []byte
    UserId int64
    Action string
}
```

3) Subscribe in real time. Your consumers get the stream; your data team gets Parquet.

## Where to go next

- Central concepts: [Structured Data Lake with SMQ and SQL](./Structured-Data-Lake-with-SMQ-and-SQL.md)
- Messaging basics: [Seaweed Message Queue](./Seaweed-Message-Queue.md)


