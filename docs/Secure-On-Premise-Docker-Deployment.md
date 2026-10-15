---
id: Secure-On-Premise-Docker-Deployment
title: "Secure On Premise Docker Deployment"
sidebar_label: "Secure On Premise Docker Deployment"
---

# Secure On-Premise SeaweedFS Deployment with Docker

This guide provides a comprehensive, production-hardened blueprint for deploying SeaweedFS on-premises using **Docker** and **Docker Compose**. It implements defense-in-depth security including **gRPC Mutual TLS (mTLS)**, **JWT data plane authorization**, **strict IAM credentials**, **disabled public UIs**, and **HTTPS reverse proxying via Nginx**.

---

## 🛡️ Architecture & Threat Model

In an on-premise production deployment, SeaweedFS components are divided into an **internal trusted control plane** and an **authenticated public/LAN perimeter**:

```
                              [ Corporate LAN / Clients ]
                                          │
                                   (HTTPS :443)
                                          ▼
                         ┌─────────────────────────────────┐
                         │   Nginx Ingress Reverse Proxy   │
                         │   (TLS Termination & Headers)   │
                         └────────────────┬────────────────┘
                                          │
                            (Internal Docker Network)
                                          │
                     ┌────────────────────┼────────────────────┐
                     │                    │                    │
                     ▼                    ▼                    ▼
             ┌───────────────┐    ┌───────────────┐    ┌───────────────┐
             │  S3 Gateway   │    │  WebDAV/SFTP  │    │   Filer UI    │
             │  (Auth & IAM) │    │  (Restricted) │    │  (Auth Only)  │
             └───────┬───────┘    └───────┬───────┘    └───────┬───────┘
                     │                    │                    │
                     └────────────────────┼────────────────────┘
                                          │
                               (gRPC mTLS + JWT Auth)
                                          │
                     ┌────────────────────┴────────────────────┐
                     │                                         │
                     ▼                                         ▼
             ┌───────────────┐                         ┌───────────────┐
             │ Filer Server  │                         │ Master Server │
             │  (LevelDB/PG) │                         │  (Raft/Coord) │
             └───────┬───────┘                         └───────┬───────┘
                     │                                         │
                     └────────────────────┬────────────────────┘
                                          │
                               (gRPC mTLS + JWT Auth)
                                          │
                     ┌────────────────────┴────────────────────┐
                     ▼                                         ▼
             ┌───────────────┐                         ┌───────────────┐
             │ Volume Node 1 │                         │ Volume Node 2 │
             │ (/data/disk1) │                         │ (/data/disk2) │
             └───────────────┘                         └───────────────┘
```

### Network Isolation Policy

| Component | Port | Network Exposure | Security Controls |
| :--- | :--- | :--- | :--- |
| **Nginx Ingress** | `443` | Corporate LAN / Clients | TLS 1.3/1.2, Strong Ciphers, Strict Headers, Rate Limiting |
| **S3 API** | `8333` | Internal Docker Network only | AWS SigV4, Strict Access Keys, Disabled Anonymous |
| **Filer REST / UI** | `8888` | Internal Docker Network only | JWT Filer Signing, Directory Metadata Disabled |
| **Filer gRPC** | `18888`| Internal Docker Network only | Mutual TLS (mTLS) with Root CA validation |
| **Master HTTP** | `9333` | Internal Docker Network only | Read-only status, UI disabled or restricted |
| **Master gRPC** | `19333`| Internal Docker Network only | Mutual TLS (mTLS) with Root CA validation |
| **Volume HTTP** | `8080` | Internal Docker Network only | JWT token validation required for writes & reads |
| **Volume gRPC** | `18080`| Internal Docker Network only | Mutual TLS (mTLS) with Root CA validation |

---

## 📁 Directory Structure

Create a dedicated directory on your Docker host (e.g. `/opt/seaweedfs-onprem`):

```bash
mkdir -p /opt/seaweedfs-onprem/{certs,config,nginx/certs,data/master,data/volume1,data/volume2,data/filer}
cd /opt/seaweedfs-onprem
```

The resulting folder structure will look like this:

