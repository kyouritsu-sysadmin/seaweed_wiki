---
id: Security-Configuration
title: "Security Configuration"
sidebar_label: "Security Configuration"
---



For an overview of SeaweedFS security architecture and communication layers, see [Security-Overview](./Security-Overview.md).
For FIPS 140-3 compliance information, see [Cryptography-and-FIPS-Compliance](./Cryptography-and-FIPS-Compliance.md).

The first step is generating `security.toml` file via `weed scaffold -config=security`:

```
$ weed scaffold -config=security

# Put this file to one of the location, with descending priority
#    ./security.toml
#    $HOME/.seaweedfs/security.toml
#    /etc/seaweedfs/security.toml
# this file is read by master, volume server, and filer

# comma separated origins allowed to make requests to the filer and s3 gateway.
# enter in this format: https://domain.com, or http://localhost:port
[cors.allowed_origins]
values = "*"

# this jwt signing key is read by master and volume server, and it is used for write operations:
# - the Master server generates the JWT, which can be used to write a certain file on a volume server
# - the Volume server validates the JWT on writing
# the jwt defaults to expire after 10 seconds.
[jwt.signing]
key = ""
expires_after_seconds = 10           # seconds

# by default, if the signing key above is set, the Volume UI over HTTP is disabled.
# by setting ui.access to true, you can re-enable the Volume UI. Despite
# some information leakage (as the UI is not authenticated), this should not
# pose a security risk.
[access]
ui = false

# by default the filer UI is enabled. This can be a security risk if the filer is exposed to the public
# and the JWT for reads is not set. If you don't want the public to have access to the objects in your
# storage, and you haven't set the JWT for reads it is wise to disable access to directory metadata.
# This disables access to the Filer UI, and will no longer return directory metadata in GET requests.
[filer.expose_directory_metadata]
enabled = true

# this jwt signing key is read by master and volume server, and it is used for read operations:
# - the Master server generates the JWT, which can be used to read a certain file on a volume server
# - the Volume server validates the JWT on reading
# NOTE: jwt for read is only supported with master+volume setup. Filer does not support this mode.
[jwt.signing.read]
key = ""
expires_after_seconds = 10           # seconds


# If this JWT key is configured, Filer only accepts writes over HTTP if they are signed with this JWT:
# - f.e. the S3 API Shim generates the JWT
# - the Filer server validates the JWT on writing
# the jwt defaults to expire after 10 seconds.
#
# NOTE: This key is ALSO used as a fallback signing key for S3 STS if s3.iam.config does not specify a signingKey.
[jwt.filer_signing]
key = ""
expires_after_seconds = 10           # seconds

# If this JWT key is configured, Filer only accepts reads over HTTP if they are signed with this JWT:
# - f.e. the S3 API Shim generates the JWT
# - the Filer server validates the JWT on writing
# the jwt defaults to expire after 10 seconds.
[jwt.filer_signing.read]
key = ""
expires_after_seconds = 10           # seconds

# gRPC mTLS configuration
# All gRPC TLS authentications are mutual (mTLS)
# The values for ca, cert, and key are paths to the certificate/key files
# The host name is not checked, only that the peer certificate chains up to the
# ca below, so the certificate files can be shared. Restrict who may connect with
# allowed_wildcard_domain here or allowed_commonNames per component.
# ca accepts a PEM bundle, so peers issued by different CAs can be trusted at once.
[grpc]
ca = ""
# Set wildcard domain for enable TLS authentication by common names
allowed_wildcard_domain = "" # .mycompany.com

# Volume server gRPC options (server-side)
# Enables mTLS for incoming gRPC connections to volume server
[grpc.volume]
cert = ""
key = ""
allowed_commonNames = ""    # comma-separated SSL certificate common names

# Master server gRPC options (server-side)
# Enables mTLS for incoming gRPC connections to master server
[grpc.master]
cert = ""
key = ""
allowed_commonNames = ""    # comma-separated SSL certificate common names

# Filer server gRPC options (server-side)
# Enables mTLS for incoming gRPC connections to filer server
[grpc.filer]
cert = ""
key = ""
allowed_commonNames = ""    # comma-separated SSL certificate common names
# Server components also dial their peers, reusing cert/key above by default.
# If your CA issues serverAuth-only certificates, set a separate pair for the
# outgoing direction. Available in every [grpc.<component>] section.
client_cert = ""
client_key = ""

# S3 server gRPC options (server-side)
# Enables mTLS for incoming gRPC connections to S3 server
[grpc.s3]
cert = ""
key = ""
allowed_commonNames = ""    # comma-separated SSL certificate common names

[grpc.msg_broker]
cert = ""
key = ""
allowed_commonNames = ""    # comma-separated SSL certificate common names

[grpc.msg_agent]
cert = ""
key = ""
allowed_commonNames = ""    # comma-separated SSL certificate common names

# gRPC client configuration for outgoing gRPC connections
# Used by clients (S3, mount, backup, benchmark, filer.copy, filer.replicate, upload, etc.)
# when connecting to any gRPC server (master, volume, filer)
# filer.sync can load a separate file per cluster with -a.security / -b.security, see
# https://github.com/seaweedfs/seaweedfs/wiki/Filer-Active-Active-cross-cluster-continuous-synchronization#cross-cluster-tls
[grpc.client]
cert = ""
key = ""

# HTTPS client configuration for outgoing HTTP connections
# Used by S3, mount, filer.copy, backup, and other clients when communicating with master/volume/filer
# Set enabled=true to use HTTPS instead of HTTP for data operations (separate from gRPC)
# If [https.filer] or [https.volume] are enabled on servers, clients must have [https.client] enabled=true
[https.client]
enabled = false  # Set to true to enable HTTPS for all outgoing HTTP client connections
cert = ""        # Client certificate for mTLS (optional if server doesn't require client cert)
key = ""         # Client key for mTLS (optional if server doesn't require client cert)
ca = ""          # CA certificate to verify server certificates (required when enabled=true)

# Volume server HTTPS options (server-side)
# Enables HTTPS for incoming HTTP connections to volume server
[https.volume]
cert = ""
key = ""
ca = ""

# Master server HTTPS options (server-side)
# Enables HTTPS for incoming HTTP connections to master server (web UI, HTTP API)
[https.master]
cert = ""
key = ""
ca = ""

# Filer server HTTPS options (server-side)
# Enables HTTPS for incoming HTTP connections to filer server (web UI, HTTP API)
[https.filer]
cert = ""
key = ""
ca = ""
# disable_tls_verify_client_cert = true|false (default: false)

# Trusted reverse proxies allowed to set X-Forwarded-For / X-Real-Ip for
# aws:SourceIp condition evaluation in S3 bucket and IAM policies. When the
# direct TCP peer is in this list, forwarded headers are honored; otherwise
# the direct peer address is used (matching AWS S3 semantics). Leave empty to
# always use the direct peer, which is the safe default.
# Can also be set via env var: WEED_S3_TRUSTED_PROXIES_WHITE_LIST
[s3.trusted_proxies]
white_list = ""  # comma separated; bare IPs or CIDRs, e.g. "10.10.10.0/24"

# white list. It's checking request ip address.
[guard]
white_list = ""
```

