---
id: Cluster-Plan-Inventory-Reference
title: "Cluster Plan Inventory Reference"
sidebar_label: "Cluster Plan Inventory Reference"
---

The inventory file is the single hand-authored input to [Cluster Plan Workflow](./Cluster-Plan-Workflow.md). It lists hosts, the roles each one runs, and SSH connection details. Everything else (disk layout, ports, max counts) is discovered or defaulted.

## Contents

- [Top-level shape](#top-level-shape)
- [defaults](#defaults)
- [hosts](#hosts)
- [Roles](#roles)
- [SSH overrides](#ssh-overrides)
- [Labels (DC / Rack)](#labels-dc--rack)
- [Disk knobs](#disk-knobs)
- [Tags and the `external` role](#tags-and-the-external-role)
- [Validation rules](#validation-rules)

## Top-level shape

```yaml
defaults:
  ssh:
    user: root
    port: 22
    identity: ~/.ssh/id_rsa
  disk:
    device_globs: ["/dev/sd*", "/dev/nvme*", "/dev/xvd*", "/dev/vd*"]
    exclude:      ["/dev/sda"]      # boot disk
    reserve_pct:  5                  # leave 5% free per disk
    auto_idx_tier: false             # see "Disk knobs" below
    allow_ephemeral: false           # AWS Nitro / GCP local SSD

hosts:
  - ip: 10.0.0.11
    roles: [master]
  # ...
```

Both `defaults` blocks are optional; everything has a sensible default.

## defaults

| Field | Default | Purpose |
| --- | --- | --- |
| `ssh.user` | OS current user | SSH login user |
| `ssh.port` | `22` | SSH port |
| `ssh.identity` | `~/.ssh/id_rsa` | SSH private key path |
| `disk.device_globs` | `[/dev/sd*, /dev/nvme*, /dev/xvd*, /dev/vd*]` | Block-device prefix allowlist scanned by the probe |
| `disk.exclude` | none | Per-host literal device paths or `/dev/&lt;prefix&gt;*` globs to skip (boot disk, swap disk, etc.) |
| `disk.reserve_pct` | `5` | Per-disk reserved headroom for the `max:` calculation (capped at 10 GiB) |
| `disk.disk_type_auto` | `true` | Auto-pick `hdd` vs `ssd` from `/sys/block/.../queue/rotational` |
| `disk.auto_idx_tier` | `false` | When a host has both rotational and small fast disks, carve the smallest fast one out as `weed volume -dir.idx` storage |
| `disk.idx_tier_size_ratio` | `0.333` | Threshold for auto_idx_tier (smallest fast must be ≤ ratio × smallest slow) |
| `disk.allow_ephemeral` | `false` | Include AWS Nitro instance store / GCP local SSD even though they're non-durable |

## hosts

Each `hosts` entry must have an `ip` and at least one `role`. Per-host overrides for `ssh:` and `labels:` shadow the inventory `defaults`.

```yaml
hosts:
  - ip: 10.0.0.11
    roles: [master]

  - ip: 10.0.0.13
    roles: [master, filer]

  - ip: 10.0.0.21
    roles: [volume]
    labels: {zone: us-east-1a, rack: r1}
    ssh:
      user: ubuntu
      port: 2222
      identity: ~/.ssh/aws_id_ed25519
```

## Roles

| Role | Goes into `cluster.yaml` section | Notes |
| --- | --- | --- |
| `master` | `master_servers:` | Raft quorum; usually 3. Default `ip.bind: 0.0.0.0` |
| `volume` | `volume_servers:` | Disk count + sizes derived from probe. Default `ip.bind: 0.0.0.0` |
| `filer` | `filer_servers:` | Metadata store via `--filer-backend`. Default `ip.bind: 0.0.0.0` |
| `s3` | `s3_servers:` | S3 gateway; auto-wired to first filer. Default `ip.bind: 0.0.0.0` |
| `sftp` | `sftp_servers:` | SFTP gateway; auto-wired to first filer. Default `ip.bind: 0.0.0.0` |
| `admin` | `admin_servers:` | Admin UI; **at most one host** may carry this role (single-instance component); password starts as `CHANGE_ME`. Default `ip.bind: 0.0.0.0` |
| `worker` | `worker_servers:` | Maintenance worker; auto-wired to first admin; runs with `-jobType=all` by default (override via `worker_servers[].jobType`) |
| `envoy` | `envoy_servers:` | Edge proxy |
| `external` | nothing emitted | Documented-but-unmanaged hosts (e.g. an external Postgres). Used with `tag:` for `--filer-backend` substitution; never SSH-probed |

### Why `ip.bind: 0.0.0.0`

SeaweedFS components default to binding `127.0.0.1` when `-ip.bind` isn't set, which makes them unreachable across the network in any multi-host deploy — peer masters can't form raft quorum, volumes can't register with masters, filers can't be reached by S3 or clients. Plan stamps a wildcard bind on every inbound role:

- **`0.0.0.0`** for v4 hosts and DNS-name hosts.
- **`::`** for IPv6 hosts (so v6-only inventories don't refuse to bind 0.0.0.0). On dual-stack Linux this also accepts v4 traffic.

If you need to bind to a specific NIC on a multi-NIC host, hand-edit the `ip.bind:` field on the relevant entry; merge runs preserve the override.

A host with multiple roles produces one entry per role across the matching sections. Inventory-side validation rejects duplicate `(ip, role)` pairs.

## SSH overrides

Per-host `ssh:` shadows the inventory `defaults.ssh`. Two rows that share an `ip:ssh-port` target must agree on user/identity (the probe deduplicates by SSH endpoint, so disagreeing rows would silently let one override the other):

```yaml
hosts:
  - ip: 10.0.0.10
    roles: [master, volume]      # one SSH session, both roles share ssh config
  - ip: 10.0.0.10
    roles: [filer]
    ssh: { user: ubuntu }        # ERROR: conflicts with the master/volume rows
```

## Labels (DC / Rack)

`labels.zone` and `labels.rack` map onto `DataCenter` / `Rack` fields on the volume server spec (and future filer/s3 fields as they grow). Use them when SeaweedFS's volume placement should respect rack/AZ topology.

```yaml
hosts:
  - ip: 10.0.2.10
    roles: [volume]
    labels: {zone: us-east-1a, rack: r1}
  - ip: 10.0.2.20
    roles: [volume]
    labels: {zone: us-east-1b, rack: r2}
```

Other labels are preserved as inventory annotations but not (yet) consumed by `plan`.

## Disk knobs

The default disk discovery scans every `/dev/sd*`, `/dev/nvme*`, `/dev/xvd*`, `/dev/vd*` block device, skips boot/partitioned/already-mounted disks, and emits one `folders:` entry per remaining device with `max:` derived from size.

Common overrides:

```yaml
defaults:
  disk:
    # Drop /dev/sda from every host (its partitions usually carry the OS).
    exclude: ["/dev/sda"]

    # Treat `roles: [volume]` as the data tier even on Nitro EC2 (default
    # skips the instance store because it's non-durable).
    allow_ephemeral: true

    # On a host with both HDDs and a small fast SSD, carve the SSD out
    # as `weed volume -dir.idx=...` storage instead of using it as data.
    auto_idx_tier: true
```

Already-mounted `/data&lt;N&gt;` disks are recognized as cluster-owned and re-emitted using their existing mountpoint; foreign mounts (`/`, `/var/lib/docker`, anything else) are skipped.

## Tags and the `external` role

Mark a host with `roles: [external]` and a `tag:` to reference it symbolically from `--filer-backend`:

```yaml
hosts:
  # SSH-probed hosts...
  - ip: 10.0.0.13
    roles: [master, filer]

  # Filer metadata store — not SSH-managed, never probed.
  # Declared so --filer-backend can reference it by tag.
  - ip: 10.0.0.41
    roles: [external]
    tag: postgres-metadata
```

Then the operator can write `--filer-backend postgres://user:pw@tag:postgres-metadata:5432/db?sslmode=disable`. Plan substitutes the tagged host's IP before parsing the DSN, so the generated `cluster.yaml` carries the resolved address — `cluster deploy` doesn't need to know about tags. Decouples "where the metadata DB lives" (one inventory edit) from "what its credentials are" (the DSN file or env var stays stable across IP changes).

Tag substitution only runs on the URL authority's host segment, so a literal `tag:` in a password (`user:tag:secret@…`) or query value (`?note=tag:prod`) is left alone.

## Validation rules

`plan` rejects an inventory at load time when:

- A host has no `ip`.
- A host has no roles.
- A role is unknown.
- A host declares the same `(ip, role)` pair twice.
- Two rows share an `ip:ssh-port` target but disagree on SSH user/identity.
- A `disk.device_globs` or `disk.exclude` entry contains anything fancier than an optional trailing `*`.
- Two hosts carry the same `tag:` (would make tag substitution ambiguous).
- More than one host carries `roles: [admin]` (the admin UI is single-instance). Hand-written `cluster.yaml` files that skip plan are caught by the same rule at deploy time.

Anything else is fine; the planner errs on the side of accepting weird-but-unambiguous inventory shapes and warning at run time.