```
/opt/seaweedfs-onprem/
├── .env                         # Secrets (JWT keys, passwords)
├── docker-compose.yml           # Production Docker Compose definition
├── certs/
│   ├── generate-certs.sh        # Automated OpenSSL CA & mTLS script
│   ├── ca.crt / ca.key          # Internal Root Certificate Authority
│   ├── master.crt / master.key  # Master mTLS certificates
│   ├── volume.crt / volume.key  # Volume mTLS certificates
│   ├── filer.crt / filer.key    # Filer mTLS certificates
│   └── client.crt / client.key  # Client/S3 mTLS certificates
├── config/
│   ├── security.toml            # Hardened security configuration
│   ├── filer.toml               # Filer store backend settings
│   └── s3_config.json           # S3 IAM users and bucket permissions
└── nginx/
    ├── nginx.conf               # Hardened reverse proxy configuration
    └── certs/                   # Public HTTPS certificates (e.g. wildcard or corporate cert)
        ├── s3.crt
        └── s3.key
```

---

## 🔑 Step 1: Generate Internal mTLS Certificates & Secrets

SeaweedFS uses mutual TLS (mTLS) for all control plane gRPC communications. Neither the master, filer, nor volume servers will accept connections unless the client presents a certificate signed by the trusted internal CA.

Create `certs/generate-certs.sh`:

```bash
cat << 'EOF' > certs/generate-certs.sh
#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "=== 1. Creating Root Certificate Authority (CA) ==="
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 -out ca.crt \
  -subj "/CN=SeaweedFS-Internal-CA/O=Internal/C=US"

create_cert() {
  local name="$1"
  local cn="$2"
  local san="$3"

  echo "=== Generating Certificate for ${name} (${cn}) ==="
  openssl genrsa -out "${name}.key" 2048
  openssl req -new -key "${name}.key" -out "${name}.csr" \
    -subj "/CN=${cn}/O=Internal/C=US"

  cat << SANEOF > "${name}.ext"
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
subjectAltName = ${san}
SANEOF

  openssl x509 -req -in "${name}.csr" -CA ca.crt -CAkey ca.key \
    -CAcreateserial -out "${name}.crt" -days 1825 -sha256 \
    -extfile "${name}.ext"

  rm -f "${name}.csr" "${name}.ext"
}

# Create certificates for components with Docker DNS Subject Alternative Names
create_cert "master" "master" "DNS:master,DNS:localhost,IP:127.0.0.1"
create_cert "volume" "volume" "DNS:volume1,DNS:volume2,DNS:localhost,IP:127.0.0.1"
create_cert "filer"  "filer"  "DNS:filer,DNS:localhost,IP:127.0.0.1"
create_cert "client" "client" "DNS:s3,DNS:localhost,IP:127.0.0.1"

# Restrict permissions
chmod 600 *.key
chmod 644 *.crt

echo "=== All mTLS Certificates Successfully Generated ==="
EOF

chmod +x certs/generate-certs.sh
./certs/generate-certs.sh
```

### Self-Signed HTTPS Cert for Nginx (or use Corporate/Let's Encrypt Cert)

For local testing or internal LAN, generate the public HTTPS certificate for Nginx:

```bash
openssl req -x509 -nodes -days 730 -newkey rsa:2048 \
  -keyout nginx/certs/s3.key -out nginx/certs/s3.crt \
  -subj "/CN=s3.mycorp.internal/O=MyCorp/C=US" \
  -addext "subjectAltName=DNS:s3.mycorp.internal,DNS:localhost,IP:127.0.0.1"

chmod 600 nginx/certs/s3.key
chmod 644 nginx/certs/s3.crt
```

---

## 🔒 Step 2: Configure Environment Secrets (`.env`)

Generate cryptographically secure random keys for JWT signing:

```bash
cat << EOF > .env
# Cryptographic JWT Signing Keys (Master <-> Volume)
JWT_SIGNING_KEY=$(openssl rand -base64 32)
JWT_SIGNING_READ_KEY=$(openssl rand -base64 32)

# Cryptographic JWT Signing Keys (Filer <-> Clients/S3)
JWT_FILER_SIGNING_KEY=$(openssl rand -base64 32)
JWT_FILER_SIGNING_READ_KEY=$(openssl rand -base64 32)

# S3 Admin Credentials
S3_ADMIN_ACCESS_KEY=$(openssl rand -hex 12)
S3_ADMIN_SECRET_KEY=$(openssl rand -base64 24)

# S3 Application User Credentials
S3_APP_ACCESS_KEY=$(openssl rand -hex 12)
S3_APP_SECRET_KEY=$(openssl rand -base64 24)
EOF
```

