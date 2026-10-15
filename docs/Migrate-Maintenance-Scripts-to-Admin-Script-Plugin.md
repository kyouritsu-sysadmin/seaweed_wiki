---
id: Migrate-Maintenance-Scripts-to-Admin-Script-Plugin
title: "Migrate Maintenance Scripts to Admin Script Plugin"
sidebar_label: "Migrate Maintenance Scripts to Admin Script Plugin"
---

# Migrate Maintenance Scripts to Admin Script Plugin

This guide explains how to migrate from the legacy `[master.maintenance]` scripts in `master.toml` to the **admin script plugin worker**.

## Why migrate?

The legacy approach runs maintenance scripts directly on the master server process. This has several drawbacks:

- Scripts compete for CPU and memory with the master server.
- No visibility into script execution progress or errors.
- No UI for editing scripts — requires restarting the master to change them.
- Erasure coding detection and encoding runs serially on a single node.

The admin script plugin worker addresses all of these:

- Scripts run on a separate `weed worker` process, offloading the master.
- The admin UI at `/plugin` provides real-time progress, run history, and error reporting.
- Script text and run interval are editable from the UI without restarts.
- Erasure coding has a dedicated `erasure_coding` plugin worker with per-volume detection and parallel execution across multiple workers.

## Migration steps

### 1. Start the admin server

```bash
weed admin -master=localhost:9333
```

The admin server connects to the master. Once connected, the master automatically skips its built-in maintenance scripts (you will see `Skipping master maintenance scripts because admin server is connected` in the master log).

### 2. Start a worker

```bash
weed worker -admin=localhost:23646
```

The worker registers with the admin server and begins handling plugin jobs. By default it handles all available job types including `admin_script` and `erasure_coding`.

### 3. Automatic migration

When the `admin_script` worker registers for the first time, the admin server automatically fetches your maintenance scripts from `master.toml` and uses them as the default admin script configuration. The `lock`/`unlock` commands are stripped automatically since the admin script worker handles locking on its own. The `sleep_minutes` value is preserved as the run interval.

If the admin server cannot reach the master or the `master.toml` has no maintenance scripts configured, the worker's built-in defaults are used instead.

You can review and adjust the imported script in the admin UI at `http://&lt;admin-host&gt;:23646/plugin` under the **Admin Script** job type.

#### Adjustments to make

Compare the imported script with the table below and customize as needed:

| Old command | What to do |
|---|---|
| `lock` / `unlock` | **Remove.** The admin script worker handles locking automatically. |
| `ec.encode -fullPercent=95 -quietFor=1h` | **Remove.** This is now handled by the dedicated `erasure_coding` plugin worker, which detects and encodes eligible volumes automatically. Configure its thresholds (fullness ratio, quiet period, etc.) separately in the UI. |
| `ec.rebuild -apply` | Add to the admin script if you still want periodic EC shard repair via the script. |
| `ec.balance -apply` | Already in the default admin script. |
| `volume.balance -apply` | **Remove.** This is now handled by the dedicated `volume_balance` plugin worker, which detects imbalanced servers and moves volumes automatically. Configure its settings separately in the UI. |
| `volume.fix.replication -apply` | Already in the default script. |
| `volume.deleteEmpty -quietFor=24h -apply` | Already in the default script. |
| `fs.log.purge -daysAgo=7` | Already in the default script. |
| `s3.clean.uploads -timeAgo=24h` | Already in the default script. |
| `volume.tier.upload -dest s3 ...` | Add to the admin script if you had tiered storage upload. |
| Any custom commands | Add them to the script in the UI. |

Your `sleep_minutes` value is automatically imported as the run interval. Adjust it in the UI if needed.

### 4. Verify

After the first run interval elapses, check the admin UI at `/plugin` for:

- **Run history**: confirms the script executed successfully.
- **Activity stream**: shows each command that was executed.
- **Error reporting**: highlights any commands that failed.

You can also trigger a manual run from the UI to verify immediately.

### 5. Clean up master.toml (optional)

Once you have confirmed the admin script plugin worker is running correctly, you can remove or blank out the `[master.maintenance]` section in `master.toml`:

```toml
[master.maintenance]
scripts = ""
sleep_minutes = 17
```

This is optional — the master already skips its scripts when the admin server is connected. But removing them avoids confusion and prevents them from running if the admin server is temporarily unavailable.

## Command flag differences

Some shell commands use different flag names between the legacy scripts and the admin script worker. The admin script worker executes the same `weed shell` commands, so the flags are identical. The only difference is:

- **`-force`** flag on older scripts (e.g. `ec.balance -force`) has been renamed to **`-apply`** in current versions. Both are accepted, but `-apply` is preferred.

## Architecture overview

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│  weed master │◄────────│  weed admin  │────────►│  weed worker │
│              │  gRPC   │  :23646      │  gRPC   │              │
│  master.toml │ ─────── │  Admin UI    │         │ admin_script │
│  [maintenance│ scripts │  /plugin     │         │ erasure_coding│
│   scripts    │ imported│              │         │ vacuum       │
│   SKIPPED]   │         │              │         │ balance      │
└──────────────┘         └──────────────┘         └──────────────┘
```

- The **master** still has the legacy maintenance code but skips it when an admin server is connected.
- The **admin server** manages plugin configuration, scheduling, and dispatching. On first worker registration, it imports maintenance scripts from the master as admin_script defaults.
- The **worker** executes admin script commands and dedicated plugin jobs (erasure coding, vacuum, balance).

## See also

- [Worker](./Worker.md) — `weed worker` command reference
- [Volume Management](./Volume-Management.md) — volume management scripts overview
- [Erasure Coding for warm storage](./Erasure-Coding-for-warm-storage.md) — erasure coding details and the `erasure_coding` plugin worker
