---
id: SQL-Queries-on-Message-Queue
title: "SQL Queries on Message Queue"
sidebar_label: "SQL Queries on Message Queue"
---

# SQL Queries on Message Queue

SeaweedFS provides a powerful SQL query engine that allows you to query Message Queue topics using standard SQL syntax. This feature enables analytics, reporting, and data exploration on your message data using familiar SQL tools and PostgreSQL-compatible clients.

## Overview

The SQL query engine bridges the gap between SeaweedFS's Message Queue and traditional SQL databases by providing:

- **PostgreSQL Wire Protocol Compatibility** - Use any PostgreSQL client, tool, or application
- **Real-time + Historical Data** - Query both live messages and archived Parquet data
- **Standard SQL Operations** - SELECT, aggregations, filtering, and schema operations
- **Multiple Interface Options** - Database server mode and interactive CLI
- **Secure Authentication** - MD5, password, and trust authentication methods

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   SQL Clients   │    │  PostgreSQL     │    │  SeaweedFS      │
│   (psql, apps)  │────│  Wire Protocol  │────│  SQL Engine     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                              ┌─────────────────┐
                                              │ Hybrid Scanner  │
                                              │ • Live Messages │
                                              │ • Parquet Files │
                                              └─────────────────┘
```

## Quick Start

### 1. Start the Database Server

```bash
# Start PostgreSQL-compatible database server
weed db -auth=md5 -users='{"admin":"secret","analyst":"readonly"}'

# Or use a JSON file for credentials
echo '{"admin":"secret","analyst":"readonly"}' > users.json
weed db -auth=md5 -users="@users.json" -port=5432
```

### 2. Connect with psql

```bash
# Connect using psql
PGPASSWORD=secret psql -h localhost -p 5432 -U admin -d default

# Or with connection string
psql "postgresql://admin:secret@localhost:5432/default"
```

### 3. Start Querying

```sql
-- List available databases (MQ namespaces)
SHOW DATABASES;

-- Switch to a namespace
USE my_namespace;

-- List tables (MQ topics) 
SHOW TABLES;

-- Query message data
SELECT * FROM user_events WHERE _ts > '2025-01-01' LIMIT 10;

-- Perform basic aggregations
SELECT COUNT(*) as total_events FROM user_events;
```

## Commands and Interfaces

### Database Server Mode (`weed db`)

Starts a PostgreSQL-compatible database server that accepts connections from any PostgreSQL client.

```bash
# Basic usage
weed db

# Production setup with MD5 authentication
weed db -auth=md5 -users="@/etc/seaweedfs/users.json" \
        -host=0.0.0.0 -port=5432

# With TLS encryption
weed db -auth=md5 -users="@users.json" \
        -tls-cert=/etc/ssl/server.crt \
        -tls-key=/etc/ssl/server.key

# Custom configuration
weed db -auth=md5 -users='{"admin":"pass"}' \
        -port=5433 \
        -master=master1:9333 \
        -max-connections=200 \
        -idle-timeout=2h
```

**Options:**
- `-auth`: Authentication method (`trust`, `password`, `md5`)
- `-users`: User credentials (JSON format or file)
- `-host`: Database server host (default: `localhost`)
- `-port`: Database server port (default: `5432`)
- `-master`: SeaweedFS master server address
- `-database`: Default database name
- `-max-connections`: Maximum concurrent connections
- `-idle-timeout`: Connection idle timeout
- `-tls-cert`, `-tls-key`: TLS certificate and key files

### Interactive CLI Mode (`weed sql`)

Provides an interactive SQL shell for quick queries and exploration.

```bash
# Start interactive SQL shell
weed sql -master=localhost:9333

# Connect to specific namespace
weed sql -master=localhost:9333 -namespace=analytics

# Execute single query
weed sql -master=localhost:9333 -exec="SHOW TABLES"
```

## Authentication and Security

### Authentication Methods

1. **`trust`** (Default - Development Only)
   - No authentication required
   - Suitable for local development only

2. **`md5`** (Recommended for Production)
   - Secure MD5 hash + salt authentication
   - Compatible with all PostgreSQL clients
   - Safe even without TLS

3. **`password`** (Development + TLS Only)
   - Clear text password transmission
   - Requires TLS encryption for production use

### Credential Formats

#### JSON Format (Inline)
```bash
weed db -auth=md5 -users='{"admin":"secret","analyst":"readonly"}'

