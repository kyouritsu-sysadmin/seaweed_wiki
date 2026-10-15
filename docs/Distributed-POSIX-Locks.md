---
id: Distributed-POSIX-Locks
title: "Distributed POSIX Locks"
sidebar_label: "Distributed POSIX Locks"
---

# Distributed POSIX Locks

`weed mount` supports cross-mount POSIX advisory locks — `flock(2)` and
`fcntl(F_SETLK/F_SETLKW)` — so a lock taken on one mount is honored by every
other mount of the same cluster. The feature is opt-in: pass `-dlm` to `weed
mount`. Without it, locks remain per-mount only (the historical behavior).

This builds directly on [Filer Operation Serialization](./Filer-Operation-Serialization.md): the same route-by-key
layer is reused, with a different authority (an in-memory POSIX lock table on
the owner filer) and a different RPC.

## Why route, not replicate

POSIX advisory locks are transient coordination, not durable data. Replicating
them through the metadata log would add write churn to every advisory lock
operation; failover would still race the application's expectations.

The chosen shape — owner filer per inode + in-memory authority + client-side
polling for blocking acquires + session leases for dead-client cleanup — is
the established pattern for shared-store advisory locking. SeaweedFS already
has the routing layer (the lock ring built for the DLM and reused by
ObjectTransaction), so adding POSIX semantics on top is a small addition.

## At a glance

```
   app on mount A                       app on mount B
        │                                    │
        │  flock(fd, LOCK_EX)                │  flock(fd, LOCK_EX)
        ▼                                    ▼
   weed mount A  ─── PosixLock RPC ───►  filer X (owner of this inode)
                                              │
                                              ▼  posixlock.Manager
                                         in-memory Set per inode
                                              ▲
   weed mount B  ─── PosixLock RPC ───►  filer Y → forward (is_moved) → filer X
```

Every mount picks the filer it talks to (the `-filer=` argument). That filer
checks the lock ring, and if it is not the owner of this key, forwards the
RPC one hop to the owner. The owner's in-memory `posixlock.Manager` is the
single source of truth.

Blocking acquires (`F_SETLKW`) are **client-side polling**: the mount
re-sends the non-blocking try with bounded backoff until it succeeds or the
syscall is cancelled. There is no server-side wait queue.

## The key