## Using Environment Variables for Secrets

All `security.toml` values can be overridden via environment variables, which avoids storing secrets in plaintext config files. This is especially useful for:

- **NixOS** and other declarative systems where config files are stored in Git
- **Docker / Kubernetes** deployments using secret management
- **CI/CD** pipelines where secrets come from a vault

The convention is: prefix with `WEED_`, uppercase the key path, and replace `.` with `_`.

### JWT Signing Keys

Instead of putting JWT keys in `security.toml`:
```shell
# Volume server JWT (write)
export WEED_JWT_SIGNING_KEY="your-secret-key"

# Volume server JWT (read)
export WEED_JWT_SIGNING_READ_KEY="your-read-secret-key"

# Filer JWT (write)
export WEED_JWT_FILER_SIGNING_KEY="your-filer-secret-key"

# Filer JWT (read)
export WEED_JWT_FILER_SIGNING_READ_KEY="your-filer-read-secret-key"
```

### TLS Certificate Paths

```shell
# gRPC CA certificate
export WEED_GRPC_CA="/path/to/ca.crt"

# gRPC volume server certificates
export WEED_GRPC_VOLUME_CERT="/path/to/volume.crt"
export WEED_GRPC_VOLUME_KEY="/path/to/volume.key"

# gRPC master server certificates
export WEED_GRPC_MASTER_CERT="/path/to/master.crt"
export WEED_GRPC_MASTER_KEY="/path/to/master.key"

# gRPC filer server certificates
export WEED_GRPC_FILER_CERT="/path/to/filer.crt"
export WEED_GRPC_FILER_KEY="/path/to/filer.key"

# gRPC client certificates
export WEED_GRPC_CLIENT_CERT="/path/to/client.crt"
export WEED_GRPC_CLIENT_KEY="/path/to/client.key"
```

### Docker Compose Example

```yaml
services:
  master:
    image: chrislusf/seaweedfs:latest
    environment:
      WEED_JWT_SIGNING_KEY: "${JWT_SECRET}"
      WEED_JWT_FILER_SIGNING_KEY: "${JWT_FILER_SECRET}"
      WEED_GRPC_CA: /run/secrets/ca.crt
      WEED_GRPC_MASTER_CERT: /run/secrets/master.crt
      WEED_GRPC_MASTER_KEY: /run/secrets/master.key
    secrets:
      - ca.crt
      - master.crt
      - master.key
    command: master
```