# Supports any special characters
weed db -auth=md5 -users='{"admin":"pass;with;semicolons","user":"pass:with:colons"}'
```

#### File Format (Recommended)
```bash
# Create users file
cat > /etc/seaweedfs/users.json << EOF
{
  "admin": "strong_password_123!",
  "analyst": "readonly_user_456",
  "developer": "dev_access_789"
}
EOF

# Use file-based credentials
weed db -auth=md5 -users="@/etc/seaweedfs/users.json"
```

### TLS Encryption

```bash
# Generate certificates (example)
openssl req -x509 -newkey rsa:2048 -keyout server.key -out server.crt -days 365 -nodes

# Start with TLS
weed db -auth=md5 -users="@users.json" \
        -tls-cert=server.crt -tls-key=server.key
```

## SQL Operations

### Schema Operations

```sql
-- List all databases (MQ namespaces)
SHOW DATABASES;

-- Switch database context
USE namespace_name;

-- List tables in current database (MQ topics)
SHOW TABLES;

-- Describe table schema
DESCRIBE table_name;
SHOW COLUMNS FROM table_name;

-- Note: CREATE TABLE, DROP TABLE and ALTER TABLE are not supported
```

### Data Queries

```sql
-- Basic SELECT
SELECT * FROM user_events LIMIT 10;

-- Filtering with WHERE clauses
SELECT * FROM user_events 
WHERE event_type = 'login' 
  AND _ts > '2025-01-01';

-- Basic aggregations (limited support)
SELECT COUNT(*) FROM user_events;
SELECT MIN(timestamp), MAX(timestamp) FROM user_events;
SELECT SUM(value_column), AVG(value_column) FROM user_events;

-- System columns (available on all topics)
SELECT 
    _ts,            -- Message timestamp (formatted, supports string parsing in WHERE)
    _key,           -- Message key
    _source,        -- Data source (parquet file or live)
    *
FROM user_events;
```

**Note:** The `_ts` system column supports automatic parsing of timestamp strings in WHERE clauses. Supported formats include `'2025-01-01'`, `'2025-01-01T15:30:00Z'`, `'2025-01-01 15:30:00'`, etc. Other timestamp columns require exact value matching.

### Supported WHERE Clause Operations

```sql
-- Comparison operators
SELECT * FROM user_events WHERE user_id = 123;
SELECT * FROM user_events WHERE _ts > '2025-01-01';
SELECT * FROM user_events WHERE value <= 100;

-- Pattern matching
SELECT * FROM user_events WHERE event_type LIKE 'login%';

-- IN clause  
SELECT * FROM user_events WHERE event_type IN ('login', 'logout', 'signup');

-- Combining conditions
SELECT * FROM user_events 
WHERE event_type = 'purchase' 
  AND _ts > '2025-01-01' 
  AND value > 50;
```

### INTERVAL Expressions and Timestamp Arithmetic

```sql
-- Basic INTERVAL expressions
SELECT INTERVAL '1 hour';
SELECT INTERVAL '30 minutes';
SELECT INTERVAL '24 hours';
SELECT INTERVAL '7 days';

-- Timestamp arithmetic with INTERVAL
SELECT NOW() - INTERVAL '1 hour' as one_hour_ago;
SELECT CURRENT_TIMESTAMP - INTERVAL '24 hours' as yesterday;

-- Using INTERVAL in WHERE clauses for time-based filtering
SELECT * FROM user_events 
WHERE _ts >= NOW() - INTERVAL '1 hour';

SELECT * FROM user_events 
WHERE _ts >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
  AND _ts < CURRENT_TIMESTAMP - INTERVAL '1 hour';