The mount converts a FUSE inode to a *cluster-stable* lock identity in
[`weed/mount/weedfs_posix_lock_routed.go: posixLockKeyForInode`](https://github.com/seaweedfs/seaweedfs/blob/master/weed/mount/weedfs_posix_lock_routed.go):

| Entry kind | Lock key |
|---|---|
| Regular file | `"s3.fuse.lock:" + path` |
| Hardlinked file | `"s3.fuse.lock:hl:" + hex(HardLinkId)` |

POSIX locks are inode-scoped, not name-scoped. Using the `HardLinkId` for
linked files makes every name for the same inode share one lock table, which
matches what local POSIX gives you and means rename does not move locks.

The FUSE NodeId is mount-local (`AsInode = hash(path) + time`), so it cannot
be used cross-mount.

## Authority — `posixlock.Manager`

The owner filer keeps the lock state in
[`weed/filer/posixlock/manager.go`](https://github.com/seaweedfs/seaweedfs/blob/master/weed/filer/posixlock/manager.go):

* `Set` — a per-inode collection of byte-range `Range`s with `Type`
  (Read/Write), `Sid` (session id, unique per mount), `Owner` (the
  application's lock owner value), and `IsFlock` (flock and fcntl live in
  separate namespaces per POSIX).
* `TryLock` / `Unlock` — non-blocking acquire and release.
* `GetLk` — query without acquiring.
* `ReleasePosixOwner` / `ReleaseFlockOwner` — drop all of an owner's locks on
  a key (close-on-fd semantics).
* `Reassert` — rebuild the lock set from a list a holder sends after an
  ownership change or restart (used by KEEP_ALIVE).
* `Renew` / `ReapExpired` — session-lease bookkeeping.

There is exactly one Manager per filer. Lock state is never written to disk;
it survives only as long as the owner filer keeps running, and the
re-assertion mechanism described below rebuilds it when ownership changes.

## The RPC

Defined in [`weed/pb/filer.proto`](https://github.com/seaweedfs/seaweedfs/blob/master/weed/pb/filer.proto)
as `PosixLockRequest` / `PosixLockResponse`. The op enum:

| Op | What it does |
|---|---|
| `TRY_LOCK` | Non-blocking acquire of one range |
| `UNLOCK` | Release one range |
| `GET_LK` | Query — returns the first conflicting range, if any |
| `RELEASE_POSIX_OWNER` | Release all fcntl ranges owned by `(Sid, Owner)` on this key |
| `RELEASE_FLOCK_OWNER` | Release all flock ranges owned by `(Sid, Owner)` on this key |
| `KEEP_ALIVE` | Renew the session lease; if `locks` is non-empty, re-assert held locks |

A non-blocking grant returns `granted = true`. A conflict returns
`has_conflict = true` and the offending range as `conflict`. The handler
lives in
[`weed/server/filer_grpc_server_posix_lock.go`](https://github.com/seaweedfs/seaweedfs/blob/master/weed/server/filer_grpc_server_posix_lock.go).

## Mount-side flow

Routed POSIX locking lives in
[`weed/mount/weedfs_posix_lock_routed.go`](https://github.com/seaweedfs/seaweedfs/blob/master/weed/mount/weedfs_posix_lock_routed.go).
The mount runs with `-dlm`, which sets `wfs.lockClient`; the FUSE handlers
in [`weed/mount/weedfs_file_lock.go`](https://github.com/seaweedfs/seaweedfs/blob/master/weed/mount/weedfs_file_lock.go)
route through the new path when `wfs.crossMountLocks()` is true.

* **Session id (`Sid`)** — random 64-bit value per mount, namespaces lock
  owners so the same FUSE `Owner` value on two mounts never aliases.
* **`SetLk` (non-blocking)** — one `TRY_LOCK` RPC; map `EWOULDBLOCK`
  to/from `granted=false`.
* **`SetLkw` (blocking)** — `posixPollAcquire` loops `TRY_LOCK` with
  exponential backoff bounded to `posixLockMaxBackoff = 200ms`; the syscall
  cancellation (FUSE INT) translates to `EINTR`.
* **`GetLk`** — single `GET_LK` RPC.
* **`flush` / `release`** — POSIX requires that closing any fd to an inode
  drops the calling process's fcntl locks on that inode. The mount tracks
  `posixLockHint` (a per-inode set of owners we have taken locks for) so it
  can fire `RELEASE_POSIX_OWNER` / `RELEASE_FLOCK_OWNER` on close without an
  RPC on every close to a file we never locked.
* **Keepalive** — `loopRenewPosixLeases` (`posixKeepaliveInterval = 5s`)
  sends KEEP_ALIVE per held key. The payload carries the held locks, so a
  filer that just took over ownership (or just restarted) gets the holder's
  state pushed to it — see "Re-assertion" below.

## Sessions, leases, reaping

Every mount has a 64-bit `Sid`. Every lock the mount takes carries that
`Sid`. The owner filer remembers, per `Sid`, the last time it saw a
KEEP_ALIVE.

`startPosixLockSweeper` ([`weed/server/filer_grpc_server_posix_lock.go`](https://github.com/seaweedfs/seaweedfs/blob/master/weed/server/filer_grpc_server_posix_lock.go))
runs on every filer:

* `posixLockSessionTTL = 15s` — sessions silent longer than this are reaped.
* `posixLockSweepInterval = 5s` — how often each filer checks.

When a session is reaped, all of its locks across every key on this filer
are released. This is how a `kill -9`'d mount stops blocking other mounts —
nothing else does, because the kernel cannot tell the cluster that the FD
holding a flock just went away.

Sessions that never call KEEP_ALIVE are never tracked (no resource cost),
so the sweeper is inert on a cluster without `-dlm` mounts.

## Ring changes — re-assertion + cooling + warm-up

The cooling-probe and warm-up machinery described in [[Filer Operation
Serialization]] applies here directly. The POSIX lock layer adds one piece
on top:

* **Re-assertion via KEEP_ALIVE.** When a mount's keepalive fires, it sends
  every held lock on that key in the request payload, not just a bare
  renew. The owner's `posixlock.Manager.Reassert` rebuilds the lock set
  from that payload and reports any range it could not reassert (a real
  loss of lock to a different session). After at most one keepalive
  interval following a ring change, every new owner has been told about
  every lock its keys carry — and the warm-up window (10s) is sized to
  cover that re-assertion round trip even under load.

The combined picture across an ownership change:

1. Master broadcasts the new filer set; every filer applies the new
   snapshot to its `LockRing` (with the old snapshot retained for
   `LockRing.snapshotInterval`).
2. New owner sees PosixLock RPCs for keys it now owns. Its in-memory
   `posixlock.Manager` has no entries for those keys yet.
3. For each request, the new owner asks the prior owner (via
   `PriorOwner(key)`) whether it sees a conflict — bounded by
   `posixCoolingProbeTimeout = 2s`. The prior owner replies from its
   in-memory state with `cooling_probe=true`, so the answer is local
   and definitive.
4. Within `posixKeepaliveInterval = 5s`, every mount holding a lock on
   one of the migrated keys re-asserts via KEEP_ALIVE. The new owner's
   state for that key is now correct.
5. The cooling-snapshot ages out (typically `snapshotInterval` after the
   ring update). After that, the new owner trusts its local state
   unconditionally.

A filer that just *started* is in its own warm-up window
(`posixLockWarmup = 10s`); during that window it fail-closes on
acquire requests whose "no conflict" answer it cannot verify yet, so
restarts cannot create double grants either.

## Platform notes

POSIX advisory locks are only forwarded to the FUSE server on Linux. The
macFUSE kernel module handles `flock` *in the kernel, per mount*, and does
not forward `SETLK` opcodes to the userspace filesystem at all — so two
`weed mount` instances on the same macOS machine cannot coordinate flocks
even with `-dlm`. This is a macFUSE behavior, not a SeaweedFS one. The
routed lock path itself works the same on macOS; there is just nothing for
it to handle.

The integration test
[`test/fuse_dlm/posix_lock_ring_test.go`](https://github.com/seaweedfs/seaweedfs/blob/master/test/fuse_dlm/posix_lock_ring_test.go)
skips on non-Linux for this reason.

## Configuration

To enable cross-mount POSIX locks:

```
weed mount -dir=/mnt/sw -filer=filer1:8888 -dlm
```

`-dlm` enables the routed POSIX locks (and the whole-file write lock that
predates this work; see [FUSE Mount](./FUSE-Mount.md)). It is opt-in because:

* `flock`/`fcntl` calls now make an RPC instead of touching a process-local
  table — meaningful for applications that lock-on-every-write.
* Cluster operators that do not need cross-mount advisory locks are not
  affected; the default keeps the per-mount table.

No filer-side flag is needed. Every filer registers itself in the lock
ring as part of joining the cluster, and the sweeper is inert until a
`-dlm` mount calls KEEP_ALIVE.

## What is not done by this layer

* **Mandatory locks** (Linux `chmod g+s,o-x` mandatory mode) — advisory
  only, as POSIX recommends.
* **Process-tree inheritance of fcntl owners** — handled by the kernel and
  the application, not the filer.
* **Replication of lock state** — locks are kept in memory and rebuilt by
  re-assertion. A filer crash with a `-dlm` mount holding locks on its
  keys means those keys are unprotected for the cooling window plus the
  re-assertion round trip; the design accepts that as the cost of keeping
  the lock path off the metadata log.

## See also

* [Filer Operation Serialization](./Filer-Operation-Serialization.md) — the routing, per-path lock, and
  ring-change machinery this page builds on.
* [FUSE Mount](./FUSE-Mount.md)
* [POSIX Compliance](./POSIX-Compliance.md)
* [S3 Object Lock and Retention](./S3-Object-Lock-and-Retention.md) — the unrelated S3 mechanism (object
  metadata, not advisory locks).
