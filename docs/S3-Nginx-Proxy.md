---
id: S3-Nginx-Proxy
title: "S3 Nginx Proxy"
sidebar_label: "S3 Nginx Proxy"
---

It's a common concept to put a proxy in front of S3 that handles requests. Nginx is well suited for this and can be used to handle TLS and virtual-hosted style bucket URLs (using subdomains instead of subfolders).

For virtual-hosted style URL buckets, you'll need to add a [wildcard DNS record](https://en.wikipedia.org/wiki/Wildcard_DNS_record) for your S3 subdomain.


Make sure the config sets the `X-Forwarded-Host` and optionally the `X-Forwarded-Port` if you are using a non-standard port. SeaweedFS will automatically combine these headers to reconstruct the correct host information for signature verification.

## aws:SourceIp and Trusted Proxies

The `X-Forwarded-For` and `X-Real-IP` headers set by the proxy are also used for `aws:SourceIp` condition evaluation in S3 bucket policies and IAM policies — but **only** when the proxy's IP is in the configured trusted-proxy allowlist. Without an allowlist, SeaweedFS uses the direct TCP peer address for `aws:SourceIp` (matching AWS S3 semantics) to prevent spoofing.

To enable forwarded-header trust, add the proxy's IP or CIDR to `security.toml`:

```toml
[s3.trusted_proxies]
white_list = "10.10.10.0/24"  # comma separated; bare IPs or CIDRs
```

