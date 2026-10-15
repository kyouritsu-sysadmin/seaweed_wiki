---
id: Security-Overview
title: "Security Overview"
sidebar_label: "Security Overview"
---

# Overview

Since SeaweedFS is a distributed system with many volume servers, the volume servers have the risk of being changed without proper access control. We want to have the freedom to place a volume server anywhere we want, with the confidence that nobody can tamper the data.

> **Looking for FIPS 140-2/140-3 compliance information?** See [Cryptography and FIPS Compliance](./Cryptography-and-FIPS-Compliance.md). 

## Understanding Communication Layers

SeaweedFS has two separate communication layers that must be secured independently:

### gRPC Communication (Control Plane)
Used for metadata operations and cluster coordination:
- S3 ↔ Filer: Getting bucket info, file metadata
- Filer ↔ Master: Getting volume assignments, cluster info
- Volume ↔ Master: Heartbeats, volume management
- **Configured via**: `[grpc.*]` sections in security.toml

### HTTP/HTTPS Communication (Data Plane)
Used for actual file data uploads/downloads:
- S3/Filer/Client → Volume Server: Uploading and downloading actual file content
- S3 → Filer: File data operations (when S3 acts as a proxy)
- **Configured via**: `[https.*]` sections in security.toml

### Configuration Sections Summary

| Configuration Block | Purpose |
|---------------------|---------|
| `[grpc.client]` | Used by clients (S3, mount, filer.copy, backup, etc.) to connect to any gRPC server |
| `[grpc.filer]`, `[grpc.master]`, `[grpc.volume]`, `[grpc.s3]` | Server-side gRPC mTLS - secures gRPC endpoints |
| `[https.client]` | Client-side HTTPS configuration - tells clients (S3/Filer/etc.) to use HTTPS for HTTP connections |
| `[https.volume]`, `[https.master]`, `[https.filer]` | Server-side HTTPS configuration - makes servers accept HTTPS connections |

**Important**: 
- `[https.client]` with `enabled = true` is required for clients to use HTTPS when connecting to HTTPS-enabled servers
- If you enable `[https.filer]` on the Filer server, you must also enable `[https.client]` so that S3 API can connect via HTTPS
- Otherwise, you'll get "client sent an HTTP request to an HTTPS server" errors

## Security Features

We will address the volume servers first. The following items are not covered, yet:
- master server http REST services

Starting with version 2.84, the Filer HTTP REST services can be secured
with a JWT, by setting `jwt.filer_signing.key` and
`jwt.filer_signing.read.key` in `security.toml`.

In summary, here are what can be achieved. 

Server | Service | Note  
---|---|---
master | gRPC | secured by mutual TLS
volume | gRPC | secured by mutual TLS
filer  | gRPC | secured by mutual TLS
master | http | "weed master -disableHttp", disable http operations, only gRPC operations are allowed.
filer  | http | **Before version 2.84:** "weed filer -disableHttp", disable http operations, only gRPC operations are allowed. This works with "weed mount" by FUSE. It does **not work** with the [S3 Gateway](./Amazon-S3-API.md), as this does HTTP calls to the Filer.<br /><br /> **Starting with version 2.84**: secured by JWT, by setting `jwt.filer_signing.key` and `jwt.filer_signing.read.key` in `security.toml`. **This now works with the [Amazon S3 API](./Amazon-S3-API.md).**
volume | http write | set `jwt.signing.key` in `security.toml` in master and volume servers to check token for write operations
volume | http read | unprotected, but url is not guessable

# Generate `security.toml` file

See [Security Configuration](./Security-Configuration.md)

