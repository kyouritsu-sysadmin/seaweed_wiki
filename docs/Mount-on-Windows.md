---
id: Mount-on-Windows
title: "Mount on Windows"
sidebar_label: "Mount on Windows"
---

Windows has no FUSE of its own, so `weed mount` goes through [WinFsp](https://winfsp.dev/), which provides the filesystem driver. The filesystem code underneath is the same one Linux and macOS run, so behaviour matches those platforms except where Windows cannot express something.

This is beta. It is exercised by CI on every change, but it has had far less production use than the unix mount.

### Install WinFsp

Download the installer from [winfsp.dev](https://winfsp.dev/rel/) or:

```powershell
choco install winfsp
```

The default feature set is enough. `weed.exe` loads `winfsp-x64.dll` at run time, so nothing is needed at build time and no developer package is required. WinFsp supports x86, x64 and ARM64; the architecture has to match the `weed.exe` you run.

### Mount

```powershell
weed.exe mount -filer=127.0.0.1:8888 -dir=S:
```

The mount point is one of:

* a **drive letter**, `S:`, which must be free
* a **directory that does not exist yet**, `C:\seaweed\data` — its parent must exist
* a **UNC path**, `\\seaweedfs\data`

WinFsp creates the directory itself and removes it again when the filesystem goes away, so the path must be free. An existing directory is refused with "mount point in use" even when it is empty.

Prefer `127.0.0.1` over `localhost`. Windows resolves `localhost` to `::1` first, and a filer listening only on IPv4 will refuse the connection.

Stop the mount with Ctrl-C, which unmounts cleanly and flushes pending writes. Killing the process leaves anything not yet flushed unwritten, the same as pulling the plug on any filesystem.

### Windows-specific options

| Flag | Meaning |
| --- | --- |
| `-windows.caseInsensitive` | Match names case-insensitively. Off by default. |
| `-readOnly` | Reject every modification at the WinFsp layer. |
| `-cacheMetaTtlSec` | How long WinFsp may cache attributes and directory entries. |
| `-debug.fuse` | Log every filesystem operation. |
| `-volumeName` | Name shown by Explorer for the disk, overriding the name taken from `-filer.path` or `-dir`. See [Disk name](#disk-name). |

Everything else — `-cacheDirForRead`, `-cacheSizeMBForRead`, `-chunkSizeLimitMB`, `-collection`, `-replication`, `-concurrentWriters` — behaves as it does elsewhere. See [FUSE Mount](./FUSE-Mount.md).

### Disk name

Explorer labels the mounted disk after the mounted path:

* `-filer.path=/Image Disk` shows up as `Image Disk`.
* Mounting the whole tree (`-filer.path=/`) takes the name from the mount point instead, so `-dir=\\seaweedfs\Images` labels the disk `Images` while still mounting everything.
* A bare drive letter (`-dir=S:`) has no name to take, so the disk falls back to the filer address.

The derived name can collide with the real drive it sits on, or with another mount's label. `-volumeName` overrides the derivation without changing what is mounted:

```powershell
weed.exe mount -filer=127.0.0.1:8888 -dir=\\seaweedfs\Images -volumeName=Photos
```

This mounts `\\seaweedfs\Images` as before but labels the disk `Photos`. The UNC share name (`\\seaweedfs\Images`) is unaffected — only the volume label changes. Leave `-volumeName` empty to keep the old behaviour. Commas in the value are replaced with `+`, since WinFsp treats commas as option separators.

#### Case sensitivity

The filer is case-sensitive, and so is the mount by default: `Report.txt` and `report.txt` are two files. Some Windows software assumes otherwise and will misbehave. `-windows.caseInsensitive` makes the mount match Windows expectations, at the cost of making one of any two names that differ only in case unreachable. WinFsp cannot do NTFS-style mixed sensitivity, so it is one or the other for the whole mount.

#### Coherence between mounts

There is no way to invalidate the Windows cache from the filesystem side, so a mount notices another mount's changes only once its cached attributes expire. Lower `-cacheMetaTtlSec` if several machines write the same files; raise it if a single machine wants the metadata cache to work harder.

### Large directories

A directory with hundreds of thousands of entries enumerates fine — the mount pages through it rather than materialising the whole listing, and CI covers directories in the thousands. Explorer itself is the slow part at that size; `dir`, PowerShell and application code are much faster than the graphical shell.

### What Windows cannot do

| | |
| --- | --- |
| Hard links | Not supported by WinFsp. `mklink /H` fails. |
| Symbolic links | Refused. The entry would need a reparse point the mount does not create yet. |
| Byte-range locks | Handled inside the WinFsp driver, so they are local to one machine. The mount's distributed locking does not extend to Windows. |
| Extended attributes | Not wired up. |
| POSIX ownership | Files belong to whoever started the mount. Unix uid/gid do not map onto Windows accounts. |

Entries whose names Windows cannot represent are invisible from a Windows mount, and stay reachable from other clients. That means anything containing `\ / : * ? " &lt;&gt; |`, anything ending in a space or a dot, and the reserved device names `CON`, `PRN`, `AUX`, `NUL`, `COM1`-`COM9`, `LPT1`-`LPT9`.

### Running as a service

`weed mount` runs in the foreground and a mount belongs to the session that created it, so a mount started by hand disappears at logout and is not visible to services. To keep one up, run it as a Windows service with a wrapper such as [WinSW](https://github.com/winsw/winsw) or [NSSM](https://nssm.cc/), and give WinFsp `-o UNC` or a drive letter that the service account can reach.

### Troubleshooting

**"WinFsp refused to mount S:"** — WinFsp is not installed, the drive letter is taken, or the directory path already exists. `net use` lists the drive letters in use.

**The mount exits reporting it cannot reach the filer** — check the filer's gRPC port, which is its HTTP port plus 10000 (`8888` → `18888`). It is the gRPC port the mount dials, so a filer answering on HTTP is not proof it is reachable. Use `127.0.0.1` rather than `localhost`.

**Nothing appears in the logs** — `weed.exe` writes through glog, which logs to its own files by default. Pass `-logtostderr` *before* the subcommand, since glog's flags are global:

```powershell
weed.exe -logtostderr mount -filer=127.0.0.1:8888 -dir=S:
```

**Explorer is sluggish in a huge directory** — it is rendering, not the filesystem. Compare against `dir` in the same folder before investigating further.

### Building from source

```powershell
$env:CGO_ENABLED=0
go build -o weed.exe ./weed
```

`CGO_ENABLED=0` matters. With cgo enabled the FUSE binding compiles against WinFsp's C headers, which the default install does not ship; without it the binding loads the DLL at run time instead. This is also how the released `weed.exe` is built, and it means Windows builds cross-compile from Linux or macOS:

```bash
CGO_ENABLED=0 GOOS=windows GOARCH=amd64 go build -o weed.exe ./weed
```
