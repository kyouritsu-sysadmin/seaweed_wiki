---
id: Environment-Variables
title: "Environment Variables"
sidebar_label: "Environment Variables"
---

# Environment Variables
You can use environment variables instead of arguments for `weed`.  
For example:  
instead of `weed master -port 5000 -mdir /tmp -volumePreallocate -ip.bind 0.0.0.0` you can use
```shell
export IP_BIND=0.0.0.0
export PORT=5000
export MDIR=/tmp
export VOLUMEPREALLOCATE=true # or export VOLUMEPREALLOCATE=
weed master
```

# Weed prefix
For `v`, `logtostderr`, `stderrthreshold`, `vmoudle`, `options`, `logdir`, `alsologtostderr`, `log_backtrace_at` , and `config_dir` you have to use `WEED_` as prefix for environment variable like this `WEED_CONFIG_DIR=/tmp`

## Configuration File Settings
For configuration file settings (like filer stores, replication settings, etc.), you must use the `WEED_` prefix with dots (`.`) replaced by underscores (`_`).

For example, the `filer.toml` configuration:
```toml
[redis2]
enabled = true
address = "localhost:6379"
password = "secret"
database = 0
```

Becomes these environment variables:
```shell
WEED_REDIS2_ENABLED=true
WEED_REDIS2_ADDRESS=localhost:6379
WEED_REDIS2_PASSWORD=secret
WEED_REDIS2_DATABASE=0
```

# S3 Admin Credentials
For S3 API server authentication, see the dedicated **[S3 Credentials](./S3-Credentials.md)** page which covers:
- Configuration file setup (highest priority)
- Filer configuration (medium priority) 
- Environment variables as fallback (lowest priority)
- AWS standard environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
- Complete authentication examples and troubleshooting

# Security Configuration (security.toml)

The same `WEED_` prefix convention works for `security.toml`, allowing you to keep secrets out of config files entirely. This is the recommended approach for systems where configuration is stored in version control (e.g., NixOS, GitOps workflows).

### JWT Signing Keys
```shell
# Volume server JWT keys
WEED_JWT_SIGNING_KEY=your-secret-key
WEED_JWT_SIGNING_READ_KEY=your-read-secret-key
WEED_JWT_SIGNING_EXPIRES_AFTER_SECONDS=10

# Filer JWT keys
WEED_JWT_FILER_SIGNING_KEY=your-filer-secret-key
WEED_JWT_FILER_SIGNING_READ_KEY=your-filer-read-secret-key
WEED_JWT_FILER_SIGNING_EXPIRES_AFTER_SECONDS=10
```

### gRPC mTLS
```shell
WEED_GRPC_CA=/path/to/ca.crt
WEED_GRPC_VOLUME_CERT=/path/to/volume.crt
WEED_GRPC_VOLUME_KEY=/path/to/volume.key
WEED_GRPC_MASTER_CERT=/path/to/master.crt
WEED_GRPC_MASTER_KEY=/path/to/master.key
WEED_GRPC_FILER_CERT=/path/to/filer.crt
WEED_GRPC_FILER_KEY=/path/to/filer.key
WEED_GRPC_CLIENT_CERT=/path/to/client.crt
WEED_GRPC_CLIENT_KEY=/path/to/client.key
```

### HTTPS
```shell
WEED_HTTPS_CLIENT_ENABLED=true
WEED_HTTPS_CLIENT_CERT=/path/to/client.crt
WEED_HTTPS_CLIENT_KEY=/path/to/client.key
WEED_HTTPS_CLIENT_CA=/path/to/ca.crt
```

### SSE-S3 Encryption Key (KEK)

These map to the `[s3.sse]` section of `security.toml`:

```shell
# Option A: hex-encoded 256-bit key (same format as /etc/s3/sse_kek).
# Maps to: s3.sse.kek in security.toml
WEED_S3_SSE_KEK=$(openssl rand -hex 32)

# Option B: any secret string. A 256-bit key is derived via HKDF-SHA256.
# Maps to: s3.sse.key in security.toml
WEED_S3_SSE_KEY=my-secret-passphrase
```

Only one may be set. See [Server-Side-Encryption](./Server-Side-Encryption.md) for details.

For full details, see [Security Configuration](./Security-Configuration.md).

# Docker
You can set environment variables easily in Docker:
```shell
docker run --name master -d -p 9333:9333 -p 19333:19333 \
  -e MDIR="/data" -e PORT="9333" \
  chrislusf/seaweedfs:latest \
  master 
```

## Docker Compose with Environment Variables
```yaml
version: '3.9'
services:
  master:
    image: chrislusf/seaweedfs:latest
    ports:
      - 9333:9333
      - 19333:19333
    environment:
      IP_BIND: 0.0.0.0
      MDIR: /data
      PORT: 9333
      VOLUMEPREALLOCATE: 'true'
      # or `VOLUMEPREALLOCATE:`
    entrypoint: weed
    command: master 

  filer:
    image: chrislusf/seaweedfs:latest
    ports:
      - 8888:8888
    environment:
      # ... other filer environment variables
    entrypoint: weed
    command: filer -master=master:9333
  
  s3:
    image: chrislusf/seaweedfs:latest
    ports:
      - 8333:8333
    environment:
      AWS_ACCESS_KEY_ID: s3admin
      AWS_SECRET_ACCESS_KEY: s3secret
    entrypoint: weed
    command: s3 -filer=filer:8888
    depends_on:
      - filer
```

# Filer Metadata Store Configuration

The filer supports multiple metadata storage backends. You can configure them using environment variables instead of a `filer.toml` file.

## Redis Configuration