> **Rotating certificates without restarts?** SeaweedFS re-reads cert/key files from disk and picks up rotated material (e.g. from Kubernetes cert-manager) without a process restart on both gRPC mTLS and HTTPS servers. See [Security Configuration#Certificate Rotation Without Restarts (k8s cert-manager)](./Security-Configuration.md#Certificate Rotation Without Restarts (k8s cert-manager)).

Servers in SeaweedFS usually support 2 kinds of operations: gRPC and REST.

# Securing gRPC operations

The following operations are implemented via gRPC.
* requests from filer to master
* requests from master to volume servers
* delete operations from filer or other clients (mount, s3, filer.copy, filer.replicate, etc) to volume servers
* requests from clients to filer

All gRPC operations can optionally be secured via mutual TLS, by customizing the `security.toml` file. See [Security Configuration](./Security-Configuration.md).

# Securing Volume Servers

Besides gRPC mentioned above, volume servers can only be changed by file upload, update, and delete operations. Json Web Token (JWT) is used to authorize access for each file id.

## JWT-based access control
To enable JWT-based access control,
1. generate `security.toml` file by `weed scaffold -config=security`
1. set `jwt.signing.key` to a secret string — or set the `WEED_JWT_SIGNING_KEY` environment variable to avoid storing the secret in the config file (see [Security Configuration#Using Environment Variables for Secrets](./Security-Configuration.md#Using Environment Variables for Secrets))
1. copy the same `security.toml` file to the masters and all volume servers.

> **Re-enabling Volume UI**
>
> By default, if the `jwt.signing.key` is set, the web UI on the volume servers is disabled. You can re-enable the web UI by
> setting `access.ui=true` in `security.toml`. Despite some information leakage (as the UI is unauthenticted), this should not
> pose a security risk, as the UI is purely read-only.

## How JWT-based access control works
* To upload a new file, when requesting a new fileId via `http://&lt;master&gt;:&lt;port&gt;/dir/assign`, the master will use the `jwt.signing.key` to generate and sign a JWT, and set it to response header `Authorization`. The JWT is valid for 10 seconds.
* To update or delete a file by fileId, the JWT can be read from the response header `Authorization` of  `http://&lt;master&gt;:&lt;port&gt;/dir/lookup?fileId=xxxxx`.
* When sending upload/update/delete HTTP operations to a volume server, the request header `Authorization` should be the JWT string. The operation is authorized after the volume server validates the JWT with `jwt.signing.key`.

JWT Summary:
* JWT is set in `/dir/assign` or `/dir/lookup` response header `Authorization`
* JWT is read from request header `Authorization`
* JWT is valid for 10 seconds.
* JWT only has permission to create/modify/delete one fileId.
* The volume server HTTP access is only for read, and only if the fileId is known. There are no way to iterate all files.
* All other volume server HTTP accesses are disabled when `jwt.signing` is enabled.

## JWT for Read Access Control
The volume server can also check JWT for reads. This mode does not work with `weed filer`. But this could be useful if the volume server is exposed to public and you do not want anyone to access it with a URL, e.g., paid content.

* To enable it, set the `jwt.signing.read.key` in `security.toml` file.
* To obtain a JWT for read, the JWT can be read from the response header `Authorization` of  `http://&lt;master&gt;:&lt;port&gt;/dir/lookup?fileId=xxxxx&read=yes`.

# Securing Filer HTTP with JWT

To enable JWT-based access control for the Filer,

1. generate `security.toml` file by `weed scaffold -config=security`
2. set `jwt.filer_signing.key` to a secret string (or use `WEED_JWT_FILER_SIGNING_KEY` env var) — and optionally `jwt.filer_signing.read.key` as well (or `WEED_JWT_FILER_SIGNING_READ_KEY`)
3. copy the same `security.toml` file to the filers and all S3 proxies.

If `jwt.filer_signing.key` is configured: When sending upload/update/delete HTTP operations to a filer server, the request header `Authorization` should be the JWT string (`Authorization: Bearer [JwtToken]`). The operation is authorized after the filer validates the JWT with `jwt.filer_signing.key`.

The JwtToken can be generated by calling `security.GenJwtForFilerServer(signingKey SigningKey, expiresAfterSec int)` in `github.com/seaweedfs/seaweedfs/weed/security` package.
https://github.com/seaweedfs/seaweedfs/blob/9b941773805400c520558d83aed633adc821988c/weed/security/jwt.go#L53

If `jwt.filer_signing.read.key` is configured: When sending GET or HEAD requests to a filer server, the request header `Authorization` should be the JWT string (`Authorization: Bearer [JwtToken]`). The operation is authorized after the filer validates the JWT with `jwt.filer_signing.read.key`.

The S3 API Gateway reads the above JWT keys and sends authenticated
HTTP requests to the filer.

### JWT Scoping

The Filer HTTP JWT can optionally include claims to restrict access to specific paths and HTTP methods.

*   `allowed_prefixes`: A list of path prefixes. If present, the request path must match at least one of these prefixes.
*   `allowed_methods`: A list of HTTP methods (e.g., "GET", "POST"). If present, the request method must match one of these methods.

Example JWT payload:
```json
{
  "exp": 17000,
  "allowed_prefixes": ["/hls/movie123/", "/subtitles/movie123/"],
  "allowed_methods": ["GET", "HEAD"]
}
```
This is useful for generating short-lived, scoped tokens for direct client access (e.g., for downloading content) without exposing global read/write permissions.