---

## ⚙️ Step 3: Hardened Configuration Files

### 1. `config/security.toml`

This file enforces mTLS on gRPC, specifies the JWT keys, disables public directory listings, and disables the unauthenticated volume web UI:

```toml
# config/security.toml

[cors.allowed_origins]
values = "https://s3.mycorp.internal,https://localhost"

# JWT token validation for volume writes (Master generates, Volume verifies)
[jwt.signing]
key = "${WEED_JWT_SIGNING_KEY}"
expires_after_seconds = 10

# JWT token validation for volume reads
[jwt.signing.read]
key = "${WEED_JWT_SIGNING_READ_KEY}"
expires_after_seconds = 10

# Disable unauthenticated Volume Server Web UI
[access]
ui = false

# Disable unauthenticated Filer directory metadata browsing
[filer.expose_directory_metadata]
enabled = false

# JWT validation for Filer writes (S3 generates, Filer verifies)
[jwt.filer_signing]
key = "${WEED_JWT_FILER_SIGNING_KEY}"
expires_after_seconds = 10

# JWT validation for Filer reads
[jwt.filer_signing.read]
key = "${WEED_JWT_FILER_SIGNING_READ_KEY}"
expires_after_seconds = 10

# Mutual TLS (mTLS) for all gRPC control plane operations
[grpc]
ca = "/etc/seaweedfs/certs/ca.crt"

[grpc.master]
cert = "/etc/seaweedfs/certs/master.crt"
key = "/etc/seaweedfs/certs/master.key"

[grpc.volume]
cert = "/etc/seaweedfs/certs/volume.crt"
key = "/etc/seaweedfs/certs/volume.key"

[grpc.filer]
cert = "/etc/seaweedfs/certs/filer.crt"
key = "/etc/seaweedfs/certs/filer.key"

[grpc.s3]
cert = "/etc/seaweedfs/certs/client.crt"
key = "/etc/seaweedfs/certs/client.key"

[grpc.client]
cert = "/etc/seaweedfs/certs/client.crt"
key = "/etc/seaweedfs/certs/client.key"

# Trusted reverse proxies for X-Forwarded-For IP resolution in S3 bucket policies
[s3.trusted_proxies]
white_list = "172.20.0.0/16,127.0.0.1"
```

### 2. `config/s3_config.json`

Disables anonymous access and configures distinct identities for administration and applications with least-privilege action permissions:

```json
{
  "identities": [
    {
      "name": "cluster_admin",
      "credentials": [
        {
          "accessKey": "${S3_ADMIN_ACCESS_KEY}",
          "secretKey": "${S3_ADMIN_SECRET_KEY}"
        }
      ],
      "actions": [
        "Admin",
        "Read",
        "Write",
        "List",
        "Tagging"
      ]
    },
    {
      "name": "app_user",
      "credentials": [
        {
          "accessKey": "${S3_APP_ACCESS_KEY}",
          "secretKey": "${S3_APP_SECRET_KEY}"
        }
      ],
      "actions": [
        "Read",
        "Write",
        "List"
      ]
    }
  ]
}
```

> ⚠️ **Security Alert**: Notice that no identity named `anonymous` is defined. This ensures that any unauthenticated S3 request is rejected with `403 Access Denied`.

### 3. `config/filer.toml`

Configures the metadata storage backend. For single-server on-premise setups, the embedded LevelDB2 is high-performance and lightweight. For multi-node distributed HA, uncomment PostgreSQL or Redis.

```toml
# config/filer.toml

# Embedded LevelDB2 for fast, zero-dependency on-premise local metadata
[leveldb2]
enabled = true
dir = "/data/filer"

# Optional: For clustered PostgreSQL metadata store:
# [postgres]
# enabled = false
# hostname = "postgres"
# port = 5432
# username = "seaweed"
# password = "secretpassword"
# database = "seaweed_filer"
# sslmode = "disable"
# connection_max_idle = 10
# connection_max_open = 100
```

---

## 🌐 Step 4: Nginx TLS Reverse Proxy (`nginx/nginx.conf`)

