---
id: TUS-Resumable-Uploads
title: "TUS Resumable Uploads"
sidebar_label: "TUS Resumable Uploads"
---

# TUS Resumable Uploads

SeaweedFS supports the [TUS](https://tus.io) protocol for resumable file uploads. TUS is an open protocol for resumable uploads built on HTTP, allowing clients to upload files in chunks and resume interrupted uploads.

## Features

- **Resumable uploads**: Resume interrupted uploads without re-sending data
- **Chunked uploads**: Upload large files in smaller pieces
- **Parallel uploads**: Upload parts of a file concurrently and concatenate them server-side
- **Simple protocol**: Standard HTTP methods with custom headers
- **Wide client support**: Libraries available for JavaScript, Python, Go, Java, and more

## Configuration

TUS is enabled by default at the `/.tus` endpoint.

| Filer flag | Server flag | Default | Description |
|------------|-------------|---------|-------------|
| `-tusBasePath` | `-filer.tusBasePath` | `/.tus` | Endpoint base path; set to empty to disable TUS |
| `-tusMaxSizeMB` | `-filer.tusMaxSizeMB` | `5120` | Maximum upload size in MB |
| `-tusSessionExpiry` | `-filer.tusSessionExpiry` | `24h` | Incomplete upload sessions are cleaned up after this duration, e.g. `48h`, `7h30m` |

### Filer Command

```bash
# Default: TUS enabled at /.tus
weed filer -master=localhost:9333

# Custom path
weed filer -master=localhost:9333 -tusBasePath=uploads/tus

# 20GB max upload, keep incomplete sessions for 3 days
weed filer -master=localhost:9333 -tusMaxSizeMB=20480 -tusSessionExpiry=72h

# Disable TUS
weed filer -master=localhost:9333 -tusBasePath=
```

### Server Command

When using `weed server`, use the `-filer.`-prefixed options:

```bash
# Default: TUS enabled at /.tus
weed server -filer=true

# Custom path
weed server -filer=true -filer.tusBasePath=uploads/tus

# 20GB max upload, keep incomplete sessions for 3 days
weed server -filer=true -filer.tusMaxSizeMB=20480 -filer.tusSessionExpiry=72h

# Disable TUS
weed server -filer=true -filer.tusBasePath=
```

## TUS Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `OPTIONS` | `/.tus/` | Server capability discovery |
| `POST` | `/.tus/{path}` | Create new upload session |
| `HEAD` | `/.tus/.uploads/{id}` | Get current upload offset |
| `PATCH` | `/.tus/.uploads/{id}` | Upload data at offset |
| `DELETE` | `/.tus/.uploads/{id}` | Cancel upload |

## Supported Extensions

- `creation`: Create new upload sessions
- `creation-with-upload`: Upload data in the creation request
- `termination`: Cancel/delete uploads
- `concatenation`: Concatenate completed partial uploads into one file, enabling parallel uploads

## Usage Examples

### 1. Discover Server Capabilities

```bash
curl -X OPTIONS http://localhost:8888/.tus/ \
  -H "Tus-Resumable: 1.0.0"
```

Response headers:
```
Tus-Resumable: 1.0.0
Tus-Version: 1.0.0
Tus-Extension: creation,creation-with-upload,termination,concatenation
Tus-Max-Size: 5368709120
```

### 2. Create Upload Session

```bash
curl -X POST http://localhost:8888/.tus/path/to/file.txt \
  -H "Tus-Resumable: 1.0.0" \
  -H "Upload-Length: 1000" \
  -H "Upload-Metadata: filename dGVzdC50eHQ=,content-type dGV4dC9wbGFpbg=="
```

Response:
```
HTTP/1.1 201 Created
Location: /.tus/.uploads/abc123-uuid
```

### 3. Upload Data

```bash
curl -X PATCH http://localhost:8888/.tus/.uploads/abc123-uuid \
  -H "Tus-Resumable: 1.0.0" \
  -H "Upload-Offset: 0" \
  -H "Content-Type: application/offset+octet-stream" \
  --data-binary @file.txt
```

Response:
```
HTTP/1.1 204 No Content
Upload-Offset: 1000
```

### 4. Check Upload Progress

```bash
curl -I http://localhost:8888/.tus/.uploads/abc123-uuid \
  -H "Tus-Resumable: 1.0.0"
```

Response:
```
HTTP/1.1 200 OK
Upload-Offset: 500
Upload-Length: 1000
```

### 5. Resume Interrupted Upload

```bash
# First, check current offset
OFFSET=$(curl -s -I http://localhost:8888/.tus/.uploads/abc123-uuid \
  -H "Tus-Resumable: 1.0.0" | grep -i "Upload-Offset" | cut -d' ' -f2 | tr -d '\r')

# Resume from offset
curl -X PATCH http://localhost:8888/.tus/.uploads/abc123-uuid \
  -H "Tus-Resumable: 1.0.0" \
  -H "Upload-Offset: $OFFSET" \
  -H "Content-Type: application/offset+octet-stream" \
  --data-binary @remaining_data.bin
```

### 6. Cancel Upload

```bash
curl -X DELETE http://localhost:8888/.tus/.uploads/abc123-uuid \
  -H "Tus-Resumable: 1.0.0"
```

### 7. Parallel Upload with Concatenation

Upload parts of one file concurrently as partial uploads, then concatenate them in order:

```bash
# Create a partial upload per part (Upload-Length is that part's size)
curl -i -X POST http://localhost:8888/.tus/path/to/file.txt \
  -H "Tus-Resumable: 1.0.0" \
  -H "Upload-Concat: partial" \
  -H "Upload-Length: 500"
# Location: /.tus/.uploads/part1-uuid

curl -i -X POST http://localhost:8888/.tus/path/to/file.txt \
  -H "Tus-Resumable: 1.0.0" \
  -H "Upload-Concat: partial" \
  -H "Upload-Length: 500"
# Location: /.tus/.uploads/part2-uuid

# Upload the parts, concurrently if desired
curl -X PATCH http://localhost:8888/.tus/.uploads/part1-uuid \
  -H "Tus-Resumable: 1.0.0" \
  -H "Upload-Offset: 0" \
  -H "Content-Type: application/offset+octet-stream" \
  --data-binary @part1.bin &
curl -X PATCH http://localhost:8888/.tus/.uploads/part2-uuid \
  -H "Tus-Resumable: 1.0.0" \
  -H "Upload-Offset: 0" \
  -H "Content-Type: application/offset+octet-stream" \
  --data-binary @part2.bin &
wait

# Concatenate the completed partials, in order, into the final file
curl -X POST http://localhost:8888/.tus/path/to/file.txt \
  -H "Tus-Resumable: 1.0.0" \
  -H "Upload-Concat: final;/.tus/.uploads/part1-uuid /.tus/.uploads/part2-uuid"
```

Notes:

- A completed partial does not appear at the target path; the file is created by the final request.
- The final request must not include `Upload-Length`; the file size is the sum of the partial sizes, capped by `-tusMaxSizeMB`.
- All listed partials must be finished before concatenation; concatenating an unfinished partial fails.
- Concatenation consumes the partials, so each partial can be used only once.
- Partials that are never concatenated expire like any other session after `-tusSessionExpiry`.

## TUS Headers

### Request Headers

| Header | Required | Description |
|--------|----------|-------------|
| `Tus-Resumable` | Yes | Protocol version (must be `1.0.0`) |
| `Upload-Length` | POST | Total file size in bytes |
| `Upload-Offset` | PATCH | Current byte offset |
| `Upload-Metadata` | Optional | Base64-encoded key-value pairs |
| `Upload-Concat` | Optional | `partial` creates a partial upload; `final;&lt;url1&gt; &lt;url2&gt; ...` concatenates completed partials |
| `Content-Type` | PATCH | Must be `application/offset+octet-stream` |
| `Content-Length` | PATCH | Size of data being uploaded |

### Response Headers

| Header | Description |
|--------|-------------|
| `Tus-Resumable` | Protocol version |
| `Tus-Version` | Supported versions |
| `Tus-Extension` | Supported extensions |
| `Tus-Max-Size` | Maximum upload size (5GB default) |
| `Upload-Offset` | Current byte offset |
| `Upload-Length` | Total file size |
| `Location` | Upload URL (on POST) |

## Client Libraries

TUS has official and community client libraries for many languages:

- **JavaScript**: [tus-js-client](https://github.com/tus/tus-js-client)
- **Python**: [tuspy](https://github.com/tus/tus-py-client)
- **Go**: [go-tus](https://github.com/eventials/go-tus)
- **Java**: [tus-java-client](https://github.com/tus/tus-java-client)
- **iOS**: [TUSKit](https://github.com/tus/TUSKit)
- **Android**: [tus-android-client](https://github.com/tus/tus-android-client)

See the [TUS implementations page](https://tus.io/implementations.html) for more options.

## JavaScript Example

```javascript
import * as tus from "tus-js-client";

const file = document.querySelector("input[type=file]").files[0];

const upload = new tus.Upload(file, {
  endpoint: "http://localhost:8888/.tus/uploads/",
  retryDelays: [0, 3000, 5000, 10000, 20000],
  parallelUploads: 3, // uses the concatenation extension

  metadata: {
    filename: file.name,
    filetype: file.type,
  },
  onError: (error) => {
    console.log("Upload failed:", error);
  },
  onProgress: (bytesUploaded, bytesTotal) => {
    const percentage = ((bytesUploaded / bytesTotal) * 100).toFixed(2);
    console.log(`${percentage}%`);
  },
  onSuccess: () => {
    console.log("Upload complete:", upload.url);
  },
});

upload.start();
```

## Python Example

```python
from tusclient import client

my_client = client.TusClient('http://localhost:8888/.tus/')

uploader = my_client.uploader('path/to/file.txt', chunk_size=1024*1024)
uploader.upload()
```

## Go Example

```go
package main

import (
    "os"
    "github.com/eventials/go-tus"
)

func main() {
    f, _ := os.Open("file.txt")
    defer f.Close()

    client, _ := tus.NewClient("http://localhost:8888/.tus/", nil)
    upload, _ := tus.NewUploadFromFile(f)
    
    uploader, _ := client.CreateUpload(upload)
    uploader.Upload()
}
```

## How It Works

1. **Session Creation**: Client sends POST to create an upload session, specifying the total file size. Server returns a unique upload URL.

2. **Data Upload**: Client sends PATCH requests with chunks of data at the current offset. Server stores chunks and returns the new offset.

3. **Resume**: If upload is interrupted, client sends HEAD to get current offset, then continues with PATCH from that offset.

4. **Completion**: When all data is uploaded (offset equals file size), the server assembles the final file at the target path.

5. **Cleanup**: Upload sessions are stored temporarily and cleaned up after completion or expiration.

## Limitations

- Maximum upload size: 5GB by default, configurable with `-tusMaxSizeMB`; a concatenated file's total size is capped by the same limit
- Session expiration: 24 hours by default, configurable with `-tusSessionExpiry`; expired sessions are removed by an hourly background cleanup
- Concatenation partials are single-use: once concatenated into a final upload they are consumed and cannot be reused
- `concatenation-unfinished` is not supported: all partials must be complete before the final request

## See Also

- [Filer Server API](./Filer-Server-API.md)
- [Large File Handling](./Large-File-Handling.md)
- [Filer Setup](./Filer-Setup.md)



