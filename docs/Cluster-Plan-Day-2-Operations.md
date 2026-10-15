---
id: Cluster-Plan-Day-2-Operations
title: "Cluster Plan Day 2 Operations"
sidebar_label: "Cluster Plan Day 2 Operations"
---

Once a cluster is deployed, ongoing operations against an inventory-managed `cluster.yaml` revolve around four `cluster plan` flags: append-merge (the default re-run behavior), `--dry-run`, `--refresh-host=&lt;ip&gt;`, and `--overwrite`. This page walks through each.

For first-time setup see [Cluster Plan Workflow](./Cluster-Plan-Workflow.md); for the inventory schema see [Cluster Plan Inventory Reference](./Cluster-Plan-Inventory-Reference.md).

## Contents

- [Adding hosts (append-merge)](#adding-hosts-append-merge)
- [Previewing changes (--dry-run)](#previewing-changes---dry-run)
- [Hardware drift detection](#hardware-drift-detection)
- [Refreshing one host (--refresh-host)](#refreshing-one-host---refresh-host)
- [Regenerating from scratch (--overwrite)](#regenerating-from-scratch---overwrite)
- [Sidecars](#sidecars)
- [Working with hand-written cluster.yaml files](#working-with-hand-written-clusteryaml-files)

## Adding hosts (append-merge)

The default behavior when `-o cluster.yaml` already exists is **append-merge**: every existing entry stays byte-identical (your hand edits, your inline comments, your key ordering survive); inventory hosts that aren't in the YAML get appended to the right `*_servers` section.

```bash
# Add a new host to inventory.yaml, then:
seaweed-up cluster plan -i inventory.yaml -o cluster.yaml
seaweed-up cluster deploy -f cluster.yaml
```

What you'll see on stderr:

```
  appended to volume_servers: 10.0.0.23:8080
```

What survives byte-for-byte:
- Operator hand edits to `max:`, `disk:`, `dataCenter`, custom config blocks.
- Comments (head, line, foot) on existing entries.
- Indent style (2-space vs 4-space) detected from the existing file.
- Section ordering and key ordering within sections.

What's added:
- One new entry per role per inventory host that isn't already keyed at `ip:port` in the YAML.
- A new `*_servers:` section if the role wasn't represented before.

What's reported but not changed:
- **Orphans** — entries in `cluster.yaml` not produced by this plan run (host removed from inventory, probe failed, or the volume role was dropped because no eligible disks were found). Surface as `WARN: orphan in cluster.yaml ...` lines. The row stays in YAML; the operator decides whether to delete, fix the probe, or repair the inventory.
- **Unparseable** — hand-edited entries `keyOfNode` couldn't extract a key from (e.g. an entry missing `port:`). Documented hazard: a fresh inventory entry with the same IP would still get appended on top, so the operator should clean these up.

## Previewing changes (--dry-run)

Before any rewrite, you can preview the diff:

```bash
seaweed-up cluster plan -i inventory.yaml -o cluster.yaml --dry-run
```

Runs the full probe + Marshal/Merge pipeline, then prints a unified diff between the current `-o` file (or empty for greenfield) and the body plan would write. Exits without touching anything on disk. Sidecars are reported as "would write" lines but not actually written.

```diff
--- cluster.yaml (current)
+++ cluster.yaml (proposed)
@@ -23,4 +23,8 @@
       port.grpc: 18081
       folders:
         - folder: /data1
+    - ip: 10.0.0.23
+      port.ssh: 22
+      port: 8080
+      port.grpc: 18080
```

Pairs naturally with append-merge: operators preview before letting plan mutate the file. Pairs with `--overwrite` too — see what regeneration is about to discard before it runs.

`--dry-run` requires `-o` (without it there's no diff target).

## Hardware drift detection

Every plan run that produces a `cluster.facts.json` sidecar lays the foundation for the next run's drift check. On the second run, plan loads the previous facts file before the fresh probe writes its replacement, then compares per-host disk paths and surfaces a warning if anything moved:

```
  WARN: drift on 10.0.0.21:22 (since previous facts.json): added /dev/sdc
```

Drift is **informational, not actionable** — the YAML isn't touched. The operator decides whether the change is intentional (added a disk on purpose) and runs `--refresh-host` to bring the entry up to date, or investigates if it's unexpected (drive failure, vendor swap).

Scope is intentionally narrow today: disk path set only. Size shifts and model-string churn aren't flagged because they're noisy on cloud hosts (in-place resizes, vendor revisions). NICs and CPU aren't compared either.

`--dry-run` also surfaces drift warnings, so you can re-run plan against an inventory that's been quiet for weeks and see whether anything moved before deciding to write.

## Refreshing one host (--refresh-host)

When drift detection flags a host, the natural follow-up is to re-emit its entries from fresh facts without disturbing the rest of the file:

```bash
seaweed-up cluster plan -i inventory.yaml -o cluster.yaml --refresh-host 10.0.0.21
seaweed-up cluster deploy -f cluster.yaml
```

The flag is repeatable (`--refresh-host 10.0.0.21 --refresh-host 10.0.0.22`) and refreshes per-IP rather than per-(ip, port). A host that maps to multiple sections — say `master` + `filer` + `volume` — gets all of its rows refreshed in one shot. Misses (an IP that didn't match any entry) surface as `WARN: --refresh-host &lt;ip&gt; did not match any existing entry`.

What survives a refresh:
- **Entry-level head, line, and foot comments** stay paired with the host (`# primary HDD bank` on top of an entry survives).

What gets clobbered:
- Every spec field on the refreshed entries — including ports (incidentally part of the dedup key but treated as just another field for refresh).
- **Field-level inline comments inside the mapping** (e.g. `port: 8080  # custom`). Pairing each fresh field with its old counterpart is out of scope for now; if you care, promote the comment to a head comment above the entry, which IS preserved.

`--refresh-host` requires `-o` pointing at an existing file. Without `-o` (greenfield) or with `--overwrite`, the flag warns and continues — there's no existing file to refresh into.

## Regenerating from scratch (--overwrite)

When you've drifted too far to merge cleanly — typically because someone restructured the spec by hand and the merge no longer makes sense — `--overwrite` regenerates everything:

```bash
seaweed-up cluster plan -i inventory.yaml -o cluster.yaml --overwrite
```

**This discards all hand edits.** Always pair with `--dry-run` first to see what's about to be lost:

```bash
seaweed-up cluster plan -i inventory.yaml -o cluster.yaml --overwrite --dry-run
```

## Sidecars

`cluster plan -o cluster.yaml` writes two JSON sidecars next to the YAML:

| File | Purpose | Consumer |
| --- | --- | --- |
| `cluster.facts.json` | Raw `HostFacts` slice from the probe (disks, CPU, memory, NICs) | Drift detection on the next plan run; operator audit |
| `cluster.deploy-disks.json` | Per-host allowlist of disk paths plan classified as eligible | `cluster deploy` — fail-closed contract: if the sidecar is missing on a plan-generated spec, deploy refuses rather than scanning every disk |

Both files are regenerated on every plan run (including merge runs). They're audit + deploy contracts, not hand-edit surfaces, so byte-stability isn't a goal. Permissions are `0600` because `facts.json` includes hostnames and disk model strings (host enumeration data).

Plan-generated specs carry a header marker comment so `cluster deploy` knows to apply the fail-closed contract; hand-written specs (no marker) take the legacy path.

## Working with hand-written cluster.yaml files

The plan workflow is opt-in. You can keep hand-writing `cluster.yaml` and using `cluster deploy -f cluster.yaml` directly — see [Deployment with seaweed-up](./Deployment-with-seaweed-up.md) for that flow. None of the plan-side fail-closed contracts apply to hand-written specs (no marker in the header → no sidecar enforcement on deploy).

You can also append-merge into a hand-written file: as long as the entries follow the standard `ip:` / `port:` shape, the merge dedupes correctly and preserves your formatting. The plan marker only gets stamped on greenfield writes.