SeaweedFS S3 is streaming-heavy. Nginx must disable request buffering (`proxy_request_buffering off`) so that multi-gigabyte uploads stream directly to SeaweedFS without filling disk caches or causing signature mismatch errors:

```nginx
# nginx/nginx.conf

events {
    worker_connections 2048;
}

http {
    include       mime.types;
    default_type  application/octet-stream;

    # Performance optimizations
    sendfile        on;
    tcp_nopush      on;
    tcp_nodelay     on;
    keepalive_timeout 65;

    # Upstream S3 Gateway service inside the Docker network
    upstream seaweedfs_s3_backend {
        server s3:8333;
        keepalive 32;
    }

    server {
        listen 443 ssl http2;
        server_name s3.mycorp.internal localhost;

        # TLS Hardening
        ssl_certificate     /etc/nginx/certs/s3.crt;
        ssl_certificate_key /etc/nginx/certs/s3.key;
        ssl_protocols       TLSv1.2 TLSv1.3;
        ssl_ciphers         HIGH:!aNULL:!MD5:!3DES;
        ssl_prefer_server_ciphers on;
        ssl_session_cache   shared:SSL:10m;
        ssl_session_timeout 1d;

        # Security Headers
        add_header X-Content-Type-Options nosniff;
        add_header X-Frame-Options DENY;
        add_header X-XSS-Protection "1; mode=block";

        # Max payload: 0 disables client body size check for large multipart uploads
        client_max_body_size 0;

        # CRITICAL for S3 Streaming Uploads:
        proxy_buffering off;
        proxy_request_buffering off;
        chunked_transfer_encoding off;

        location / {
            proxy_pass http://seaweedfs_s3_backend;

            proxy_http_version 1.1;
            proxy_set_header Connection "";

            # Forward Host and Client IP for SigV4 validation
            proxy_set_header Host $http_host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto https;
            proxy_set_header X-Forwarded-Host $host;
            proxy_set_header X-Forwarded-Port $server_port;

            proxy_connect_timeout 300s;
            proxy_send_timeout    300s;
            proxy_read_timeout    300s;
        }
    }
}
```

---

## 🐳 Step 5: Production `docker-compose.yml`

This setup establishes:
- An isolated internal bridge network (`seaweedfs_internal`).
- Resource constraints (`limits` and `reservations`).
- File descriptor ulimits (`65536`).
- Automatic container restarts (`unless-stopped`).
- Separate volume servers on dedicated directories.
- Zero public port exposure for Master and Volume servers.

