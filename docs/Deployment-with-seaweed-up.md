---
id: Deployment-with-seaweed-up
title: "Deployment with seaweed up"
sidebar_label: "Deployment with seaweed up"
---

[seaweed-up](https://github.com/seaweedfs/seaweed-up) is an SSH-based deployment tool for SeaweedFS clusters on Linux hosts. A single YAML file describes the topology, and `seaweed-up` installs binaries, generates configs, sets up `systemd` units, and manages the full lifecycle (deploy / status / upgrade / scale / destroy) over SSH.

It is complementary to the Kubernetes Helm chart / Operator: use the [Operator](./Deployment-to-Kubernetes-and-Minikube.md) on Kubernetes, and `seaweed-up` on plain VMs or bare-metal.

> **Tip:** if you'd rather not hand-write `cluster.yaml`, the [Cluster Plan Workflow](./Cluster-Plan-Workflow.md) generates it from a much smaller `inventory.yaml` (just hosts and roles) by SSHing to each box and discovering disks/ports/sizes. Both flows are fully supported and `cluster deploy -f cluster.yaml` doesn't care which produced the file.

## Contents

- [Install](#install)
- [Topology file](#topology-file)
- [Core commands](#core-commands)
- [Recipe: small (single host, all-in-one)](#recipe-small-single-host-all-in-one)
- [Recipe: medium (3 hosts, HA)](#recipe-medium-3-hosts-ha)
- [Recipe: large (dedicated roles, TLS, observability)](#recipe-large-dedicated-roles-tls-observability)
- [Day-2 operations](#day-2-operations)
- [Tips](#tips)

## Install

```bash
# grab the latest release binary
curl -sSL https://github.com/seaweedfs/seaweed-up/releases/latest/download/seaweed-up_linux_amd64.tar.gz | tar -xz
sudo mv seaweed-up /usr/local/bin/

# or build from source
git clone https://github.com/seaweedfs/seaweed-up && cd seaweed-up
go build -o seaweed-up . && sudo mv seaweed-up /usr/local/bin/

seaweed-up version
```

`seaweed-up` assumes passwordless (or sudo-with-password) SSH access to every host in the topology, with a user that can write to `/opt/seaweed`, `/etc/seaweed`, and `/etc/systemd/system`.

## Topology file

A minimal cluster spec is a single YAML file listing each component and which hosts run it:

```yaml
cluster_name: prod

global:
  dir.conf: /etc/seaweed
  dir.data: /opt/seaweed
  volumeSizeLimitMB: 30000
  replication: "010"        # 1 replica in the same data center

master_servers:
  - ip: 10.0.0.10

volume_servers:
  - ip: 10.0.0.10
    folders:
      - folder: /opt/seaweed/volume0
        max: 100

filer_servers:
  - ip: 10.0.0.10
```

Component-level fields (`port`, `ip.bind`, `dataCenter`, `rack`, per-component `config` map, etc.) are documented in the [repo README](https://github.com/seaweedfs/seaweed-up#topology-specification). Per-component **Config** maps are passed straight through to `weed`'s CLI flags, so anything `weed master -h` accepts is available.

## Core commands

```bash
# preflight: verify SSH, sudo, disk, ports, time skew, arch/os
seaweed-up cluster check  -f cluster.yaml -u root -i ~/.ssh/id_rsa

# deploy everything in the topology
seaweed-up cluster deploy prod -f cluster.yaml -u root -i ~/.ssh/id_rsa --yes

# real health status from master/volume/filer HTTP probes
seaweed-up cluster status  prod
seaweed-up cluster status  prod --json --refresh 5

# rolling upgrade with per-host health gates and rollback
seaweed-up cluster upgrade prod --version 4.19

# start/stop/restart all services or a specific component
seaweed-up cluster stop    prod
seaweed-up cluster start   prod --component filer

# scale in with safe volume drain
seaweed-up cluster scale in prod --remove-node 10.0.0.13 --yes

# uninstall services (add --remove-data to wipe data dirs too)
seaweed-up cluster destroy prod --remove-data --yes

# one-shot host prep (ulimits, sysctls, firewall, time sync); also runnable
# as part of deploy via --host-prep
seaweed-up cluster prepare prod
```

Once a cluster has been deployed, its topology is persisted under `~/.seaweed-up/clusters/&lt;name&gt;/` so subsequent commands can be referenced by name without passing `-f`.

## Recipe: small (single host, all-in-one)

One VM, everything co-located. Good for dev, staging, or small internal workloads.

```yaml
cluster_name: small
global:
  dir.data: /opt/seaweed
  volumeSizeLimitMB: 30000
  replication: "000"

master_servers:
  - ip: 10.0.0.10
volume_servers:
  - ip: 10.0.0.10
    folders:
      - folder: /opt/seaweed/volume0
        max: 200
filer_servers:
  - ip: 10.0.0.10
```

Deploy:

```bash
seaweed-up cluster check  -f small.yaml -u root -i ~/.ssh/id_rsa
seaweed-up cluster deploy small -f small.yaml -u root -i ~/.ssh/id_rsa \
  --host-prep --yes
seaweed-up cluster status small
```

`--host-prep` runs the included host-prep script (raises `nofile`, sets `vm.max_map_count`, opens firewall ports, ensures time sync). Skip it if you manage those separately.

Back up and restore:

```bash
# stop the cluster, rsync /opt/seaweed off-host, then restart
seaweed-up cluster stop  small
rsync -avzP root@10.0.0.10:/opt/seaweed/ ./backup/
seaweed-up cluster start small
```

## Recipe: medium (3 hosts, HA)

Three VMs, one of each role per host, with HA masters and volume replication across hosts. Good for small production clusters.

```yaml
cluster_name: medium
global:
  dir.data: /opt/seaweed
  volumeSizeLimitMB: 30000
  replication: "010"        # 1 replica in the same DC, different volume server

master_servers:
  - ip: 10.0.0.10
  - ip: 10.0.0.11
  - ip: 10.0.0.12

volume_servers:
  - ip: 10.0.0.10
    folders: [{ folder: /opt/seaweed/volume0, max: 500 }]
  - ip: 10.0.0.11
    folders: [{ folder: /opt/seaweed/volume0, max: 500 }]
  - ip: 10.0.0.12
    folders: [{ folder: /opt/seaweed/volume0, max: 500 }]

filer_servers:
  - ip: 10.0.0.10
    config:
      defaultReplication: "010"
  - ip: 10.0.0.11
    config:
      defaultReplication: "010"

s3_servers:
  - ip: 10.0.0.10
    port: 8333
    # filer auto-defaults to the first filer in the spec
    s3_config:
      identities:
        - name: anonymous
          actions: [Read]
        - name: admin
          credentials:
            - accessKey: admin
              secretKey: change-me
          actions: [Admin, Read, Write, List, Tagging]
```

Deploy with the real preflight checks and host prep enabled:

```bash
seaweed-up cluster check  -f medium.yaml -u root -i ~/.ssh/id_rsa
seaweed-up cluster deploy medium -f medium.yaml \
  -u root -i ~/.ssh/id_rsa \
  --check --host-prep --yes
seaweed-up cluster status medium
```

Rolling upgrade (volumes → filers → masters, with per-host health gate):

```bash
seaweed-up cluster upgrade medium --version 4.19
```

## Recipe: large (dedicated roles, TLS, observability)

A production topology with dedicated masters, many volume servers, dedicated filers, S3 gateways behind a load balancer, the Admin UI, maintenance Workers, mTLS between components, and metrics shipped to Prometheus + Grafana.

```yaml
cluster_name: prod
global:
  dir.data: /opt/seaweed
  volumeSizeLimitMB: 30000
  replication: "020"
  enable_tls: true          # persists; probes and upgrade use https

# 3 dedicated masters (raft quorum)
master_servers:
  - { ip: 10.0.1.10 }
  - { ip: 10.0.1.11 }
  - { ip: 10.0.1.12 }

# many volume servers across racks
volume_servers:
  - ip: 10.0.2.10
    rack: rack-a
    folders:
      - { folder: /data/vol0, max: 2000 }
      - { folder: /data/vol1, max: 2000 }
  - ip: 10.0.2.11
    rack: rack-a
    folders:
      - { folder: /data/vol0, max: 2000 }
      - { folder: /data/vol1, max: 2000 }
  - ip: 10.0.2.20
    rack: rack-b
    folders: [{ folder: /data/vol0, max: 2000 }]
  - ip: 10.0.2.21
    rack: rack-b
    folders: [{ folder: /data/vol0, max: 2000 }]

# dedicated filers with a postgres backend (shared filer store)
filer_servers:
  - ip: 10.0.3.10
    config:
      type: postgres
      hostname: pg.internal
      port: 5432
      username: seaweedfs
      password: ${PG_PASSWORD}
      database: seaweedfs
      sslmode: require
  - ip: 10.0.3.11
    config:
      type: postgres
      hostname: pg.internal
      port: 5432
      username: seaweedfs
      password: ${PG_PASSWORD}
      database: seaweedfs
      sslmode: require

# standalone S3 gateways behind an LB
s3_servers:
  - ip: 10.0.4.10
    port: 8333
  - ip: 10.0.4.11
    port: 8333

# Admin UI (dashboard for topology + bucket management)
admin_servers:
  - ip: 10.0.5.10
    port: 23646

# maintenance Workers (EC, replication, balancing, vacuum)
worker_servers:
  - ip: 10.0.5.20
    # admin defaults to the first admin_server when omitted
  - ip: 10.0.5.21
```

Deploy end-to-end with preflight, host prep, and TLS bootstrap:

```bash
seaweed-up cluster check  -f prod.yaml -u root -i ~/.ssh/id_rsa
seaweed-up cluster deploy prod -f prod.yaml \
  -u root -i ~/.ssh/id_rsa \
  --host-prep \
  --check \
  --tls \
  --concurrency 8 \
  --yes
```

`--tls` runs `cluster cert init` before the component deploy: it generates a CA and per-component certificates, uploads them to `/etc/seaweed/certs/`, writes `security.toml`, and stamps `enable_tls: true` in the persisted topology so later `cluster status` / `cluster upgrade` probes talk HTTPS against the cluster CA.

Rotate certificates later:

```bash
seaweed-up cluster cert rotate prod
```

### Observability

`seaweed-up` includes helpers to install node_exporter, emit a Prometheus scrape config, and push a SeaweedFS Grafana dashboard:

```bash
# install node_exporter on every host in the topology
seaweed-up cluster node-exporter install prod

# print a scrape_configs snippet covering masters, volumes, filers,
# S3, admin, workers, and node_exporter
seaweed-up cluster prometheus-config prod > seaweedfs-scrape.yaml

# import the bundled SeaweedFS dashboard into Grafana
seaweed-up cluster dashboard install prod \
  --grafana-url https://grafana.internal \
  --grafana-token $GRAFANA_TOKEN
```

## Day-2 operations

Common operations on a deployed cluster:

```bash
# inspect health of every component (table or JSON)
seaweed-up cluster status prod
seaweed-up cluster status prod --json

# rolling upgrade with per-host health gate and automatic rollback
seaweed-up cluster upgrade prod --version 4.20

# scale out: add new nodes to the YAML then redeploy
seaweed-up cluster deploy prod -f prod.yaml --yes

# scale in with safe volume drain (marks target read-only, evacuates
# shards, then removes the systemd unit)
seaweed-up cluster scale in prod --remove-node 10.0.2.21 --yes

# stop / start / restart the whole cluster or a specific component
seaweed-up cluster stop    prod
seaweed-up cluster start   prod --component filer
seaweed-up cluster restart prod --component volume

# fully uninstall (leave data dirs alone unless --remove-data is passed)
seaweed-up cluster destroy prod
seaweed-up cluster destroy prod --remove-data
```

## Tips

- Pin a specific SeaweedFS version with `--version 4.19` on `deploy` / `upgrade` for reproducible installs. Without it, `seaweed-up` fetches the latest release from GitHub at deploy time.
- In CI, set the `GITHUB_TOKEN` environment variable to avoid anonymous rate limits when `seaweed-up` resolves the latest release.
- Run `seaweed-up cluster check -f cluster.yaml` before every deploy — it catches port conflicts, sudo misconfiguration, clock skew, and disk-space issues up front.
- Use `--concurrency N` on `deploy` and `upgrade` to bound parallelism on large clusters.
- The persisted state at `~/.seaweed-up/clusters/&lt;name&gt;/topology.yaml` is the source of truth after deploy. If you edit `prod.yaml` locally, re-run `cluster deploy prod -f prod.yaml` to reconcile.
- For dedicated S3 gateways fronting many buckets, put the gateways behind a TCP or HTTP load balancer (HAProxy, nginx, an ALB) and point clients at the LB.
- When running multiple filers on the same host, give each an instance-scoped LevelDB directory (seaweed-up derives `&lt;dataDir&gt;/&lt;instance&gt;/filerldb2` by default) or switch to an external store like postgres to avoid sharing state.
