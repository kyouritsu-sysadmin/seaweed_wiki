---
id: SeaweedFS-in-Docker-Swarm
title: "SeaweedFS in Docker Swarm"
sidebar_label: "SeaweedFS in Docker Swarm"
---

## Architecture

This is an example stack for a Docker Swarm consisting of three nodes (`node1, node2, node3`). There is one SeaweedFS [Master](https://github.com/seaweedfs/seaweedfs/wiki/Components#master-service) in total, with one [Filer](https://github.com/seaweedfs/seaweedfs/wiki/Components#filer-service) per node and one [Volume](https://github.com/seaweedfs/seaweedfs/wiki/Components#volume-concept) per node as well. The Filers are configured to prefer writing to Volumes on the same node as itself—if one exists—and likewise with the globally deployed [Mounts](https://github.com/seaweedfs/seaweedfs/wiki/Components#volume-concept) (see "Optional Services" below) preferring to connect to a local Filer. 

## Default configuration

The included configurations are just examples. Here, for instance, the default is a volume replication of `200`, meaning that all writes will be replicated on two nodes on two different datacenters. In the case of our example three nodes, this means the same volumes will be present on every node. Additionally, volumes are configured to be smaller (`1 GB`) than the default (`30 GB`), garbage collection is more aggressive than usual (`-garbageThreshold=0.01`), and the Filers are configured to use `leveldb3` as an embedded store for easy [replication](https://github.com/seaweedfs/seaweedfs/wiki/Filer-Store-Replication). 

In other words, make sure to adapt the configuration to your needs.

## Optional services

Also included are two add-on services that might prove useful: `mount` and `cron`. 

+ `mount` uses [Docker-in-Docker](https://hub.docker.com/_/docker) to deploy a [FUSE mount](https://github.com/seaweedfs/seaweedfs/wiki/FUSE-Mount) on every node in the Swarm, so that the files on SeaweedFS may be accessed from anywhere in the Swarm.
+ `cron` relies on a [swarm-cronjob](https://github.com/crazy-max/swarm-cronjob/) service (not included in this example) to run various maintenance operations on a set schedule.

## Deployment

Assuming you have adjusted the Docker stack files and configs below to suit your environment (for instance, your nodes are probably not called `node1, node2...`, you may have another [overlay network](https://docs.docker.com/network/overlay/) than the `public` of this example, etc.):

+ On every Swarm node:

```
mkdir -p /mnt/{cch,cld,seaweedfs}
mkdir -p /mnt/seaweedfs/{filer,master,metabackup,volume}
```

The published Docker image now defaults to the non-root `seaweed` user (UID/GID `1000:1000`). Since this stack bind-mounts host directories and overrides the image entrypoint with custom scripts, make those directories writable by `1000:1000` before deployment. A simple option is:

```
chown -R 1000:1000 /mnt/seaweedfs
```

+ On a Swarm master node:

```
docker stack deploy -c docker-compose.yml seaweedfs
``` 

---
**`docker-compose.yml`**
```
version: "3.9"

networks:
  public:
    external: true

configs:
  filer:
    file: ./filer.sh
  mount:
    file: ./mount.sh
  volume:
    file: ./volume.sh

x-filer: &filer
  image: chrislusf/seaweedfs:latest
  environment:
    - HOST={{.Node.Hostname}}
  entrypoint: /filer.sh
  networks:
    - public
  volumes:
    - /mnt/seaweedfs/filer:/data/filerdb
  configs:
    - source: filer
      target: /filer.sh
      mode: 755

x-volume: &volume
  image: chrislusf/seaweedfs:latest
  environment:
    - HOST={{.Node.Hostname}}
  entrypoint: /volume.sh
  networks:
    - public
  volumes:
    - /mnt/seaweedfs/volume:/data
  configs:
    - source: volume
      target: /volume.sh
      mode: 755

services:
  master:
    image: chrislusf/seaweedfs:latest
    command: 
      - "master"
      - "-defaultReplication=200"
      - "-volumeSizeLimitMB=1024"
      - "-garbageThreshold=0.01"
      - "-mdir=/data"
    networks:
      - public
    volumes:
      - /mnt/seaweedfs/master:/data
    deploy:
      placement:
        max_replicas_per_node: 1

  mount:
    image: docker:dind
    cap_add: 
      - SYS_ADMIN
    networks:
      - public
    environment:
      - HOST={{.Node.Hostname}}
    volumes:
      - /mnt:/mnt:rshared
      - /var/run/docker.sock:/var/run/docker.sock:ro
    entrypoint: /mount.sh
    init: true
    stop_grace_period: 30s
    configs:
      - source: mount
        target: /mount.sh
        mode: 755
    deploy:
      mode: global

  cron: # depends on https://github.com/crazy-max/swarm-cronjob/
    image: chrislusf/seaweedfs:latest
    networks:
      - public
    environment:
      SHELL_MASTER: seaweedfs_master:9333
    volumes:
      - /mnt/seaweedfs/metabackup:/data
    command: 
      - "shell"
      - "lock;"
      - "volume.deleteEmpty -quietFor=24h -force;"
      - "volume.balance -force;"
      - "volume.fix.replication;"
      - "unlock"
    deploy:
      restart_policy:
        condition: none
      labels: 
        - swarm.cronjob.enable=true
        - swarm.cronjob.schedule=0 3 * * *
        - swarm.cronjob.skip-running=true

  filer_node1:
    <<: *filer
    deploy:
      placement:
        constraints:
          - "node.hostname == node1"
  filer_node2:
    <<: *filer
    deploy:
      placement:
        constraints:
          - "node.hostname == node2"
  filer_node3:
    <<: *filer
    deploy:
      placement:
        constraints:
          - "node.hostname == node3"

  volume_node1:
    <<: *volume
    deploy:
      placement:
        constraints:
          - "node.hostname == node1"
  volume_node2:
    <<: *volume
    deploy:
      placement:
        constraints:
          - "node.hostname == node2"
  volume_node3:
    <<: *volume
    deploy:
      placement:
        constraints:
          - "node.hostname == node3"
```
---
**`filer.sh`**
```
#!/bin/sh

# prefer writing to volume server on the same node
volume_hosts="node1 node2 node3"
if [ "${volume_hosts#*"$HOST"}" != "$volume_hosts" ]; then
	dc=$HOST
else
	dc=node2 # default value if no volume server exists on the same node
fi

cat > /etc/seaweedfs/filer.toml <<- EOF
	[leveldb3]
	enabled = true
	dir = "/data/filerdb"
EOF

weed filer \
	-master=seaweedfs_master:9333 \
	-ip.bind=0.0.0.0 \
	-ip=seaweedfs_filer_"$HOST" \
	-dataCenter="$dc"
```
---
**`volume.sh`**
```
#!/bin/sh

weed volume \
	-master=seaweedfs_master:9333 \
	-max=0 \
	-dir=/data \
	-dataCenter="$HOST"
```
---
**`mount.sh`**
```
#!/bin/sh

cch=/mnt/cch
mnt=/mnt/cld
cnt_name=seaweedfs_mount_"$HOST"

filer1=node1
filer2=node2
filer3=node3

# prefer connecting to filer on the same node, with the other filers as fallback
case $HOST in
	"$filer1")
		filer=seaweedfs_filer_"$filer1":8888,seaweedfs_filer_"$filer2":8888,seaweedfs_filer_"$filer3":8888
		;;
	"$filer2")
		filer=seaweedfs_filer_"$filer2":8888,seaweedfs_filer_"$filer1":8888,seaweedfs_filer_"$filer3":8888
		;;
	"$filer3")
		filer=seaweedfs_filer_"$filer3":8888,seaweedfs_filer_"$filer1":8888,seaweedfs_filer_"$filer2":8888
		;;
	*) # default value if no filers exist on the same node
		filer=seaweedfs_filer_"$filer2":8888,seaweedfs_filer_"$filer3":8888,seaweedfs_filer_"$filer1":8888
		;;
esac

trap 'cleanup' INT TERM

cleanup() {
	if [ -n "$mount_proc" ]; then
		kill -TERM "$mount_proc"
	else
		docker stop "$cnt_name" > /dev/null 2>&1
		sleep 5
	fi

	if mountpoint -q "$mnt"; then
		umount -f "$mnt" > /dev/null 2>&1
		while mountpoint -q "$mnt"; do
			sleep 5
		done
	fi
}

cleanup
docker run \
	--rm \
	--name="$cnt_name" \
	--net=public \
	--cap-add SYS_ADMIN \
	--security-opt apparmor:unconfined \
	--device /dev/fuse \
	-v /mnt:/mnt:rshared \
	chrislusf/seaweedfs \
		mount \
		-dir="$mnt" \
		-cacheDir="$cch" \
		-cacheCapacityMB=15000 \
		-dirAutoCreate \
		-map.uid="1000:0" \
		-map.gid="1000:0" \
		-allowOthers=true \
		-filer="$filer" \
		-filer.path=/cld/ &

mount_proc=$!
wait "$mount_proc"
```
