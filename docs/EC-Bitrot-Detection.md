---
id: EC-Bitrot-Detection
title: "EC Bitrot Detection"
sidebar_label: "EC Bitrot Detection"
---

Erasure-coded volumes can suffer **silent disk corruption (bitrot)** that normal serving never notices. EC bitrot detection adds an optional per-volume checksum sidecar so corruption in any shard — including cold parity shards — can be detected and the rebuild path refuses to consume unverified bytes.

## The problem

* **Data shards** (`.ec00`–`.ec09`) are read on the serving path, so corruption in regions that happen to be read is already caught by the per-needle CRC. Padding and unread regions are not.
* **Parity shards** (`.ec10`–`.ec13`) are **never read during normal serving**. They are only touched during reconstruction, and Reed-Solomon treats every present shard as authoritative — it fills missing shards but does not detect corruption in the shards it reads.

So a parity shard can rot silently for months. The day a data shard is lost and reconstruction runs, the corrupt parity is fed into Reed-Solomon and **silently produces wrong data**.

## How it works

A small sidecar file `&lt;volume&gt;.ecsum` stores a `CRC32C` (Castagnoli, the same polynomial used for needles) for every fixed-size block (default 16 MiB) of every shard. It is wrapped in a self-integrity header (`magic | format_version | payload_len | payload_crc32c`), so a corrupt sidecar is itself detectable and can never be mistaken for shard corruption.

* **Tiny:** about 11 KB for a 30 GB volume.
* **Optional and backward compatible:** an absent sidecar means "feature off". Older binaries simply ignore the file — no mount failure, safe to roll back.

### At encode time

The checksums are computed inline during the single EC encode pass and written next to the shards. When shards are distributed across servers, the sidecar travels with them.

### Detecting corruption — `ec.scrub`

A new read-only `checksum` mode reads each local shard in blocks and compares it to the sidecar. This is the only path that exercises **cold parity shards**.

```
ec.scrub -mode checksum
ec.scrub -mode checksum -volumeId 7 -node 127.0.0.1:8080
```

A flagged shard is arbitrated by Reed-Solomon: the shard is reconstructed from the other (clean) shards and compared to what is on disk, so a stale sidecar block can never cause a healthy shard to be reported as corrupt. If more than `parity` shards mismatch at once, the sidecar itself is treated as suspect rather than reporting mass corruption. `ec.scrub` is read-only and never deletes anything.

### Safe reconstruction

During rebuild, present input shards are verified against the sidecar and corrupt ones are **excluded from Reed-Solomon and regenerated** (written to a temp file and atomically renamed), then re-verified. This closes the "corrupt parity silently poisons a rebuild" hole.

If the sidecar is present but malformed, the rebuild **fails closed** rather than rebuilding without verification — pass `-unsafeIgnoreSidecar` to override. On any verification failure the rebuild removes every file it generated, so it never publishes bytes it could not verify.

### Backfilling existing volumes

Volumes encoded before this feature have no sidecar. When such a volume is rebuilt on a server that can reach all of its shards, a sidecar is written automatically (trust-on-first-use), so existing volumes become protected over time.

## Configuration

On the volume server:

| Flag | Default | Meaning |
|------|---------|---------|
| `-ec.bitrotChecksum` | `true` | Write a `.ecsum` sidecar when generating EC shards |
| `-ec.bitrotBlockSizeMB` | `16` | Checksum block granularity in MiB (power of two, ≥ 1) |

```bash
weed volume -dir=/data -ec.bitrotChecksum -ec.bitrotBlockSizeMB=16
```

## Side notes

* The 10+4 ratio is the default for the open source version.
* The checksum block size is a uniform overlay on the raw shard bytes; it does not need to align with the 1 GB / 1 MB EC block layout.
* The [SeaweedFS Enterprise](https://seaweedfs.com/) version adds a **scheduled background scrubber** that continuously verifies cold parity across the fleet with optional auto-repair, ties checksums into the versioned EC vacuum, and provides a coordinator-driven backfill command for protecting existing volumes in bulk.

See also: [Erasure coding for warm storage](./Erasure-Coding-for-warm-storage.md).
