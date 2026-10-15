---
id: Plugin-Worker-Scheduling
title: "Plugin Worker Scheduling"
sidebar_label: "Plugin Worker Scheduling"
---

# Plugin Worker Scheduling

This page explains how the admin server discovers, schedules, and dispatches work to plugin workers.

## Architecture Overview

```
                  Admin Server                              Workers
                  ────────────                              ───────
            ┌──────────────────┐
            │  Scheduler Loop  │
            │  (single goroutine)│
            └────────┬─────────┘
                     │
         ┌───────────┼───────────┐
         ▼           ▼           ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐
    │ vacuum  │ │ balance │ │  ec     │   ← per-job-type detection intervals
    └────┬────┘ └────┬────┘ └────┬────┘
         │           │           │
         ▼           ▼           ▼
   ┌───────────────────────────────────┐
   │        gRPC Bidirectional         │
   │        Streams (one per worker)   │
   └────────┬──────────┬──────────┬────┘
            ▼          ▼          ▼
        Worker A   Worker B   Worker C
```

All communication between the admin server and workers flows over a **single bidirectional gRPC stream per worker** (`PluginControlService.WorkerStream`). This stream carries registration, heartbeats, detection requests, job dispatch, progress updates, and completion reports.

## Worker Registration

When a worker starts, it dials the admin server's gRPC port (admin HTTP port + 10000) and initiates a `WorkerStream`:

1. Worker sends `WorkerHello` — contains worker ID, capabilities (which job types it can detect and/or execute), and concurrency limits.
2. Admin upserts the worker into its **Registry** and replies with `AdminHello` (heartbeat interval, reconnect settings).
3. Admin prefetches job type descriptors from the worker's declared capabilities.

Workers send `WorkerHeartbeat` every ~15 seconds, reporting:
- Detection and execution slot usage (used / total)
- Currently running work with progress
- Queued jobs by type

The registry uses heartbeats to track worker health and available capacity for scheduling decisions.

## The Scheduler Loop

A single goroutine (`schedulerLoop`) drives all periodic scheduling:

```
loop:
    runSchedulerIteration()
    if hadJobs → loop immediately (stay busy)
    if !hadJobs → sleep until the earliest job type's next detection time
```

### Sequential Group Execution

Each scheduler iteration processes job types **one at a time, sequentially**. Each job type is a "group" — its detection and all resulting executions run as a single unit before the next job type begins. This ensures job types don't compete for the admin lock or cluster resources simultaneously.

```
Iteration starts (admin lock acquired)
│
├─ [Group 1] admin_script       (max runtime: 30m, configurable)
│   ├─ detect → find scripts to run
│   └─ execute all detected jobs → blocks until done or timeout
│
├─ [Group 2] erasure_coding     (max runtime: 30m, configurable)
│   ├─ detect → find volumes to encode
│   └─ execute all detected jobs → blocks until done or timeout
│
├─ [Group 3] vacuum             (max runtime: 30m, configurable)
│   ├─ detect → find volumes to vacuum
│   └─ execute all detected jobs → blocks until done or timeout
│
├─ [Group 4] volume_balance     (max runtime: 30m, configurable)
│   ├─ detect → find imbalanced servers
│   └─ execute all detected jobs → blocks until done or timeout
│
Iteration ends (lock released) → sleep until earliest nextDetectionAt
```

Job types are processed in **alphabetical order**. Each group only runs if its detection interval has elapsed — groups that aren't due yet are skipped with no cost.

### Per-Group Timeout

Each job type group has a configurable **max runtime** (`job_type_max_runtime_seconds`, default 30 minutes) that caps the total time for detection + all executions in that group. If the timeout fires, remaining jobs in the group are canceled and the scheduler moves on to the next job type.

The timeout hierarchy within a group:

```
job_type_max_runtime_seconds (30m default, configurable per job type)
├── detection_timeout_seconds (45s default, capped by remaining runtime)
└── execution_timeout (per job, capped by remaining runtime)
    ├── Job 1 ─┐
    ├── Job 2  ├── up to global_execution_concurrency in parallel
    └── Job N ─┘
```

This means a slow job type (e.g., erasure coding encoding large volumes) won't starve other job types indefinitely — it will be cut off at its max runtime.

### Per-Job-Type Detection Intervals

Each job type has its own `detection_interval_seconds` that controls how often the scheduler checks for new work. These come from the job type's descriptor defaults and can be overridden in the admin UI per job type.

| Job Type | Default Interval |
|----------|-----------------|
| `vacuum` | 2 hours |
| `volume_balance` | 30 minutes |
| `erasure_coding` | 5 minutes |
| `admin_script` | configurable |
| `iceberg_maintenance` | 1 hour |
| `lance_compact` | from the worker's descriptor |
| `lance_optimize_indices` | from the worker's descriptor |
| `lance_cleanup_versions` | from the worker's descriptor |

