---
id: Volume-Server-API
title: "Volume Server API"
sidebar_label: "Volume Server API"
---

You can append to any HTTP API with `&pretty=y` to see a formatted json output.

## Volume Server Reads

GET/HEAD operations are direction http requests to file ids, e.g., `http://127.0.0.1:8080/3,01637037d6`.

| URL Parameter | Description | Default |
| ---- | -- | -- |
| readDeleted | if "true", possibly read a deleted file. Does not work if volume server is restarted or the volume is compacted. | false |
| width  | if the stored file has ".png", ".jpg", ".jpeg", ".gif", apply resizing | empty |
| height | if the stored file has ".png", ".jpg", ".jpeg", ".gif", apply resizing | empty |
| mode   | if resizing, "fit", or "fill". Or just resizing, unless width==height, which default to thumbnail mode | empty |
| crop_x1 | if the stored file has ".png", ".jpg", ".jpeg", ".gif", apply cropping, requires: 0 &lt;= value &lt; image width   | empty |
| crop_y1 | if the stored file has ".png", ".jpg", ".jpeg", ".gif", apply cropping, requires: 0 &lt;= value &lt; image height | empty |
| crop_x2 | if the stored file has ".png", ".jpg", ".jpeg", ".gif", apply cropping, requires: crop_x1 &lt; value &lt;= image width | empty |
| crop_y2 | if the stored file has ".png", ".jpg", ".jpeg", ".gif", apply cropping, requires: crop_y1 &lt; value &lt;= image height | empty |

| Request Header | Description | Default |
| ---- | -- | -- |
| Authorization | Json Web Token for reads issued by master | empty |
| Range | for http range request, support multiple ranges | empty |
| If-Modified-Since | format "Mon, 02 Jan 2006 15:04:05 GMT", if not modified, return StatusNotModified 304  | empty |
| If-None-Match | if matches the ETag, return StatusNotModified 304  | empty |
| Accept-Encoding: gzip | compress response by gzip | empty |


## Volume Server Writes

### Upload File

```bash
curl -F file=@/home/chris/myphoto.jpg http://127.0.0.1:8080/3,01637037d6
{"size": 43234}
```

The size returned is the size stored on SeaweedFS, sometimes the file is automatically gzipped based on the file extension or mime type [(see when compression will be applied automatically)](https://github.com/seaweedfs/seaweedfs/blob/c42b95c596f762dcca2bc9c7e7a918ab8ca8b206/weed/util/compression.go#L111).

| URL Parameter | Description | Default |
| ---- | -- | -- |
| fsync | if "true", the write will incur an fsync operation | false |
| type | if "replicate", this is a replicated request, so the writes will not be replicated to other volume servers | empty |
| ts | modification timestamp in epoch seconds | empty |
| cm | content is a chunk manifest file | empty |

| Request Header | Description | Default |
| ---- | -- | -- |
| Content-Encoding: gzip|the uploaded content is already compressed to gzip | empty |
| Content-Type | use the specified content type | "application/octet-stream" |
| Content-MD5  | verify the uploaded content by MD5. MD5 digest needs to be encoded as base64 string. | empty |
| Authorization | Json Web Token for writes issued by master | empty |
| Seaweed-xxxxx | Any key-value pair with custom `Seaweed-` prefix. All the custom key-value data are stored as json, should be less than 64KB. The key will trim out the `Seaeweed-` prefix and then convert into a canonical header key. See https://golang.org/pkg/net/http/#CanonicalHeaderKey | empty |



### Upload File Directly

```bash
curl -F file=@/home/chris/myphoto.jpg http://localhost:9333/submit
{"fid":"3,01fbe0dc6f1f38","fileName":"myphoto.jpg","fileUrl":"localhost:8080/3,01fbe0dc6f1f38","size":68231}
```

This API is just for convenience. The master server would get a file id and store the file to the right volume server.
It is a convenient API and does not support different parameters when assigning file id. (or you can add the support and make a pull request.)

### Delete File

```bash
curl -X DELETE http://127.0.0.1:8080/3,01637037d6
```

### View Manifest File Content for chunked big file

```bash
curl http://127.0.0.1:8080/3,01637037d6?cm=false
```

### Check Volume Server Health

The `/healthz` endpoint checks if the volume server is healthy. It returns:
- `200 OK` - Server is healthy
- `503 Service Unavailable` - Server is unhealthy (shutting down or lost connection to master)

```bash
curl -I "http://localhost:8080/healthz"
HTTP/1.1 200 OK
```

This endpoint is suitable for Kubernetes liveness and readiness probes. It only checks local server conditions and will not fail due to other volume servers being unavailable.

### Check Volume Server Status

```bash
curl "http://localhost:8080/status?pretty=y"
{
  "Version": "0.34",
  "Volumes": [
    {
      "Id": 1,
      "Size": 1319688,
      "RepType": "000",
      "Version": 2,
      "FileCount": 276,
      "DeleteCount": 0,
      "DeletedByteCount": 0,
      "ReadOnly": false
    },
    {
      "Id": 2,
      "Size": 1040962,
      "RepType": "000",
      "Version": 2,
      "FileCount": 291,
      "DeleteCount": 0,
      "DeletedByteCount": 0,
      "ReadOnly": false
    },
    {
      "Id": 3,
      "Size": 1486334,
      "RepType": "000",
      "Version": 2,
      "FileCount": 301,
      "DeleteCount": 2,
      "DeletedByteCount": 0,
      "ReadOnly": false
    },
    {
      "Id": 4,
      "Size": 8953592,
      "RepType": "000",
      "Version": 2,
      "FileCount": 320,
      "DeleteCount": 2,
      "DeletedByteCount": 0,
      "ReadOnly": false
    },
    {
      "Id": 5,
      "Size": 70815851,
      "RepType": "000",
      "Version": 2,
      "FileCount": 309,
      "DeleteCount": 1,
      "DeletedByteCount": 0,
      "ReadOnly": false
    },
    {
      "Id": 6,
      "Size": 1483131,
      "RepType": "000",
      "Version": 2,
      "FileCount": 301,
      "DeleteCount": 1,
      "DeletedByteCount": 0,
      "ReadOnly": false
    },
    {
      "Id": 7,
      "Size": 46797832,
      "RepType": "000",
      "Version": 2,
      "FileCount": 292,
      "DeleteCount": 0,
      "DeletedByteCount": 0,
      "ReadOnly": false
    }
  ]
}
```
