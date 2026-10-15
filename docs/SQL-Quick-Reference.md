---
id: SQL-Quick-Reference
title: "SQL Quick Reference"
sidebar_label: "SQL Quick Reference"
---

# SQL Quick Reference

Quick reference guide for SeaweedFS SQL queries on Message Queue topics.

## Commands

### Start Database Server
```bash
# Basic (development)
weed db

# Production with MD5 auth
weed db -auth=md5 -users='{"admin":"secret"}' -host=0.0.0.0

# With TLS encryption
weed db -auth=md5 -users="@users.json" -tls-cert=server.crt -tls-key=server.key
```

### Interactive CLI
```bash
# Start SQL shell
weed sql

# Execute single query
weed sql -exec="SHOW TABLES"
```

## Authentication

### Credential Formats
```bash
# JSON inline
-users='{"user1":"pass1","user2":"pass2"}'

# JSON file
-users="@/path/to/users.json"
```

### Auth Methods
- `trust` - No auth (dev only)
- `md5` - Hash + salt (recommended)
- `password` - Clear text (TLS required)

## Client Connections

### psql
```bash
# Basic connection
psql -h localhost -p 5432 -U admin -d default

# With password
PGPASSWORD=secret psql -h localhost -p 5432 -U admin -d default

# Connection string
psql "postgresql://admin:secret@localhost:5432/default"
```

### Programming Languages
```python
# Python
import psycopg2
conn = psycopg2.connect(host="localhost", port=5432, user="admin", password="secret", database="default")
```

```java
// Java
String url = "jdbc:postgresql://localhost:5432/default";
Connection conn = DriverManager.getConnection(url, "admin", "secret");
```

```go
// Go
db, err := sql.Open("postgres", "host=localhost port=5432 user=admin password=secret dbname=default sslmode=disable")
```

## SQL Operations

### Schema Commands
```sql
SHOW DATABASES;                    -- List MQ namespaces
USE namespace_name;                -- Switch database  
SHOW TABLES;                       -- List MQ topics
DESCRIBE table_name;               -- Show table schema
-- Note: CREATE TABLE, DROP TABLE and ALTER TABLE not supported
```

### Query Commands
```sql
-- Basic queries
SELECT * FROM events LIMIT 10;
SELECT * FROM events WHERE _ts > '2025-01-01';
SELECT * FROM events WHERE status IN ('active', 'completed');
SELECT COUNT(*) FROM events;

-- NULL checking operations
SELECT * FROM events WHERE status IS NULL;
SELECT * FROM events WHERE status IS NOT NULL;
SELECT * FROM events WHERE user_id IS NOT NULL AND status = 'active';

-- System columns (available on all tables)
SELECT _ts, _key, _source, * FROM events;

-- Aggregations (optimized)
SELECT COUNT(*) FROM events;
SELECT MIN(timestamp), MAX(timestamp) FROM events;
```

### Time-based Queries
```sql
-- Time filtering with system timestamp column (_ts)
-- Automatic string-to-timestamp conversion for _ts system column
SELECT * FROM events 
WHERE _ts >= '2025-01-01' 
  AND _ts < '2025-02-01' 
LIMIT 1000;

-- INTERVAL expressions and timestamp arithmetic
SELECT NOW() - INTERVAL '1 hour';
SELECT * FROM events WHERE _ts >= NOW() - INTERVAL '24 hours';
SELECT * FROM events WHERE _ts >= CURRENT_TIMESTAMP - INTERVAL '1 day';

-- BETWEEN clauses with INTERVAL arithmetic
SELECT * FROM events WHERE _ts BETWEEN NOW() - INTERVAL '1 week' AND NOW();
SELECT * FROM events WHERE _ts BETWEEN '2025-01-01' AND '2025-12-31';

-- Current time functions
SELECT NOW(), CURRENT_TIMESTAMP, CURRENT_DATE FROM events LIMIT 1;
```

## System Columns

Every topic includes these system columns:
- `_ts` - Message timestamp (formatted timestamp, supports automatic string-to-timestamp conversion in WHERE clauses)
- `_key` - Message partition key  
- `_source` - Data source ("live" or parquet file path)

**Note:** The `_ts` column supports automatic parsing of timestamp strings in WHERE clauses. Formats supported: `'2025-01-01'`, `'2025-01-01T15:30:00Z'`, `'2025-01-01 15:30:00'`, etc.

## NULL Value Handling

### NULL Checking Operations
```sql
-- Check for NULL values
SELECT * FROM events WHERE description IS NULL;

-- Check for non-NULL values  
SELECT * FROM events WHERE user_id IS NOT NULL;

-- Combine with other conditions
SELECT * FROM events 
WHERE user_id IS NOT NULL 
  AND status = 'active' 
  AND _ts >= '2025-01-01';

-- Filter out records with missing data
SELECT * FROM events WHERE user_id IS NOT NULL AND description IS NOT NULL;
```

### NULL Value Semantics
- **Empty strings** are treated as valid values (not NULL)
- **Missing fields** in records are considered NULL
- **Boolean, numeric, and timestamp values** are never NULL once present
- **Bytes values** are treated as non-NULL even if empty
- NULL values are excluded from aggregate functions like `COUNT(column_name)`

## Troubleshooting

### Check Status
```sql
-- Verify tables exist
SHOW TABLES;

-- Check data sources  
SELECT _source FROM table_name LIMIT 100;

-- Verify time range
SELECT MIN(timestamp), MAX(timestamp) FROM table_name;
```

### Common Issues
1. **No data**: Check `SHOW TABLES` and topic names
2. **Auth failed**: Verify credentials in users file
3. **Timeouts**: Increase `-idle-timeout` setting
4. **Slow queries**: Add WHERE clauses and LIMIT
5. **NULL filtering**: Use `IS NULL` / `IS NOT NULL` instead of `= NULL` / `!= NULL`

### Debug Mode
```bash
# Enable verbose logging
export GLOG_v=2
weed db -v=2 ...
```

## Performance Tips

1. **Filter by time** for large datasets:
   ```sql
   WHERE _ts >= '2025-01-01' AND _ts < '2025-02-01'
   ```

2. **Use LIMIT** for exploration:
   ```sql
   SELECT * FROM events WHERE _ts > '2025-01-01' LIMIT 1000
   ```

3. **Fast aggregations** (basic functions only):
   ```sql
   SELECT COUNT(*) FROM events;  -- Optimized
   SELECT MIN(timestamp), MAX(timestamp) FROM events;  -- Optimized  
   ```

4. **Check data sources**:
   ```sql
   SELECT _source, _ts FROM events LIMIT 100;
   ```

5. **Filter NULL values for cleaner results**:
   ```sql
   SELECT * FROM events WHERE user_id IS NOT NULL LIMIT 100;
   ```

## Limitations

**Not Supported:**
- `ORDER BY`, `GROUP BY`, `HAVING` clauses
- `JOIN` operations between tables
- `CREATE TABLE`, `DROP TABLE`, `ALTER TABLE` statements
- Window functions and subqueries  
- Complex aggregations with grouping

## Links

For detailed documentation, see [SQL Queries on Message Queue](./SQL-Queries-on-Message-Queue.md).
