---
id: Run-Blob-Storage-on-Public-Internet
title: "Run Blob Storage on Public Internet"
sidebar_label: "Run Blob Storage on Public Internet"
---

# How to setup SeaweedFS on servers that face the public internet

This guide is for setting up master and volume servers only, we will *not* setup filer or S3. All services will run in Docker, which also acts as a firewall to block direct access to the HTTP API of the master server (single master, no HA). gRPC communication between volume and master server is encrypted with mutual TLS, all gRPC ports are exposed to the public internet. Master server HTTP API port (9333) is exposed via reverse proxy [Caddy](https://caddyserver.com/), which handles SSL termination and checks for an `Authorization` header (this header is completely separate from SeaweedFS JWT mechanism). Other reverse proxy can also be used instead of Caddy.

## Step by step setup

We will use 2 servers. Server 1 will host master, 2x volumes (2 disks, one volume server each), caddy reverse proxy. Server 2 will host 2 volume servers.

1. Install docker and docker-compose
2. Start master server. Using my own Dockerfile here to run the large_disk version
  `Dockerfile`
  ```dockerfile
# todo: set version as ARG
# todo: use 2 step build process, copy over weed binary to fresh container (do not need curl and tar at runtime)
FROM alpine
RUN apk update && apk add wget tar
RUN wget https://github.com/seaweedfs/seaweedfs/releases/download/3.80/linux_amd64_large_disk.tar.gz
RUN tar -xf linux_amd64_large_disk.tar.gz
RUN chmod +x weed
RUN mv weed /usr/bin/
  ```

`docker-compose.yml`

```yml
version: '3.7'
services:
  master:
    build: .
    volumes:
      - /data/seaweedfs/master:/data/seaweedfs/master
    ports:
      - 19333:19333
    entrypoint: weed master -mdir='/data/seaweedfs/master' -ip=<public ip of server> -volumeSizeLimitMB=100000 -defaultReplication=010
```

3. `docker-compose up` and see if it looks ok
4. Run volume server on server 2 (to test connection between physical servers)
  - same dockerfile
  - `docker-compose.yml`
```yml
version: '3.7'
services:
  volume-sda:
    build: .
    volumes:
      - /data/seaweedfs/volume:/data/seaweedfs/volume
    ports:
      - 8080:8080
      - 18080:18080
    command: weed volume -master=<public IP of server 1>:9333 -dir=/data/seaweedfs/volume -ip=<public ip of this server (server2)>
```

5. `docker-compose up` on both servers and check that the master sees the volume
6. Follow [security guide](https://github.com/seaweedfs/seaweedfs/wiki/Security-Configuration) to add secrets and certs. Scaffold `security.toml` file and generate certs, in this example, all certs are in `certs/` folder. Update `docker-compose.yml` of master server:
```yml
version: '3.7'
services:
  master:
    build: .
    volumes:
      - /data/seaweedfs/master:/data/seaweedfs/master
      - ./security.toml:/etc/seaweedfs/security.toml
      - ./certs:/etc/seaweedfs/certs
    ports:
      - 19333:19333
    entrypoint: weed master -mdir='/data/seaweedfs/master' -ip=<public ip of server> -volumeSizeLimitMB=100000 -defaultReplication=010
```
7. `docker-compose up` the master and volume. Because the volume server doesn't have the security config, the heartbeat should fail.
8. Copy `security.toml` and `certs/` folder to server2 and add mounts in `docker-compose.yml` file of volume server.
9. `docker-compose up`, now heartbeat should work and master should see volume server again
10. Test that JWT auth works as you expect. For that, edit docker-compose.yml of master server to temporarily expose port 9333 to the host machine. All testing will be done from command line of server 1:
  - `curl -i http://localhost:9333/dir/assign` should include bearer token
  - uploading with bearer token should work (for hand testing, might want to update the 10 second JWT timeout to something longer)
  - uploading without bearer token fails (3 test cases: not provided, incorrect provided, or token expired)
  - downloading with bearer token works
  - downloading without bearer token fails
  - delete with bearer token works, doesn't work without token
11. Great, JWT auth works as expected. `docker-compose down`, remove port `9333` from master server `docker-compose.yml`, clean data directory `rm -rf /data/seaweedfs/master/*` and `rm -rf /data/seaweedfs/volume/*`
12. Add caddyserver to master server `docker-compose.yml`. Caddy will automatically and without config issue a SSL cert from Lets Encrypt, redirect traffic from HTTP to HTTPS (on HTTP the header value can be sniffed, please remember to use HTTPS), and we will add config to check for `Authorization` header. A domain is needed for SSL. On master servers `docker-compose.yml`, add a new service:
```yml
  caddy:
    image: caddy:2.3.0-alpine
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
    ports:
      - 80:80
      - 443:443
```

Add `Caddyfile`

```
seaweedfs.yourdomain.com

@bearertoken header Authorization "Bearer <your token>"
@notBearertoken not header Authorization "Bearer <your token>"

reverse_proxy @bearertoken master:9333

respond @notBearertoken 401
```

13. `docker-compose up`, wait for Caddy to get certs from LetsEncrypt, test it via curl:
   - `curl -i http://seaweedfs.yourdomain.com` redirects to `HTTPS`
   - `curl -i https://seaweedfs.yourdomain.com` responds with 401
   - `curl -H "Authorization: Bearer &lt;your token&gt;" https://seaweedfs.yourdomain.com/dir/assign` works
   - `curl -iH "Authorization: Bearer someOtherToken" https://seaweedfs.yourdomain.com/dir/assign` 401

14. Add more volume servers, take notice of port bindings. In my case, server 1 `docker-compose.yml` has master, volume-sda, volume-sdb, caddy, server 2 has volume-sda, volume-sdb.

`docker-compose.yml` server 2:

```yml
version: '3.7'
services:
  volume-sda:
    build: .
    volumes:
      # /dev/sda4 mounts to /data
      - /data/seaweedfs/volume:/data/seaweedfs/volume
      - ./security.toml:/etc/seaweedfs/security.toml
      - ./certs:/etc/seaweedfs/certs
    ports:
      - 8080:8080
      - 18080:18080
    command: weed volume -master=<master server ip>:9333 -dir=/data/seaweedfs/volume -ip=<publicIp>

  volume-sdb:
    build: .
    volumes:
      # /dev/sdb1 mounts to /data2
      - /data2/seaweedfs/volume:/data/seaweedfs/volume
      - ./security.toml:/etc/seaweedfs/security.toml
      - ./certs:/etc/seaweedfs/certs
    ports:
      - 8081:8081
      - 18081:18081
    command: weed volume -master=<master server ip>:9333 -dir=/data/seaweedfs/volume -ip=<publicIp>  -port=8081
```

## High availability

I haven't tested this, but this is how I would go about making it HA:
- Run master server on 3 or 5 physical servers
- Run caddy as a sidecar on every server that runs a master
- Install caddy from own Dockerfile, adding [redis plugin](https://github.com/gamalan/caddy-tlsredis) for distributed SSL cert storage and distributed locks for SSL cert issuing.
- Run redis in high-availability mode, for example by [following this docker swarm guide](https://medium.com/@emmano3h/redis-high-availability-with-docker-swarm-2142a4d80b49). Caddy redis plugin probably doesn't allow multiple IP addresses, so might have to add `haproxy` sidecar to every caddy sidecar as well to load balance to redis cluster.
- Update `command` of volume servers docker-compose file to add all master server IPs

Alternatively:
- Use another caddy plugin for distributed SSL certs, not redis
- Use a loadbalancer-as-a-service that does SSL termination from some cloud provider (i.e. Cloudflare - easier to setup but less secure as traffic between cloudflare and nodes is not encrypted)
- Disable HTTP API on master server (`-disableHttp` flag) and use clients that can speak gRPC protocol
