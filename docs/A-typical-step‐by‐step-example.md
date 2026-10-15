---
id: A-typical-step‐by‐step-example
title: "A typical step by step example"
sidebar_label: "A typical step by step example"
---

# A typical step‐by‐step example of SeaweedFS HA Setup Guide
3 VMs + 1 Postgres metadata store on docker hosted on separate VM

## Simplified Architecture Overview

```mermaid
graph TD
    subgraph "VIP: 192.168.10.30 (keepalived)"
        LB["Embedded Load Balancer"]
    end

    subgraph "VM1 - 192.168.10.31"
        M1["Master :9331"]
        V1["Volume :8080"]
        F1["Filer :8888"]
        S3_1["S3 :8333"]
    end

    subgraph "VM2 - 192.168.10.32"
        M2["Master :9332"]
        V2["Volume :8080"]
        F2["Filer :8888"]
        S3_2["S3 :8333"]
    end

    subgraph "VM3 - 192.168.10.33"
        M3["Master :9333"]
        V3["Volume :8080"]
        F3["Filer :8888"]
        S3_3["S3 :8333"]
    end

    subgraph "VM4 - 192.168.12.31"
        PG["PostgreSQL :4235"]
        PGB["PgBouncer :4235"]
    end

    LB --> M1 & M2 & M3
    LB --> F1 & F2 & F3
    LB --> S3_1 & S3_2 & S3_3
    F1 & F2 & F3 --> PGB
    PGB --> PG
    V1 & V2 & V3 -->|"Heartbeat"| M1 & M2 & M3
    S3_1 --> F1
    S3_2 --> F2
    S3_3 --> F3
```

## Complete architecture Overview

An updated Architecture Overview with more detail and accuracy:

```mermaid
graph TB
    subgraph "Clients"
        C["S3 / HTTP Clients"]
    end

    subgraph "Keepalived VIP: 192.168.10.30"
        VIP["Floating VIP"]
    end

    C --> VIP

    subgraph "VM1 — 192.168.10.31 — dc1/r1"
        M1["Master :9331 / gRPC :19331"]
        V1["Volume :8080 / gRPC :18080"]
        F1["Filer :8888 / gRPC :18888"]
        S31["S3 Gateway :8333"]
    end

    subgraph "VM2 — 192.168.10.32 — dc1/r2"
        M2["Master :9332 / gRPC :19332"]
        V2["Volume :8080 / gRPC :18080"]
        F2["Filer :8888 / gRPC :18888"]
        S32["S3 Gateway :8333"]
    end

    subgraph "VM3 — 192.168.10.33 — dc1/r3"
        M3["Master :9333 / gRPC :19333"]
        V3["Volume :8080 / gRPC :18080"]
        F3["Filer :8888 / gRPC :18888"]
        S33["S3 Gateway :8333"]
    end

    subgraph "VM4 — 192.168.12.31 — Metadata Store"
        PGB["PgBouncer :4235"]
        PG["PostgreSQL :4235"]
    end

    VIP -.->|"Routes to active node"| S31
    VIP -.->|"Routes to active node"| S32
    VIP -.->|"Routes to active node"| S33

    M1 <-->|"Raft Hashicorp Consensus"| M2
    M2 <-->|"Raft Hashicorp Consensus"| M3
    M3 <-->|"Raft Hashicorp Consensus"| M1

    V1 -->|"Heartbeat"| M1
    V1 -->|"Heartbeat"| M2
    V1 -->|"Heartbeat"| M3
    V2 -->|"Heartbeat"| M1
    V2 -->|"Heartbeat"| M2
    V2 -->|"Heartbeat"| M3
    V3 -->|"Heartbeat"| M1
    V3 -->|"Heartbeat"| M2
    V3 -->|"Heartbeat"| M3

    F1 -->|"Volume coordination"| M1
    F1 -->|"Volume coordination"| M2
    F1 -->|"Volume coordination"| M3
    F2 -->|"Volume coordination"| M1
    F2 -->|"Volume coordination"| M2
    F2 -->|"Volume coordination"| M3
    F3 -->|"Volume coordination"| M1
    F3 -->|"Volume coordination"| M2
    F3 -->|"Volume coordination"| M3

    S31 -->|"Local-first + failover"| F1
    S31 -.->|"Failover"| F2
    S31 -.->|"Failover"| F3
    S32 -->|"Local-first + failover"| F2
    S32 -.->|"Failover"| F1
    S32 -.->|"Failover"| F3
    S33 -->|"Local-first + failover"| F3
    S33 -.->|"Failover"| F1
    S33 -.->|"Failover"| F2

    F1 -->|"Metadata (encrypted)"| PGB
    F2 -->|"Metadata (encrypted)"| PGB
    F3 -->|"Metadata (encrypted)"| PGB
    PGB -->|"Connection pooling"| PG

    V1 <-.->|"Replication 010 (diff rack)"| V2
    V2 <-.->|"Replication 010 (diff rack)"| V3
    V3 <-.->|"Replication 010 (diff rack)"| V1
```

### Diagram Legend

| Symbol                  | Meaning                            |
| ----------------------- | ---------------------------------- |
| Solid arrow (`-->`)   | Primary / always-active connection |
| Dashed arrow (`-.->`) | Failover / secondary connection    |
| Double arrow (`&lt;--&gt;`) | Bidirectional communication        |

### Key HA Mechanisms