```yaml
services:
  # 1. Master Server: Coordinates volumes and cluster state
  master:
    image: chrislusf/seaweedfs:latest
    container_name: seaweedfs_master
    restart: unless-stopped
    command: >
      weed -v=2 master
      -ip=master
      -port=9333
      -mdir=/data/master
      -volumeSizeLimitMB=1024
      -defaultReplication=001
    environment:
      WEED_SECURITY_CONFIG: /etc/seaweedfs/security.toml
      WEED_JWT_SIGNING_KEY: ${JWT_SIGNING_KEY}
      WEED_JWT_SIGNING_READ_KEY: ${JWT_SIGNING_READ_KEY}
    volumes:
      - ./data/master:/data/master
      - ./config/security.toml:/etc/seaweedfs/security.toml:ro
      - ./certs:/etc/seaweedfs/certs:ro
    networks:
      - seaweedfs_internal
    ulimits:
      nofile:
        soft: 65536
        hard: 65536

  # 2. Volume Server 1: Stores binary chunk data
  volume1:
    image: chrislusf/seaweedfs:latest
    container_name: seaweedfs_volume1
    restart: unless-stopped
    command: >
      weed -v=2 volume
      -mserver=master:9333
      -ip=volume1
      -port=8080
      -dir=/data/volume1
      -max=100
    environment:
      WEED_SECURITY_CONFIG: /etc/seaweedfs/security.toml
      WEED_JWT_SIGNING_KEY: ${JWT_SIGNING_KEY}
      WEED_JWT_SIGNING_READ_KEY: ${JWT_SIGNING_READ_KEY}
    volumes:
      - ./data/volume1:/data/volume1
      - ./config/security.toml:/etc/seaweedfs/security.toml:ro
      - ./certs:/etc/seaweedfs/certs:ro
    depends_on:
      - master
    networks:
      - seaweedfs_internal
    ulimits:
      nofile:
        soft: 65536
        hard: 65536

  # 3. Volume Server 2: Second volume server for replication & concurrency
  volume2:
    image: chrislusf/seaweedfs:latest
    container_name: seaweedfs_volume2
    restart: unless-stopped
    command: >
      weed -v=2 volume
      -mserver=master:9333
      -ip=volume2
      -port=8080
      -dir=/data/volume2
      -max=100
    environment:
      WEED_SECURITY_CONFIG: /etc/seaweedfs/security.toml
      WEED_JWT_SIGNING_KEY: ${JWT_SIGNING_KEY}
      WEED_JWT_SIGNING_READ_KEY: ${JWT_SIGNING_READ_KEY}
    volumes:
      - ./data/volume2:/data/volume2
      - ./config/security.toml:/etc/seaweedfs/security.toml:ro
      - ./certs:/etc/seaweedfs/certs:ro
    depends_on:
      - master
    networks:
      - seaweedfs_internal
    ulimits:
      nofile:
        soft: 65536
        hard: 65536

  # 4. Filer: Manages hierarchical filesystem & metadata
  filer:
    image: chrislusf/seaweedfs:latest
    container_name: seaweedfs_filer
    restart: unless-stopped
    command: >
      weed -v=2 filer
      -master=master:9333
      -ip=filer
      -port=8888
    environment:
      WEED_SECURITY_CONFIG: /etc/seaweedfs/security.toml
      WEED_JWT_FILER_SIGNING_KEY: ${JWT_FILER_SIGNING_KEY}
      WEED_JWT_FILER_SIGNING_READ_KEY: ${JWT_FILER_SIGNING_READ_KEY}
    volumes:
      - ./data/filer:/data/filer
      - ./config/security.toml:/etc/seaweedfs/security.toml:ro
      - ./config/filer.toml:/etc/seaweedfs/filer.toml:ro
      - ./certs:/etc/seaweedfs/certs:ro
    depends_on:
      - master
      - volume1
      - volume2
    networks:
      - seaweedfs_internal
    ulimits:
      nofile:
        soft: 65536
        hard: 65536

  # 5. S3 Gateway: S3 compatible API fronting the Filer
  s3:
    image: chrislusf/seaweedfs:latest
    container_name: seaweedfs_s3
    restart: unless-stopped
    command: >
      weed -v=2 s3
      -filer=filer:8888
      -ip=s3
      -port=8333
      -config=/etc/seaweedfs/s3_config.json
    environment:
      WEED_SECURITY_CONFIG: /etc/seaweedfs/security.toml
      WEED_JWT_FILER_SIGNING_KEY: ${JWT_FILER_SIGNING_KEY}
      WEED_JWT_FILER_SIGNING_READ_KEY: ${JWT_FILER_SIGNING_READ_KEY}
    volumes:
      - ./config/s3_config.json:/etc/seaweedfs/s3_config.json:ro
      - ./config/security.toml:/etc/seaweedfs/security.toml:ro
      - ./certs:/etc/seaweedfs/certs:ro
    depends_on:
      - filer
    networks:
      - seaweedfs_internal
    ulimits:
      nofile:
        soft: 65536
        hard: 65536

  # 6. Nginx Ingress: Hardened HTTPS Reverse Proxy
  nginx:
    image: nginx:alpine
    container_name: seaweedfs_nginx
    restart: unless-stopped
    ports:
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/certs:/etc/nginx/certs:ro
    depends_on:
      - s3
    networks:
      - seaweedfs_internal

networks:
  seaweedfs_internal:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

---

## 🚀 Step 6: Launch & Verify the Stack

### 1. Launch Containers

```bash
# Substitute environment variables into configs if necessary, then start
docker compose up -d
```

Check running services:

```bash
docker compose ps
```

All 6 services (`master`, `volume1`, `volume2`, `filer`, `s3`, `nginx`) should show `Up` status.

---

### 2. Verify Security Controls

#### A. Test S3 Authentication with AWS CLI

Verify that legitimate authenticated requests succeed:

```bash
# Load credentials from .env
source .env

# Configure AWS CLI profile for testing
aws configure set aws_access_key_id "$S3_ADMIN_ACCESS_KEY" --profile seaweed-admin
aws configure set aws_secret_access_key "$S3_ADMIN_SECRET_KEY" --profile seaweed-admin

