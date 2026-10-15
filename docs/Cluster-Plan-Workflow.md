---
id: Cluster-Plan-Workflow
title: "Cluster Plan Workflow"
sidebar_label: "Cluster Plan Workflow"
---

[seaweed-up](https://github.com/seaweedfs/seaweed-up) ships a `cluster plan` command that turns a host inventory into the `cluster.yaml` that `cluster deploy` consumes. Instead of hand-writing the topology and chasing per-host disk paths and ports, you list hosts and the roles each one runs; `plan` SSHes to each box, discovers its hardware, and synthesizes a reviewable spec.

This page walks through the workflow end to end. For the inventory schema in detail see [Cluster Plan Inventory Reference](./Cluster-Plan-Inventory-Reference.md); for ongoing operations see [Cluster Plan Day 2 Operations](./Cluster-Plan-Day-2-Operations.md).

## Contents

- [Mental model](#mental-model)
- [1. Write inventory.yaml](#1-write-inventoryyaml)
- [2. Probe (optional, dry information-gathering)](#2-probe-optional-dry-information-gathering)
- [3. Synthesize cluster.yaml](#3-synthesize-clusteryaml)
- [4. Preview before applying changes](#4-preview-before-applying-changes)
- [5. Deploy](#5-deploy)
- [6. Day-2: grow the cluster](#6-day-2-grow-the-cluster)
- [7. Day-2: a host's hardware changed](#7-day-2-a-hosts-hardware-changed)
- [Escape hatches](#escape-hatches)

## Mental model

| Phase | Verb | Mutates? | Use when |
| --- | --- | --- | --- |
| 1 | `plan --json` | nothing | sanity-checking SSH/probe |
| 2 | `plan -o cluster.yaml` (greenfield) | creates files | first time |
| 3 | `plan -o cluster.yaml` (re-run) | append-merge | adding hosts |
| 4 | `plan --dry-run` | nothing | preview any of the above |
| 4 | `plan --refresh-host=&lt;ip&gt;` | swaps one entry | drift remediation |
| — | `deploy -f cluster.yaml` | the cluster | apply the spec |

The pattern: inventory is your source of truth; `cluster.yaml` is a reviewable intermediate; `deploy` only acts on `cluster.yaml`.

## 1. Write inventory.yaml

The inventory is the only file you author by hand. It lists hosts, the roles each one runs, and SSH connection details. Everything else (disk layout, ports, max counts) is discovered or defaulted.

```yaml
defaults:
  ssh:
    user: root
    port: 22
    identity: ~/.ssh/id_rsa
hosts:
  - ip: 10.0.0.11
    roles: [master]
  - ip: 10.0.0.12
    roles: [master]
  - ip: 10.0.0.13
    roles: [master, filer]
  - ip: 10.0.0.21
    roles: [volume]
    labels: {zone: us-east-1a, rack: r1}
  - ip: 10.0.0.22
    roles: [volume]
```

Recognized roles: `master`, `volume`, `filer`, `s3`, `sftp`, `admin`, `worker`, `envoy`, `external`. A host can carry multiple roles; `plan` emits one entry per role into the corresponding `*_servers` section. Per-host `ssh:` and `labels:` override the inventory `defaults`. See [Cluster Plan Inventory Reference](./Cluster-Plan-Inventory-Reference.md) for every field.

## 2. Probe (optional, dry information-gathering)

```bash
seaweed-up cluster plan -i inventory.yaml --json > facts.json
```

Read-only on every target. Useful for sanity-checking that SSH works and seeing what disks the planner sees on each host before you let it write anything.

## 3. Synthesize cluster.yaml

```bash
seaweed-up cluster plan -i inventory.yaml -o cluster.yaml \
    --filer-backend-file /etc/seaweed-up/filer.dsn
```

`plan` SSHes to each host, generates a `cluster.yaml` (the file `cluster deploy` consumes), and writes two sidecars next to it:

- `cluster.facts.json` — the raw probe output (audit + drift baseline for the next run)
- `cluster.deploy-disks.json` — the per-host allowlist of disks `deploy` is permitted to mkfs+mount

The generated `cluster.yaml` carries a header comment marking it plan-generated and is safe to hand-edit. You'll want to review it before the first deploy.

### Filer backend

If your filer needs an external metadata store (Postgres, MySQL, Redis…), pass the DSN with one of:

```bash
# 1. file (recommended: avoids leaking the password via `ps`)
seaweed-up cluster plan -i inventory.yaml -o cluster.yaml \
    --filer-backend-file /etc/seaweed-up/filer.dsn

# 2. direct CLI flag
seaweed-up cluster plan -i inventory.yaml -o cluster.yaml \
    --filer-backend 'postgres://seaweed:CHANGE_ME@10.0.0.41:5432/seaweedfs?sslmode=disable'

# 3. environment variable (good for CI)
SEAWEEDUP_FILER_BACKEND='postgres://seaweed:s3cret@10.0.0.41/seaweedfs' \
    seaweed-up cluster plan -i inventory.yaml -o cluster.yaml
```

Precedence is `file > flag > env`. You can also reference a tagged inventory host symbolically — see [Cluster Plan Inventory Reference](./Cluster-Plan-Inventory-Reference.md)'s tag section.

## 4. Preview before applying changes

```bash
seaweed-up cluster plan -i inventory.yaml -o cluster.yaml --dry-run
```

Prints a unified diff of what the next `plan` run *would* write, without touching anything on disk. This is the safe review step before any rewrite. Sidecars are summarized but not written.

## 5. Deploy

```bash
seaweed-up cluster deploy -f cluster.yaml
```

Reads `cluster.yaml` plus the `deploy-disks.json` sidecar (fail-closed: if the sidecar is missing on a plan-generated spec, deploy refuses rather than scanning every disk). Brings up systemd units, mounts disks, configures filer/admin/etc.

## 6. Day-2: grow the cluster

Add a host to `inventory.yaml`:

```yaml
  - ip: 10.0.0.23
    roles: [volume]
```

Re-run plan:

```bash
seaweed-up cluster plan -i inventory.yaml -o cluster.yaml
```

The default behavior when `-o` already exists is **append-merge** — every existing entry stays byte-identical (your hand edits, your inline comments, your key ordering survive), and the new `10.0.0.23` row gets appended to `volume_servers`. Then `cluster deploy -f cluster.yaml` again.

## 7. Day-2: a host's hardware changed

You added a disk to `10.0.0.21`. Run `plan` and you'll see:

```
WARN: drift on 10.0.0.21:22 (since previous facts.json): added /dev/sdc
```

`plan` compared the new probe against the previous run's `facts.json` and noticed the disk count moved. The YAML wasn't touched — drift is informational. To actually update that one host's entry without disturbing the rest of the file:

```bash
seaweed-up cluster plan -i inventory.yaml -o cluster.yaml --refresh-host 10.0.0.21
```

That host's `master_servers` / `filer_servers` / `volume_servers` rows get re-emitted from fresh facts; every other entry stays byte-identical. Then deploy.

See [Cluster Plan Day 2 Operations](./Cluster-Plan-Day-2-Operations.md) for the full drift / refresh / dry-run workflow.

## What plan does NOT generate

`cluster plan` brings up the infrastructure; a few things it deliberately leaves for the operator:

- **Buckets**: none auto-created. SeaweedFS doesn't pre-create any S3 bucket; the S3 gateway exposes the filer's `/buckets/` directory as the bucket namespace, but it starts empty. After deploy, create buckets via the S3 API (`aws --endpoint http://&lt;s3-host&gt;:8333 s3 mb s3://photos`) or `weed shell` (`bucket.create -name photos`).

- **Filer metadata-store credentials**: the `filer_servers[].config:` block is empty unless you pass `--filer-backend` / `--filer-backend-file` / `$SEAWEEDUP_FILER_BACKEND`. With no backend, the filer falls back to embedded LevelDB at `&lt;dataDir&gt;/&lt;instance&gt;/filerldb2` (no credentials needed; not horizontally scalable). See [Cluster Plan Inventory Reference](./Cluster-Plan-Inventory-Reference.md) for the `tag:`-substitution form.

- **S3 IAM identities**: plan emits empty `s3_servers[]` entries; access keys / secret keys / per-user permissions are operator-authored. Hand-edit the `s3_servers[].s3_config.identities` block (see [examples/typical.yaml](https://github.com/seaweedfs/seaweed-up/blob/main/examples/typical.yaml)) before deploy or your S3 gateway runs anonymous-only.

- **Admin UI password**: plan stamps `admin_user: admin` / `admin_password: CHANGE_ME` so the deployed UI isn't silently unauthenticated. The header comment in the generated `cluster.yaml` calls this out — **edit it to a real secret before deploy** or your admin UI accepts a known-bad password.

## Escape hatches

- `--overwrite` — regenerate `cluster.yaml` from scratch, discarding all hand edits. Use when you've drifted too far to merge cleanly.
- Hand-written `cluster.yaml` files are still fully supported — see [Deployment with seaweed-up](./Deployment-with-seaweed-up.md) for the no-inventory workflow.
