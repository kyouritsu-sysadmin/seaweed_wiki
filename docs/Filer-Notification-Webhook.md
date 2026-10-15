---
id: Filer-Notification-Webhook
title: "Filer Notification Webhook"
sidebar_label: "Filer Notification Webhook"
---

# Filer Notification Webhook

The webhook notification feature allows SeaweedFS filers to send real-time file system events to external HTTP endpoints. This enables integration with external systems for monitoring, auditing, data processing pipelines, and event-driven workflows.

## Overview

The webhook notification system sends HTTP POST requests containing file system event data (create, update, delete, rename operations) to a configured endpoint. The system includes features like retry logic, concurrent workers, event filtering, and authentication support.

### Architecture: Push Model

**Important**: The webhook notification system uses a **push model**, where SeaweedFS actively sends events to your HTTP endpoint. This architecture is designed for **low to moderate traffic scenarios** where you need real-time event notifications for triggering actions.

**When to Use Webhooks:**
- Real-time monitoring and alerting (low volume)
- Triggering workflows on specific file events
- Audit logging for compliance
- Integration with external systems for selected directories
- Development and testing environments

**When NOT to Use Webhooks:**
- High-traffic production environments with thousands of events per second
- Bulk file processing operations
- Large-scale data synchronization
- Scenarios requiring guaranteed message delivery order

**For High-Traffic Scenarios**, consider these alternatives:
- **[Filer Metadata Events](./Filer-Metadata-Events.md)**: Pull model using local event logs that can be consumed at your own pace
- **Message Queue Systems**: Use Kafka, AWS SQS, or Google Pub/Sub notification backends for scalable event processing
- **Direct gRPC Subscription**: Use the `SubscribeMetadata` RPC API for efficient streaming of metadata changes

The webhook system includes buffering (default 10,000 events) and retry logic, but under sustained high load, events may be dropped if the buffer fills up or if your webhook endpoint cannot keep up with the event rate.

## Limitations and Considerations

### Push Model Constraints

The webhook system operates as a **push model** where SeaweedFS actively pushes events to your endpoint. This has important implications:

**Traffic Limitations:**
- Best suited for **low to moderate traffic** (&lt; 100 events/second sustained)
- Each event requires an HTTP round-trip to your endpoint
- Network latency and endpoint processing time directly impact throughput
- Under sustained high load, the internal buffer may fill up, causing events to be dropped

**Delivery Guarantees:**
- **At-least-once delivery**: With retries enabled, events may be delivered more than once (implement idempotency)
- **No strict ordering**: Events may arrive out of order, especially with retries
- **Best-effort delivery**: Events may be lost if buffer overflows or all retries fail

**Blocking Behavior:**
- Slow webhook endpoints can create backpressure on the filer
- Failed endpoints with max retries can delay event processing
- Consider setting reasonable timeout and retry limits

### Alternatives for High-Traffic Scenarios

If you're experiencing or expecting high event volumes, consider:

1. **Kafka Notifications** (`notification.kafka`): Industry-standard message queue with high throughput
2. **AWS SQS** (`notification.aws_sqs`): Managed queue service with unlimited scaling
3. **Google Pub/Sub** (`notification.google_pub_sub`): Managed pub/sub with global scale
4. **Pull-based Event Logs**: Read from `/topics/.system/log` directory at your own pace (see [Filer Metadata Events](./Filer-Metadata-Events.md))
5. **Direct gRPC Subscription**: Use `SubscribeMetadata` RPC for efficient streaming

## Configuration

### Basic Setup

Add the webhook configuration to your `notification.toml` file. This file should be placed in one of these locations (in descending priority):
- `./notification.toml` (the working directory of the `weed` process)
- `$HOME/.seaweedfs/notification.toml`
- `/etc/seaweedfs/notification.toml`

The file is read once at startup by any process that runs a filer: `weed filer`, `weed server -filer`, and `weed mini`. There is no command line flag for it — place the file where the filer can find it and restart. When the configuration is picked up, the filer logs:

```
Configure notification message queue for webhook
```

To generate a template with all options:

```bash
weed scaffold -config=notification > notification.toml
```

### Minimal Configuration Example

```toml
[notification.webhook]
enabled = true
endpoint = "https://your-server.com/webhook"
```

### Complete Configuration Example

