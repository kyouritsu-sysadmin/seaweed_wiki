---
id: Filer-Operation-Serialization
title: "Filer Operation Serialization"
sidebar_label: "Filer Operation Serialization"
---

# Filer Operation Serialization

How SeaweedFS serializes multi-step operations across a filer cluster so that
read-modify-write sequences on the same key are atomic without a heavyweight
distributed lock held across RPCs.

The architecture is a small, layered design:

```
  caller (S3 gateway, mount, …)
            │
            ▼   route-by-key
   any filer in the cluster
            │
            ▼   ring.GetPrimary(route_key)
       owner filer        ← single serialization point per key
            │
            ▼   entryLockTable.AcquireLock(lock_key)
   apply condition + mutations atomically
```

Everything that needs cross-filer atomicity — S3 conditional writes, version
pointer recomputes, multi-entry object transactions, [Distributed POSIX Locks](./Distributed-POSIX-Locks.md)
— rides on these same three layers.

## Why not just a distributed lock?

The older mechanism (the `DistributedLock` RPC, still used for whole-file
write locking) hands the caller a lease token; the caller holds it across one
or more RPCs, then releases it. That works, but every read-modify-write step
costs an extra round trip, and a slow or crashed caller can leave a lease that
must be timed out.

The serialization architecture inverts this: the caller sends *the whole
operation* (a precondition plus an ordered list of mutations) in one RPC to
the filer that owns the key. The lock is held only for that call. If the
caller dies, there is nothing to time out.

## Layer 1 — Route by key

