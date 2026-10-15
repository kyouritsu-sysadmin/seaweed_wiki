---
id: Worker
title: "Worker"
sidebar_label: "Worker"
---

# Weed Worker

The `weed worker` command starts a plugin worker that connects to an admin server to detect and execute cluster maintenance jobs.

## Overview

Workers are distributed maintenance agents that connect to the admin server via a bidirectional gRPC stream. Each worker registers its capabilities, receives detection and execution requests, and reports progress back to the admin scheduler.

Built-in job types:

| Job Type | Category | Description |
|----------|----------|-------------|
| `vacuum` | default | Reclaim disk space by removing deleted files from volumes |
| `volume_balance` | default | Redistribute volumes across servers to reduce skew |
| `admin_script` | default | Execute custom admin shell scripts |
| `erasure_coding` | heavy | Convert volumes to erasure-coded format for storage efficiency |
| `iceberg_maintenance` | heavy | Compact, expire snapshots, remove orphans for Iceberg tables |

`weed worker` is the Go implementation of the plugin protocol, not the only one.
`PluginControlService` is language-agnostic, and a worker in another language is
a first-class worker: it registers capabilities, answers detection and execution,
and gets its settings page rendered from its own descriptor. The Lance jobs
(`lance_compact`, `lance_optimize_indices`, `lance_cleanup_versions`) come from
one — see [Lance Maintenance Worker](./Lance-Maintenance-Worker.md) — because reading the Lance format in Go
is not implemented. That worker ships in the same image, as
`docker run chrislusf/seaweedfs worker-rust`, and on each release as
`weed-worker_linux_{amd64,arm64}.tar.gz`.

## Usage

```bash
weed worker [options]
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `-admin` | `localhost:23646` | Admin server address |
| `-id` | *(auto-generated)* | Worker ID (persisted to `-workingDir` when auto-generated) |
| `-jobType` | `all` | Job types or categories to serve (comma-separated) |
| `-workingDir` | *(empty)* | Directory for persistent worker state (worker.id) |
| `-heartbeat` | `15s` | Heartbeat interval to admin server |
| `-reconnect` | `5s` | Reconnect delay after disconnection |
| `-maxDetect` | `1` | Maximum concurrent detection requests |
| `-maxExecute` | `4` | Maximum concurrent execution requests |
| `-metricsPort` | `0` | Prometheus metrics listen port (disabled when 0) |
| `-metricsIp` | `0.0.0.0` | Prometheus metrics listen IP |
| `-address` | *(empty)* | Worker address advertised to admin |
| `-debug` | `false` | Enable pprof debug server |
| `-debug.port` | `6060` | pprof debug HTTP port |

## Job Type Categories

The `-jobType` flag accepts a mix of **categories** and **explicit job type names**:

| Token | Resolves to |
|-------|-------------|
| `all` | Every registered job type |
| `default` | Lightweight jobs: vacuum, volume_balance, admin_script |
| `heavy` | Resource-intensive jobs: erasure_coding, iceberg_maintenance |
| *(explicit name)* | A single job type by canonical name or alias |

Categories and explicit names can be combined freely:

```bash
# All registered job types (default behavior)
weed worker -admin=localhost:23646 -jobType=all

# Only lightweight maintenance jobs
weed worker -admin=localhost:23646 -jobType=default

# Only resource-intensive jobs on dedicated hardware
weed worker -admin=localhost:23646 -jobType=heavy

# Default category plus a specific heavy job
weed worker -admin=localhost:23646 -jobType=default,iceberg

# Explicit job types (aliases work too)
weed worker -admin=localhost:23646 -jobType=vacuum,ec
```

### Job Type Aliases

Each job type accepts several aliases on the CLI:

| Canonical Name | Aliases |
|---------------|---------|
| `vacuum` | `vol.vacuum`, `volume.vacuum` |
| `volume_balance` | `balance`, `volume.balance`, `volume-balance` |
| `erasure_coding` | `ec`, `erasure-coding`, `erasure.coding` |
| `admin_script` | `admin`, `script`, `admin-script`, `admin.script` |
| `iceberg_maintenance` | `iceberg`, `iceberg-maintenance`, `iceberg.maintenance` |

## Examples

### Basic Usage

```bash
# Start worker connecting to local admin server (all job types)
weed worker -admin=localhost:23646

# Connect to remote admin server
weed worker -admin=admin.example.com:23646

# Persist worker ID across restarts
weed worker -admin=localhost:23646 -workingDir=/var/lib/seaweedfs-worker
```

### Specialised Workers

```bash
# Dedicated lightweight worker
weed worker -admin=localhost:23646 -jobType=default

# Dedicated heavy worker on beefy hardware
weed worker -admin=localhost:23646 -jobType=heavy -maxExecute=8

# Only vacuum
weed worker -admin=localhost:23646 -jobType=vacuum

# Named worker with specific job type
weed worker -admin=localhost:23646 -id=ec-worker-1 -jobType=erasure_coding
```

### Monitoring

```bash
# Enable Prometheus /metrics, /health, /ready endpoints
weed worker -admin=localhost:23646 -metricsPort=9328