```toml
[notification.webhook]
enabled = true

# Required: The HTTP endpoint to receive webhook notifications
endpoint = "https://your-server.com/webhook"

# Optional: Bearer token for authentication
bearer_token = "your-secret-token-here"

# Optional: HTTP request timeout in seconds (default: 10, range: 1-300)
timeout_seconds = 10

# Optional: Maximum number of retry attempts (default: 3, range: 0-10)
max_retries = 3

# Optional: Initial backoff delay in seconds (default: 3, range: 1-60)
backoff_seconds = 3

# Optional: Maximum backoff delay in seconds (default: 30, range: backoff_seconds-300)
max_backoff_seconds = 30

# Optional: Number of concurrent worker threads (default: 5, range: 1-100)
workers = 5

# Optional: Internal buffer size for queued events (default: 10000, range: 100-1000000)
buffer_size = 10000

# Optional: Filter by event types (if empty, all events are sent)
# Valid values: "create", "update", "delete", "rename"
event_types = ["create", "delete"]

# Optional: Filter by path prefixes (if empty, all paths are monitored)
path_prefixes = ["/important", "/data"]
```

## Configuration Parameters

| Parameter | Type | Required | Default | Range | Description |
|-----------|------|----------|---------|-------|-------------|
| `enabled` | boolean | Yes | false | - | Enable/disable webhook notifications |
| `endpoint` | string | Yes | - | Valid URL | HTTP endpoint to receive webhook POST requests |
| `bearer_token` | string | No | "" | - | Bearer token for Authorization header |
| `timeout_seconds` | integer | No | 10 | 1-300 | HTTP request timeout |
| `max_retries` | integer | No | 3 | 0-10 | Number of retry attempts on failure |
| `backoff_seconds` | integer | No | 3 | 1-60 | Initial backoff delay between retries |
| `max_backoff_seconds` | integer | No | 30 | backoff_seconds-300 | Maximum backoff delay (exponential backoff) |
| `workers` | integer | No | 5 | 1-100 | Number of concurrent worker threads |
| `buffer_size` | integer | No | 10000 | 100-1000000 | Internal queue buffer size |
| `event_types` | array | No | all | create, update, delete, rename | Filter events by type |
| `path_prefixes` | array | No | all | - | Filter events by path prefix |

### One Endpoint, One Target

Only one notification target can be enabled at a time — if two sections (e.g. `[notification.webhook]` and `[notification.kafka]`) are both `enabled = true`, the filer fails at startup. The webhook target itself supports a single endpoint: exactly one `[notification.webhook]` block with one `endpoint`. Named sub-tables such as `[notification.webhook.my_service]` are not additional endpoints; they are ignored.

To route events to multiple services, point the webhook at one service that fans out, or use the Kafka/SQS/Pub-Sub targets and let each consumer subscribe. Use `event_types` and `path_prefixes` to narrow what the single endpoint receives.

## Quick Test

A minimal receiver that prints every event, using only the Python standard library:

```python
from http.server import BaseHTTPRequestHandler, HTTPServer
import json

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        print(json.dumps(json.loads(body), indent=2))
        self.send_response(200)
        self.end_headers()

HTTPServer(("", 3000), Handler).serve_forever()
```

With this `notification.toml` in the directory where you start `weed`:

```toml
[notification.webhook]
enabled = true
endpoint = "http://localhost:3000/webhook"
```

start a filer (`weed mini`, `weed server -filer`, or `weed filer`) and create a file:

```bash
curl -F "file=@test.txt" "http://localhost:8888/data/"
```

The receiver prints a `create` event for `/data/test.txt`.

## Event Types

The webhook notification system supports four types of file system events:

### 1. Create Event
Triggered when a new file or directory is created.
- **Detection**: `new_entry` is present, `old_entry` is null
- **Event Type**: `"create"`

### 2. Update Event
Triggered when an existing file or directory is modified.
- **Detection**: Both `old_entry` and `new_entry` are present, and neither the directory nor the file name changed
- **Event Type**: `"update"`

### 3. Delete Event
Triggered when a file or directory is deleted.
- **Detection**: `old_entry` is present, `new_entry` is null
- **Event Type**: `"delete"`

### 4. Rename Event
Triggered when a file or directory is moved or renamed.
- **Detection**: Both `old_entry` and `new_entry` are present, and the directory or the file name changed
- **Event Type**: `"rename"`

## Webhook Payload Format

### HTTP Request Details

- **Method**: POST
- **Content-Type**: application/json
- **Authorization**: Bearer &#123;bearer_token&#125; (if configured)

### Payload Structure

