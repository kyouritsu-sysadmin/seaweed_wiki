---
id: Rust-Volume-Server
title: "Rust Volume Server"
sidebar_label: "Rust Volume Server"
---

# Rust Volume Server

The Rust volume server (`weed-volume`) is a drop-in replacement for the Go volume server, built for higher throughput and lower tail latency. It reads and writes the same `.dat`, `.idx`, and `.vif` files — you can point it at an existing Go volume directory and it just works.

## Installation

### From Binary Release

```bash
# Install the Go weed binary + Rust volume server
curl -fsSL https://raw.githubusercontent.com/seaweedfs/seaweedfs/master/install.sh | bash -s -- --component all

# Or just the Rust volume server
curl -fsSL https://raw.githubusercontent.com/seaweedfs/seaweedfs/master/install.sh | bash -s -- --component volume-rust

# Large disk variant (8TB max volume)
curl -fsSL https://raw.githubusercontent.com/seaweedfs/seaweedfs/master/install.sh | bash -s -- --component volume-rust --large-disk
```

### Docker

```bash
# Run the Rust volume server in a container
docker run -d chrislusf/seaweedfs volume-rust -mserver=localhost:9333

# The standard image includes both Go and Rust volume servers.
# Use "volume" for Go, "volume-rust" for Rust.
```

The Rust binary is included in the standard Docker image for `amd64` and `arm64` platforms. On `arm` and `386`, only the Go volume server is available.

The image carries one other Rust binary on the same terms: `weed-worker`, the
maintenance worker for Lance tables, under the verb `worker-rust`. See
[Lance Maintenance Worker](./Lance-Maintenance-Worker.md).

### Build from Source

```bash
cd seaweed-volume
cargo build --release
# Binary at target/release/weed-volume
```