The Lance job types come from an external worker (see [Lance Maintenance Worker](./Lance-Maintenance-Worker.md)),
so their defaults arrive with the worker's descriptor rather than being compiled in.

### Lanes

Job types are grouped into lanes, and a lane runs one group at a time. `default`
takes the cluster admin lock, so anything in it is serialised behind vacuum and
balancing; `iceberg`, `lifecycle` and `lance` do not, because they act on table
data rather than on volumes.

Lane assignment lives in the admin server, not in the worker: a new job type from
an external worker lands in `default` until it is mapped, which silently serialises
it behind cluster maintenance.

On each iteration, the scheduler:

1. Lists all **detectable job types** from the registry (job types with at least one connected worker that has `CanDetect` capability).
2. For each job type, checks `markDetectionDue(jobType, interval)`:
   - If `now &lt; nextDetectionAt[jobType]` → skip, not due yet.
   - If due → set `nextDetectionAt[jobType] = now + interval` and proceed.
3. Loads the **scheduler policy** for the job type (from persisted admin config or descriptor defaults).
4. Runs the group: detection first, then dispatches any resulting jobs, all under the group timeout.

### Scheduler Policy

Each job type's scheduling behavior is governed by a policy loaded from persisted configuration:

| Setting | Default | Description |
|---------|---------|-------------|
| `detection_interval_seconds` | varies by job type | How often to run detection |
| `detection_timeout_seconds` | 45s | Max time for a detection request |
| `job_type_max_runtime_seconds` | 30 min | Max total time for detection + execution per group |
| `max_jobs_per_detection` | 1000 | Max proposals returned per detection run |
| `global_execution_concurrency` | 1 | Max jobs dispatched in parallel within the group |
| `per_worker_execution_concurrency` | 1 | Max jobs per worker |
| `retry_limit` | 0 | How many times to retry a failed job |
| `retry_backoff_seconds` | 5s | Wait between retries |

All of these are editable per job type in the admin UI at `/plugin`.

## Detection Flow (Discovering Work)

Detection answers the question: "What work needs to be done for this job type?"

```
Scheduler                        Admin Server                     Worker
────────                         ────────────                     ──────
  │                                   │                              │
  ├─ detection due ──────────────────►│                              │
  │                                   ├─ pickDetector() ────────────►│
  │                                   │  (round-robin, prefers       │
  │                                   │   leased worker)             │
  │                                   │                              │
  │                                   ├── RunDetectionRequest ──────►│
  │                                   │   (job type, cluster context, │
  │                                   │    admin config, max results) │
  │                                   │                              │
  │                                   │                              ├── handler.Detect()
  │                                   │                              │   queries cluster state
  │                                   │                              │
  │                                   │◄── DetectionProposals ───────┤  (streamed in batches)
  │                                   │◄── DetectionComplete ────────┤
  │                                   │                              │
  │  ◄── proposals (filtered) ────────┤                              │
  │                                   │                              │
```

1. The scheduler picks a **detector worker** via round-robin selection (prefers a "leased" worker for consistency).
2. Sends `RunDetectionRequest` with the cluster context (topology, volume layout) and admin config.
3. The worker's handler runs `Detect()`, which inspects cluster state and streams back `DetectionProposals` — each proposal describes one unit of work (e.g., "vacuum volume 42", "move volume 7 from server A to server B").
4. The worker sends `DetectionComplete` to signal it's done.
5. Admin filters proposals:
   - **Deduplication**: Removes proposals whose `dedupe_key` matches an already-active job.
   - **Within-run dedup**: Removes duplicate proposals within the same detection run.

## Execution Flow (Dispatching Jobs)

Once detection produces proposals, the scheduler converts them to `JobSpec` objects and dispatches them:

```
Scheduler                        Admin Server                     Worker
────────                         ────────────                     ──────
  │                                   │                              │
  ├─ dispatch proposals ─────────────►│                              │
  │                                   │                              │
  │   ┌─ worker pool ──────────────┐  │                              │
  │   │ (GlobalExecutionConcurrency│  │                              │
  │   │  goroutines)               │  │                              │
  │   │                            │  │                              │
  │   │  for each job:             │  │                              │
  │   │   reserveExecutor() ───────┼──┤                              │
  │   │   (check heartbeat slots   │  │                              │
  │   │    + local reservations    │  │                              │
  │   │    vs per-worker limit)    │  │                              │
  │   │                            │  ├── ExecuteJobRequest ────────►│
  │   │                            │  │   (job spec, config,         │
  │   │                            │  │    cluster context)          │
  │   │                            │  │                              ├── handler.Execute()
  │   │                            │  │◄── JobProgressUpdate ────────┤  (streamed)
  │   │                            │  │◄── JobCompleted ─────────────┤
  │   │   release reservation ─────┼──┤                              │
  │   └────────────────────────────┘  │                              │
```