### Mixing Config File and Environment Variables

You can keep non-sensitive settings in `security.toml` and override only the secrets via environment variables. Environment variables take precedence over values in the config file.

```toml
# security.toml — no secrets here, safe to commit to Git
[jwt.signing]
key = ""                         # overridden by WEED_JWT_SIGNING_KEY
expires_after_seconds = 10

[grpc]
ca = "/etc/seaweedfs/certs/ca.crt"
```

For the full list of environment variable conventions, see [Environment Variables](./Environment-Variables.md).

## Certificate Rotation Without Restarts (k8s cert-manager)

SeaweedFS re-reads certificate and key files from disk periodically, so rotating certs (e.g. when cert-manager renews a `Certificate` resource and updates the mounted `Secret`) does **not** require a process restart.

**Scope:**

| Surface | Cert/key rotates without restart | CA rotates without restart | Refresh window |
|---|---|---|---|
| gRPC mTLS (`[grpc.*]`) — server and client, all roles (master, volume, filer, s3, mq.broker, mq.agent, admin, worker, mount, backup, upload, …) | Yes | No (loaded once) | ~5h |
| HTTPS server (`[https.master]`, `[https.volume]`, `[https.filer]`, `[https.s3]`, `[https.admin]`, WebDav) | Yes | No (ClientCAs loaded once) | ~5h |
| HTTPS client (`[https.client]`) — used by FUSE mount, backup, upload, filer.copy, filer→volume, s3→filer/volume | Yes | No (RootCAs loaded once) | ~5h |

New TLS handshakes pick up the rotated cert. In-flight connections keep the cert they were established with, which is normal TLS behavior. HTTPS clients hold pooled TCP connections via `http.Transport`, so rotation takes effect as pooled connections recycle (idle timeout + churn), not instantly on the first renewal.

**CA rotation caveat.** Only leaf cert/key pairs hot-reload. CA bundles (`[grpc.ca]`, `[https.*.ca]`, `[https.client.ca]`) are loaded once at startup. In k8s, cert-manager typically rotates leaf certs far more often than CAs — if your CA rolls, you still need a rolling restart.

**How it works.** A `GetCertificate` callback is wired into every server-side `tls.Config`. Under the hood it's backed by gRPC's `pemfile.NewProvider`, which stats the cert/key files on its refresh tick and re-parses them only when `mtime` or contents change. The default refresh interval is 5 hours.

**Tuning the refresh window.** Set the environment variable `WEED_TLS_CERT_REFRESH_INTERVAL` (accepts any `time.ParseDuration` value, e.g. `30m`, `5m`, `500ms`) on every `weed` process that should pick up rotations faster. Useful with short-lived certs (Vault, cert-manager with `duration: 24h`, etc.). Example:

```yaml
env:
  - name: WEED_TLS_CERT_REFRESH_INTERVAL
    value: "1m"
```

The same env var tunes both gRPC mTLS and HTTPS reload.

**Requirements for hot reload to work:**

1. **The file paths must stay stable.** cert-manager → k8s Secret → volume mount does this by default: the file paths (e.g. `/etc/seaweedfs/tls/tls.crt`) are unchanged; only the symlinked target under `..data` flips. Point `cert` / `key` in `security.toml` at those stable paths.
2. **Both cert and key must update atomically.** cert-manager's Secret update is atomic from the pod's perspective (kubelet swaps the `..data` symlink), so the pemfile poll never sees a half-rotated pair. If you manage certs manually, write to a temp file and `mv` into place — do not edit in-place.
3. **The refresh window is up to ~5 hours.** If you need tighter bounds (short-lived certs from Vault, etc.), you currently need a rolling restart or a custom build.

**cert-manager example (HTTPS filer).** Mount the issued Secret at a known path and reference those files in `security.toml`:

```yaml
# Certificate resource
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: seaweedfs-filer-tls
spec:
  secretName: seaweedfs-filer-tls
  duration: 2160h       # 90d
  renewBefore: 360h     # 15d
  issuerRef:
    name: my-issuer
    kind: ClusterIssuer
  dnsNames:
    - filer.seaweedfs.svc.cluster.local
```

```yaml
# Pod spec excerpt
volumes:
  - name: filer-tls
    secret:
      secretName: seaweedfs-filer-tls
containers:
  - name: filer
    volumeMounts:
      - name: filer-tls
        mountPath: /etc/seaweedfs/tls
        readOnly: true
```

```toml
# security.toml
[https.filer]
cert = "/etc/seaweedfs/tls/tls.crt"
key  = "/etc/seaweedfs/tls/tls.key"
ca   = "/etc/seaweedfs/tls/ca.crt"
```

