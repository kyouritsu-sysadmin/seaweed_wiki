---
id: fstab-and-systemd-mount
title: "fstab and systemd mount"
sidebar_label: "fstab and systemd mount"
---

# fstab

To mount SeaweedFS using `/etc/fstab` (such as on boot):
 
* Follow the directions in https://github.com/seaweedfs/seaweedfs/wiki/FUSE-Mount for setting up a SeaweedFS mount subtype for FUSE (hint: `cp weed /sbin/mount.weed`)
* Install SeaweedFS as usual, making sure any specific settings (such as `security.toml`) are in the correct location to be read
* Add the fstab entry as described below

If you have a single filer server, this is the syntax you will use:

`fuse /path/to/mountpoint fuse.weed filer=localhost:8888,filer.path=/,defaults,_netdev 0 0`

If you have multiple filer servers, this is the syntax you will use:

`fuse /path/to/mountpoint fuse.weed filer='192.168.0.1:8888,192.168.0.2:8888',filer.path=/,defaults,_netdev 0 0`

Place the appropriate line into `/etc/fstab` and attempt to mount your filesystem. If you encounter any issues, run `weed mount` directly in verbose/debug mode to diagnose the issue, and switch back to fstab-style mounting once you have resolved the issues.

## Systemd

Systemd takes over and enhances fstab-based mount in the following two ways:

* `systemd-fstab-generator(8)` will translate the mount option in /etc/fstab into `systemd.mount` / `systemd.automount` units. Systemd-related enhancement option (`nofail`, `x-systemd.device-timeout`, `x-systemd.mount-timeout`, `x-systemd.automount`, etc.) will be parsed into systemd.mount options.
* Explicit `systemd.mount` / `systemd.automount` unit files configured.

If you don't use `systemd.automount` option, editing /etc/fstab as above and enable systemd-fstab-generator. (On modern systemd-based systems this is enabled by default).

### systemd.automount

[`systemd.automount`](https://www.freedesktop.org/software/systemd/man/latest/systemd.automount.html) is a tool where systemd automatically and transparently handles on-demand connection and disconnect when not needed.

**Mount onto root-owned mountpoint**

If mountpoint is owned by root, fstab can do the job, by adding x-systemd.automount (and related options) and `autofs` to fstab entries.

`fuse /path/to/mountpoint fuse.weed filer='192.168.0.1:8888,192.168.0.2:8888',filer.path=/,x-systemd.automount,x-systemd.idle-timeout=300,autofs,defaults,_netdev 0 0`

Added options:
- `x-systemd.automount`: enables systemd automount
- `x-systemd.idle-timeout=300`: set systemd auto-disconnect timeout
- `autofs`: makes weed fuse compatible with systemd.automount.

**Mount onto user-owned mountpoint**

If the mountpoint needs to be owned by a user, e.g. mounting `/home/user` which is owned by user:user, manual systemd.mount / systemd.automount files is required to pass correct uid/gid to autofs.

Create following systemd unit files:

/etc/systemd/system/path-to-mount.automount
```
[Automount]
Where=/path/to/mount
TimeoutIdleSec=30
ExtraOptions=uid=USERID,gid=GROUPID
```

Here ExtraOptions sets the uid/gid.

/etc/systemd/system/path-to-mount.mount
```
[Mount]
What=fuse
Where=/path/to/mount
Type=weed
Options=filer=localhost:8888,filer.path=/,autofs
```

If you are unsure about the options, you can utilize systemd-fstab-generator to generate one:

Add your line to /etc/fstab temporarily:
```
fuse /path/to/mountpoint fuse.weed filer='192.168.0.1:8888,192.168.0.2:8888',filer.path=/,x-systemd.automount,x-systemd.idle-timeout=300,autofs,defaults,_netdev 0 0
```

run `systemd daemon-reload` and check generated files:

```
systemd cat path-to-mountpoint.mount
systemd cat path-to-mountpoint.automount
```

Add the line `ExtraOptions=uid=USERID,gid=GROUPID` to the automount and create both files in /etc/systemd/system. Remove the temporary fstab entries, and run `systemd daemon-reload` again.

You can enable the automount by `systemctl enable --now path-to-mountpoint.automount`.