1. The scheduler creates a **worker pool** of `GlobalExecutionConcurrency` goroutines.
2. Each goroutine pulls a job from the queue and calls `reserveScheduledExecutor()`:
   - Lists executor workers for the job type, sorted by available slots.
   - Checks the worker's heartbeat-reported slot usage plus local reservation count against `PerWorkerConcurrency`.
   - If no executor has capacity, waits and retries with backoff until the `ExecutionTimeout`.
3. Sends `ExecuteJobRequest` to the chosen worker.
4. The worker's handler runs `Execute()`, streaming `JobProgressUpdate` messages during execution.
5. When done, the worker sends `JobCompleted` with the result.
6. On failure, the scheduler retries up to `RetryLimit` times with `RetryBackoff` between attempts.

### Slot-Based Capacity Control

The system enforces concurrency limits at multiple levels:

| Level | Control | Mechanism |
|-------|---------|-----------|
| **Global** | `GlobalExecutionConcurrency` | Size of the dispatch worker pool |
| **Per-Worker** | `PerWorkerConcurrency` | Checked against heartbeat slots + reservations |
| **Worker-Side** | `-maxExecute` flag | Worker rejects with "at capacity" if slots full |
| **Capability** | `MaxExecutionConcurrency` in descriptor | Per-job-type cap declared by the handler |

If a worker returns "at capacity", the scheduler tries the next available executor.

## Job Lifecycle

A job transitions through these states:

```
pending → assigned → running → completed
                            → failed (→ retry → assigned)
                            → canceled
                            → stale (expired)
```

### Stale Job Expiration

`expireStaleJobs()` runs every scheduler iteration and marks jobs stale if:
- No heartbeat from the assigned worker for >15 minutes
- No progress update for >24 hours

This prevents stale jobs from blocking new work indefinitely.

### Job Tracking

The admin server tracks:
- **In-process jobs**: Currently active jobs with progress (max ~1000)
- **Activities**: Audit log of all scheduler actions (max ~4000)
- **Run history**: Last 10 successful + 10 failed runs per job type

All tracked state is persisted to disk every 2 seconds (when dirty) via the persistence loop.

## Worker-Side Processing

When the worker receives a message from the admin server:

| Message | Worker Action |
|---------|--------------|
| `RunDetectionRequest` | Acquires detection slot, calls `handler.Detect(sender)`. Handler streams proposals back. |
| `ExecuteJobRequest` | Acquires execution slot (returns "at capacity" if full). Calls `handler.Execute(sender)`. Handler streams progress and sends completion. |
| `CancelRequest` | Cancels the context of the in-flight detection or execution. |

Workers are stateless — all scheduling state lives on the admin server. If a worker disconnects, the admin server detects it via missing heartbeats and marks its jobs stale.

## Persistence

The admin server persists all plugin state to its `-dataDir`:

| Data | File | Purpose |
|------|------|---------|
| Job type configs | `plugin/&lt;jobType&gt;/config.json` | Admin runtime settings, admin/worker config values |
| Descriptors | `plugin/&lt;jobType&gt;/descriptor.json` | Job type schema from worker |
| Tracked jobs | `plugin/tracked_jobs.json` | In-flight and recent job history |
| Activities | `plugin/activities.json` | Audit log |
| Run history | `plugin/&lt;jobType&gt;/run_history.json` | Per-type success/error history |
| Scheduler config | `plugin/scheduler_config.json` | Legacy global config |

If `-dataDir` is not set, all state is in-memory only.

## Concrete Example: Volume Balance

With `DetectionIntervalSeconds: 1800` (30 minutes), the flow is:

1. **t=0**: Scheduler calls `markDetectionDue("volume_balance", 30m)` → due (first run). Sets `nextDetectionAt = t+30m`.
2. **Detection**: Picks a worker with `CanDetect` for `volume_balance`. Sends cluster context (topology with disk usage per server). Worker's `Detect()` compares disk utilization, proposes moves like "move volume 42 from server-a to server-b".
3. **Filtering**: Admin checks no existing active job already targets volume 42.
4. **Dispatch**: Up to 16 moves dispatched concurrently (`GlobalExecutionConcurrency: 16`). Each move is sent to an available executor worker.
5. **Execution**: Worker copies volume data to the target server, reports progress, sends completion.
6. **t=30m**: Scheduler wakes, runs detection again.

## See Also

- [Worker](./Worker.md) — `weed worker` command reference and options
- [Admin UI](./Admin-UI.md) — Admin server setup and UI reference
- [Migrate Maintenance Scripts to Admin Script Plugin](./Migrate-Maintenance-Scripts-to-Admin-Script-Plugin.md) — Migration guide from legacy maintenance scripts
