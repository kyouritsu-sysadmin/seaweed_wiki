---
id: Kafka-to-Kafka-Gateway-to-SMQ-to-SQL
title: "Kafka to Kafka Gateway to SMQ to SQL"
sidebar_label: "Kafka to Kafka Gateway to SMQ to SQL"
---

# Kafka client → Kafka gateway → SMQ → SQL

Bring your existing Kafka clients. Point them at the SeaweedFS Kafka gateway. Messages flow into Seaweed Message Queue (SMQ) for streaming, while SeaweedFS persists them into Parquet for SQL analytics.

> See the end-to-end picture: [Structured Data Lake with SMQ and SQL](./Structured-Data-Lake-with-SMQ-and-SQL.md).

## Why use the Kafka gateway

- Keep your Kafka tooling and clients
- Scale stateless brokers and storage independently
- Get streaming + Parquet-based analytics without changing producers

## Architecture

```
Kafka Clients  <=>  SeaweedFS Kafka Gateway  <=>  SMQ Brokers  =>  Subscribers
                                                  \
                                                   +--> SeaweedFS (Parquet) => SQL Engines
```

The gateway speaks the Kafka protocol to clients and maps topics/partitions, offsets, and consumer groups to SMQ semantics.

## What stays the same

- Kafka client libraries and tooling (producers/consumers)
- Topic/partition concepts
- Consumer groups and offsets

## What you gain

- Durable Parquet storage for batch analytics
- One pipeline for both streaming and SQL
- Simple, scalable operations (stateless brokers, disaggregated storage)

## Getting started

1) Start SMQ and the Kafka gateway (example ports):

```bash
weed mq.broker -port=17777 -master=localhost:9333
weed mq.agent  -port=16777 -broker=localhost:17777
weed mq.kafka  -port=19092 -broker=localhost:17777
```

2) Point your Kafka producer/consumer at `localhost:19092`.

3) Query the resulting Parquet data with your SQL engine of choice (Trino, Spark, DuckDB, etc.).

## Next steps

- Central concepts: [Structured Data Lake with SMQ and SQL](./Structured-Data-Lake-with-SMQ-and-SQL.md)
- SMQ overview: [Seaweed Message Queue](./Seaweed-Message-Queue.md)