| Layer                  | HA Mechanism                     | Details                                                                                     |
| ---------------------- | -------------------------------- | ------------------------------------------------------------------------------------------- |
| **Client entry** | Keepalived VIP `192.168.10.30` | Floating IP with VRRP, priority-based failover across VM1/VM2/VM3                           |
| **Master**       | Hashicorp Raft (3-node quorum)   | Automatic leader election; tolerates 1 node failure                                         |
| **Volume**       | Replication `010`              | Each volume replicated to a different rack within the same data center (`dc1`)            |
| **Filer**        | Shared PostgreSQL metadata       | All 3 filers are stateless; any can serve any request                                       |
| **S3 Gateway**   | Built-in filer failover          | Comma-separated `-filer` addresses with circuit breaker pattern; local filer listed first |
| **Metadata**     | PgBouncer connection pooling     | Transaction pooling mode with `pgbouncer_compatible=true`                                 |

### Port Summary

> **NOTE:**  Assuming that: \
    - VM1--ip=192.168.10.31\
    - VM2--ip=192.168.10.32\
    - VM3--ip=192.168.10.33\
    - VM4--ip=192.168.12.31 (yes! on different subnet)

| Component   | VM1 (`.31`) | VM2 (`.32`) | VM3 (`.33`) | VM4 (`.12.31`) |
| ----------- | ------------- | ------------- | ------------- | ---------------- |
| Master HTTP | 9331          | 9332          | 9333          | —               |
| Master gRPC | 19331         | 19332         | 19333         | —               |
| Volume HTTP | 8080          | 8080          | 8080          | —               |
| Volume gRPC | 18080         | 18080         | 18080         | —               |
| Filer HTTP  | 8888          | 8888          | 8888          | —               |
| Filer gRPC  | 18888         | 18888         | 18888         | —               |
| S3 Gateway  | 8333          | 8333          | 8333          | —               |
| PostgreSQL  | —            | —            | —            | 4235             |
| PgBouncer   | —            | —            | —            | 4236             |

>**NOTE on VM4 Ports**\
For `PostgreSQL`  and `PostgreSQL` mentioned ports are those at the host site NOT CONTAINERS INTERNAL PORT.

### Startup Dependency Chain

```mermaid
graph LR
    KA["1. keepalived"] --> MA["2. Master (Raft)"]
    MA --> VO["3. Volume"]
    VO --> FI["4. Filer"]
    FI --> S3["5. S3 Gateway"]
```

---
---

## Notes (To understand why what is used)

- **No embedded load balancer exists in SeaweedFS.** The "load balancing" is achieved through two mechanisms:

  1. **Keepalived VIP** — provides a single entry point that floats to the highest-priority healthy node
  2. **S3 built-in filer failover** — the S3 gateway's `-filer` flag accepts multiple comma-separated addresses and implements a circuit breaker pattern with health tracking, automatically failing over to healthy filers.
- **Replication `010`** means: `0` copies on the same rack, `1` copy on a different rack in the same data center, `0` copies on a different data center. With racks `r1`, `r2`, `r3` all in `dc1`, each volume is stored on 2 different racks.
- **gRPC ports** default to HTTP port + 10000 when `-port.grpc` is not explicitly set (e.g., master on 9331 → gRPC on 19331).
- **VM4 containers mapped host ports** are changed to avoid conflict and for security reason
  - 5432 → to 4235 for Postgres container mapped host port.
    - so in docker-compose\
        `port
          "4235:5432"`
  - 5432 or 6432 (edoburu/pgbouncer image used the same internal port 5432 for transparency) → to 4236 for Pgbouncer container mapped host port.
    - so in docker-compose\
        `port
          "4236:5432"`
- **Filer discovery**: When the S3 gateway is configured with master addresses, it can dynamically discover filers via the `FilerClient` with a configurable refresh interval (default 5 minutes), providing additional resilience beyond the static filer list.
- **Volume data encryption** is enabled via `-encryptVolumeData` on both filer and S3 gateway, ensuring data is encrypted at rest on volume servers.

- **Why `ip.bind=0.0.0.0`**: By default, if `-ip.bind` is empty, SeaweedFS binds to the same address as `-ip`. When `-ip` is set to a specific address (e.g., `192.168.10.31`), the server only listens on that interface. Using `-ip.bind=0.0.0.0` makes the server listen on **all network interfaces**, which is required when:

  - The keepalived VIP floats between nodes (the VIP address may arrive on any interface)
  - You need the service reachable from multiple networks/subnets
  - Health checks or monitoring come from localhost or other interfaces
  - gRPC internal communication may use different interfaces.

---
---

## !!! Before starting, prepare your infrastructure or ensure that it is similar to the following
  
- **Common instructions**

  - **For VM1, VM2, VM3, VM4**
    - **check and set** proper hostname if needed
    - **check and set** needed line to /etc/hosts
    - **with UFW** open needed ports on host

  - **for VM1, VM2, VM3**
    - **on local disk(first disk)**
      - install ufw (if you prefer it)
      - install Go
      - Install seaweedfs
    - Additional disk (or partition) for storing data
      - size: 70G
      - type:ext4
      - mount disk
    - mount dedicated 70G disk for object storage on /mnt/objstore(for example)
- **individual instructions**
  - For VM4
    - Install docker
    - instal ufw
    - install ufw-docker (An extender for ufw.)\
    If like me you worry about security concern with ufw **not automatically** handling with docker containers privacy!! Search for **ufw-docker** is on github and **read carefully** the guide.
    - **with UFW-DOCKER** open needed ports(using container's port. it's will automatically take care of host port)

- **other instructions**
  - **on router**(if you have one in front of everything)
    - Set node's ip with dhcp lease per mac address
    - open needed ports
    - allow traffic between nodes
    - restrict access to the admin interface, which runs on port 23646
  - Reboot all node's host for proper/correct ip based on dhcp lease configured above