### Basic Redis (`redis2`)
```yaml
version: '3.9'
services:
  redis:
    image: redis:7-alpine
    ports:
      - 6379:6379
    command: redis-server --requirepass your_password

  master:
    image: chrislusf/seaweedfs:latest
    ports:
      - 9333:9333
    command: master

  volume:
    image: chrislusf/seaweedfs:latest
    ports:
      - 8080:8080
    command: volume -master=master:9333
    depends_on:
      - master

  filer:
    image: chrislusf/seaweedfs:latest
    ports:
      - 8888:8888
    environment:
      # Enable Redis as metadata store
      - WEED_REDIS2_ENABLED=true
      - WEED_REDIS2_ADDRESS=redis:6379
      - WEED_REDIS2_PASSWORD=your_password
      - WEED_REDIS2_DATABASE=0
      # Optional: TLS configuration
      - WEED_REDIS2_ENABLE_TLS=false
      # Disable default leveldb2
      - WEED_LEVELDB2_ENABLED=false
    command: filer -master=master:9333
    depends_on:
      - master
      - volume
      - redis
```

### Redis Sentinel
```shell
WEED_REDIS2_SENTINEL_ENABLED=true
WEED_REDIS2_SENTINEL_ADDRESSES=sentinel1:26379,sentinel2:26379,sentinel3:26379
WEED_REDIS2_SENTINEL_MASTERNAME=mymaster
WEED_REDIS2_SENTINEL_USERNAME=
WEED_REDIS2_SENTINEL_PASSWORD=secret
WEED_REDIS2_SENTINEL_DATABASE=0
WEED_LEVELDB2_ENABLED=false
```

### Redis Cluster
```shell
WEED_REDIS_CLUSTER2_ENABLED=true
WEED_REDIS_CLUSTER2_ADDRESSES=redis1:6379,redis2:6379,redis3:6379
WEED_REDIS_CLUSTER2_PASSWORD=secret
WEED_REDIS_CLUSTER2_READONLY=false
WEED_REDIS_CLUSTER2_ROUTEBYLATENCY=false
WEED_LEVELDB2_ENABLED=false
```

## MySQL/MariaDB Configuration
```yaml
version: '3.9'
services:
  mysql:
    image: mysql:8
    ports:
      - 3306:3306
    environment:
      - MYSQL_ROOT_PASSWORD=secret
      - MYSQL_DATABASE=seaweedfs
      - MYSQL_USER=seaweedfs
      - MYSQL_PASSWORD=secret

  master:
    image: chrislusf/seaweedfs:latest
    ports:
      - 9333:9333
    command: master

  volume:
    image: chrislusf/seaweedfs:latest
    ports:
      - 8080:8080
    command: volume -master=master:9333
    depends_on:
      - master

  filer:
    image: chrislusf/seaweedfs:latest
    ports:
      - 8888:8888
    environment:
      # MySQL configuration
      - WEED_MYSQL_ENABLED=true
      - WEED_MYSQL_HOSTNAME=mysql
      - WEED_MYSQL_PORT=3306
      - WEED_MYSQL_DATABASE=seaweedfs
      - WEED_MYSQL_USERNAME=seaweedfs
      - WEED_MYSQL_PASSWORD=secret
      - WEED_MYSQL_CONNECTION_MAX_IDLE=5
      - WEED_MYSQL_CONNECTION_MAX_OPEN=75
      - WEED_MYSQL_CONNECTION_MAX_LIFETIME_SECONDS=600
      - WEED_MYSQL_INTERPOLATEPARAMS=true
      # Disable default leveldb2
      - WEED_LEVELDB2_ENABLED=false
    command: filer -master=master:9333
    depends_on:
      - master
      - volume
      - mysql
```

## PostgreSQL Configuration
```shell
WEED_POSTGRES_ENABLED=true
WEED_POSTGRES_HOSTNAME=postgres
WEED_POSTGRES_PORT=5432
WEED_POSTGRES_DATABASE=seaweedfs
WEED_POSTGRES_USERNAME=seaweedfs
WEED_POSTGRES_PASSWORD=secret
WEED_POSTGRES_SSLMODE=disable
WEED_POSTGRES_CONNECTION_MAX_IDLE=5
WEED_POSTGRES_CONNECTION_MAX_OPEN=75
WEED_POSTGRES_CONNECTION_MAX_LIFETIME_SECONDS=600
WEED_LEVELDB2_ENABLED=false
```

## MongoDB Configuration
```shell
WEED_MONGODB_ENABLED=true
WEED_MONGODB_URI=mongodb://mongodb:27017
WEED_MONGODB_DATABASE=seaweedfs
WEED_MONGODB_USERNAME=seaweedfs
WEED_MONGODB_PASSWORD=secret
WEED_LEVELDB2_ENABLED=false
```

## Etcd Configuration
```shell
WEED_ETCD_ENABLED=true
WEED_ETCD_SERVERS=etcd1:2379,etcd2:2379,etcd3:2379
WEED_ETCD_KEY_PREFIX=seaweedfs.
WEED_ETCD_TIMEOUT=3s
WEED_LEVELDB2_ENABLED=false
```

## Important Notes

1. **Only one store can be enabled**: Make sure to disable the default `leveldb2` store when using an external metadata store:
   ```shell
   WEED_LEVELDB2_ENABLED=false
   ```

2. **Available stores**: To see all available filer stores and their configuration options, run:
   ```shell
   weed scaffold -config=filer
   ```

3. **Data migration**: Changing stores doesn't automatically migrate existing data. Apply these configurations to new installations or migrate data manually.

4. **Array values**: For configuration options that accept arrays (like Redis cluster addresses), use comma-separated values:
   ```shell
   WEED_REDIS_CLUSTER2_ADDRESSES=host1:6379,host2:6379,host3:6379
   ```
