---
id: S3-Rate-Limiting
title: "S3 Rate Limiting"
sidebar_label: "S3 Rate Limiting"
---

# S3 Rate Limiting

SeaweedFS provides rate limiting features to control resource usage and prevent overload on the S3 API server. There are two mechanisms available:

1. **Concurrent Upload Limiting** - Command-line flags for simple upload throttling
2. **Circuit Breaker** - Advanced per-action and per-bucket rate limiting

## Concurrent Upload Limiting

These command-line flags control the total concurrent upload capacity when starting `weed s3`:

| Flag | Default | Description |
|------|---------|-------------|
| `-concurrentUploadLimitMB` | 128 | Limit total concurrent upload data size in MB |
| `-concurrentFileUploadLimit` | 0 | Limit number of concurrent file uploads (0 = unlimited) |

### Example

```bash
# Limit concurrent uploads to 256MB total data and max 100 files
weed s3 -filer=localhost:8888 -concurrentUploadLimitMB=256 -concurrentFileUploadLimit=100
```

### Behavior

- These limits apply to **write operations** (PUT/POST)
- When limits are exceeded, new requests **wait** until capacity is available (backpressure)
- Requests are not rejected; they queue until the in-flight data/count drops below the limit
- Metrics are exposed via Prometheus: `seaweedfs_s3_inflight_upload_count` and `seaweedfs_s3_inflight_upload_bytes`

## Circuit Breaker

The circuit breaker provides more granular rate limiting that can be configured globally or per-bucket, and by action type.

### Configuration

Circuit breaker is configured via `weed shell` and stored in the filer at `/etc/s3/circuit_breaker.json`. Changes are picked up dynamically by the S3 server.

### Available Actions

| Action | Description |
|--------|-------------|
| `Read` | GET/HEAD object operations |
| `Write` | PUT/POST object operations |
| `List` | List bucket/objects operations |
| `Tagging` | Object tagging operations |
| `Admin` | Administrative operations |

### Limit Types

| Type | Description |
|------|-------------|
| `count` | Maximum number of simultaneous requests |
| `MB` | Maximum total content size (in MB) of simultaneous requests |

### Examples

#### Global Limits

```bash
# Limit globally: max 500 concurrent Read requests, max 200 concurrent Write requests
weed shell
> s3.circuitBreaker -global -type count -actions Read,Write -values 500,200 -apply

# Limit by content size: max 1024MB concurrent Write data globally
> s3.circuitBreaker -global -type MB -actions Write -values 1024 -apply

# Apply same limit to all actions
> s3.circuitBreaker -global -type count -actions Read,Write,List,Tagging,Admin -values 100 -apply
```

#### Per-Bucket Limits

```bash
# Limit specific buckets: max 200 concurrent Reads, 100 concurrent Writes
> s3.circuitBreaker -buckets mybucket,otherbucket -type count -actions Read,Write -values 200,100 -apply

# Different limits per action for a bucket
> s3.circuitBreaker -buckets critical-bucket -type count -actions Read -values 50 -apply
> s3.circuitBreaker -buckets critical-bucket -type count -actions Write -values 10 -apply
```

#### Managing Configuration

```bash
# View current configuration (without -apply)
> s3.circuitBreaker

# Disable circuit breaker for specific buckets
> s3.circuitBreaker -buckets mybucket -disable -apply

# Disable global circuit breaker
> s3.circuitBreaker -global -disable -apply

# Delete circuit breaker config for specific buckets
> s3.circuitBreaker -buckets mybucket -delete -apply

# Delete specific actions from global config
> s3.circuitBreaker -global -actions Read -type count -delete -apply

# Clear all circuit breaker configuration
> s3.circuitBreaker -delete -apply
```

### Behavior

- When limits are exceeded, the server returns **HTTP 429 (Too Many Requests)** with error code `SlowDown`
- When byte limits are exceeded, returns error code `RequestBytesExceed`
- Both global and bucket-specific limits are checked; the request must pass both
- Configuration changes are applied dynamically without restarting the S3 server

### Configuration File Format

The circuit breaker configuration is stored as JSON. Here's an example of what the configuration looks like:

```json
{
  "global": {
    "enabled": true,
    "actions": {
      "Read:count": 500,
      "Write:count": 200,
      "Write:bytes": 1073741824
    }
  },
  "buckets": {
    "mybucket": {
      "enabled": true,
      "actions": {
        "Read:count": 100,
        "Write:count": 50
      }
    }
  }
}
```

## Choosing the Right Approach

| Use Case | Recommended Approach |
|----------|---------------------|
| Simple upload throttling | `-concurrentUploadLimitMB` and `-concurrentFileUploadLimit` flags |
| Per-bucket limits | Circuit breaker with `-buckets` |
| Different limits per action type | Circuit breaker with `-actions` |
| Dynamic configuration changes | Circuit breaker (no restart needed) |
| Reject requests when overloaded | Circuit breaker (returns 429) |
| Queue requests when overloaded | Concurrent upload flags (backpressure) |

## Monitoring

Rate limiting metrics are exposed via Prometheus when `-metricsPort` is configured:

```bash
weed s3 -filer=localhost:8888 -metricsPort=9327
```

Relevant metrics:
- `seaweedfs_s3_inflight_upload_count` - Current number of in-flight uploads
- `seaweedfs_s3_inflight_upload_bytes` - Current bytes of in-flight upload data
- `seaweedfs_s3_request_total` - Total requests by action and status (look for 429 status)



