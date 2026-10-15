---
id: PostgreSQL-compatible-Server-weed-db
title: "PostgreSQL compatible Server weed db"
sidebar_label: "PostgreSQL compatible Server weed db"
---

# PostgreSQL-compatible Server (weed db)

SeaweedFS exposes a PostgreSQL wire protocol server so you can connect with any PostgreSQL client (psql, JDBC/ODBC, BI tools) and run SQL over Seaweed Message Queue (SMQ) topics. It is read-only and designed for analytics: query live streams and Parquet-backed history without ETL.

## What you get

- PostgreSQL wire protocol compatibility (psql, JDBC/ODBC, BI tools)
- Query live + historical data (hybrid scanner: brokers + Parquet files)
- Simple ops: stateless server, MD5 auth, optional TLS
- Works alongside pub/sub and Kafka ingestion — one structured data lake

## Start the server

```bash
# Development (no auth)
weed db

# Production (MD5 auth)
weed db -auth=md5 -users='{"admin":"secret","analyst":"readonly"}' -host=0.0.0.0 -port=5432

# Credentials from file (recommended)
echo '{"admin":"secret","analyst":"readonly"}' > /etc/seaweedfs/users.json
weed db -auth=md5 -users="@/etc/seaweedfs/users.json"

# With TLS
auth_users='@/etc/seaweedfs/users.json'
weed db -auth=md5 -users="$auth_users" -tls-cert=/etc/ssl/server.crt -tls-key=/etc/ssl/server.key
```

Key options:
- `-auth`: `trust` (dev), `password`, `md5` (recommended)
- `-users`: inline JSON or `@/path/to/users.json`
- `-master`: SeaweedFS master (comma-separated for HA)
- `-max-connections`, `-idle-timeout`, `-database`
- `-tls-cert`, `-tls-key` for encrypted connections

## Connect with clients

```bash
# psql
PGPASSWORD=secret psql -h localhost -p 5432 -U admin -d default
psql "postgresql://admin:secret@localhost:5432/default"
```

```java
// JDBC
String url = "jdbc:postgresql://localhost:5432/default";
Connection conn = DriverManager.getConnection(url, "admin", "secret");
```

```python
# psycopg2
import psycopg2
conn = psycopg2.connect(host="localhost", port=5432, user="admin", password="secret", database="default")
```

BI tools: use the native PostgreSQL connector (host, port 5432, database `default`, user/password).

## SQL you can run

Schema/navigation:
```sql
SHOW DATABASES;         -- MQ namespaces
USE my_namespace;       -- switch database
SHOW TABLES;            -- topics in namespace
DESCRIBE topic_name;    -- schema
```

Queries (read-only):
```sql
SELECT * FROM events LIMIT 10;
SELECT * FROM events WHERE _ts >= '2025-01-01' LIMIT 1000;
SELECT COUNT(*) FROM events;                -- fast-path optimized
SELECT MIN(timestamp), MAX(timestamp) FROM events;  -- fast-path

-- System columns available on all tables
SELECT _ts, _key, _source, * FROM events LIMIT 5;
```

Notes:
- `_ts` supports convenient string-to-timestamp parsing in WHERE clauses
- Live + Parquet results are merged transparently

## Limitations (current)

- Read-only: no INSERT/UPDATE/DELETE, no DDL (CREATE/DROP/ALTER)
- Not supported yet: `JOIN`, `ORDER BY`, `GROUP BY`, `HAVING`, window functions, subqueries

## Operations and scaling

- Stateless server; run multiple `weed db` instances behind a load balancer
- Use MD5 auth and TLS in production
- Tune `-max-connections` and `-idle-timeout`

## How this fits your data lake

- Producers (Kafka or pub/sub) write schematized messages into SMQ
- SeaweedFS persists to Parquet; brokers serve live data
- PostgreSQL-compatible server exposes SQL over both — one data lake

## Related

- [Structured Data Lake with SMQ and SQL](./Structured-Data-Lake-with-SMQ-and-SQL.md)
- [SQL Queries on Message Queue](./SQL-Queries-on-Message-Queue.md)
- [SQL Quick Reference](./SQL-Quick-Reference.md)
- [Seaweed Message Queue](./Seaweed-Message-Queue.md)