See [S3 Policy Conditions — Source IP Handling](./S3-Policy-Conditions.md#source-ip-handling) for the full resolution logic.

## Explicit External URL for Signature Verification

In scenarios where the reverse proxy cannot easily be configured to send the necessary headers, or in complex multi-hop environments, you can use the `-s3.externalUrl` flag to explicitly set the public-facing URL of the S3 service.

When `-s3.externalUrl` is set, SeaweedFS will use the host and port from this URL for all S3 signature verification, ignoring incoming `Host` or `X-Forwarded-*` headers.

### Usage Example

```bash
# SeaweedFS S3 is reachable externally at https://s3.example.com:9000
weed s3 -s3.externalUrl=https://s3.example.com:9000
```

Alternatively, set the environment variable:
```bash
export WEED_S3_EXTERNAL_URL=https://s3.example.com:9000
```

This flag is also supported in `weed mini` and `weed filer`:
```bash
weed mini -s3.externalUrl=http://localhost:9000
weed filer -s3 -s3.externalUrl=https://s3.mycorp.internal
```

### Why use this?
AWS Signature V4 includes the `Host` header in the signed payload. If SeaweedFS is behind a proxy, the `Host` header it receives might be the internal address (e.g., `localhost:8333`), while the client signed the request with the external address (e.g., `s3.example.com`). Setting `-s3.externalUrl` ensures SeaweedFS uses the correct host for signature validation.

## Reverse Proxy with URL Path Prefixes

SeaweedFS S3 API supports the `X-Forwarded-Prefix` header for scenarios where a reverse proxy strips URL path prefixes before forwarding requests. This is common when hosting the S3 API under a subpath like `/s3/` or `/api/s3/`.

### How X-Forwarded-Prefix Works

When a reverse proxy strips a URL prefix:
1. **Client request**: `https://example.com/s3/my-bucket/my-object`
2. **Proxy strips prefix** and forwards: `https://backend:8333/my-bucket/my-object`
3. **Proxy adds header**: `X-Forwarded-Prefix: /s3`

SeaweedFS will:
1. First attempt signature verification using the **original path** (`/s3/my-bucket/my-object`)
2. Fall back to verification using the **stripped path** (`/my-bucket/my-object`) if the first attempt fails

This ensures both regular S3 requests and presigned URLs work correctly with reverse proxies that strip prefixes.

### Example Use Cases

- **API Gateway**: `/api/s3/bucket/object` → `/bucket/object`
- **Multi-tenant setup**: `/tenant1/s3/bucket/object` → `/bucket/object`  
- **Subpath hosting**: `/storage/s3/bucket/object` → `/bucket/object`

### Important Notes

- The `X-Forwarded-Prefix` header should contain the stripped prefix (e.g., `/s3`)
- `X-Forwarded-Port` is automatically combined with `X-Forwarded-Host` for non-standard ports
- Standard ports (80 for HTTP, 443 for HTTPS) are omitted from the host header automatically
- Both regular S3 authentication and presigned URLs are supported
- This feature works with all S3 operations that require signature verification

Additionally, make sure that `proxy_request_buffering` is `off` (default is `on`), as the proxy will buffer the request, and send the request to the backend as a whole instead of chunked, and again the signature computed by the client side will be different as it would have taken into account the `Transfer-Encoding: chunked` header that is dropped by the proxy when it buffers.

### Example Nginx config

#### Standard Configuration (without URL prefix stripping)

```
upstream seaweedfs { 
        # Hash on uploadId query string in the GET request create consistency for multipart uploads,
        # only necessary when using local embedded filer store (leveldb)
	hash $arg_uploadId consistent;
	server localhost:8333 fail_timeout=0; 
	keepalive 20;
}

## Also you can use unix domain socket instead for better performance:
# upstream seaweedfs { server unix:/tmp/seaweedfs-s3-8333.sock; keepalive 20;}

server {
	listen 443 ssl;

	# Assumes that your subdomain is s3
	# The regex will support path style as well as virtual-hosted style bucket URLs
	# path style: http://s3.yourdomain.com/mybucket
	# virtual-hosted style: http://mybucket.s3.yourdomain.com
	server_name ~^(?:(?<bucket>[^.]+)\.)?s3\.yourdomain\.com;

	ignore_invalid_headers off;

    # Make sure that we can upload files larger than 1MB (nginx default cutoff)
	client_max_body_size 0;

	proxy_buffering off;

	proxy_set_header Host $host;
	proxy_set_header X-Real-IP $remote_addr;
	proxy_set_header X-Forwarded-For $remote_addr;
	proxy_set_header X-Forwarded-Host $host;
	proxy_set_header X-Forwarded-Port $server_port;

	proxy_set_header X-Forwarded-Proto $scheme;

	proxy_connect_timeout 300;
	proxy_http_version 1.1;
	proxy_set_header Connection "";
	proxy_request_buffering off;
	chunked_transfer_encoding off;

	# If bucket subdomain is not empty,
	# rewrite request to backend.
	if ($bucket != "") {
		rewrite (.*) /$bucket$1 last;
	}

	location / {
		proxy_pass http://seaweedfs;
	}

	ssl on;
	ssl_certificate /{path_to_ssl_cert}/cert.pem;
	ssl_certificate_key /{path_to_ssl_cert}/key.pem;
}
```

#### Configuration with URL Prefix Stripping (X-Forwarded-Prefix)

For scenarios where you need to host SeaweedFS S3 API under a subpath:

```
upstream seaweedfs { 
	hash $arg_uploadId consistent;
	server localhost:8333 fail_timeout=0; 
	keepalive 20;
}

server {
	listen 443 ssl;
	server_name yourdomain.com;

	ignore_invalid_headers off;

    # Make sure that we can upload files larger than 1MB (nginx default cutoff)
	client_max_body_size 0;

	proxy_buffering off;

	proxy_set_header Host $host;
	proxy_set_header X-Real-IP $remote_addr;
	proxy_set_header X-Forwarded-For $remote_addr;
	proxy_set_header X-Forwarded-Host $host;
	proxy_set_header X-Forwarded-Port $server_port;
	proxy_set_header X-Forwarded-Proto $scheme;

	proxy_connect_timeout 300;
	proxy_http_version 1.1;
	proxy_set_header Connection "";
	proxy_request_buffering off;
	chunked_transfer_encoding off;

	# S3 API under /s3/ subpath
	location /s3/ {
		# Set the X-Forwarded-Prefix header to the stripped prefix
		proxy_set_header X-Forwarded-Prefix /s3;
		
		# Strip the /s3 prefix before forwarding to backend
		rewrite ^/s3/(.*) /$1 break;
		
		proxy_pass http://seaweedfs;
	}

	# Alternative: S3 API under /api/s3/ subpath  
	location /api/s3/ {
		proxy_set_header X-Forwarded-Prefix /api/s3;
		rewrite ^/api/s3/(.*) /$1 break;
		proxy_pass http://seaweedfs;
	}

	ssl on;
	ssl_certificate /{path_to_ssl_cert}/cert.pem;
	ssl_certificate_key /{path_to_ssl_cert}/key.pem;
}
```