Every filer registers with the master and joins a hash ring keyed by its
`ServerAddress` (see [`weed/cluster/lock_manager/lock_ring.go`](https://github.com/seaweedfs/seaweedfs/blob/master/weed/cluster/lock_manager/lock_ring.go)).
The ring is a consistent hash with virtual nodes (`DefaultVnodeCount`); the
master broadcasts membership changes so every filer converges on the same
ring view.

A *route key* is a stable string derived from the object the caller wants to
mutate (e.g. the object's path, or `"s3.fuse.lock:" + path` for an inode
lock). `LockRing.GetPrimary(route_key)` returns the filer that owns it.

The caller does not have to talk to the owner directly. Any filer that
receives the request checks ownership and, if it is not the owner, forwards
the request one hop. Only one hop is allowed: a forwarded request carries
`is_moved=true` and is always applied locally on the receiver. This bounds
the forwarding cost and prevents a loop when two filers temporarily disagree
on the owner (a ring change in flight).

See `ObjectTransaction` for the canonical example:
[`weed/server/filer_grpc_server.go`](https://github.com/seaweedfs/seaweedfs/blob/master/weed/server/filer_grpc_server.go).

```
if req.RouteKey != "" && !req.IsMoved && fs.filer.Dlm != nil {
    if owner := fs.filer.Dlm.LockRing.GetPrimary(req.RouteKey); owner != "" && owner != fs.option.Host {
        // forward one hop with IsMoved=true
        ...
    }
}
```

## Layer 2 — Per-path lock on the owner

Each filer keeps an in-memory `entryLockTable` keyed by `util.FullPath`
([`weed/server/filer_server.go`](https://github.com/seaweedfs/seaweedfs/blob/master/weed/server/filer_server.go)):

```
// entryLockTable serializes mutations to the same entry path on this filer.
// ...the local serialization point for read-modify-write operations that
// replaces the distributed lock for that key. Idle keys are evicted
// automatically, so the table stays bounded.
entryLockTable *util.LockTable[util.FullPath]
```

`AcquireLock(name, fullpath, ExclusiveLock)` blocks until any other holder of
the same path releases. `CreateEntry`, `ObjectTransaction`, and the POSIX
lock layer all take it. Because routing always sends a given key's writes to
the same owner filer, this in-memory mutex is sufficient cluster-wide: there
is exactly one place in the system that holds the lock for that key.

Idle entries are evicted by the `util.LockTable` itself, so the table size
tracks active concurrency, not total entries.

## Layer 3 — `ObjectTransaction` (composite atomic op)

`ObjectTransaction` is the canonical atomic primitive. One request describes:

* `route_key` — used by Layer 1 to forward to the owner;
* `lock_key` — the path the per-path lock is taken on (Layer 2);
* `condition` (optional) — a precondition evaluated against `condition_key`
  (or `lock_key`), e.g. "object exists with this ETag", or `If-None-Match: *`;
* `mutations` — an ordered list of CreateEntry / UpdateEntry / DeleteEntry
  operations applied in order under the lock.

If the condition fails, the request returns `FilerError_PRECONDITION_FAILED`
with no mutations applied. If any mutation fails, the response carries the
error and the rest are not applied. The whole sequence runs under one
exclusive hold of the per-path lock, so concurrent writers of the same
object cannot interleave.

`ObjectTransactionBatch` lets a caller submit several independent
transactions in one round trip; each runs under its own per-path lock, and a
failure in one does not abort the rest (matching S3 multi-object semantics).

This replaces the old pattern of "take a distributed lock → do RPC A → do
RPC B → release lock" with one RPC that the caller cannot drop mid-sequence.

Typical callers:

| Caller | Why a transaction |
|---|---|
| S3 versioned PUT/DELETE | Atomically write the version + flip the `latest` pointer + create/delete a marker |
| S3 conditional writes ([S3 Conditional Operations](./S3-Conditional-Operations.md)) | Evaluate `If-Match`/`If-None-Match` against current state under lock |
| S3 Object Lock ([S3 Object Lock and Retention](./S3-Object-Lock-and-Retention.md)) | Enforce WORM guards against the existing entry as a precondition |
| Lifecycle expirations | Delete an entry only if its metadata still matches the rule that selected it |

The implementation lives at
[`weed/server/filer_grpc_server.go: ObjectTransaction`](https://github.com/seaweedfs/seaweedfs/blob/master/weed/server/filer_grpc_server.go);
the proto is in [`weed/pb/filer.proto`](https://github.com/seaweedfs/seaweedfs/blob/master/weed/pb/filer.proto)
(messages `ObjectTransactionRequest`, `ObjectTransactionResponse`,
`ObjectMutation`, `WriteCondition`).

## Ring changes — the hard part

A filer joining or leaving the ring shifts which filer owns a subset of
keys. For a single key, ownership transitions atomically the moment every
filer applies the new snapshot — but they do not all apply it at the same
instant. There is a brief window in which:

1. The new owner has the snapshot and starts accepting writes,
2. The old owner has not yet seen the snapshot and still accepts writes,
3. The new owner's in-memory state for that key is empty (it never owned it
   before).

Two mechanisms keep this window safe.

### Snapshot history + prior-owner cooling probe

`LockRing` keeps the last few snapshots, not just the current one, with
timestamps ([`weed/cluster/lock_manager/lock_ring.go`](https://github.com/seaweedfs/seaweedfs/blob/master/weed/cluster/lock_manager/lock_ring.go)).
`PriorOwner(key)` returns the previous snapshot's owner, but only while the
previous snapshot is still inside the cooling-off window (the snapshot
interval). Each snapshot prebuilds its own `HashRing` so prior-owner lookup
is O(1).

When the new owner gets a non-blocking call that would normally answer
"no conflict, granted," it first checks: is there a prior owner in the
cooling window? If so, it sends a bounded probe to the prior owner asking
"do you hold a conflict for this key?" The probe is marked so the recipient
answers locally without re-forwarding. The probe is deadline-bounded
(`posixCoolingProbeTimeout = 2 * time.Second`) so a slow peer cannot stall
a non-blocking call.

If the probe says "conflict," the new owner reports the conflict and lets
the caller retry. If the probe times out or errors, the new owner
fail-closes (treats it as a conflict) rather than risk a double grant.

### Warm-up window on owner (re)start

When a filer starts (or restarts), it has no in-memory state for any key.
For a short warm-up period it cannot trust "no local conflict" as the truth
even for keys it now owns — a holder from before the restart may still be
in the system.

Each filer tracks `posixLockReadyAt` (atomic, set by the sweeper after the
first successful sweep). For `posixLockWarmup` (currently 10s) after that
timestamp, the owner defers granting non-blocking acquires whose
conflicts it cannot verify, instead returning the same fail-closed
conflict shape as the cooling probe. Holders re-assert their locks on the
next keepalive (see [Distributed POSIX Locks](./Distributed-POSIX-Locks.md)), so the warm-up window
ends with the owner's state correctly rebuilt.

This combination — snapshot history + cooling probe + warm-up — is what
lets the cluster admit and evict filers without dropping the
"single-serialization-point-per-key" guarantee that everything else
depends on.

The cooling logic is in
[`weed/server/filer_grpc_server_posix_lock.go`](https://github.com/seaweedfs/seaweedfs/blob/master/weed/server/filer_grpc_server_posix_lock.go);
ObjectTransaction reuses the same `LockRing.GetPrimary` / forwarding path
and inherits the snapshot-history protection.

## What this lets you build

Because the serialization layer is generic, anything routed by key inherits
the same atomicity guarantee. Two examples shipped in master:

* **S3 conditional / versioned writes** ([S3 Conditional Operations](./S3-Conditional-Operations.md),
  [S3 Object Versioning](./S3-Object-Versioning.md), [S3 Object Lock and Retention](./S3-Object-Lock-and-Retention.md)) — the S3
  gateway sends an `ObjectTransaction` with the conditional headers as the
  precondition and the version-pointer recompute as the mutation list. No
  distributed lock is held across the multi-entry update.
* **Cross-mount POSIX advisory locks** ([Distributed POSIX Locks](./Distributed-POSIX-Locks.md)) — the
  mount calls a dedicated `PosixLock` RPC that uses the same route-by-key,
  one-hop forwarding, snapshot history, and warm-up logic; the authority is
  an in-memory `posixlock.Manager` on the owner filer rather than the entry
  lock table.

## See also

* [Distributed POSIX Locks](./Distributed-POSIX-Locks.md)
* [S3 Conditional Operations](./S3-Conditional-Operations.md)
* [S3 Object Versioning](./S3-Object-Versioning.md)
* [Filer Server API](./Filer-Server-API.md)
