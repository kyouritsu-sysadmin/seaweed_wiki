---
id: POSIX-Compliance
title: "POSIX Compliance"
sidebar_label: "POSIX Compliance"
---

# POSIX Compliance for `weed mount`

**`weed mount` passes 100% of the pjdfstest POSIX compliance suite
(236 test files, 8,819 assertions, zero skipped).**

SeaweedFS runs the [pjdfstest](https://github.com/pjd/pjdfstest) POSIX
compliance suite against `weed mount` on every change to `weed/mount/**`,
`weed/filer/**`, or the test harness itself. The job is defined in
[`.github/workflows/pjdfstest.yml`](https://github.com/seaweedfs/seaweedfs/blob/master/.github/workflows/pjdfstest.yml)
and the harness lives under [`test/pjdfstest/`](https://github.com/seaweedfs/seaweedfs/tree/master/test/pjdfstest).

The suite is pinned to the [`sanwan/pjdfstest`](https://github.com/sanwan/pjdfstest)
fork, which adds NAME_MAX-aware variants of the upstream tests.

## How it runs

1. A SeaweedFS e2e image (master + volume + filer + mount) is built and
   started via `test/pjdfstest/docker-compose.yml`.
2. `test/pjdfstest/run.sh` mounts the filesystem with `weed mount
   -allowOthers=true` and clones pjdfstest pinned to an immutable commit
   for reproducibility.
3. `prove -rv` runs every `tests/**/*.t`. Any failure that is not listed
   in [`known_failures.txt`](https://github.com/seaweedfs/seaweedfs/blob/master/test/pjdfstest/known_failures.txt)
   fails CI.

## Status

**100% passing.** All 236 pjdfstest test files (8,819 individual
assertions) pass on `weed mount`, with zero tests skipped. The
`known_failures.txt` allow-list is empty, so any regression in any test
fails CI immediately.

The syscall groups exercised by the suite are:

| Group | Coverage |
|-------|----------|
| `tests/chflags/` | BSD file flags (skipped on Linux by the suite itself) |
| `tests/chmod/` | `chmod(2)` permission, errno, and setuid/setgid behavior |
| `tests/chown/` | `chown(2)` ownership, errno, and clearing of set\*id bits |
| `tests/link/` | `link(2)` creation, permission, and errno cases |
| `tests/mkdir/` | `mkdir(2)` creation and errno paths |
| `tests/mkfifo/` | `mkfifo(2)` FIFO creation |
| `tests/mknod/` | `mknod(2)` regular/FIFO node creation |
| `tests/open/` | `open(2)` flags, permissions, `O_CREAT`, `O_TRUNC`, errno |
| `tests/rename/` | `rename(2)` same/cross-directory, errno cases |
| `tests/rmdir/` | `rmdir(2)` empty-directory and errno cases |
| `tests/symlink/` | `symlink(2)` creation, traversal, errno cases |
| `tests/truncate/` | `truncate(2)` resize, permission, and errno cases |
| `tests/unlink/` | `unlink(2)` removal and errno cases |
| `tests/utimensat/` | `utimensat(2)` atime/mtime/ctime semantics, errno paths |
| `tests/granular/` | Granular timestamp update checks |

## Running locally

```sh
# Full suite against a local weed binary (requires sudo, fusermount3,
# autoconf, make, perl TAP::Harness::Archive).
test/pjdfstest/run.sh

# Subset, e.g. only chmod tests
PJDFSTEST_TESTS=tests/chmod test/pjdfstest/run.sh

# Containerized (matches CI exactly)
docker compose -f test/pjdfstest/docker-compose.yml up --wait
docker compose -f test/pjdfstest/docker-compose.yml exec mount /run.sh
```

See also: [FUSE Mount](./FUSE-Mount.md).
