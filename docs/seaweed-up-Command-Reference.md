---
id: seaweed-up-Command-Reference
title: "seaweed up Command Reference"
sidebar_label: "seaweed up Command Reference"
---

A complete reference of the `seaweed-up cluster` subcommands and their flags. For an introduction, install steps, the topology file format, and end-to-end recipes, see [Deployment with seaweed-up](./Deployment-with-seaweed-up.md); to generate `cluster.yaml` from a small inventory, see [Cluster Plan Workflow](./Cluster-Plan-Workflow.md).

Every command operates on a topology file (`-f cluster.yaml`) and reaches hosts over SSH. Most state-changing commands accept a positional `&lt;cluster-name&gt;` as well; when omitted, the name is read from `cluster_name:` in the YAML.

## Contents

- [Common flags](#common-flags)
- [Lifecycle: deploy, status, start/stop/restart, upgrade, destroy](#lifecycle)
- [Scaling: scale out, scale in](#scaling)
- [Hosts: check, prepare](#hosts)
- [TLS: cert init, cert rotate](#tls)
- [Observability: node-exporter, prometheus-config, dashboard](#observability)
- [Discovery: list, plan](#discovery)
- [Operating behind a bastion / jump host](#operating-behind-a-bastion--jump-host)
- [See also](#see-also)

## Common flags

These appear on most subcommands:

| Flag | Meaning |
|------|---------|
| `-f, --file` | cluster configuration file (required by most commands) |
| `-u, --user` | SSH user (defaults to the current OS user) |
| `-i, --identity` | SSH identity file (defaults to the agent / `~/.ssh/id_rsa`) |
| `-p, --port` | SSH port (default `22`) |
| `-c, --component` | restrict to one role: `master\|volume\|filer\|s3\|sftp\|admin\|envoy\|worker\|monitoring` |
| `-y, --yes` | skip confirmation prompts (for automation) |

`seaweed-up` assumes passwordless (or sudo-with-password) SSH to every host, with a user that can write `/opt/seaweed`, `/etc/seaweed`, and `/etc/systemd/system`. The jump-host (`global.bastion`) is read from the YAML — see [below](#operating-behind-a-bastion--jump-host).

## Lifecycle

### deploy

Install/converge every component in the topology. Idempotent: it skips work that is already in the desired state, so re-running after editing the YAML rolls out only the diff.

```bash
seaweed-up cluster deploy -f cluster.yaml
seaweed-up cluster deploy -f cluster.yaml --version=4.33      # pin a release (default: latest)
seaweed-up cluster deploy -f cluster.yaml --component=s3      # one role only
seaweed-up cluster deploy -f cluster.yaml --version=dev       # rolling "dev" pre-release
```

Notable flags: `--version` (release tag, `latest`, or `dev`), `--component`, `--check` (run preflight first and abort on failure), `--host-prep` (run host tuning before deploy), `--mount-disks` (auto-format/mount fresh disks on volume servers, default `true`), `--restart` (force service restart), `--tls` (generate + install a CA and per-host certs as part of deploy), `--concurrency` (cap concurrent per-host deploys), `--enterprise` (pull binaries from the enterprise release repo), `--proxy`, `--plain` (disable the live per-component console).

### status

Probe master/volume/filer HTTP endpoints and report real health (not just "is the process up"). On a TTY it shows a live, one-line-per-component view; otherwise a plain table.

```bash
seaweed-up cluster status -f cluster.yaml
seaweed-up cluster status -f cluster.yaml --json            # machine-readable
seaweed-up cluster status -f cluster.yaml --refresh=5       # repaint every 5s
seaweed-up cluster status -f cluster.yaml --plain           # force the table (pipe/CI safe)
```

Notable flags: `--json`, `--verbose` (include raw probe bodies), `--refresh` (seconds; `0` = once), `--timeout` (default `30s`), `--plain`.

The HTTP probes ride the `global.bastion` tunnel when one is configured, so `status` works against private-IP clusters behind a jump host (see [below](#operating-behind-a-bastion--jump-host)).

### start / stop / restart

Control `systemd` units across the cluster (or one role with `--component`).

```bash
seaweed-up cluster restart -f cluster.yaml
seaweed-up cluster restart -f cluster.yaml --component=volume
seaweed-up cluster stop    -f cluster.yaml
seaweed-up cluster start   -f cluster.yaml
```

### upgrade

Rolling upgrade to a target version, one host at a time, with a per-host health gate and automatic rollback on failure.

```bash
seaweed-up cluster upgrade prod -f cluster.yaml --version=4.33
seaweed-up cluster upgrade prod -f cluster.yaml --version=dev --dry-run
```

Notable flags: `--version` (required; release tag, `latest`, or `dev`), `--dry-run` (print the plan only), `--rollback-on-failure` (reinstall the previous version on a host whose post-upgrade health check fails, default `true`), `--insecure-skip-tls-verify`, `--enterprise`, `--plain`. The per-host health gate and version probe ride the `global.bastion` tunnel, so `upgrade` works behind a jump host.

### destroy

Uninstall services and remove unit files. Data directories are left intact unless `--remove-data` is passed.

```bash
seaweed-up cluster destroy prod -f cluster.yaml                 # keep data
seaweed-up cluster destroy prod -f cluster.yaml --remove-data  # wipe data dirs (irreversible)
```

## Scaling

### scale out

Append volume or filer servers, then converge.

```bash
seaweed-up cluster scale out prod -f cluster.yaml --add-volume=2
seaweed-up cluster scale out prod -f cluster.yaml --add-filer=1
```

### scale in

Remove one or more nodes, draining their data first: the target volume server is marked read-only, its volumes/EC shards are evacuated to other servers, then the `systemd` unit is removed.

```bash
seaweed-up cluster scale in prod -f cluster.yaml --remove-node=10.0.0.5
seaweed-up cluster scale in prod -f cluster.yaml --remove-node=node1,node2 --drain-timeout=30m
```

Notable flags: `--remove-node` (comma-separated hosts or `host:port`), `--drain-timeout` (default `30m`).

> ⚠️ Two caveats. (1) `scale in` removes **volume servers** only; any s3/worker on the host and the YAML entries are not touched — edit those yourself. (2) Evacuation needs free capacity on the remaining servers, or it has nowhere to move the volumes/shards — free space (e.g. delete unused collections) first if the cluster is full. The master health check and drain poll ride the `global.bastion` tunnel, so `scale in` works behind a jump host.

## Hosts

### check

Preflight: SSH reachability, sudo, disk, ports, time skew, arch/OS — without changing anything.

```bash
seaweed-up cluster check -f cluster.yaml -u root -i ~/.ssh/id_rsa
seaweed-up cluster check -f cluster.yaml --json
```

### prepare (alias: host-prep)

Apply host tuning: ulimits, sysctls, firewall, time sync. Also runnable inline via `deploy --host-prep`.

```bash
seaweed-up cluster prepare -f cluster.yaml
```

## TLS

```bash
seaweed-up cluster cert init   -f cluster.yaml   # generate CA, issue per-host certs, distribute
seaweed-up cluster cert rotate -f cluster.yaml   # re-issue per-host certs from the existing CA
```

`deploy --tls` runs `cert init` as part of a deploy. Once certs are installed, set `global.tls.enabled: true` (or use `--tls`) so components talk gRPC/HTTP over TLS, and `status`/`upgrade` probe over HTTPS with the cluster CA.

## Observability

```bash
# install node_exporter on every master/volume/filer host
seaweed-up cluster node-exporter install -f cluster.yaml

# print a scrape_configs snippet covering masters, volumes, filers, s3, admin, workers, node_exporter
seaweed-up cluster prometheus-config -f cluster.yaml

# import the bundled SeaweedFS dashboard into Grafana
seaweed-up cluster dashboard install -f cluster.yaml \
  --grafana-url=https://grafana.example.com --grafana-token=$GRAFANA_TOKEN --cluster-name=prod
```

Prometheus/Grafana themselves are deployed when the YAML has a `monitoring:` block (`deploy --component=monitoring`).

## Discovery

```bash
seaweed-up cluster list            # clusters this CLI has state for
seaweed-up cluster list --verbose
```

`cluster plan` probes an `inventory.yaml` and emits a reviewable `cluster.yaml`; it has its own guide — see [Cluster Plan Workflow](./Cluster-Plan-Workflow.md), [Cluster Plan Inventory Reference](./Cluster-Plan-Inventory-Reference.md), and [Cluster Plan Day 2 Operations](./Cluster-Plan-Day-2-Operations.md).

## Operating behind a bastion / jump host

When nodes have only private addresses, declare the jump host once in the topology:

```yaml
global:
  bastion:
    host: bastion.example.com   # or host:port
    user: ops                   # optional; defaults to the current user
    identity: ~/.ssh/id_rsa     # optional; falls back to the SSH agent
```

`seaweed-up` then routes **everything** through it automatically. SSH operations (`deploy`, `upgrade`, `start`/`stop`/`restart`, `prepare`, `check`, `destroy`, `cert`, `node-exporter install`, `scale in`) tunnel over it, and so do the **HTTP probes** — `status`'s health checks and the `upgrade`/`scale in` master probes dial through the jump host as well, so they reach private component addresses instead of failing. One bastion connection is multiplexed across all hosts, so a wide fan-out won't trip the jump host's `sshd` `MaxStartups`.

There's nothing extra to configure: any command that loads `cluster.yaml` installs the jump host before it runs.

For ad-hoc inspection of things the CLI doesn't expose — collections, EC layout, manual evacuation — reach the cluster **on a node** over the same tunnel with `weed shell`:

```bash
# authoritative topology: per-node volumes, EC shards, capacity
ssh -J ops@bastion.example.com ops@10.0.0.1 'curl -s http://10.0.0.1:9333/dir/status'

# weed shell for collections / EC / evacuation
ssh -J ops@bastion.example.com ops@10.0.0.1 \
  "printf 'volume.list\ncollection.list\n' | weed shell -master=10.0.0.1:9333"
```

## See also

- [Deployment with seaweed-up](./Deployment-with-seaweed-up.md) — intro, install, topology file, recipes
- [Cluster Plan Workflow](./Cluster-Plan-Workflow.md) — generate `cluster.yaml` from an inventory
- [Cluster Plan Day 2 Operations](./Cluster-Plan-Day-2-Operations.md) — append-merge, drift, refresh
- [weed shell](./weed-shell.md) — the interactive admin shell used for EC/collection/volume operations