-- Supported INTERVAL units
SELECT NOW() - INTERVAL '1 second';
SELECT NOW() - INTERVAL '5 minutes';  
SELECT NOW() - INTERVAL '2 hours';
SELECT NOW() - INTERVAL '3 days';
SELECT NOW() - INTERVAL '1 week';
```

### Limitations

**Not Supported:**
- `ORDER BY` clauses
- `GROUP BY` clauses  
- `HAVING` clauses
- `JOIN` operations
- `CREATE TABLE` statements
- `DROP TABLE` statements
- `ALTER TABLE` statements
- Complex aggregations with grouping
- Window functions
- Subqueries

## Client Examples

### Python (psycopg2)

```python
import psycopg2
import pandas as pd

# Connect to SeaweedFS SQL server
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    user="admin", 
    password="secret",
    database="default"
)

# Query data  
query = """
SELECT event_type, user_id, _ts
FROM user_events 
WHERE _ts > '2025-01-01'
LIMIT 100
"""

# Use pandas for easy data analysis
df = pd.read_sql(query, conn)
print(df)

# Close connection
conn.close()
```

### Java JDBC

```java
import java.sql.*;

public class SeaweedFSQuery {
    public static void main(String[] args) throws SQLException {
        String url = "jdbc:postgresql://localhost:5432/default";
        Connection conn = DriverManager.getConnection(url, "admin", "secret");
        
        String query = "SELECT * FROM user_events LIMIT 10";
        Statement stmt = conn.createStatement();
        ResultSet rs = stmt.executeQuery(query);
        
        while (rs.next()) {
            System.out.println("User ID: " + rs.getInt("user_id"));
            System.out.println("Event: " + rs.getString("event_type"));
            System.out.println("Timestamp: " + rs.getTimestamp("timestamp"));
        }
        
        conn.close();
    }
}
```

### Go (lib/pq)

```go
package main

import (
    "database/sql"
    "fmt"
    "log"
    _ "github.com/lib/pq"
)

func main() {
    connStr := "host=localhost port=5432 user=admin password=secret dbname=default sslmode=disable"
    db, err := sql.Open("postgres", connStr)
    if err != nil {
        log.Fatal(err)
    }
    defer db.Close()
    
    query := "SELECT event_type, user_id, _ts FROM user_events WHERE _ts > '2025-01-01' LIMIT 100"
    rows, err := db.Query(query)
    if err != nil {
        log.Fatal(err)
    }
    defer rows.Close()
    
    for rows.Next() {
        var eventType string
        var userID int
        var timestamp string
        if err := rows.Scan(&eventType, &userID, &timestamp); err != nil {
            log.Fatal(err)
        }
        fmt.Printf("Event: %s, User: %d, Time: %s\n", eventType, userID, timestamp)
    }
}
```

### Node.js (pg)

```javascript
const { Client } = require('pg');

const client = new Client({
  host: 'localhost',
  port: 5432,
  user: 'admin',
  password: 'secret',
  database: 'default'
});

async function queryData() {
  await client.connect();
  
  const query = `
    SELECT event_type, user_id, timestamp
    FROM user_events 
    WHERE timestamp > $1
    LIMIT 100
  `;
  
  const result = await client.query(query, ['2024-01-01']);
  
  console.log('Recent Events:');
  result.rows.forEach(row => {
    console.log(`${row.event_type} by user ${row.user_id} at ${row.timestamp}`);
  });
  
  await client.end();
}

queryData().catch(console.error);
```

## Data Sources and Architecture

### Hybrid Message Scanner

The SQL engine uses a hybrid approach to query both real-time and historical data:

1. **Live Messages** - Queries unflushed messages directly from MQ brokers
2. **Parquet Files** - Queries archived/flushed messages from Parquet storage
3. **Seamless Integration** - Results are merged to provide complete data view

### System Columns

Every topic automatically includes system columns:

- `_ts` - Message timestamp (formatted timestamp)
- `_key` - Message partition key
- `_source` - Data source identifier (parquet file path or "live")

### Schema Evolution

The SQL engine supports backward-compatible schema evolution:
- New columns can be added to existing topics
- Old queries continue to work with new data
- Missing columns return NULL values

## Performance Optimization

### Fast Path Aggregations

The engine optimizes common aggregation queries:

```sql
-- These queries use optimized fast paths
SELECT COUNT(*) FROM user_events;
SELECT MIN(timestamp) FROM user_events;  
SELECT MAX(timestamp) FROM user_events;

