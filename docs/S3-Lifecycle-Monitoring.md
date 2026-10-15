---
id: S3-Lifecycle-Monitoring
title: "S3 Lifecycle Monitoring"
sidebar_label: "S3 Lifecycle Monitoring"
---

# S3 Lifecycle — Monitoring

This page lists the Prometheus signals the worker exposes and how to read the heartbeat log line. For incident response, see [S3-Lifecycle-Troubleshooting](./S3-Lifecycle-Troubleshooting.md).

## Prometheus metrics

All metrics are registered in `weed/stats/metrics.go` under the `s3_lifecycle` subsystem. The name a scrape sees is the namespace + subsystem + metric — e.g. the `cursor_min_ts_ns` gauge is exposed as `SeaweedFS_s3_lifecycle_cursor_min_ts_ns`. The fully-qualified names are used throughout this page; query them exactly as written.

### Per-shard gauges

| Metric | Labels | What |
|---|---|---|
| `SeaweedFS_s3_lifecycle_cursor_min_ts_ns` | `shard` | UnixNano of the last meta-log event on this shard for which all matches dispatched successfully |
| `SeaweedFS_s3_lifecycle_daily_run_last_walked_ns` | `shard` | UnixNano of the most recent successful walker fire |

Derived queries:

```promql
# Per-shard replay lag in seconds
(time() * 1e9 - SeaweedFS_s3_lifecycle_cursor_min_ts_ns) / 1e9

# Per-shard walker freshness in seconds
(time() * 1e9 - SeaweedFS_s3_lifecycle_daily_run_last_walked_ns) / 1e9

# Worst-shard lag across the cluster
max(time() * 1e9 - SeaweedFS_s3_lifecycle_cursor_min_ts_ns) / 1e9
```

Zero values mean "not started yet" — distinct from "0s caught up". The heartbeat line uses `cold` as the marker for that state.

`SeaweedFS_s3_lifecycle_schedule_depth{shard}` is still registered but is a leftover from the prior streaming dispatcher, which kept an in-memory match heap. The daily-run worker has no such heap, so this gauge stays at zero — don't alert on it.

### Counters

| Metric | Labels | What |
|---|---|---|
| `SeaweedFS_s3_lifecycle_dispatch_total` | `bucket`, `kind`, `outcome` | Per-bucket dispatch counter, partitioned by action kind and server outcome |
| `SeaweedFS_s3_lifecycle_events_total` | `shard` | Meta-log events the reader emitted to the router |
| `SeaweedFS_s3_lifecycle_daily_run_events_scanned_total` | `shard` | Meta-log events `drainShardEvents` processed |
| `SeaweedFS_s3_lifecycle_bootstrap_dispatch_total` | `bucket`, `kind` | Walker dispatch counter |
| `SeaweedFS_s3_lifecycle_metadata_only_total` | `bucket`, `rule_hash` | Successful deletes that took the metadata-only path. `rule_hash` is the hex-encoded rule identity; on clusters with many rules, drop it via Prometheus relabeling to control cardinality |

`events_total` counts what the reader fanned out; `daily_run_events_scanned_total` counts what each shard actually drained. In steady state they track together — a persistent gap means events are being filtered before drain (out-of-window TsNs) rather than processed.

`outcome` values: `DONE`, `NOOP_RESOLVED`, `SKIPPED_OBJECT_LOCK`, `RETRY_LATER`, `BLOCKED`, `LIFECYCLE_DELETE_OUTCOME_UNSPECIFIED`, `RPC_ERROR`. The first three are success outcomes that advance the cursor; the others halt the run. `LIFECYCLE_DELETE_OUTCOME_UNSPECIFIED` is the proto zero-value — a healthy worker / server pair should never emit it; a non-zero count there indicates an internal error or a version mismatch between worker and server.

### Histograms

| Metric | What |
|---|---|
| `SeaweedFS_s3_lifecycle_daily_run_shard_duration_seconds{shard}` | Wall-clock per shard pass. Rising p95 means shards are taking longer; if you've set a finite Execution Timeout for the job type, p95 approaching it means passes risk being cut short (the default is effectively unbounded). |
| `SeaweedFS_s3_lifecycle_dispatch_limiter_wait_seconds` | Time spent waiting on the cluster rate limiter before issuing `LifecycleDelete`. Near-zero = cap not binding; long-tail at `1/rate` = cap is the active throttle. |

