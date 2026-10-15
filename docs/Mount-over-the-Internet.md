---
id: Mount-over-the-Internet
title: "Mount over the Internet"
sidebar_label: "Mount over the Internet"
---

# Mount over the Internet

This page covers running `weed mount` or the [CSI driver](https://github.com/seaweedfs/seaweedfs-csi-driver) on a different network than the SeaweedFS cluster, with only mTLS between them. For general TLS setup see [Security Configuration](./Security-Configuration.md).

The mount client opens exactly two paths:

- **Filer gRPC** (HTTP port + 10000, e.g. 8888 → 18888) for all metadata
- **Volume server HTTP** for file data — unless proxied through the filer, see Option A

The mount never talks to the master. Keep the master private in every setup.

The simplest and safest approach is still a VPN (WireGuard, Tailscale, or site-to-site): private addresses keep working and nothing is exposed. If you cannot use one, the two setups below expose only client-cert-gated ports. Both were verified end to end (see Verification).

## Option A: expose only the filer

The mount proxies all reads and writes through the filer, so the volume servers stay private. Only two filer ports are exposed: gRPC and HTTPS.

Server side `security.toml`:

```toml
[grpc]
ca = "/etc/seaweedfs/ca.crt"

[grpc.filer]
cert = "/etc/seaweedfs/server.crt"
key = "/etc/seaweedfs/server.key"

# used by servers when dialing each other
[grpc.client]
cert = "/etc/seaweedfs/server.crt"
key = "/etc/seaweedfs/server.key"

# filer HTTPS; ca makes the port require and verify client certs
[https.filer]
cert = "/etc/seaweedfs/server.crt"
key = "/etc/seaweedfs/server.key"
ca = "/etc/seaweedfs/ca.crt"
```

Mount side `security.toml`:

```toml
[grpc]
ca = "/etc/seaweedfs/ca.crt"

[grpc.client]
cert = "/etc/seaweedfs/client.crt"
key = "/etc/seaweedfs/client.key"

[https.client]
enabled = true
cert = "/etc/seaweedfs/client.crt"
key = "/etc/seaweedfs/client.key"
ca = "/etc/seaweedfs/ca.crt"
```

Mount with:

```bash
weed mount -filer=filer.example.com:8888 -dir=/mnt/weed -volumeServerAccess=filerProxy
```

or set the CSI driver parameter `volumeServerAccess: "filerProxy"`.

Trade-off: all data funnels through the filer, so its bandwidth becomes the ceiling.

## Option B: direct volume access

Better throughput: the mount talks to volume servers directly, so every volume server is exposed on its HTTPS port.

Server side, replace `[https.filer]` with:

```toml
[https.volume]
cert = "/etc/seaweedfs/server.crt"
key = "/etc/seaweedfs/server.key"
ca = "/etc/seaweedfs/ca.crt"
```

Then:

- Run the filer with `-disableHttp`. Its HTTP port then serves only embedded static assets — no file API, no UI, no TUS, not even `/healthz`.
- Start each volume server with `-publicUrl=&lt;externally routable host:port&gt;` and mount with `-volumeServerAccess=publicUrl` if the internal addresses are not routable from the clients.
- The mount side `security.toml` is the same as Option A.
- Servers upload to each other over HTTP too, so the server-side `security.toml` also needs `[https.client]` enabled with the server cert.

## Certificates

- gRPC verifies the chain against `grpc.ca` plus the CommonName only. The `[https.*]` sections use standard hostname verification, so server certs must carry SANs for every name or IP the clients dial.
- Any cert signed by `grpc.ca` is accepted. Use `allowed_commonNames` in the server-side `[grpc.*]` sections to narrow which client certs may connect.
- There is no CRL/OCSP support: a leaked cert stays valid until it expires. Keep lifetimes short.

## Caveats

- The TLS handshake surface is open to the internet with no rate limiting. A VPN keeps that surface closed.
- These ports are safe to expose only with the client-cert (`ca`) settings above; without them, HTTP endpoints such as the filer UI and volume `/status` answer anyone.
- On a shared internal network with untrusted-but-not-hostile actors, this same setup applies and the caveats matter much less.

## Verification

Both options were tested with 4.41: a rejected TLS handshake without a client cert on the filer HTTPS, volume HTTPS, and filer gRPC ports; plaintext HTTP rejected; `-disableHttp` leaving only static assets; and an 8 MB write and remount read-back with matching md5 through each path. In Option A the mount's only connections were the two filer ports, confirming data flows through the filer proxy.
