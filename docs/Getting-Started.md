---
id: Getting-Started
title: "Getting Started"
sidebar_label: "Getting Started"
---

# Getting Started

## Quick Start with `weed mini` (Recommended for Most Single-Node and Small-Cluster Setups)

The easiest way to get started with SeaweedFS is the `weed mini` command, which starts all components (master, volume, filer, S3, WebDAV, Admin UI, and the maintenance worker for vacuum/EC/balance) in one process with auto-tuned defaults:

```bash
weed mini -dir=./data
```

This gives you a complete SeaweedFS setup including S3 compatibility and a built-in Admin UI. See [Quick-Start-with-weed-mini.md](./Quick-Start-with-weed-mini.md) for detailed instructions.

**Good for:**
- Learning SeaweedFS, development, and prototyping
- Single-node production setups (S3 gateway, presigned URLs, file storage)
- Small clusters where one node runs `weed mini` and additional `weed volume` servers connect to it for extra capacity

**When to choose [Multi-Component Setup](#multi-component-setup-for-larger-clusters-and-advanced-users) instead:**
- You need multiple master servers (HA / Raft quorum) — `weed mini` is single-master by design
- You want to run components on separate hosts for isolation or scaling
- You need fine-grained per-component tuning that the auto-tuned defaults don't cover

> **Note on backward compatibility**: `weed mini` defaults (volume size, port layout, bundled components) may evolve over releases. Pin a SeaweedFS version if you depend on specific defaults, or pass them explicitly as flags.

### `weed mini` vs `weed server -filer -s3`

Both run multiple components in one process, but they serve different goals:

| | `weed mini` | `weed server -filer -s3` |
|---|---|---|
| Components | master + volume + filer + S3 + WebDAV + **Admin UI** + **maintenance worker** | master + volume (+ optional filer / s3 / iam / webdav / sftp / mq) |
| Master mode | Single master (no peers) | Supports multi-master peers |
| Volume size limit | Auto-tuned (64–1024 MB) | Fixed default (~30 GB) |
| Volume max count | Auto (based on free disk) | 8 by default |
| Default volume port | 9340 | 8080 |
| Iceberg REST catalog | Enabled (8181) | Off |
| Pre-stop seconds | 1 (fast shutdown) | 10 |
| Best for | Single-node, small clusters, dev | Building block for multi-master clusters, custom tuning |

For a single-node S3 setup (e.g. presigned upload/download URLs), `weed mini` is the simpler choice — you also get the Admin UI and built-in maintenance for vacuum/EC/balance without extra processes.

---

## Multi-Component Setup (For Larger Clusters and Advanced Users)

For multi-master clusters, deployments where components live on separate hosts, or setups that need fine-grained tuning beyond `weed mini`'s auto-defaults, follow the manual setup instructions below.

Decompress the downloaded file. You will only find one executable file, either "weed" on most systems or "weed.exe" on windows.

Put the file "weed" to all related computers, in any folder you want. Use 

```bash
./weed -h # to check available options
```

### Set up Weed Master

```bash
./weed master -h # to check available options
```

If no replication is required, this will be enough. The "mdir" option is to configure a folder where the maximum of generated volume id are saved.

```bash
./weed master -mdir="."
./weed master -mdir="." -ip=xxx.xxx.xxx.xxx # usually set the ip instead the default "localhost"
```

### Set up Weed Volume Server

```bash
./weed volume -h # to check available options
```

Usually volume servers are spread on different computers. They can have different disk space, or even different operating system.

Usually you would need to specify the available disk space, the Weed Master location, and the storage folder.

```bash
./weed volume -max=100 -master="localhost:9333" -dir="./data"
```
If you are using a custom gRPC port for master, the address format for `-master` is `&lt;host&gt;:&lt;port&gt;.&lt;grpcPort&gt;`. By default the gRPC port is `port + 10000`.

### Cheat Sheet: Setup One Master Server and One Volume Server

You can set up one master and one volume server in one shot:

```bash
./weed server -dir="./data"
# same, just specifying the default values
# use "weed server -h" to find out more
./weed server -master.port=9333 -volume.port=8080 -dir="./data"
```

To also start a filer and S3 gateway in the same process:

```bash
./weed server -dir="./data" -filer -s3
```

If you want all of that plus the Admin UI, the maintenance worker (vacuum / erasure coding / balance), and auto-tuned volume sizing on a single node, use [`weed mini`](./Quick-Start-with-weed-mini.md) instead.

## Testing SeaweedFS

With the master and volume server up, now what? Let's pump in a lot of files into the system!

```bash
./weed upload -dir="/some/big/folder"
```

This command would recursively upload all files. Or you can specify what files you want to include.

```bash
./weed upload -dir="/some/big/folder" -include=*.txt
```

Then, you can simply check "du -m -s /some/big/folder" to see the actual disk usage by OS, and compare it with the file size under "/data". Usually if you are uploading a lot of textual files, the consumed disk size would be much smaller since textual files are gzipped automatically.

Now you can use your tools to hit SeaweedFS as hard as you can.



## Running with Docker ##

Use with docker is easy as run locally, you can pass all args like above. But you don't need to worry about "-ip". It'll be treated by the entrypoint script.

```
docker run -p 9333:9333 --name master chrislusf/seaweedfs master -ip=master
```
```
docker run -p 8080:8080 -p 18080:18080 --name volume --link master chrislusf/seaweedfs volume -max=5 -master="master:9333" -port=8080
```
#### With Compose ####
But with Compose it's easiest.
To startup just run:
```
docker compose -f docker/seaweedfs-compose.yml -p seaweedfs up
```

## Using SeaweedFS in docker

You can use image "chrislusf/seaweedfs" or build your own with [dockerfile][] in the root of repo.

[dockerfile]: https://github.com/seaweedfs/seaweedfs/blob/master/docker/Dockerfile


### Using pre-built Docker image

```bash
docker run --name weed chrislusf/seaweedfs server
```

And in another terminal

```bash
IP=$(docker inspect --format '{{ .NetworkSettings.IPAddress }}' weed)
curl "http://$IP:9333/cluster/status?pretty=y"	
{
  "IsLeader": true,
  "Leader": "localhost:9333"
}
# use $IP as host for api queries
```

### Building image from dockerfile

Make a local copy of seaweedfs from github

```bash
git clone https://github.com/seaweedfs/seaweedfs.git
```

Minimal Image (~19.6 MB)

```bash
docker build --no-cache -t 'chrislusf/seaweedfs' .
```

Go-Build Docker Image (~764 MB)

```bash
mv Dockerfile Dockerfile.minimal
mv Dockerfile.go_build Dockerfile
docker build --no-cache -t 'chrislusf/seaweedfs' .
```

### Building image from source code
Create an executable for docker and move it to the docker folder
```bash
cd weed
make build_docker
mv weed ../docker/
cd ..
```

Build the image
```bash
cd docker
docker build -f Dockerfile.local --no-cache -t localregistry/seaweedfs .
```

### In production

You can use docker volumes to persist data:
```bash
# start our weed server daemonized
docker run --name weed -d -p 9333:9333 -p 8080:8080 -p 18080:18080 \
  -v seaweedvolume:/data chrislusf/seaweedfs server -dir="/data"
```

Alternatively, you can mount a directory on the host machine into the container:
```bash
# start our weed server daemonized
docker run --name weed -d -p 9333:9333 -p 8080:8080 -p 18080:18080 \
  -v /opt/weedfs/data:/data chrislusf/seaweedfs server -dir="/data"
```
The Docker image now defaults to the non-root `seaweed` user. If you bind-mount a host directory, make sure it is writable by UID/GID `1000:1000`, or start the container with `--user root` on first run so the entrypoint can repair `/data` ownership before dropping privileges.

Note that according to [Docker's documentation](https://docs.docker.com/storage/volumes/), volumes are the preferred mechanism for persisting data.



Now our SeaweedFS server will be persistent and accessible by localhost:9333, :8080 and :18080 on host machine.
Dont forget to specify "-publicIp" for correct connectivity.

[Using SeaweedFS in kubernetes(k8s)](https://github.com/seaweedfs/seaweedfs/wiki/Deployment-to-Kubernetes-and-Minikube)