## Heartbeat log line

Emitted at the end of every `dailyrun.Run` invocation, at `glog.V(0)` (default verbosity):

```text
daily_run: status=ok shards=16 errors=0 duration=7s cursor_lag_max=2m walked_max_age=3m
```

Tokens are space-separated `key=value` for grep / log-aggregator filtering. Stable across versions:

| Token | Meaning |
|---|---|
| `status=ok` or `status=error` | Whether any shard returned an error |
| `shards=N` | Number of shards processed this pass |
| `errors=N` | Per-shard error count |
| `duration=Ns` | Wall-clock for the whole pass |
| `cursor_lag_max=...` | Worst per-shard replay lag, or `cold` if no shard has a persisted cursor yet |
| `walked_max_age=...` | Worst per-shard walker age, or `cold` if no shard has walked yet |

A healthy production heartbeat looks like:

```text
daily_run: status=ok shards=16 errors=0 duration=12.3s cursor_lag_max=45s walked_max_age=58m
```

Read it as: 16 shards finished cleanly in 12 seconds; the worst-case replay lag is 45 seconds behind real-time; the oldest walker fire on any shard is 58 minutes ago (so `walker_interval_minutes=60` is roughly honored).

## Anti-patterns to alert on

| Pattern | Meaning | What to do |
|---|---|---|
| `cursor_lag_max` grows unbounded | Stuck cursor; head-of-line blocking on some shard | See [Troubleshooting → Stuck cursor](./S3-Lifecycle-Troubleshooting.md#stuck-cursor) |
| `walked_max_age` exceeds `walker_interval_minutes × 2` | Walker isn't firing as configured | Check `errors=N` in heartbeat and `SeaweedFS_s3_lifecycle_dispatch_total{outcome="RPC_ERROR"}` |
| `errors=16` (all shards) on every pass | Filer is unreachable or returning errors | Check filer health |
| `SeaweedFS_s3_lifecycle_dispatch_total{outcome="RETRY_LATER"}` rising fast | Server rate-limited or filer overloaded | Lower `cluster_deletes_per_second` or add capacity |
| `SeaweedFS_s3_lifecycle_dispatch_total{outcome="BLOCKED"}` non-zero | Programmatic event content error | Check worker logs for `FATAL_EVENT_ERROR` |
| `duration=Ns` ramping up across passes | Walker is firing too often | Set `walker_interval_minutes` |

## Suggested alerts

```yaml
# `> 0` filters out shards whose gauge is still the proto zero (never
# started); without it, every fresh-install heartbeat triggers the alert.
- alert: S3LifecycleCursorLagHigh
  expr: max(time() * 1e9 - (SeaweedFS_s3_lifecycle_cursor_min_ts_ns > 0)) / 1e9 > 3600
  for: 30m
  annotations:
    summary: "S3 lifecycle replay lag > 1h on shard {{ $labels.shard }}"
    runbook: https://github.com/seaweedfs/seaweedfs/wiki/S3-Lifecycle-Troubleshooting#stuck-cursor

- alert: S3LifecycleWalkerStuck
  expr: max(time() * 1e9 - (SeaweedFS_s3_lifecycle_daily_run_last_walked_ns > 0)) / 1e9 > 86400
  for: 1h
  annotations:
    summary: "S3 lifecycle walker hasn't run in > 24h"
    runbook: https://github.com/seaweedfs/seaweedfs/wiki/S3-Lifecycle-Troubleshooting#walker-stuck

- alert: S3LifecycleDispatchFailures
  expr: |
    rate(SeaweedFS_s3_lifecycle_dispatch_total{outcome=~"RETRY_LATER|BLOCKED|RPC_ERROR"}[5m]) > 0.1
  for: 15m
  annotations:
    summary: "S3 lifecycle delete failure rate > 0.1/s"
```

Adjust thresholds to your cluster's normal levels — these are starting points.