```json
{
  "key": "/path/to/file.txt",
  "event_type": "create",
  "message": {
    "old_entry": null,
    "new_entry": {
      "name": "file.txt",
      "is_directory": false,
      "attributes": {
        "file_size": 1024,
        "mtime": 1733616000,
        "file_mode": 420,
        "uid": 1000,
        "gid": 1000,
        "mime": "text/plain"
      },
      "chunks": [
        {
          "file_id": "3,01637037d6",
          "offset": 0,
          "size": 1024,
          "mtime": 1733616000
        }
      ]
    },
    "delete_chunks": false,
    "new_parent_path": "",
    "is_from_other_cluster": false
  }
}
```

Fields with empty values are omitted from the JSON: a `create` event has no `old_entry` key at all, a `delete` event has no `new_entry` key, and `delete_chunks` / `new_parent_path` only appear when set. Check for key presence rather than expecting explicit `null`s. `mtime` and `crtime` are unix time in seconds. The examples below show absent fields as `null` for readability.

## Example Payloads

### Create File Event

```json
{
  "key": "/documents/report.pdf",
  "event_type": "create",
  "message": {
    "old_entry": null,
    "new_entry": {
      "name": "report.pdf",
      "is_directory": false,
      "attributes": {
        "file_size": 524288,
        "mtime": 1733616000,
        "file_mode": 420,
        "uid": 1000,
        "gid": 1000,
        "mime": "application/pdf"
      },
      "chunks": [
        {
          "file_id": "4,023f8a9c2e",
          "offset": 0,
          "size": 524288,
          "mtime": 1733616000
        }
      ]
    },
    "delete_chunks": false,
    "new_parent_path": ""
  }
}
```

### Update File Event

```json
{
  "key": "/documents/report.pdf",
  "event_type": "update",
  "message": {
    "old_entry": {
      "name": "report.pdf",
      "is_directory": false,
      "attributes": {
        "file_size": 524288,
        "mtime": 1733616000,
        "file_mode": 420,
        "uid": 1000,
        "gid": 1000,
        "mime": "application/pdf"
      }
    },
    "new_entry": {
      "name": "report.pdf",
      "is_directory": false,
      "attributes": {
        "file_size": 612352,
        "mtime": 1733617200,
        "file_mode": 420,
        "uid": 1000,
        "gid": 1000,
        "mime": "application/pdf"
      },
      "chunks": [
        {
          "file_id": "5,034b9d1a3f",
          "offset": 0,
          "size": 612352,
          "mtime": 1733617200
        }
      ]
    },
    "delete_chunks": true,
    "new_parent_path": ""
  }
}
```

### Delete File Event

```json
{
  "key": "/documents/old_file.txt",
  "event_type": "delete",
  "message": {
    "old_entry": {
      "name": "old_file.txt",
      "is_directory": false,
      "attributes": {
        "file_size": 2048,
        "mtime": 1733610000,
        "file_mode": 420,
        "uid": 1000,
        "gid": 1000,
        "mime": "text/plain"
      }
    },
    "new_entry": null,
    "delete_chunks": true,
    "new_parent_path": ""
  }
}
```

### Rename/Move File Event

```json
{
  "key": "/documents/old_name.txt",
  "event_type": "rename",
  "message": {
    "old_entry": {
      "name": "old_name.txt",
      "is_directory": false,
      "attributes": {
        "file_size": 1024,
        "mtime": 1733616000,
        "file_mode": 420,
        "uid": 1000,
        "gid": 1000,
        "mime": "text/plain"
      }
    },
    "new_entry": {
      "name": "new_name.txt",
      "is_directory": false,
      "attributes": {
        "file_size": 1024,
        "mtime": 1733616000,
        "file_mode": 420,
        "uid": 1000,
        "gid": 1000,
        "mime": "text/plain"
      }
    },
    "delete_chunks": false,
    "new_parent_path": "/archive"
  }
}
```

### Create Directory Event

```json
{
  "key": "/data/new_folder",
  "event_type": "create",
  "message": {
    "old_entry": null,
    "new_entry": {
      "name": "new_folder",
      "is_directory": true,
      "attributes": {
        "file_size": 0,
        "mtime": 1733616000,
        "file_mode": 493,
        "uid": 1000,
        "gid": 1000
      },
      "chunks": []
    },
    "delete_chunks": false,
    "new_parent_path": ""
  }
}
```

## Event Filtering

### Filter by Event Types

To receive only specific types of events, use the `event_types` parameter:

```toml
[notification.webhook]
enabled = true
endpoint = "https://your-server.com/webhook"
# Only receive create and delete events
event_types = ["create", "delete"]
```