# Create a bucket
aws --endpoint-url https://localhost --no-verify-ssl \
  --profile seaweed-admin s3 mb s3://secure-bucket

# Upload a test file
echo "SeaweedFS Secure Storage Test" > testfile.txt
aws --endpoint-url https://localhost --no-verify-ssl \
  --profile seaweed-admin s3 cp testfile.txt s3://secure-bucket/testfile.txt

# List files
aws --endpoint-url https://localhost --no-verify-ssl \
  --profile seaweed-admin s3 ls s3://secure-bucket/
```

#### B. Verify Anonymous Access is Rejected

Test that unauthenticated requests without credentials fail:

```bash
curl -k -I https://localhost/secure-bucket/testfile.txt
```

Expected output:
```http
HTTP/2 403
x-amz-error-code: AccessDenied
```

#### C. Verify Direct Volume Server Access is Blocked

Try to execute an unauthenticated upload directly against a volume server inside the network without a Master-issued JWT token:

```bash
docker compose exec s3 curl -I -X POST http://volume1:8080/submit
```

Expected output:
```http
HTTP/1.1 401 Unauthorized
```
Direct writes without a valid `jwt.signing.key` token issued by the Master are rejected.

#### D. Verify Volume Server Web UI is Disabled

```bash
docker compose exec s3 curl -I http://volume1:8080/ui/index.html
```

Expected output:
```http
HTTP/1.1 404 Not Found
```

---

## 🛠️ Step 7: Day-2 Operations & Security Maintenance

### 1. Interactive Cluster Administration with `weed shell`

To run administrative commands while respecting gRPC mTLS:

```bash
docker compose exec s3 weed -v=0 shell \
  -master=master:9333 \
  -filer=filer:8888
```

Useful commands inside `weed shell`:

```text
> volume.list                    # View volume status across volume1 and volume2
> volume.balance                 # Rebalance chunks across volumes
> volume.compact -force          # Reclaim deleted chunk space
> s3.bucket.list                 # List existing S3 buckets
> s3.bucket.create -name=logs    # Create S3 bucket
```

### 2. Zero-Downtime Certificate Renewal

SeaweedFS automatically detects rotated certificates on disk without requiring container restarts. To renew certificates:

1. Re-run `certs/generate-certs.sh` with new expiry dates.
2. SeaweedFS watches file modification timestamps and transparently reloads the new TLS certificates in-memory.
3. Reload Nginx without dropping active connections:
   ```bash
   docker compose exec nginx nginx -s reload
   ```

### 3. Automated Backup Routine

Set up a daily cron job to back up the Filer metadata:

```bash
#!/usr/bin/env bash
# /opt/seaweedfs-onprem/backup-meta.sh
BACKUP_DIR="/backup/seaweedfs/$(date +%F)"
mkdir -p "$BACKUP_DIR"

docker compose -f /opt/seaweedfs-onprem/docker-compose.yml exec -T filer \
  weed filer.meta.backup -filer=filer:8888 -output=/data/filer/meta-$(date +%F).json

cp /opt/seaweedfs-onprem/data/filer/meta-*.json "$BACKUP_DIR/"
```

---

## 📋 Security Checklist Summary

- [x] **Private Docker Network**: Master, Volumes, and Filer are not exposed to host ports.
- [x] **gRPC mTLS**: All cluster communication is mutually authenticated using 2048-bit keys and an internal CA.
- [x] **Volume Write JWT**: Direct unauthenticated HTTP POST uploads to volume servers are blocked.
- [x] **Volume Read JWT**: Volume reads require valid JWT signatures.
- [x] **Filer Signing JWT**: S3 Gateway authenticates to Filer via dedicated JWT.
- [x] **No Anonymous S3**: `anonymous` block omitted from `s3_config.json`.
- [x] **Web UIs Disabled**: Volume and Filer directory browsing UIs are disabled.
- [x] **HTTPS Termination**: Nginx terminates TLS with modern protocols (`TLSv1.2`/`TLSv1.3`).
- [x] **Streaming Optimization**: Request buffering disabled for multi-part large file uploads.
- [x] **Persistent Mounts**: Separate storage volumes for master metadata, filer database, and volume chunks.
