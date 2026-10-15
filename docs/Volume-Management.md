---
id: Volume-Management
title: "Volume Management"
sidebar_label: "Volume Management"
---

When managing large clusters, it's common to add more volume servers, have some servers go down, or replace others. These changes can lead to missing volume replicas or an uneven distribution of volumes across the servers.

## Optimize volumes
See [Optimization](./Optimization.md) page on how to optimize for concurrent writes and concurrent reads.

## Configure volume management scripts

Maintenance scripts are managed by the **admin script plugin worker**. Start the admin server and a worker:

```bash
# Start admin server (connects to master)
weed admin -master=localhost:9333

# Start worker (connects to admin server)
weed worker -admin=localhost:23646
```

The admin script plugin has a built-in default script:

```
ec.balance -apply
fs.log.purge -daysAgo=7
volume.deleteEmpty -quietFor=24h -apply
volume.fix.replication -apply
s3.clean.uploads -timeAgo=24h
```

The script and run interval (default: 17 minutes) are configurable from the admin UI at `/plugin`.

Several commands that were previously part of the maintenance script now have dedicated plugin workers:

- **`ec.encode`** is replaced by the **`erasure_coding`** plugin worker. See [Erasure Coding for warm storage](./Erasure-Coding-for-warm-storage.md) for details.
- **`volume.balance`** is replaced by the **`volume_balance`** plugin worker, which detects imbalanced servers and moves volumes automatically.

See the [Worker](./Worker.md) page for more details on `weed worker` options and capabilities.

> **Legacy note:** Previously, maintenance scripts were configured in `master.toml` under `[master.maintenance]`. That mechanism still exists as a fallback but is automatically skipped when an admin server is connected. When migrating, the admin server automatically imports your `master.toml` maintenance scripts as the default admin script configuration. See [Migrate Maintenance Scripts to Admin Script Plugin](./Migrate-Maintenance-Scripts-to-Admin-Script-Plugin.md) for details.

## Fix missing volumes
When running large clusters, it is common that some volume servers are down. If a volume is replicated and one replica is missing, the volume will be marked as readonly.

One way to fix is to find one healthy copy and replicated to other servers, to meet the replication requirement. This volume id will be marked as writable.

In `weed shell`, the command `volume.fix.replication` will do exactly that, automating the replication fixing process. You can start a crontab job to periodically run `volume.fix.replication` to ensure the system health.

## Balance volumes
When running large clusters, it is common to add more volume severs, or some volume servers are down, or some volume servers are replaced. These topology changes can cause unbalanced number of volumes on volume servers.

In `weed shell`, the command `volume.balance` will generate a balancing plan, and `volume.balance -force` will execute the balancing plan and move the actual volumes.

The balancing plan will try to evenly spread the number of writable and readonly 

```
	For each type of volume server (different max volume count limit){
		for each collection {
			balanceWritableVolumes()
			balanceReadOnlyVolumes()
		}
	}

	func balanceWritableVolumes(){
		idealWritableVolumes = totalWritableVolumes / numVolumeServers
		for {
			sort all volume servers ordered by the number of local writable volumes
			pick the volume server A with the lowest number of writable volumes x
			pick the volume server B with the highest number of writable volumes y
			if y > idealWritableVolumes and x+1 <= idealWritableVolumes {
				if B has a writable volume id v that A does not have {
					move writable volume v from A to B
				}
			}
		}
	}
	func balanceReadOnlyVolumes(){
		//similar to balanceWritableVolumes
	}
```
## Add volumes

Run `weed shell` and `volume.mount -node &lt;host&gt;:&lt;port&gt; -volumeId &lt;id&gt;` to mount a volume file.

To mount all new volume files you can send a hang-up signal to the volume server causing a reload with a command such as `pkill -HUP -f "weed volume"`.

## Servicing live volumes

When dealing with hardware storage issues, it can be useful to prevent writes to volume servers _without_ stopping the service altogether - f.ex. on volumes with RAID storage backends. Volume servers support a maintenance mode for this: when enabled, the server becomes read-only. Reads will succeed, but any write attempt will error out.

Maintenance mode can be managed via the `volumeServer.state` shell command:

```
> volumeServer.state
192.168.10.111:9007	 -> Maintenance mode: no
192.168.10.111:9008	 -> Maintenance mode: no
192.168.10.111:9009	 -> Maintenance mode: no

> volumeServer.state --nodes 192.168.10.111:9009 --maintenanceOn
192.168.10.111:9009	 -> Maintenance mode: yes

> volumeServer.state
192.168.10.111:9007	 -> Maintenance mode: no
192.168.10.111:9008	 -> Maintenance mode: no
192.168.10.111:9009	 -> Maintenance mode: yes
```

Maintenance mode is a sticky server state flag. Changes are effective immediately, and will persist even if the server is restarted.