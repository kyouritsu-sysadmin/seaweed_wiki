---
id: System-Metrics
title: "System Metrics"
sidebar_label: "System Metrics"
---

SeaweedFS uses [Prometheus](https://prometheus.io/) to store the metrics and [Grafana](https://grafana.com/grafana) to visualize them. 

SeaweedFS supports both push and pull metrics.

# Push Metrics
SeaweedFS can publish metrics to [Prometheus Push Gateway](https://github.com/prometheus/pushgateway), and the gateway pass along to the Prometheus server.

Master | Volume Server | Filer => Prometheus Push Gateway => Prometheus Server => Grafana

Note: Setting Prometheus, push gateway, and Grafana can be simplified with this https://github.com/evnsio/prom-stack

## Configuration

Just add a metrics address to `weed master` or `weed server` command line options. If you have multiple masters, please add it to all the master command line options.

```
weed master -master.metrics.address=<protocol><prometheus_gateway_host_name>:<prometheus_gateway_port>
# example
weed master -master.metrics.address=localhost:9091               # Defaults to http://localhost:9091
weed master -master.metrics.address=https://example.com

weed server -master.metrics.address=<protocol><prometheus_gateway_host_name>:<prometheus_gateway_port>
# example
weed server -master.metrics.address=localhost:9091               # Defaults to http://localhost:9091
weed server -master.metrics.address=https://example.com
```

The SeaweedFS filer or volume servers will read this metrics configuration from the master, and report the metrics directly to the Prometheus Gateway. Filer and volume servers need to be restarted for the changes to take effect.

# Pull Metrics
SeaweedFS can also start with ports accepting Prometheus metrics queries.

```
weed server -metricsPort=1234
weed master -metricsPort=1235
weed volume -metricsPort=1236
weed filer  -metricsPort=1237
```
Note: All server should be running on different ports for accepting prometheus metrics queries.

And then you can configure your Prometheus to crawl them periodically.

# Plugin Worker Metrics

Maintenance workers publish their own metrics when started with a metrics port —
`weed worker -metricsPort=9328` for the Go worker, `--metrics-port 9328` for the
Rust one (see [Lance Maintenance Worker](./Lance-Maintenance-Worker.md)). Both serve `/health`, `/ready` and
`/metrics` on it, so one scrape config covers either.

Pick a port that is free: master 9324, volume 9325, filer 9326 and s3 9327 are
the convention, so a worker on the same host wants 9328.

| Metric | Type | Labels |
|--------|------|--------|
| `SeaweedFS_worker_build_info` | gauge | `worker_id`, `version` |
| `SeaweedFS_worker_connected` | gauge | 1 while the control stream is up |
| `SeaweedFS_worker_stream_events_total` | counter | `event` = connected, closed, failed, shutdown |
| `SeaweedFS_worker_slots_used` / `_slots_total` | gauge | `lane` = detection, execution |
| `SeaweedFS_worker_detections_total` | counter | `job_type`, `result` |
| `SeaweedFS_worker_detection_seconds` | histogram | `job_type` |
| `SeaweedFS_worker_proposals_total` | counter | `job_type` |
| `SeaweedFS_worker_objects_seen_total` | counter | `job_type` |
| `SeaweedFS_worker_objects_skipped_total` | counter | `job_type`, `reason` |
| `SeaweedFS_worker_jobs_total` | counter | `job_type`, `result` |
| `SeaweedFS_worker_job_seconds` | histogram | `job_type` |
| `SeaweedFS_worker_previews_total` | counter | `result` |

The Lance worker adds what it reclaimed: `SeaweedFS_worker_lance_fragments_removed_total`,
`_lance_rows_indexed_total`, `_lance_versions_removed_total`, `_lance_bytes_reclaimed_total`.

**The pair worth alerting on is `objects_seen_total` against `objects_skipped_total`.**
A sweep that proposes nothing because there is nothing to do and a sweep that
proposes nothing because it could read nothing produce the same
`proposals_total`; skips are what tells them apart, and the usual cause is
credentials.

> [!NOTE]
> `SeaweedFS_admin_workers_connected`, `SeaweedFS_admin_worker_slots` and
> `SeaweedFS_admin_worker_events_total` are fed by the older maintenance-worker
> queue, **not** the plugin system. Plugin workers — Go or Rust — do not appear
> in them. Use the `SeaweedFS_worker_*` family above for those.

# Dashboard

The dashboard is shared at https://github.com/seaweedfs/seaweedfs/blob/master/other/metrics/grafana_seaweedfs.json

If you modify the dashboard, please share your revisions.

## Example Dashboard

![](https://pbs.twimg.com/media/ET7tiEcUMAIet9M?format=jpg&name=large)
