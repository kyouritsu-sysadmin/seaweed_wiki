---
id: Filer-Active-Active-cross-cluster-continuous-synchronization
title: "Filer Active Active cross cluster continuous synchronization"
sidebar_label: "Filer Active Active cross cluster continuous synchronization"
---

# What can it do?

If you have two or more SeaweedFS clusters using filers, now you can asynchronously replicate changes to each other.

It can run either in Active-Active mode or Active-Passive mode.

# Usage

From any computer that can access filer and volume servers in both SeaweedFS clusters, run one of these commands:

```
# synchronize each cluster
weed filer.sync -a <filer1_host>:<filer1_port> -b <filer2_host>:<filer2_port>

# synchronize only specific folders:
weed filer.sync -a <filer1_host>:<filer1_port> -b <filer2_host>:<filer2_port> -a.path /filer1/path1 -b.path /filer2/path2

# active-passive mode, replicate all changes in filer1 to filer2
weed filer.sync -a <filer1_host>:<filer1_port> -b <filer2_host>:<filer2_port> -isActivePassive

```

At the beginning, it will bootstrap from the beginning of time, or resume from the last replication checkpoint. Later, it will just run continuously and persist checkpoints periodically.

## On Kubernetes with the SeaweedFS Operator

If you are running SeaweedFS on Kubernetes via the [SeaweedFS Operator](https://github.com/seaweedfs/seaweedfs-operator), you can run `weed filer.sync` as a sidecar inside the filer pod itself, so it shares the pod's lifecycle and dials the local filer over loopback. Each `ComponentSpec` exposes a `sidecars` field that accepts arbitrary `v1.Container` entries.

```yaml
apiVersion: seaweed.seaweedfs.com/v1
kind: Seaweed
metadata:
  name: prod
spec:
  image: chrislusf/seaweedfs:latest
  master:
    replicas: 3
  volume:
    replicas: 3
    requests:
      storage: 100Gi
  filer:
    replicas: 2
    sidecars:
      - name: filer-sync
        image: chrislusf/seaweedfs:latest
        command:
          - weed
          - filer.sync
          - -a=localhost:8888
          - -b=remote-filer.dr.svc.cluster.local:8888
          - -isActivePassive
```

The sidecar runs alongside every filer replica. For active-passive replication you typically want a single sync process — pin the sidecar to one replica with a separate single-replica filer, or run `filer.sync` as its own `Deployment` instead.

## How it works?

Each filer has its own local change logs. `weed filer.sync` will read the logs and replay them in the other cluster.

`weed filer.sync` remembers each filer's "signature" and replication checkpoints. So you can stop `weed filer.sync` and start it later safely.

Also, the "signature" will ensure same change will only be applied once in one filer. Active-Active synchronization would not cause multiple ping-pong changes for one file update.


## More clusters?

If there are 3 or more clusters, you can choose fully connected setup or chained setup, or any more complicated topology.

In a sense, you can mix and match to setup filer synchronization as you wish.

### Fully Connected Setup?

It is tempting to create a fully connected network topology. E.g., run one `weed filer.sync` for each pair of clusters. The fully connected topology may seem to be able to provide redundancy in case of network failures.

```
cluster1 <-- filer.sync --> cluster2
cluster2 <-- filer.sync --> cluster3
cluster3 <-- filer.sync --> cluster1
```

However, this topology has a loop. 

Every filer will leave a signature on each message. The `filer.sync` use the signatures to avoid processing the same message twice. But for any node within a loop, the same message can come from two difference neighbors. So this mechanism could not help to identify the duplicated the messages.

Because most metadata messages are idempotent, the network loop is not efficient but still works OK.

But for directory renaming, the execution order matters. So the loop should be avoided, or the directories will be inconsistent.

### Chained Setup
```
cluster1 <-- filer.sync --> cluster2 <-- filer.sync --> cluster3
```

### One-Master-Multiple-Slaves

With `weed filer.sync -isActivePassive` configured, nothing stops you from setting up multiple following clusters.

```
cluster1  -- filer.sync --> cluster2
cluster1  -- filer.sync --> cluster3
cluster1  -- filer.sync --> cluster4
```

### Multiple-Master-Multiple-Slaves

This should also work, multiple active-active clusters, with chained following clusters.

```

cluster1  <-- filer.sync --> cluster2 -- filer.sync --> cluster3 -- filer.sync --> cluster4
                                                             |
                                                             +----- filer.sync --> cluster5
```

### Different Sync strategy for different folders

Here the first folder is active-active synchronized on 2 clusters, but the `/home/public` on `cluster1` is single directionally synchronized to `cluster2`

```
cluster1:/home/chris <-- filer.sync --> cluster2:/Users/chris

cluster1:/home/public -- filer.sync --> cluster2:/home/www/public

``` 

## Filer Proxy 

By default, `filer.sync` will upload files directly to volume servers. This is the most efficient way to avoid extra hops and distribute the network traffic.

However, it uses volume server IP addresses configured for the local cluster. `filer.sync` is usually cross network. These IPs may not be accessible to the `filer.sync` because of network configurations (for example cluster1 and cluster2 are on different hosting providers). In this case, it could be useful to use the `filerProxy` option to make `filer.sync` does all the transfers through the filer. In order to enable this option, `-a.filerProxy` or/and `-b.filerProxy` can be added to the `weed filer.sync` process starting command line.

## Cross-cluster TLS

`filer.sync` opens two channels to each filer: gRPC (port `18888` by default) for the change-event stream, and HTTP (`8888`) for chunk transfer whenever `-a.filerProxy` / `-b.filerProxy` is used. Both have to be reachable, and both can be secured.

If the two clusters share a CA, one `security.toml` with `[grpc] ca` plus `[grpc.client] cert`/`key` covers everything. When they don't, give each side its own file:

```
weed filer.sync \
  -a=hub.example.com:8888.18888 -a.security=/certs/hub-security.toml \
  -b=edge-filer:8888.18888      -b.security=/certs/edge-security.toml
```

Each file supplies the `[grpc.client]` certificate used to dial that cluster, and, when `[https.client] enabled = true`, the certificate for its HTTP leg. The `-a.security` / `-b.security` files are read only for that cluster, so one side can use TLS while the other stays plaintext.

### Verification is not symmetric

The two channels do not check certificates the same way:

- **gRPC** verifies only that the server certificate chains up to `[grpc] ca`. The hostname is *not* checked, so a certificate issued for a different name still works. Constrain who may connect with `allowed_commonNames` or `grpc.allowed_wildcard_domain` on the server side instead.
- **HTTP** is an ordinary Go HTTPS client and does full hostname verification, so the certificate's SAN must match the host you passed in `-a` / `-b`.

Since `[grpc] ca` takes a PEM bundle, a cluster reached through a proxy that presents its own certificate can be trusted by concatenating both CAs. That also means any CA in the bundle can vouch for any SeaweedFS gRPC server the process dials, so keep public CAs out of it.

### Behind a Kubernetes Ingress

An L4 route (TCP passthrough, a `LoadBalancer` Service, or a NodePort) is the better option, because it leaves the filer's own mTLS intact end to end. If all you can create is `Ingress` objects, this works with nginx-ingress.

Every gRPC method path is `/filer_pb.SeaweedFiler/...`, so one host on 443 serves both channels through two path rules. Annotations, all prefixed `nginx.ingress.kubernetes.io/`:

```yaml
# path /filer_pb.SeaweedFiler -> filer svc 18888
backend-protocol: "GRPC"
auth-tls-secret: "<ns>/seaweed-ca"
auth-tls-verify-client: "on"
proxy-read-timeout: "3600"      # 60s default cuts the metadata stream

# path / -> filer svc 8888
backend-protocol: "HTTP"
auth-tls-secret: "<ns>/seaweed-ca"
auth-tls-verify-client: "on"
proxy-read-timeout: "3600"
proxy-body-size: "0"            # 1m default truncates chunk transfers
```

`auth-tls` is a per-location annotation, so it belongs on both rules. nginx performs the client certificate check, and the remote `filer.sync` presents its `[grpc.client]` certificate to satisfy it.

`backend-protocol: "GRPCS"` does not work here: nginx-ingress emits no `grpc_ssl_*` directives, so `proxy-ssl-secret` cannot supply a client certificate to the backend and the filer rejects the connection with `tlsv13 alert certificate required`. Only `GRPC` (h2c) is available, which makes the hop from nginx to the filer plaintext, so the hub filer's `[grpc.filer] cert`/`key` must be unset. Since every in-cluster caller would otherwise dial that filer with TLS credentials, this effectively moves the authentication boundary from the filer to the ingress.

The remote side then reaches the cluster with:

```
weed filer.sync -a=filer.example.com:443.443 -a.filerProxy -a.security=/certs/a-security.toml ...
```

```toml
# a-security.toml
[grpc]
ca = "/certs/ca-bundle.crt"     # SeaweedFS CA + the ingress certificate's CA

[grpc.client]
cert = "/certs/client.crt"
key  = "/certs/client.key"

[https.client]
enabled = true
cert = "/certs/client.crt"
key  = "/certs/client.key"
ca   = "/certs/ca-bundle.crt"
```

The ingress certificate's SAN has to match `filer.example.com`, since the HTTP leg verifies it.

## Debug log
To see all detail of transfers executed by `filer.sync`, options `-a.debug` or/and `-b.debug` can be added to the `weed filer.sync` process starting command line.

## Server-Side Encryption (SSE)

`weed filer.sync` copies encrypted chunk data and encryption metadata as-is between clusters — no decryption or re-encryption occurs. This means both clusters must share the same SSE key configuration:

- **SSE-S3**: Both filers must use the same KEK (configured via `WEED_S3_SSE_KEK` or `WEED_S3_SSE_KEY` in `security.toml`, or the same `/etc/s3/sse_kek` file on the filer).
- **SSE-KMS**: Both clusters must have access to the same KMS provider and keys.
- **SSE-C**: Works automatically since the encryption metadata is copied with the chunks.

> **Warning:** If the destination cluster uses different SSE keys, replicated encrypted objects will be stored but cannot be decrypted. Reads will fail or return corrupt data.

## Limitations

This should be fairly scalable. However, it is limited by network bandwidth and latency. So even though changes are received within milliseconds and replayed right away, there would be data discrepancies if a file is changed quickly in two distant data centers.

For large clusters, the rate of change may be so high that the replication can not catch up. You may want to only synchronize a specific folder to reduce the work load.

