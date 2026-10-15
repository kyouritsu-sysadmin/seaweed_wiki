---
id: Lance-Maintenance-Worker
title: "Lance Maintenance Worker"
sidebar_label: "Lance Maintenance Worker"
---

# Lance Maintenance Worker

A Lance table needs upkeep the Iceberg worker cannot do, because reading the Lance format in Go is not implemented. The Lance maintenance worker is a separate process, written in Rust, that connects to the admin server over the same plugin protocol `weed worker` uses.

It is **not a sidecar**: `PluginControlService` is a language-agnostic gRPC contract for external maintenance workers, and `weed worker` is the Go reference implementation of it. Everything the Go worker gets from the protocol — scheduling, retries, dedupe, progress, concurrency limits, and a settings page rendered in the admin UI from the worker's own descriptor — the Rust worker gets too.

Source: `seaweed-worker/` in the SeaweedFS repository. The binary is
`weed-worker`: it is the Rust side of `weed worker`, the way `weed-volume` is
the Rust side of `weed volume`, and the Lance jobs are the first family it
carries rather than the only one it ever will.

## Getting it

### Docker

```bash
docker run chrislusf/seaweedfs worker-rust \
  --admin admin:23646 --namespace http://s3:9101
```

The standard image carries it at `/usr/bin/weed-worker` on `amd64` and `arm64`,
beside the Rust volume server. The verb mirrors `volume-rust`, so plain `worker`
still runs the Go one. On `arm` and `386` the image says the worker is not
available for the platform rather than failing as "not found".

### From a release

```bash
curl -fsSL https://raw.githubusercontent.com/seaweedfs/seaweedfs/master/install.sh \
  | bash -s -- --component worker-rust
```

`--component all` takes it along with `weed` and the Rust volume server, and
skips it on a platform it has no build for. The assets behind it are
`weed-worker_linux_amd64.tar.gz` and `weed-worker_linux_arm64.tar.gz`, with
md5s, on each GitHub release. Linux only: the worker runs beside the cluster it
maintains, and lance, arrow and datafusion make every extra target an expensive
build.

### From source

A Rust toolchain and a protoc; see [Building it](#building-it) below.

## Running it

```bash
weed-worker \
  --admin localhost:23646 \
  --namespace http://localhost:9101
```

`--admin` takes the admin server's **HTTP** address; the gRPC port is derived from it the same way the Go worker does. Dialling the gRPC port directly fails with "frame with invalid size", which reads like a protocol bug rather than a wrong port.

| Flag | Default | Meaning |
|------|---------|---------|
| `--admin` | `localhost:23646` | admin server's HTTP address |
| `--namespace` | | Lance Namespace URL (`WEED_LANCE_NAMESPACE`) |
| `--id` | hostname-derived | worker id; **two workers sharing one id evict each other** |
| `--heartbeat-seconds` | `10` | |
| `--max-concurrency` | `1` | detection and execution slots |
| `--access-key`, `--secret-key` | | storage credentials for a gateway that vends none |
| `--tls-ca`, `--tls-cert`, `--tls-key` | | mTLS for the control stream; all three together |
| `--tls-server-name` | | when admin's certificate does not name the address dialled |
| `--metrics-port` | `0` (off) | serves `/health`, `/ready`, `/metrics` |
| `--metrics-ip` | `127.0.0.1` | the endpoint is unauthenticated |

### Credentials

The worker holds none of its own. It asks the namespace to describe a table with `vend_credentials` and hands the `storage_options` to lance. A gateway without STS vends no credentials at all, so `--access-key` and `--secret-key` are a fallback; anything the namespace does vend wins over them.

If detection reports nothing at all, credentials are the first thing to check: a table the worker cannot open is skipped with a warning, and a sweep that could open nothing looks exactly like a cluster with no work to do. The `objects_skipped_total` metric below exists to tell those apart.

### TLS

`--tls-ca`, `--tls-cert` and `--tls-key` take the same certificates the Go worker reads from the `[grpc.worker]` section of `security.toml`, and must be given together — a CA on its own would quietly mean one-way TLS, which a mutual setup rejects anyway. Without them the stream is plaintext, which is the Go worker's behaviour too when nothing is configured.

## The jobs

| Job type | What it does | Detected from |
|----------|--------------|---------------|
| `lance_compact` | merges small fragments | fragment count |
| `lance_optimize_indices` | extends indices to cover rows written after they were built | rows no index covers |
| `lance_cleanup_versions` | removes old versions and the files only they referenced | version count and age |

**`lance_optimize_indices` is the one that matters most**, and has no Iceberg equivalent. Rows written after an index was built are not covered by it, so a vector search silently misses them. It is a correctness problem wearing a performance problem's clothes.

Each job type has a settings form in the admin UI, rendered from the worker's descriptor:

| Setting | Job | Default |
|---------|-----|---------|
| `min_fragments` | compact | 8 |
| `target_rows_per_fragment` | compact | 1048576 |
| `max_unindexed_rows` | optimize indices | 100000 |
| `retain_hours` | cleanup | 168 |
| `min_versions_to_keep` | cleanup | 5 |

`min_versions_to_keep` is a floor applied when the job runs, not only when it is proposed: versions that age past the retention window between proposal and execution do not take the table below it.

### Job types start disabled

Like every plugin job type, these are `enabled=false` until an operator turns them on in the admin UI (or via `PUT /api/plugin/job-types/{jobType}/config`). A connected worker with nothing running is usually this.

## What the worker tells the admin UI

SeaweedFS cannot read a Lance table, so the admin UI would otherwise show a location and nothing else. The worker fills that in:

- **Observations** — while detection opens a dataset to decide whether it needs work, it reports the schema, row count, fragment count and version count. Admin caches the last one per table and serves it back with the time it was taken and which worker took it. Nothing is scheduled from it; it is a cache with its staleness on the label. Also available at `GET /api/plugin/observations`.
- **Sample rows** — fetched from a worker when the Browse Data page is opened, never cached, because rows are the table's data rather than a description of it.

## Metrics

With `--metrics-port`, the worker serves the same three endpoints as `weed worker -metricsPort`:

| Path | |
|------|--|
| `/health` | process is alive |
| `/ready` | the control stream is up — a worker whose admin has gone away is running but will do nothing |
| `/metrics` | Prometheus |

Names are `SeaweedFS_worker_*`; see [System Metrics](./System-Metrics.md) for the list. The pair worth alerting on is `objects_seen_total` against `objects_skipped_total`.

Note the port convention: master 9324, volume 9325, filer 9326, s3 9327 — so a worker on the same host wants 9328.

## Building it

```bash
cd seaweed-worker
cargo build --release -p weed-lance-worker      # binary at target/release/weed-worker
```

The package keeps the lance name; the binary it produces does not.

`seaweed-worker-core` compiles the protocol straight out of `weed/pb/plugin.proto`
with a protoc it vendors, so it needs no system install. The lance crates compile
protos of their own, in build scripts nothing SeaweedFS sets can reach, so they
need a protoc on PATH (`brew install protobuf`, `apt install protobuf-compiler`)
or `PROTOC` naming one. A cold build pulls in lance and DataFusion and takes a
while — the binary is around 200MB.

## See also

- [SeaweedFS Lance Catalog](./SeaweedFS-Lance-Catalog.md)
- [Worker](./Worker.md) — the Go plugin worker
- [Plugin Worker Scheduling](./Plugin-Worker-Scheduling.md)
- [System Metrics](./System-Metrics.md)