# Debug with pprof
weed worker -admin=localhost:23646 -debug -debug.port=6060
```

The metric names are listed in [System Metrics](./System-Metrics.md). Note that 9327 is the S3
gateway's metrics port in the sample configurations, so a worker sharing a host
with one wants 9328.

## Worker Architecture

### Worker Lifecycle

1. **Connect**: Worker dials the admin server's gRPC plugin stream
2. **Hello**: Worker sends `WorkerHello` with its capabilities and supported job types
3. **Heartbeat**: Worker sends periodic heartbeats reporting load
4. **Detection**: Admin sends `RunDetectionRequest`; worker proposes jobs
5. **Execution**: Admin sends `ExecuteJobRequest`; worker runs the job and streams progress
6. **Shutdown**: Worker sends `WorkerShutdown` on SIGINT/SIGTERM

### Connection Details

- **Protocol**: Bidirectional gRPC stream (`plugin.proto`)
- **Port**: Admin HTTP port + 10000 by default (e.g., admin on 23646 → gRPC on 33646)
- **Auto-discovery**: Worker queries `GET /api/plugin/status` to resolve the gRPC port when it differs from the default offset
- **Security**: Supports TLS using `[grpc.worker]` in `security.toml`

### How Scheduling Works

The admin server runs a single scheduler goroutine that processes job types **sequentially, one group at a time**. Each job type is a group — its detection and all resulting executions complete (or time out) before the next job type begins.

For each group:

1. **Detection**: The scheduler picks a detector worker and sends a `RunDetectionRequest`. The worker inspects cluster state and proposes work items (e.g., "vacuum volume 42").
2. **Filtering**: The admin server deduplicates proposals against already-active jobs.
3. **Dispatch**: Proposals are converted to jobs and dispatched to executor workers in parallel (up to `global_execution_concurrency`).
4. **Execution**: Workers run the jobs, stream progress updates, and report completion.

Each group has a configurable **max runtime** (`job_type_max_runtime_seconds`, default 30 minutes). If the timeout fires, remaining jobs are canceled and the scheduler moves to the next job type. This prevents a slow job type from starving others.

Each job type also has independent settings for detection interval, concurrency, timeouts, and retries — all editable in the admin UI at `/plugin`. For a detailed walkthrough, see [Plugin Worker Scheduling](./Plugin-Worker-Scheduling.md).

## Configuration

### Security Configuration

Workers read TLS configuration from `security.toml`:

```toml
[grpc.worker]
cert = "/etc/ssl/worker.crt"
key = "/etc/ssl/worker.key"
ca = "/etc/ssl/ca.crt"
```

### Worker Identification

- **Worker ID**: Auto-generated (format `w-&lt;hostname&gt;-&lt;random&gt;`) and persisted to `&lt;workingDir&gt;/worker.id`
- **Explicit ID**: Set via `-id` to override auto-generation

## Adding a New Job Type

With the handler registry, adding a new job type requires minimal changes:

1. Create the handler file implementing the `JobHandler` interface
2. Add an `init()` function that calls `RegisterHandler` with the job type, category, aliases, and build function

If the handler lives in the root `plugin/worker` package, no other files need to change.

If the handler lives in a **subpackage** (like `plugin/worker/iceberg`), add a blank import to the aggregator file `plugin/worker/handlers/handlers.go` so its `init()` runs:

```go
import (
    _ "github.com/seaweedfs/seaweedfs/weed/plugin/worker/iceberg"
    _ "github.com/seaweedfs/seaweedfs/weed/plugin/worker/yourpkg" // add new subpackages here
)
```

The handler is then automatically available to all workers using `all` or the matching category.

## Best Practices

### Deployment

1. **Separate by category**: Run `default` workers broadly, `heavy` workers on dedicated nodes with more CPU/memory
2. **Multiple workers**: Deploy multiple workers for redundancy and throughput
3. **Stable identity**: Use `-workingDir` so worker IDs survive restarts
4. **Resource sizing**: Tune `-maxExecute` based on available resources

### Troubleshooting

1. **Cannot connect to admin server**: Verify address, check network, ensure admin is running, check gRPC port
2. **No tasks received**: Verify `-jobType` includes the desired job types, check admin scheduler configuration
3. **TLS failures**: Check `security.toml` paths and certificate validity
4. **Debug logging**: `weed worker -admin=... -v=4`

## Related Commands

- [`weed admin`](./Admin-UI.md): Start admin server that manages workers
- [`weed master`](./Master-Server-API.md): Start master servers
- [`weed volume`](./Volume-Server-API.md): Start volume servers

## See Also

- [Plugin Worker Scheduling](./Plugin-Worker-Scheduling.md) — how the admin server schedules and dispatches work
- [Migrate Maintenance Scripts to Admin Script Plugin](./Migrate-Maintenance-Scripts-to-Admin-Script-Plugin.md) — migration guide from `master.toml` maintenance scripts
- [Erasure Coding](./Erasure-Coding-for-warm-storage.md)