By default the build enables the `5bytes` feature (8TB max volume, matching Go's `-tags 5BytesOffset`). For 32GB max volume size:

```bash
cargo build --release --no-default-features
```

## Quick Start

```bash
# Start a Go master server
weed master

# Start the Rust volume server (same flags as Go, but with dashes)
weed-volume --dir /data --mserver localhost:9333 --port 8080
```

## CLI Compatibility

The Rust volume server accepts all 40+ flags from the Go volume server. Both single-dash (`-port 8080`) and double-dash (`--port 8080`) formats work.

```bash
# Go style
weed-volume -port 8080 -dir /data -mserver localhost:9333

# Standard CLI style
weed-volume --port 8080 --dir /data --mserver localhost:9333
```

### Options File

Load flags from a file (same format as Go's `-options` flag):

```bash
weed-volume --options /etc/seaweedfs/volume.conf
```

Options file format (one per line, `#` comments):

```
# /etc/seaweedfs/volume.conf
port=8080
dir=/data
mserver=localhost:9333
max=0
```

CLI flags override values from the options file.

### SIGHUP Reload

Sending `SIGHUP` to the Rust volume server reloads:
- **Security config** — re-reads `security.toml` and updates the IP whitelist
- **New volumes** — scans disk directories for newly added volume files

```bash
kill -HUP $(pidof weed-volume)
```

This matches the Go volume server's reload behavior.

## Subtle Differences from Go

The Rust server passes all 109 Go integration tests (53 HTTP + 56 gRPC) and is binary-compatible at the storage layer. However, there are minor behavioral differences worth knowing about:

### Storage Format

| Aspect | Go | Rust |
|--------|------|------|
| Needle format | V1/V2/V3, CRC32-C | Identical |
| Index format | 16-byte (normal) or 17-byte (5BytesOffset) entries | Identical |
| SuperBlock | 8-byte header | Identical |
| `.vif` files | protobuf-JSON, uint64 as strings | Identical |
| Compaction | Vacuum compact/commit/cleanup | Identical |

### Index Backend

| Backend | Go | Rust |
|---------|------|------|
| `memory` | In-memory HashMap | In-memory `CompactMap` (sorted Vec, binary search) |
| `leveldb` | LevelDB via CGo | `rusty-leveldb` (pure Rust) |
| `leveldbMedium` | LevelDB | `rusty-leveldb` |
| `leveldbLarge` | LevelDB | `rusty-leveldb` |
| `redb` | Not available | `redb` (pure Rust, crash-safe B-tree) |

The `redb` backend is Rust-only. It provides crash-safe disk-backed needle maps without CGo dependencies. If you use `redb` and later switch back to the Go volume server, delete the `.rdb` files first — Go will rebuild the index from the `.idx` file.

### HTTP Behavior

| Behavior | Go | Rust | Notes |
|----------|------|------|-------|
| Request ID format | `%X%08X` (hex timestamp + random) | Identical | Not a UUID despite the `x-amz-request-id` header name |
| Range suffix beyond file size | Clamps to file size | Identical | Returns 206 with clamped range, not 416 |
| `If-Modified-Since` / `If-None-Match` order | Checks `If-Modified-Since` first | Identical | Per Go behavior, not RFC 7232 order |
| JWT extraction precedence | Query `?jwt=` > `Authorization` header > `AT` cookie | Identical | |
| Chunk manifest MIME | Uses stored MIME, skips extension override | Identical | |
| Method routing | GET/HEAD→read, POST/PUT→write, DELETE→delete, else→400 | Identical | |
| Pretty JSON | `json.MarshalIndent` with 2-space indent | Identical | |

### gRPC Behavior

| Behavior | Go | Rust | Notes |
|----------|------|------|-------|
| All 48 RPCs | Implemented | Implemented | |
| `VolumeTierMoveDat` progress | No final 100% message | Identical | |
| `VolumeUnmount` for missing volume | Returns nil | Identical | |
| `TierMoveDatFromRemote` | No maintenance mode check | Identical | |
| Cookie mismatch in streaming | Returns empty stream, nil error | Identical | |
| `BatchDelete` EC shard cookie mismatch | Returns 406 status | Identical | HTTP reads return 404 for cookie mismatch |

### Security

| Behavior | Go | Rust | Notes |
|----------|------|------|-------|
| JWT without `exp` claim | Accepted | Identical | Go's jwt-go doesn't require expiration |
| JWT algorithm | HS256 | HS256 only | |
| IP whitelist | CIDR matching | Identical | |
| mTLS | Supported | Supported | Same `security.toml` format |

### Heartbeat & Cluster

| Behavior | Go | Rust | Notes |
|----------|------|------|-------|
| Master gRPC port | `port + 10000` | Identical | |
| Duplicate UUID retry | Exponential backoff (2s, 4s, 8s), exit after 3 | Identical | |
| Leader redirect | Reconnect via seed list | Sleeps 3s, connects directly to new leader | Functionally equivalent, slightly different reconnection path |
| `GetMasterConfiguration` | Called on startup | Identical | |
| Pre-stop shutdown | `preStopSeconds` default 10 | Identical | |

### Operational

| Behavior | Go | Rust | Notes |
|----------|------|------|-------|
| Profiling | Go pprof on debug port | Rust pprof (prost-codec) on debug port | Same `/debug/pprof` endpoint, different profiler |
| Prometheus metrics | Go client library | Rust `prometheus` crate | Same metric names and label patterns |
| `/metrics` endpoint | On admin/metrics port | On admin (debug) port | Both serve on admin port, not the main volume port |
| Disk monitoring | `sysinfo` package | `sysinfo` crate + `libc` | |
| Volume preallocation | `fallocate` on Linux | `fallocate` on Linux via `libc` | Identical behavior |
| Write batching | Synchronous per-request | Batched write queue (up to 128, mpsc) | Rust groups concurrent writes to reduce lock acquisitions. Each client still blocks until its write is durable — no crash-safety difference |
| Streaming reads | Files > 1MB | Files > 1MB via `spawn_blocking` | Same threshold, async I/O |

### Extra CLI Flags (Rust only)

| Flag | Description |
|------|-------------|
| `--securityFile` | Explicit path to `security.toml` (Go discovers it via `viper`) |
| `--options` | Load CLI flags from a file (Go supports this via `fla9` but it's less visible) |

### Extra Index Backend (Rust only)

| Flag value | Description |
|------------|-------------|
| `--index redb` | Crash-safe disk-backed needle map using redb. Not available in Go. Files use `.rdb` extension. |

## Architecture

```
seaweed-volume/
├── src/
│   ├── main.rs              # Entry point, signal handling, SIGHUP reload
│   ├── config.rs             # CLI parsing, options file, security.toml
│   ├── security.rs           # JWT validation, IP whitelist
│   ├── images.rs             # JPEG EXIF orientation fix
│   ├── server/
│   │   ├── volume_server.rs  # Axum router, middleware, request ID
│   │   ├── handlers.rs       # HTTP read/write/delete/status/healthz
│   │   ├── grpc_server.rs    # All 48 VolumeServer RPCs
│   │   ├── heartbeat.rs      # Master registration, leader tracking
│   │   └── write_queue.rs    # Async batched write processing
│   ├── storage/
│   │   ├── needle/           # Needle serialization (V1/V2/V3)
│   │   ├── volume.rs         # Volume read/write/delete, .vif
│   │   ├── disk_location.rs  # Per-directory volume + EC shard management
│   │   ├── store.rs          # Multi-disk Store layer
│   │   └── needle_map.rs     # CompactMap, LevelDB, redb backends
│   └── remote_storage/
│       ├── s3.rs             # S3 fetch-and-write for remote needles
│       └── s3_tier.rs        # S3 multipart upload/download for tier moves
├── proto/                    # Shared .proto files (volume_server, master, remote)
├── vendor/                   # Vendored reed-solomon-erasure
└── tests/                    # Integration tests
```

## Test Coverage

| Suite | Count | Status |
|-------|-------|--------|
| Rust unit tests | 137 | All pass |
| Rust integration tests | 7 | All pass |
| Go HTTP integration tests | 53 | All pass |
| Go gRPC integration tests | 56 | All pass |
| S3 remote storage tests | 3 | All pass |

Run the Go integration tests against the Rust server:

```bash
cd seaweedfs
VOLUME_SERVER_IMPL=rust go test -v -count=1 -timeout 1200s \
  ./test/volume_server/grpc/... \
  ./test/volume_server/http/...
```

Run the Rust tests:

```bash
cd seaweed-volume
cargo test
```

## Protobuf Code Generation

When updating `.proto` files, run `make` in `weed/pb/` to regenerate Go code and copy the volume-server-related proto files to the Rust directory:

```bash
cd weed/pb && make
# This copies volume_server.proto, master.proto, and remote.proto
# to seaweed-volume/proto/
```

The Rust server's `build.rs` runs `tonic-build` to generate Rust code from these protos at compile time.