### Filter by Path Prefixes

To monitor only specific directories, use the `path_prefixes` parameter:

```toml
[notification.webhook]
enabled = true
endpoint = "https://your-server.com/webhook"
# Only monitor /important and /data directories
path_prefixes = ["/important", "/data"]
```

Prefixes are plain string prefixes on the full path. For renames, the event matches if either the old or the new path matches a prefix.

### Combined Filtering

You can combine both filters:

```toml
[notification.webhook]
enabled = true
endpoint = "https://your-server.com/webhook"
# Only receive create/delete events from /important directory
event_types = ["create", "delete"]
path_prefixes = ["/important"]
```

## Backfilling Existing Files

Webhooks only fire for events that happen while the filer is running. To send events for files that already exist, run `fs.meta.notify` in `weed shell` — it walks a directory tree and publishes a `create` event for every entry to the configured notification target. Place `notification.toml` in the directory where you run `weed shell`.

## Retry and Error Handling

The webhook system includes robust error handling:

1. **Automatic Retries**: Failed requests are automatically retried up to `max_retries` times
2. **Exponential Backoff**: Retry delays double from `backoff_seconds` up to `max_backoff_seconds`, with up to 30% random jitter
3. **Dead Letter Logging**: After exhausting retries, failed messages are written to the filer log (`received dead letter message: ...`); they are not persisted or redelivered
4. **Status Code Validation**: Only 2xx status codes are considered successful; 3xx redirects are followed (the redirect target is cached for subsequent deliveries) and anything else is retried

### Example Retry Configuration

```toml
[notification.webhook]
enabled = true
endpoint = "https://your-server.com/webhook"
max_retries = 5
backoff_seconds = 2
max_backoff_seconds = 60
```

This configuration will retry up to 5 times with delays around 2s, 4s, 8s, 16s, 32s (each with up to 30% jitter).

## Performance Tuning

**Note**: While you can tune these parameters, remember that webhooks use a push model best suited for low to moderate traffic. For high-traffic scenarios (>1000 events/second sustained), consider using Kafka, message queues, or the pull-based metadata event logs instead.

### Concurrent Workers

Adjust the number of concurrent workers based on your webhook endpoint's capacity:

```toml
[notification.webhook]
enabled = true
endpoint = "https://your-server.com/webhook"
workers = 10  # Increase for higher throughput
```

**Trade-offs**: More workers increase throughput but also increase the load on your webhook endpoint and network connections.

### Buffer Size

Increase buffer size for high-volume environments to prevent event loss during traffic bursts:

```toml
[notification.webhook]
enabled = true
endpoint = "https://your-server.com/webhook"
buffer_size = 50000  # Handle more concurrent events
```

**Trade-offs**: Larger buffers consume more memory and may delay detection of delivery failures. If events are being generated faster than they can be delivered, increasing the buffer only delays the inevitable - you need to either increase processing capacity or switch to a pull-based model.

## Security Considerations

### Authentication

Use bearer token authentication to secure your webhook endpoint:

```toml
[notification.webhook]
enabled = true
endpoint = "https://your-server.com/webhook"
bearer_token = "your-secret-token-here"
```

The token will be sent as: `Authorization: Bearer your-secret-token-here`

### HTTPS

Always use HTTPS endpoints in production:

```toml
[notification.webhook]
enabled = true
endpoint = "https://your-server.com/webhook"  # Use HTTPS
```

### Webhook Receiver Validation

Your webhook receiver should:
1. Validate the bearer token (if configured)
2. Validate request content type is `application/json`
3. Parse and validate JSON payload structure
4. Respond with 2xx status code for successful processing
5. Respond quickly — acknowledge first, then process asynchronously; a delivery worker is tied up until your endpoint responds or `timeout_seconds` elapses
6. Implement idempotency to handle potential duplicate events (delivery is at-least-once and may be out of order)

## Example Webhook Receiver (Node.js/Express)

```javascript
const express = require('express');
const app = express();

app.use(express.json());

app.post('/webhook', (req, res) => {
  // Validate bearer token
  const authHeader = req.headers.authorization;
  const expectedToken = 'Bearer your-secret-token-here';
  
  if (authHeader !== expectedToken) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  // Process webhook payload
  const { key, event_type, message } = req.body;
  
  console.log(`Received ${event_type} event for: ${key}`);
  
  // Process based on event type
  switch (event_type) {
    case 'create':
      handleCreate(key, message);
      break;
    case 'update':
      handleUpdate(key, message);
      break;
    case 'delete':
      handleDelete(key, message);
      break;
    case 'rename':
      handleRename(key, message);
      break;
  }

  // Return success response
  res.status(200).json({ success: true });
});

app.listen(3000, () => {
  console.log('Webhook receiver listening on port 3000');
});
```