When cert-manager renews the Secret, the next pemfile refresh tick (within ~5h) picks up the new material. You do **not** need a reloader sidecar, a `kubectl rollout restart`, or a SIGHUP handler.

**Logs to watch for.** A successful rotation is silent on the happy path. If the new cert/key pair fails to parse (e.g. mismatched files), you'll see `pemfile.NewProvider` / `KeyMaterial` errors in the server's logs — existing connections continue with the old cert, so there's no outage, but new handshakes will fail until the files are fixed.

**What about `weed mount`, `weed mq.broker`, and other components?**

- **`weed mount`, `weed mq.broker`, `weed mq.agent`, `weed mq.kafka.gateway`**: these are gRPC-only (no HTTPS listener), so TLS rotation is already handled by the gRPC mTLS refresh path. Mount also talks to volume servers over HTTPS when `[https.client].enabled = true`; that path is the HTTPS client covered above, which rotates client cert/key without restart.
- **`weed worker`, `weed admin`, `weed sftp`, `weed filer.sync`, `weed backup`, `weed upload`, `weed filer.copy`**: all use the gRPC client plus, where relevant, the HTTPS client. Both rotate without restart.
- **Filer notification → Kafka SASL/TLS** (`weed/notification/kafka/kafka_sasl_tls.go`) and **filer-store drivers** (mysql/redis/mongodb TLS) load certs once via `tls.LoadX509KeyPair`. These are outside the `security.toml` cert-manager flow; rotating them requires restarting the filer.

---

The following command is what I used to generate the private key and certificate files, using https://github.com/square/certstrap. To compile this tool, you can run `go get github.com/square/certstrap` - or alternatively `brew install certstrap` if you are on Mac OS and use [Homebrew](https://brew.sh).

```
certstrap init --common-name "SeaweedFS CA"
certstrap request-cert --common-name volume01
certstrap request-cert --common-name master01
certstrap request-cert --common-name filer01
certstrap request-cert --common-name client01
certstrap sign --expires "2 years" --CA "SeaweedFS CA" volume01
certstrap sign --expires "2 years" --CA "SeaweedFS CA" master01
certstrap sign --expires "2 years" --CA "SeaweedFS CA" filer01
certstrap sign --expires "2 years" --CA "SeaweedFS CA" client01
```

Here is my `security.toml` file content:
```

# Put this file to one of the location, with descending priority
#    ./security.toml
#    $HOME/.seaweedfs/security.toml
#    /etc/seaweedfs/security.toml

[jwt.signing]
key = "blahblahblahblah"

[jwt.filer_signing]
key = "blahblahblahblah"

# all grpc tls authentications are mutual 
[grpc]
ca = "/Users/chris/.seaweedfs/out/SeaweedFS_CA.crt"

[grpc.volume]
cert = "/Users/chris/.seaweedfs/out/volume01.crt"
key  = "/Users/chris/.seaweedfs/out/volume01.key"

[grpc.master]
cert = "/Users/chris/.seaweedfs/out/master01.crt"
key  = "/Users/chris/.seaweedfs/out/master01.key"

[grpc.filer]
cert = "/Users/chris/.seaweedfs/out/filer01.crt"
key  = "/Users/chris/.seaweedfs/out/filer01.key"

[grpc.client]
cert = "/Users/chris/.seaweedfs/out/client01.crt"
key  = "/Users/chris/.seaweedfs/out/client01.key"


```

### For Java gRPC
Java gRPC uses Netty's SslContext. From https://netty.io/wiki/sslcontextbuilder-and-private-key.html

> The SslContextBuilder and so Netty's SslContext implementations only support PKCS8 keys.
>
> If you have a key with another format you need to convert it to PKCS8 first to be able to use it. This can be done easily by using openssl.
>
> For example to convert a non-encrypted PKCS1 key to PKCS8 you would use:
>
> openssl pkcs8 -topk8 -nocrypt -in pkcs1_key_file -out pkcs8_key.pem

### Existing certificates

If you are using existing certificates: make sure they all have the **Extended Key Usage** 'TLS Web Server Authentication' AND 'TLS Web Client Authentication' set - as grpc uses them for both use-cases!

Else you will see those errors: `error reading server preface: remote error: tls: bad certificate`

Choose your CA carefully when using existing certificates in an enterprise environment. Since Seaweed only checks the certificate against the CA and optionally validates the CN of the certificate against a whitelist, do not use the root CA of the company or any other CA you don't control, as this means someone else can generate a client certificate your cluster will accept as legitimate. Instead, generate an intermediate CA for each Seaweed cluster and use it to generate server and client certificates. This intermediate CA is the one you should use in `grpc.ca` and `https.*.ca` properties.