---
---

## Step 1: Keepalived VIP Setup

---

>**NOTE: Recommendation**\
Use **unicast** by default for bare metal VMs. It is more reliable across different network environments and avoids issues with multicast being silently dropped by switches, hypervisors, or firewalls. The only trade-off is slightly more configuration (listing each peer explicitly), which is negligible for a 3-node cluster.

### Requirements for this step

- `keepalived` installed on VM1, VM2, VM3: `apt install keepalived` or `yum install keepalived`
- `tcpdump` installed on VM1, VM2, VM3: `apt install tcpdump`
- A free VIP address: `192.168.10.30`
- If decided to use `Multicast` make sure VRRP multicast allowed between the 3 VMs
- If instead `Unicast` make sure unicast configured as detailed below in guidance.
- The network interface name (e.g., `eth0`) — adjust to match your environment
- For both cases:
  - `net.ipv4.ip_nonlocal_bind=1` in `/etc/sysctl.conf` (allows binding to VIP before it's assigned)
  
      ```bash
    echo "net.ipv4.ip_nonlocal_bind = 1" >> /etc/sysctl.conf
    sysctl -p
    ```

  - Remember to enable end start `keepalived` on all 3 VMs:

    ```bash
    systemctl enable keepalived
    systemctl start keepalived
    ```

## Guidance — System/network Multicast or Unicast (not specific to SeaweedFS)

---

### ***Checking VRRP Multicast — using multicast

VRRP uses multicast address `224.0.0.18` on IP protocol 112. To verify it works between your 3 VMs:

#### 1. Check if multicast is enabled on the interface

```bash
# On all 3 VMs
ip link show eth0 | grep -i multicast
```

You should see `MULTICAST` in the flags. If not:

```bash
sudo ip link set eth0 multicast on
```

#### 2. Check firewall rules allow VRRP

```bash
# iptables
sudo iptables -L -n | grep -i vrrp
sudo iptables -L -n | grep 112

# or nftables
sudo nft list ruleset | grep vrrp
```

If VRRP is blocked, allow it:

```bash
# iptables — allow VRRP (protocol 112) between the 3 VMs
sudo iptables -A INPUT -p 112 -s 192.168.10.31 -j ACCEPT
sudo iptables -A INPUT -p 112 -s 192.168.10.32 -j ACCEPT
sudo iptables -A INPUT -p 112 -s 192.168.10.33 -j ACCEPT

# Also allow multicast
sudo iptables -A INPUT -d 224.0.0.18/32 -j ACCEPT
```

For `firewalld`:

```bash
sudo firewall-cmd --add-protocol=vrrp --permanent
sudo firewall-cmd --reload
```

#### 3. Test multicast reachability

On VM1 (listener):
```bash
sudo tcpdump -i eth0 -n proto 112
```

On VM2/VM3 (with keepalived running):
```bash
sudo systemctl start keepalived
```

You should see VRRP advertisements in the tcpdump output on VM1. If you see nothing, multicast is blocked (likely by the hypervisor, switch, or firewall).

---

### ***If Multicast Is Blocked —> Use Unicast

Many virtualization platforms (VMware, some cloud providers, certain switch configurations) block multicast. In that case, configure keepalived with **unicast** instead.

#### VM1 — `/etc/keepalived/keepalived.conf` (unicast — MASTER priority)

```conf
vrrp_script chk_seaweedfs {
    script "/usr/bin/curl -sf http://127.0.0.1:9331/cluster/status || exit 1"
    interval 2
    weight -20
    fall 3
    rise 2
}

vrrp_instance VI_SEAWEEDFS {
    state MASTER
    interface eth0
    virtual_router_id 51
    priority 150
    advert_int 1

    authentication {
        auth_type PASS
        auth_pass SeaweedHA!
    }

    unicast_src_ip 192.168.10.31
    unicast_peer {
        192.168.10.32
        192.168.10.33
    }

    virtual_ipaddress {
        192.168.10.30/24
    }

    track_script {
        chk_seaweedfs
    }
}
```

#### VM2 — `/etc/keepalived/keepalived.conf` (unicast — BACKUP)

```conf
vrrp_script chk_seaweedfs {
    script "/usr/bin/curl -sf http://127.0.0.1:9332/cluster/status || exit 1"
    interval 2
    weight -20
    fall 3
    rise 2
}

vrrp_instance VI_SEAWEEDFS {
    state BACKUP
    interface eth0
    virtual_router_id 51
    priority 140
    advert_int 1

    authentication {
        auth_type PASS
        auth_pass SeaweedHA!
    }

    unicast_src_ip 192.168.10.32
    unicast_peer {
        192.168.10.31
        192.168.10.33
    }

    virtual_ipaddress {
        192.168.10.30/24
    }

    track_script {
        chk_seaweedfs
    }
}
```

#### VM3 — `/etc/keepalived/keepalived.conf` (unicast — BACKUP)

```conf
vrrp_script chk_seaweedfs {
    script "/usr/bin/curl -sf http://127.0.0.1:9333/cluster/status || exit 1"
    interval 2
    weight -20
    fall 3
    rise 2
}

vrrp_instance VI_SEAWEEDFS {
    state BACKUP
    interface eth0
    virtual_router_id 51
    priority 130
    advert_int 1

    authentication {
        auth_type PASS
        auth_pass SeaweedHA!
    }

    unicast_src_ip 192.168.10.33
    unicast_peer {
        192.168.10.31
        192.168.10.32
    }

    virtual_ipaddress {
        192.168.10.30/24
    }

    track_script {
        chk_seaweedfs
    }
}
```

#### Key differences from multicast config

| Directive | Purpose |
|-----------|---------|
| `unicast_src_ip` | This VM's own IP address |
| `unicast_peer { ... }` | List of the **other** VMs' IP addresses |

The `unicast_peer` block replaces multicast — keepalived sends VRRP advertisements directly to each peer via unicast UDP instead of multicast `224.0.0.18`.

#### Verify unicast is working

```bash
# Check keepalived logs
sudo journalctl -u keepalived -f

# Check VIP is assigned
ip addr show eth0 | grep 192.168.10.30

# Check VRRP traffic between nodes
sudo tcpdump -i eth0 -n host 192.168.10.32 and proto 112
```

---
---

## Step 2: PostgreSQL+PgBouncer (Docker containers) on VM4

### Directory to set on VM4

```bash
mkdir -p /opt/seaweedfs-meta/{pgdata,pgbouncer}
chown -R 1000:1000 /opt/seaweedfs-meta/{pgdata,pgbouncer}
chmod 755 /opt/seaweedfs-meta/{pgdata,pgbouncer}
```

### Set  `.env` file — `/opt/seaweedfs-meta/.env` with below content

```env
POSTGRES_DB=seaweedfs
POSTGRES_USER=seaweedfs
POSTGRES_PASSWORD=YourStrongPasswordHere
```

### Set `docker-compose.yml` — `/opt/seaweedfs-meta/docker-compose.yml` with below content

```yaml
version: "3.9"

services:
  servpgswdfsmeta:
    image: dhi.io/postgres:15-alpine3.22
    container_name: servpgswdfsmeta
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - /opt/seaweedfs-meta/pgdata:/var/lib/postgresql/data
    ports:
      - "4235:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  pgbouncer:
    image: edoburu/pgbouncer:latest
    container_name: pgbouncer-seaweedfs
    restart: unless-stopped
    environment:
      DATABASE_URL: "postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@servpgswdfsmeta:5432/${POSTGRES_DB}"
      POOL_MODE: transaction
      MAX_CLIENT_CONN: 200
      DEFAULT_POOL_SIZE: 50
    ports:
      - "4236:5432"
    depends_on:
      servpgswdfsmeta:
        condition: service_healthy
```

Start:

```bash
cd /opt/seaweedfs-meta
docker compose up -d
```

---
---

## Step 3: Prepare Directories on VM1, VM2, VM3

Run on **all 3 VMs**:

- creating directories

    ```bash
    mkdir -p /mnt/objstore/seaweedfs/master
    mkdir -p /mnt/objstore/seaweedfs/volume
    mkdir -p /etc/seaweedfs
    ```

- Set permissions on created directories

    ```bash
    chown -R 1000:1000 /mnt/objstore/seaweedfs
    chmod 755 /mnt/objstore/seaweedfs
    chown -R 1000:1000 /etc/seaweedfs
    chmod 755 /etc/seaweedfs
    ```

---
---

## Step 4: `filer.toml` Configuration

Place this file at `/etc/seaweedfs/filer.toml` on **all 3 VMs** (VM1, VM2, VM3). The `hostname` must be the network-accessible address of VM4.

```toml
# /etc/seaweedfs/filer.toml

[filer.options]
recursive_delete = false

# Disable default leveldb2
[leveldb2]
enabled = false

[postgres2]
enabled = true
createTable = """
  CREATE TABLE IF NOT EXISTS "%s" (
    dirhash   BIGINT,
    name      VARCHAR(65535),
    directory VARCHAR(65535),
    meta      bytea,
    PRIMARY KEY (dirhash, name)
  );
"""
hostname = "192.168.12.31"
port = 4236
username = "seaweedfs"
password = "YourStrongPasswordHere"
database = "seaweedfs"
schema = ""
sslmode = "disable"
connection_max_idle = 10
connection_max_open = 50
connection_max_lifetime_seconds = 300
pgbouncer_compatible = true
enableUpsert = true
upsertQuery = """
  INSERT INTO "%[1]s" (dirhash, name, directory, meta)
    VALUES($1, $2, $3, $4)
    ON CONFLICT (dirhash, name) DO UPDATE SET
      directory=EXCLUDED.directory,
      meta=EXCLUDED.meta
"""
```

> **NOTE:** `pgbouncer_compatible = true` adds `prefer_simple_protocol=true` to the connection string, which avoids prepared statement issues with PgBouncer's transaction pooling mode. The `hostname` points to VM4's PgBouncer port (`4236`).

---
---

## Step 5: Master Server Configuration

### VM1 — Master

```bash
weed master \
  -ip=192.168.10.31 \
  -ip.bind=0.0.0.0 \
  -port=9331 \
  -mdir=/mnt/objstore/seaweedfs/master \
  -peers=192.168.10.32:9332,192.168.10.33:9333 \
  -raftHashicorp \
  -defaultReplication=010 \
  -volumeSizeLimitMB=1000
```

### VM2 — Master

```bash
weed master \
  -ip=192.168.10.32 \
  -ip.bind=0.0.0.0 \
  -port=9332 \
  -mdir=/mnt/objstore/seaweedfs/master \
  -peers=192.168.10.31:9331,192.168.10.33:9333 \
  -raftHashicorp \
  -defaultReplication=010 \
  -volumeSizeLimitMB=1000
```

### VM3 — Master

```bash
weed master \
  -ip=192.168.10.33 \
  -ip.bind=0.0.0.0 \
  -port=9333 \
  -mdir=/mnt/objstore/seaweedfs/master \
  -peers=192.168.10.31:9331,192.168.10.32:9332 \
  -raftHashicorp \
  -defaultReplication=010 \
  -volumeSizeLimitMB=1000
```

> **NOTE**: The `-peers` flag for Hashicorp Raft **should only list other masters** masters. Note that peers only contain `ip` of others masters

---
---

## Step 6: Volume Server Configuration

### VM1 — Volume

```bash
weed volume \
  -ip=192.168.10.31 \
  -ip.bind=0.0.0.0 \
  -port=8080 \
  -dir=/mnt/objstore/seaweedfs/volume \
  -max=0 \
  -master=192.168.10.31:9331,192.168.10.32:9332,192.168.10.33:9333 \
  -dataCenter=dc1 \
  -rack=r1 \
  -minFreeSpace=15
```

### VM2 — Volume

```bash
weed volume \
  -ip=192.168.10.32 \
  -ip.bind=0.0.0.0 \
  -port=8080 \
  -dir=/mnt/objstore/seaweedfs/volume \
  -max=0 \
  -master=192.168.10.31:9331,192.168.10.32:9332,192.168.10.33:9333 \
  -dataCenter=dc1 \
  -rack=r2 \
  -minFreeSpace=15
```

### VM3 — Volume

```bash
weed volume \
  -ip=192.168.10.33 \
  -ip.bind=0.0.0.0 \
  -port=8080 \
  -dir=/mnt/objstore/seaweedfs/volume \
  -max=0 \
  -master=192.168.10.31:9331,192.168.10.32:9332,192.168.10.33:9333 \
  -dataCenter=dc1 \
  -rack=r3 \
  -minFreeSpace=15
```

> **NOTE**
>
> - **`-max=0`:** When set to zero, the limit is auto-configured as free disk space divided by volume size (`volumeSizeLimitMB`)
> - **`-minFreeSpace=15`:** on the volume server (reserve ~15GB for compaction headroom)

---
---

## Step 7: Filer Server Configuration

### VM1 — Filer

```bash
weed filer \
  -ip=192.168.10.31 \
  -ip.bind=0.0.0.0 \
  -port=8888 \
  -master=192.168.10.31:9331,192.168.10.32:9332,192.168.10.33:9333 \
  -defaultReplicaPlacement=010 \
  -dataCenter=dc1 \
  -rack=r1 \
  -encryptVolumeData
```

### VM2 — Filer

```bash
weed filer \
  -ip=192.168.10.32 \
  -ip.bind=0.0.0.0 \
  -port=8888 \
  -master=192.168.10.31:9331,192.168.10.32:9332,192.168.10.33:9333 \
  -defaultReplicaPlacement=010 \
  -dataCenter=dc1 \
  -rack=r2 \
  -encryptVolumeData
```

### VM3 — Filer

```bash
weed filer \
  -ip=192.168.10.33 \
  -ip.bind=0.0.0.0 \
  -port=8888 \
  -master=192.168.10.31:9331,192.168.10.32:9332,192.168.10.33:9333 \
  -defaultReplicaPlacement=010 \
  -dataCenter=dc1 \
  -rack=r3 \
  -encryptVolumeData
```

> **NOTE on expected `-filerGroup`:** The `-filerGroup` flag is used when you want multiple groups of filers sharing the same masters but with **separate metadata namespaces** (e.g., multi-tenant). In this setup, all 3 filers share the same PostgreSQL metadata store and serve the same namespace, so `-filerGroup` is **not needed**. If you later add a separate set of filers for a different application, you would use `-filerGroup=groupA` and `-filerGroup=groupB` to isolate them.

---
---

## Step 8: S3 Configuration Files

### `s3.json` (S3.config) — `/etc/seaweedfs/s3.json`

This is the standard S3 identity/credential config with encryption enabled (no Object Lock). Place on all 3 VMs.

```json
{
  "identities": [
    {
      "name": "admin",
      "credentials": [
        {
          "accessKey": "REPLACE_WITH_ADMIN_ACCESS_KEY",
          "secretKey": "REPLACE_WITH_ADMIN_SECRET_KEY"
        }
      ],
      "actions": [
        "Admin",
        "Read",
        "List",
        "Tagging",
        "Write"
      ]
    },
    {
      "name": "readonly_user",
      "credentials": [
        {
          "accessKey": "REPLACE_WITH_RO_ACCESS_KEY",
          "secretKey": "REPLACE_WITH_RO_SECRET_KEY"
        }
      ],
      "actions": [
        "Read",
        "List"
      ]
    },
    {
      "name": "readwrite_user",
      "credentials": [
        {
          "accessKey": "REPLACE_WITH_RW_ACCESS_KEY",
          "secretKey": "REPLACE_WITH_RW_SECRET_KEY"
        }
      ],
      "actions": [
        "Read",
        "List",
        "Tagging",
        "Write"
      ]
    }
  ],
  "buckets": [
    {
      "name": "my-encrypted-bucket",
      "encryption": {
        "sseS3": {
          "enabled": true
        }
      }
    }
  ]
}
```

### `s3.iam.json` (S3.iam.config) — `/etc/seaweedfs/s3.iam.json`

This is the advanced IAM config with STS support, policies, and encryption. No Object Lock.

```json
{
  "identities": [
    {
      "name": "admin",
      "credentials": [
        {
          "accessKey": "REPLACE_WITH_ADMIN_ACCESS_KEY",
          "secretKey": "REPLACE_WITH_ADMIN_SECRET_KEY"
        }
      ],
      "actions": [
        "Admin",
        "Read",
        "List",
        "Tagging",
        "Write"
      ]
    },
    {
      "name": "readonly_user",
      "credentials": [
        {
          "accessKey": "REPLACE_WITH_RO_ACCESS_KEY",
          "secretKey": "REPLACE_WITH_RO_SECRET_KEY"
        }
      ],
      "actions": [
        "Read",
        "List"
      ]
    },
    {
      "name": "readwrite_user",
      "credentials": [
        {
          "accessKey": "REPLACE_WITH_RW_ACCESS_KEY",
          "secretKey": "REPLACE_WITH_RW_SECRET_KEY"
        }
      ],
      "actions": [
        "Read",
        "List",
        "Tagging",
        "Write"
      ]
    }
  ],
  "sts": {
    "tokenDuration": "1h",
    "maxSessionLength": "12h",
    "issuer": "seaweedfs-sts",
    "signingKey": "REPLACE_WITH_BASE64_ENCODED_SIGNING_KEY"
  },
  "policy": {
    "storeType": "memory",
    "defaultEffect": "Deny"
  },
  "policies": [
    {
      "name": "ReadWriteAccess",
      "document": {
        "Version": "2012-10-17",
        "Statement": [
          {
            "Effect": "Allow",
            "Action": [
              "s3:GetObject",
              "s3:PutObject",
              "s3:DeleteObject",
              "s3:ListBucket"
            ],
            "Resource": [
              "arn:aws:s3:::*",
              "arn:aws:s3:::*/*"
            ]
          }
        ]
      }
    },
    {
      "name": "ReadOnlyAccess",
      "document": {
        "Version": "2012-10-17",
        "Statement": [
          {
            "Effect": "Allow",
            "Action": [
              "s3:GetObject",
              "s3:ListBucket"
            ],
            "Resource": [
              "arn:aws:s3:::*",
              "arn:aws:s3:::*/*"
            ]
          }
        ]
      }
    }
  ]
}
```

> **NOTE:** Generate the `signingKey` with: `echo -n "your-secret-signing-key" | base64`

---
---

## Step 9: S3 Gateway Configuration

The S3 gateway is run as a **standalone process** pointing to the local filer. It supports multiple filer addresses for HA failover.

### VM1 — S3

```bash
weed s3 \
  -ip.bind=0.0.0.0 \
  -port=8333 \
  -filer=192.168.10.31:8888,192.168.10.32:8888,192.168.10.33:8888 \
  -config=/etc/seaweedfs/s3.json \
  -iam.config=/etc/seaweedfs/s3.iam.json \
  -encryptVolumeData
```

### VM2 — S3

```bash
weed s3 \
  -ip.bind=0.0.0.0 \
  -port=8333 \
  -filer=192.168.10.32:8888,192.168.10.31:8888,192.168.10.33:8888 \
  -config=/etc/seaweedfs/s3.json \
  -iam.config=/etc/seaweedfs/s3.iam.json \
  -encryptVolumeData
```

### VM3 — S3

```bash
weed s3 \
  -ip.bind=0.0.0.0 \
  -port=8333 \
  -filer=192.168.10.33:8888,192.168.10.31:8888,192.168.10.32:8888 \
  -config=/etc/seaweedfs/s3.json \
  -iam.config=/etc/seaweedfs/s3.iam.json \
  -encryptVolumeData
```

> **NOTE:**
>
> - The `-filer` flag accepts comma-separated addresses. The S3 server will automatically failover between filers if one becomes unavailable. Listing the local filer first is a best practice for latency
> - Make sure for each VM to execute :
>```weed shell``` in terminal to confirm being able to enter weed cli mode (It may be very useful in case you won't be comfortable with management through http-API).\
If you receive error like `masterclient.go:486 .adminShell masterClient reconnection` do the following:
>   - in terminal run `weed scaffold -config=shell`
>   - for more certainty create `/etc/seaweedfs/shell.toml` and paste in the output generated by the above command

---
---

## Step 10: Bucket Creation

### With AWS CLI

```bash
# Configure AWS CLI
export AWS_ACCESS_KEY_ID=REPLACE_WITH_ADMIN_ACCESS_KEY
export AWS_SECRET_ACCESS_KEY=REPLACE_WITH_ADMIN_SECRET_KEY
export AWS_DEFAULT_REGION=us-east-1

# Create an encrypted bucket (SSE-S3 is configured in s3.json)
aws --endpoint-url http://192.168.10.30:8333 s3 mb s3://my-encrypted-bucket

# Verify
aws --endpoint-url http://192.168.10.30:8333 s3 ls

# Upload a file (encrypted at rest via filer -encryptVolumeData)
aws --endpoint-url http://192.168.10.30:8333 s3 cp /tmp/testfile.txt s3://my-encrypted-bucket/testfile.txt

# Download
aws --endpoint-url http://192.168.10.30:8333 s3 cp s3://my-encrypted-bucket/testfile.txt /tmp/downloaded.txt
```

### Without AWS CLI (using `curl`)

```bash
# Create bucket
curl -X PUT http://192.168.10.30:8333/my-encrypted-bucket

# Upload a file
curl -X PUT -T /tmp/testfile.txt \
  -H "Content-Type: application/octet-stream" \
  http://192.168.10.30:8333/my-encrypted-bucket/testfile.txt

# Download a file
curl -o /tmp/downloaded.txt \
  http://192.168.10.30:8333/my-encrypted-bucket/testfile.txt

# List bucket contents
curl http://192.168.10.30:8333/my-encrypted-bucket?list-type=2
```

> **NOTE on encryption:** The `-encryptVolumeData` flag on the filer and S3 gateway enables server-side encryption of data on volume servers. The `sseS3` bucket config in `s3.json` enables S3-compatible SSE-S3 encryption headers. Object Lock is **not** configured in this setup as requested.

---
---

## Step 11: Systemd Services

### Desired starting Order

1. **keepalived** — VIP management
2. **seaweedfs-master** — Raft consensus
3. **seaweedfs-volume** — registers with masters
4. **seaweedfs-filer** — connects to masters + PostgreSQL
5. **seaweedfs-s3** — connects to filers

---

### VM1 (192.168.10.31)

#### `/etc/systemd/system/seaweedfs-master.service`

```ini
[Unit]
Description=SeaweedFS Master Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/weed master \
  -ip=192.168.10.31 \
  -ip.bind=0.0.0.0 \
  -port=9331 \
  -mdir=/mnt/objstore/seaweedfs/master \
  -peers=192.168.10.32:9332,192.168.10.33:9333 \
  -raftHashicorp \
  -defaultReplication=010 \
  -volumeSizeLimitMB=1000
Restart=on-failure
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

#### `/etc/systemd/system/seaweedfs-volume.service`

```ini
[Unit]
Description=SeaweedFS Volume Server
After=seaweedfs-master.service
Wants=seaweedfs-master.service

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/weed volume \
  -ip=192.168.10.31 \
  -ip.bind=0.0.0.0 \
  -port=8080 \
  -dir=/mnt/objstore/seaweedfs/volume \
  -max=0 \
  -master=192.168.10.31:9331,192.168.10.32:9332,192.168.10.33:9333 \
  -dataCenter=dc1 \
  -rack=r1 \
  -minFreeSpace=15
Restart=on-failure
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

#### `/etc/systemd/system/seaweedfs-filer.service`

```ini
[Unit]
Description=SeaweedFS Filer Server
After=seaweedfs-volume.service
Wants=seaweedfs-volume.service

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/weed filer \
  -ip=192.168.10.31 \
  -ip.bind=0.0.0.0 \
  -port=8888 \
  -master=192.168.10.31:9331,192.168.10.32:9332,192.168.10.33:9333 \
  -defaultReplicaPlacement=010 \
  -dataCenter=dc1 \
  -rack=r1 \
  -encryptVolumeData
Restart=on-failure
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

#### `/etc/systemd/system/seaweedfs-s3.service`

```ini
[Unit]
Description=SeaweedFS S3 Gateway
After=seaweedfs-filer.service
Wants=seaweedfs-filer.service

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/weed s3 \
  -ip.bind=0.0.0.0 \
  -port=8333 \
  -filer=192.168.10.31:8888,192.168.10.32:8888,192.168.10.33:8888 \
  -config=/etc/seaweedfs/s3.json \
  -iam.config=/etc/seaweedfs/s3.iam.json \
  -encryptVolumeData
Restart=on-failure
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

---

### VM2 (192.168.10.32)

#### `/etc/systemd/system/seaweedfs-master.service`

```ini
[Unit]
Description=SeaweedFS Master Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/weed master \
  -ip=192.168.10.32 \
  -ip.bind=0.0.0.0 \
  -port=9332 \
  -mdir=/mnt/objstore/seaweedfs/master \
  -peers=192.168.10.31:9331,192.168.10.33:9333 \
  -raftHashicorp \
  -defaultReplication=010 \
  -volumeSizeLimitMB=1000
Restart=on-failure
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

#### `/etc/systemd/system/seaweedfs-volume.service`

```ini
[Unit]
Description=SeaweedFS Volume Server
After=seaweedfs-master.service
Wants=seaweedfs-master.service

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/weed volume \
  -ip=192.168.10.32 \
  -ip.bind=0.0.0.0 \
  -port=8080 \
  -dir=/mnt/objstore/seaweedfs/volume \
  -max=0 \
  -master=192.168.10.31:9331,192.168.10.32:9332,192.168.10.33:9333 \
  -dataCenter=dc1 \
  -rack=r2 \
  -minFreeSpace=15
Restart=on-failure
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

#### `/etc/systemd/system/seaweedfs-filer.service`

```ini
[Unit]
Description=SeaweedFS Filer Server
After=seaweedfs-volume.service
Wants=seaweedfs-volume.service

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/weed filer \
  -ip=192.168.10.32 \
  -ip.bind=0.0.0.0 \
  -port=8888 \
  -master=192.168.10.31:9331,192.168.10.32:9332,192.168.10.33:9333 \
  -defaultReplicaPlacement=010 \
  -dataCenter=dc1 \
  -rack=r2 \
  -encryptVolumeData
Restart=on-failure
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

#### `/etc/systemd/system/seaweedfs-s3.service`

```ini
[Unit]
Description=SeaweedFS S3 Gateway
After=seaweedfs-filer.service
Wants=seaweedfs-filer.service

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/weed s3 \
  -ip.bind=0.0.0.0 \
  -port=8333 \
  -filer=192.168.10.32:8888,192.168.10.31:8888,192.168.10.33:8888 \
  -config=/etc/seaweedfs/s3.json \
  -iam.config=/etc/seaweedfs/s3.iam.json \
  -encryptVolumeData
Restart=on-failure
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

---

### VM3 (192.168.10.33)

#### `/etc/systemd/system/seaweedfs-master.service`

```ini
[Unit]
Description=SeaweedFS Master Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/weed master \
  -ip=192.168.10.33 \
  -ip.bind=0.0.0.0 \
  -port=9333 \
  -mdir=/mnt/objstore/seaweedfs/master \
  -peers=192.168.10.31:9331,192.168.10.32:9332 \
  -raftHashicorp \
  -defaultReplication=010 \
  -volumeSizeLimitMB=1000
Restart=on-failure
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

#### `/etc/systemd/system/seaweedfs-volume.service`

```ini
[Unit]
Description=SeaweedFS Volume Server
After=seaweedfs-master.service
Wants=seaweedfs-master.service

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/weed volume \
  -ip=192.168.10.33 \
  -ip.bind=0.0.0.0 \
  -port=8080 \
  -dir=/mnt/objstore/seaweedfs/volume \
  -max=0 \
  -master=192.168.10.31:9331,192.168.10.32:9332,192.168.10.33:9333 \
  -dataCenter=dc1 \
  -rack=r3 \
  -minFreeSpace=15
Restart=on-failure
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

#### `/etc/systemd/system/seaweedfs-filer.service`

```ini
[Unit]
Description=SeaweedFS Filer Server
After=seaweedfs-volume.service
Wants=seaweedfs-volume.service

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/weed filer \
  -ip=192.168.10.33 \
  -ip.bind=0.0.0.0 \
  -port=8888 \
  -master=192.168.10.31:9331,192.168.10.32:9332,192.168.10.33:9333 \
  -defaultReplicaPlacement=010 \
  -dataCenter=dc1 \
  -rack=r3 \
  -encryptVolumeData
Restart=on-failure
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

#### `/etc/systemd/system/seaweedfs-s3.service`

```ini
[Unit]
Description=SeaweedFS S3 Gateway
After=seaweedfs-filer.service
Wants=seaweedfs-filer.service

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/weed s3 \
  -ip.bind=0.0.0.0 \
  -port=8333 \
  -filer=192.168.10.33:8888,192.168.10.31:8888,192.168.10.32:8888 \
  -config=/etc/seaweedfs/s3.json \
  -iam.config=/etc/seaweedfs/s3.iam.json \
  -encryptVolumeData
Restart=on-failure
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```
> **NOTE:**
The systemd `After=` and `Wants=` directives in the service files ensure that on a full system reboot, services start in the correct dependency order automatically. The manual commands above are for the initial deployment or when you need explicit control over the startup sequence.

---

### Starting in desired order through terminal commands

Run these commands on **each VM** after placing the service files.

#### 1. Reload systemd daemon (all VMs)

```bash
sudo systemctl daemon-reload
```

#### 2. Enable all services at boot (all VMs)

```bash
sudo systemctl enable keepalived
sudo systemctl enable seaweedfs-master
sudo systemctl enable seaweedfs-volume
sudo systemctl enable seaweedfs-filer
sudo systemctl enable seaweedfs-s3
```

### Starting services

> **NOTE:** It is recommended to start all 3 masters first (across all VMs) before starting volume/filer/s3 on any VM. This ensures the Raft cluster has quorum. An alternative approach below
>

#### 3. Start services in order — VM1 (Repeat for VM2 and 3)

```bash
# Step 1: Keepalived (if not already running)
sudo systemctl start keepalived

# Step 2: Master
sudo systemctl start seaweedfs-master && sleep 10
# Wait for Raft cluster to form (check logs)
sleep 10
sudo journalctl -u seaweedfs-master --no-pager -n 20

# Step 3: Volume
sudo systemctl start seaweedfs-volume && sleep 5

# Step 4: Filer
sudo systemctl start seaweedfs-filer && sleep 5

# Step 5: S3 Gateway
sudo systemctl start seaweedfs-s3
```

#### Alternative: Start all masters first, then volumes, then filers, then S3

```bash
# === On ALL 3 VMs simultaneously ===
sudo systemctl start keepalived
sudo systemctl start seaweedfs-master

# === Wait for Raft quorum (check on any VM) ===
curl -s http://192.168.10.31:9331/cluster/status | python3 -m json.tool
# Verify "Leader" is set and "Peers" shows all 3 nodes

# === On ALL 3 VMs simultaneously ===
sudo systemctl start seaweedfs-volume

# === On ALL 3 VMs simultaneously ===
sudo systemctl start seaweedfs-filer

# === On ALL 3 VMs simultaneously ===
sudo systemctl start seaweedfs-s3
```

#### 6. Verify all services are running (on each VM)

```bash
sudo systemctl status keepalived
sudo systemctl status seaweedfs-master
sudo systemctl status seaweedfs-volume
sudo systemctl status seaweedfs-filer
sudo systemctl status seaweedfs-s3
```

Or as a one-liner:

```bash
for svc in keepalived seaweedfs-master seaweedfs-volume seaweedfs-filer seaweedfs-s3; do
  echo "=== $svc ===" && sudo systemctl is-active $svc
done
```

#### 7. Verify cluster health

```bash
# Check master cluster status
curl -s http://192.168.10.30:9331/cluster/status

# Check volume servers
curl -s http://192.168.10.30:9331/dir/status

# Check filer connectivity
curl -s http://192.168.10.30:8888/

# Check S3 gateway
aws --endpoint-url http://192.168.10.30:8333 s3 ls
```

#### 8. Stop services (reverse order)

```bash
sudo systemctl stop seaweedfs-s3
sudo systemctl stop seaweedfs-filer
sudo systemctl stop seaweedfs-volume
sudo systemctl stop seaweedfs-master
sudo systemctl stop keepalived
```

Or as a one-liner:

```bash
for svc in seaweedfs-s3 seaweedfs-filer seaweedfs-volume seaweedfs-master keepalived; do
  sudo systemctl stop $svc
done
```