## Example Webhook Receiver (Python/Flask)

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

EXPECTED_TOKEN = "your-secret-token-here"

@app.route('/webhook', methods=['POST'])
def webhook():
    # Validate bearer token
    auth_header = request.headers.get('Authorization')
    if auth_header != f'Bearer {EXPECTED_TOKEN}':
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Parse webhook payload
    data = request.json
    key = data.get('key')
    event_type = data.get('event_type')
    message = data.get('message')
    
    print(f"Received {event_type} event for: {key}")
    
    # Process based on event type
    if event_type == 'create':
        handle_create(key, message)
    elif event_type == 'update':
        handle_update(key, message)
    elif event_type == 'delete':
        handle_delete(key, message)
    elif event_type == 'rename':
        handle_rename(key, message)
    
    # Return success response
    return jsonify({'success': True}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
```

## Troubleshooting

### Enable Debug Logging

Check SeaweedFS logs for webhook-related errors:

```bash
weed filer -v=1
```

### Common Issues

1. **Webhook not receiving events**
   - Verify `enabled = true` in configuration
   - Check endpoint URL is correct and accessible
   - Verify filer is using the notification.toml file
   - Check event/path filters aren't blocking events

2. **Authentication failures**
   - Verify bearer_token matches on both sides
   - Check Authorization header format

3. **Timeout errors**
   - Increase `timeout_seconds`
   - Optimize webhook receiver response time
   - Check network connectivity

4. **Events being dropped**
   - Increase `buffer_size`
   - Increase `workers` for higher throughput
   - Check dead letter queue logs

5. **Webhook endpoint receiving duplicate events**
   - This is expected behavior with retry logic
   - Implement idempotency in your webhook receiver

6. **Consistent high latency or event backlog**
   - Check if event rate exceeds webhook capacity
   - Monitor buffer utilization in logs
   - Consider migrating to Kafka, SQS, or pull-based event logs for higher throughput
   - Webhooks are a push model designed for low-moderate traffic; high sustained traffic requires alternative architectures

## Monitoring

Monitor webhook health through logs:

```bash
# Watch for failed webhook deliveries
weed filer -v=1 | grep webhook

# Look for dead letter queue messages (failed after all retries)
weed filer -v=1 | grep "dead letter"
```

## Related Documentation

- [Filer Metadata Events](./Filer-Metadata-Events.md) - Understanding the underlying event system
- [Filer Setup](./Filer-Setup.md) - Basic filer configuration
- [Notification Configuration](https://github.com/seaweedfs/seaweedfs/blob/master/weed/command/scaffold/notification.toml) - Example notification.toml

## Use Cases

### Appropriate Webhook Use Cases (Low-Moderate Traffic)

1. **Real-time Alerting**: Send notifications to Slack, email, or monitoring systems for critical file events
2. **Selective Audit Logging**: Track file system changes for specific sensitive directories
3. **Triggered Workflows**: Start business processes when specific files are uploaded (e.g., invoice processing)
4. **Development/Test Environments**: Real-time event monitoring during development
5. **Configuration Change Detection**: Monitor configuration directories for changes
6. **Compliance Notifications**: Alert on access or modifications to regulated data
7. **Backup Triggers**: Trigger backups for specific critical files or directories

### Consider Alternatives For (High Traffic)

1. **Large-scale Search Indexing**: Use Kafka → Elasticsearch pipeline for high-volume indexing
2. **Bulk Data Processing**: Use pull-based event logs or Kafka for processing thousands of files
3. **Content Distribution at Scale**: Use Kafka or message queues for reliable high-volume sync
4. **Data Lake Integration**: Use Kafka or direct event log consumption for streaming at scale
5. **High-frequency Monitoring**: Use pull-based metrics or dedicated monitoring integrations

**Rule of Thumb**: If you're processing more than 50-100 events per second sustained, or if you have large batch operations, webhooks are likely not the right tool. Use Kafka, message queues, or pull-based event logs instead.

## References

- Feature Pull Request: [#6962](https://github.com/seaweedfs/seaweedfs/pull/6962)
- Issue: [#7617](https://github.com/seaweedfs/seaweedfs/issues/7617)

