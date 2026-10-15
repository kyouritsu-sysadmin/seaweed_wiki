---
id: Quick-Start-with-weed-mini
title: "Quick Start with weed mini"
sidebar_label: "Quick Start with weed mini"
---

## Quick Start

Start a ready-to-use S3 object store with credentials and a pre-created bucket in one command:

```bash
AWS_ACCESS_KEY_ID=admin \
AWS_SECRET_ACCESS_KEY=secret \
S3_BUCKET=my-bucket \
weed mini -dir=./data
```

That's it — the S3 endpoint is at http://localhost:8333, `my-bucket` already exists, and `admin`/`secret` are valid credentials. Test it:

```bash
aws --endpoint-url http://localhost:8333 s3 ls s3://my-bucket/
```

The same command also brings up:
- Master UI: http://localhost:9333
- Volume Server: http://localhost:9340
- Filer UI: http://localhost:8888
- WebDAV: http://localhost:7333
- Admin UI: http://localhost:23646

### What each piece does (and how to drop it)

- **`-dir=/data`** — where data lives. Required.
- **`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`** — seed initial S3 credentials for the `mini` user. Omit them to start in unauthenticated "Allow All" mode (development only — see [Default S3 Access](#default-s3-access)).
- **`S3_BUCKET=my-bucket`** — pre-create this bucket on first start. Comma-separated list is accepted (`S3_BUCKET=raw,processed`). Idempotent on later starts. Equivalent to `-bucket=my-bucket` on the command line. Omit to skip bucket creation.
- **`S3_TABLE_BUCKET=iceberg-tables`** — same idea but creates an [S3 Tables](./S3-Table-Bucket.md) (Iceberg) bucket. Comma-separated list also supported. Equivalent to `-tableBucket=iceberg-tables`.

### Custom port

```bash
weed mini -dir=./data -master.port=9444 -s3.port=8334
```

### S3 with Reverse Proxy

If `weed mini` is behind a reverse proxy (e.g. Nginx, Cloudflare Tunnel), use the `-s3.externalUrl` flag to ensure S3 signature verification works correctly:

```bash
# SeaweedFS reachable externally at https://s3.example.com
weed mini -dir=./data -s3.externalUrl=https://s3.example.com
```

For more configuration details, see the **[S3 Nginx Proxy](./S3-Nginx-Proxy.md)** page.

## Quick Start with `weed mini`

`weed mini` is an all-in-one SeaweedFS command that starts all essential components in a single process with auto-tuned defaults. It is appropriate for development and testing **and** for many single-node and small-cluster production setups — for example, an S3 gateway that issues presigned upload/download URLs.

**Good for:**
- Learning SeaweedFS and S3-compatible storage
- Development, testing, and prototyping
- Single-node production setups (S3 gateway, file storage, presigned URLs)
- Small clusters: run `weed mini` on the primary node and connect additional `weed volume` servers to it for extra capacity

**When to use [Multi-Component Setup](./Getting-Started.md#multi-component-setup-for-larger-clusters-and-advanced-users) instead:**
- You need multiple master servers (HA / Raft quorum) — `weed mini` runs a single master by design
- You want components on separate hosts for isolation, or fine-grained tuning beyond the auto-defaults

> **Backward compatibility**: `weed mini` defaults (volume size, port layout, bundled components) may evolve between releases. Pin a SeaweedFS version or pass the relevant flags explicitly if you depend on specific defaults.

## Features

The `weed mini` command starts:
- **Master Server** - Cluster coordination
- **Volume Server** - Data storage
- **Filer** - Hierarchical file system interface
- **S3 Gateway** - S3-compatible API endpoint (with embedded IAM)
- **Iceberg REST Catalog** - Iceberg table catalog
- **WebDAV Gateway** - WebDAV file access
- **Admin UI** - Web-based management console
- **Maintenance Worker** - Background tasks (vacuuming, erasure coding, balancing)

All components run in a single process with optimized settings:
- Auto-configured volume size limit (64MB–1024MB, based on disk capacity)
- Auto-scaling volume count based on available disk space
- Single master mode (no Raft peers / quorum overhead)
- 1-second pre-stop time (faster shutdown)
- Embedded IAM for S3 credential management

## How `weed mini` differs from `weed server -filer -s3`

Both commands run multiple SeaweedFS components in a single process, but they target different use cases.

| | `weed mini` | `weed server -filer -s3` |
|---|---|---|
| Components started | master + volume + filer + S3 + WebDAV + **Admin UI** + **maintenance worker** | master + volume + filer + S3 (admin UI and worker not bundled) |
| Master mode | Single master (no peers) | Supports multi-master peers (HA) |
| Volume size limit | Auto-tuned (64–1024 MB based on disk) | Fixed ~30 GB default |
| Volume max count | Auto (based on free disk space) | 8 by default |
| Default volume port | 9340 | 8080 |
| Iceberg REST catalog | Enabled on port 8181 | Not bundled |
| Pre-stop seconds | 1 (fast shutdown) | 10 |
| Intent | Single-node and small-cluster all-in-one | Composable building block for clusters |

For a typical single-node S3 setup, `weed mini` is the simpler choice — you get the Admin UI and built-in vacuum/EC/balance maintenance without running extra processes. Choose `weed server` when you want explicit control over which components run, plan to run multiple master peers, or are building a larger cluster from individual `weed master` / `weed volume` / `weed filer` processes.


## Run with Docker

The `chrislusf/seaweedfs` image runs `weed mini -dir=/data` by default, so the only thing you pass is the env vars (and a volume mount if you want data to survive restarts):

```bash
docker run -d --name weed-mini \
  -p 8333:8333 -p 8888:8888 -p 9333:9333 -p 23646:23646 \
  -v weed-data:/data \
  -e AWS_ACCESS_KEY_ID=admin \
  -e AWS_SECRET_ACCESS_KEY=secret \
  -e S3_BUCKET=my-bucket \
  chrislusf/seaweedfs
```

Exposed ports:
- `8333` — S3 endpoint
- `8888` — Filer UI
- `9333` — Master UI
- `23646` — Admin UI

Drop any of the env vars to skip that piece (no `S3_BUCKET` → no bucket created; no AWS keys → "Allow All" mode). Drop `-v weed-data:/data` if you don't need data to persist across container restarts.

### Manage buckets after startup

Use the built-in `weed shell` — it talks directly to the master, so no AWS CLI or credentials needed:

```bash
docker exec -i weed-mini weed shell <<< "s3.bucket.create -name another-bucket"
docker exec -i weed-mini weed shell <<< "s3.bucket.list"
```

For an interactive prompt: `docker exec -it weed-mini weed shell`, then `help`.

### Use as a GitHub Actions service container

GitHub Actions service containers cannot pass arguments to the image entrypoint, so the default `CMD` is what makes the image work directly under `services:`:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      seaweedfs:
        image: chrislusf/seaweedfs
        ports:
          - 8333:8333
        env:
          AWS_ACCESS_KEY_ID: admin
          AWS_SECRET_ACCESS_KEY: secret
          S3_BUCKET: my-bucket
    env:
      AWS_ACCESS_KEY_ID: admin
      AWS_SECRET_ACCESS_KEY: secret
      AWS_DEFAULT_REGION: us-east-1
      S3_ENDPOINT: http://localhost:8333
    steps:
      - uses: actions/checkout@v5
      - name: Wait for S3 endpoint
        run: |
          for _ in $(seq 1 60); do
            curl -sfo /dev/null "$S3_ENDPOINT/" && exit 0
            sleep 1
          done
          echo "S3 endpoint did not become ready" >&2
          exit 1
      - run: ./run-tests.sh
```

## Default S3 Access

The S3 gateway starts in **"Allow All" mode** when no credentials are configured — convenient for development, but not what you want in production. The Quick Start command above seeds credentials via `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` so authentication is enabled from the first request.

- **No credentials configured**: All S3 operations are allowed without authentication.
- **Credentials added**: As soon as *any* credentials are configured (env vars at startup, the Admin UI at http://localhost:23646, or `weed shell`), authentication switches on and all requests must be signed.

For larger credential sets, use a JSON file with `-s3.config=s3.config` instead of env vars.

---

## Using S3 Endpoint

### Unauthenticated Access (Default)

If you haven't configured any credentials, you can use the S3 endpoint with the `--no-sign-request` flag in the AWS CLI:

```bash
# Create a bucket
aws --endpoint-url $S3_ENDPOINT s3 mb s3://my-bucket --no-sign-request

# List contents
aws --endpoint-url $S3_ENDPOINT s3 ls s3://my-bucket/ --no-sign-request
```

### Authenticated Access

If you have configured credentials, you'll need to use your access keys:

```bash
# Using AWS CLI
aws configure
# AWS Access Key ID: <your-access-key>
# AWS Secret Access Key: <your-secret-key>

# Use the local endpoint
aws --endpoint-url $S3_ENDPOINT s3 ls s3://my-bucket/
```

## Web Interfaces

### Admin UI
- **URL**: http://localhost:23646
- **Purpose**: User/credential management, task monitoring, system status
- **No authentication by default** (configurable)

### Filer UI
- **URL**: http://localhost:8888
- **Purpose**: Hierarchical file system browser
- **View and manage files** with directory structure

### Master UI
- **URL**: http://localhost:9333
- **Purpose**: Cluster topology and volume management
- **Monitor volume distribution** across servers

## Common Options

```bash
# Specify data directory
weed mini -dir=./data

# Custom S3 port
weed mini -dir=./data -s3.port=8334

# Custom IAM config file
weed mini -dir=./data -s3.iam.config=/path/to/iam.json

# Pre-create one or more S3 buckets on startup if they do not already exist
weed mini -dir=./data -bucket=raw,processed

# Pre-create an S3 Tables (Iceberg) bucket
weed mini -dir=./data -tableBucket=iceberg-tables
```

## Growing Into a Small Cluster

`weed mini` runs a single master, but the embedded master accepts heartbeats from additional volume servers on other hosts. To add storage capacity to a `weed mini` deployment, run extra `weed volume` processes pointing at the mini node's master:

```bash
# On the additional storage node:
weed volume -dir=/data -max=0 -master="<mini-host>:9333" -port=8080
```

This keeps the all-in-one simplicity of `weed mini` while spreading data across multiple machines. If you reach a point where you need a multi-master HA setup, migrate to the [Multi-Component Setup](./Getting-Started.md#multi-component-setup-for-larger-clusters-and-advanced-users).

## Stopping the Server

```bash
# Press Ctrl+C in the terminal
# All services will gracefully shut down
```

## Next Steps

- Read [S3-API-FAQ.md](./S3-API-FAQ.md) for S3-specific questions
- Check [Filer-Commands-and-Operations.md](./Filer-Commands-and-Operations.md) for file operations
- See [Admin-UI.md](./Admin-UI.md) for admin interface documentation
- Explore [Production-Setup.md](./Production-Setup.md) when ready to scale beyond `mini`

## Performance Considerations

`weed mini` is tuned for single-node and small-cluster deployments. As your workload grows, consider:

- **Configure replication** for data safety (set `-master.defaultReplication`, e.g. `010` to keep a copy on another rack)
- **Add volume servers** on additional hosts for more capacity (see [Growing Into a Small Cluster](#growing-into-a-small-cluster))
- **Increase the volume size limit** with `-master.volumeSizeLimitMB` if the auto-tuned default is too small for your file mix
- **Set up monitoring** with `-metricsPort` for Prometheus scraping
- **Move to multi-master / multi-component** when you need master HA or want to isolate components on separate hosts

## Related Documentation

- [Getting-Started.md](./Getting-Started.md) - Traditional multi-process setup
- [Production-Setup.md](./Production-Setup.md) - Production deployment guidance
- [S3-Credentials.md](./S3-Credentials.md) - Detailed credential management
- [Admin-UI.md](./Admin-UI.md) - Admin interface documentation
- [Docker-Compose-for-S3.md](./Docker-Compose-for-S3.md) - Docker deployment