-- Add WHERE clauses for more specific queries
SELECT COUNT(*) FROM user_events WHERE event_type = 'login';
```

### Query Best Practices

1. **Use time-based filtering** for large datasets:
   ```sql
   SELECT * FROM events WHERE _ts >= '2025-01-01' AND _ts < '2025-02-01';
   ```

2. **Limit result sets** for exploration:
   ```sql
   SELECT * FROM events WHERE _ts > '2025-01-01' LIMIT 1000;
   ```

3. **Use appropriate indexes** on frequently queried columns (when supported)

4. **Leverage system columns** for debugging:
   ```sql
   SELECT _source, _ts FROM events LIMIT 100;
   ```

## BI Tool Integration

### Apache Superset

```python
# Database URI for Apache Superset
postgresql://admin:secret@localhost:5432/default
```

### Grafana

```yaml
# Grafana datasource configuration
apiVersion: 1
datasources:
  - name: SeaweedFS
    type: postgres
    url: localhost:5432
    database: default
    user: admin
    password: secret
    sslmode: disable
```

### Tableau

Use the PostgreSQL connector with:
- Server: `localhost`
- Port: `5432`
- Database: `default`
- Username: `admin`
- Password: `secret`

## Troubleshooting

### Common Issues

1. **"Database server not running"**
   ```bash
   # Check if weed db is running
   ps aux | grep "weed db"
   
   # Check port availability
   netstat -ln | grep 5432
   ```

2. **"Authentication failed"**
   ```bash
   # Verify user credentials
   cat users.json
   
   # Test with trust authentication
   weed db -auth=trust
   ```

3. **"No data returned"**
   ```sql
   -- Check if topics exist
   SHOW TABLES;
   
   -- Check data sources
   SELECT _source FROM topic_name LIMIT 100;
   
   -- Check timestamp ranges
   SELECT MIN(timestamp), MAX(timestamp) FROM topic_name;
   ```

4. **"Connection timeout"**
   ```bash
   # Increase timeout settings
   weed db -idle-timeout=24h -max-connections=50
   
   # Check network connectivity
   telnet localhost 5432
   ```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
# Set debug mode
export GLOG_v=2

# Start with verbose logging
weed db -auth=md5 -users="@users.json" -v=2
```

### Performance Issues

1. **Slow queries on large datasets**:
   - Add time-based WHERE clauses
   - Use LIMIT for exploration
   - Consider data partitioning strategies

2. **High memory usage**:
   - Reduce concurrent connections
   - Limit result set sizes
   - Monitor broker memory usage

3. **Network timeouts**:
   - Increase idle timeout settings
   - Check network stability between components
   - Use connection pooling in applications

## Production Deployment

### Recommended Setup

```bash
# Production database server
weed db \
  -auth=md5 \
  -users="@/etc/seaweedfs/users.json" \
  -host=0.0.0.0 \
  -port=5432 \
  -master=master1:9333,master2:9333,master3:9333 \
  -max-connections=100 \
  -idle-timeout=1h \
  -tls-cert=/etc/ssl/seaweedfs-db.crt \
  -tls-key=/etc/ssl/seaweedfs-db.key
```

### High Availability

- Run multiple `weed db` instances behind a load balancer
- Use master server failover configuration
- Monitor connection health and query performance
- Implement connection pooling in client applications

### Security Checklist

- [ ] Use MD5 or password authentication (never trust in production)
- [ ] Enable TLS encryption for data in transit
- [ ] Store credentials in secure files with proper permissions
- [ ] Limit database server network access with firewalls
- [ ] Monitor authentication attempts and query patterns
- [ ] Regular security updates and credential rotation

## Related Documentation

- [Seaweed Message Queue](./Seaweed-Message-Queue.md)
- [Security Configuration](./Security-Configuration.md)
- [Production Setup](./Production-Setup.md)
- [System Metrics](./System-Metrics.md)
