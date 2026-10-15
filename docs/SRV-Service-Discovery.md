---
id: SRV-Service-Discovery
title: "SRV Service Discovery"
sidebar_label: "SRV Service Discovery"
---

## Filer server

The Filer server also accepts SRV records (prepended with `dnssrv+`) to discover the master server:

```bash
 weed filer -master=dnssrv+_http._tcp.seaweedfs-master.consul
```
where `_http._tcp.seaweedfs-master.consul` is a DNS SRV record that returns the HTTP port of the master (or, alternatively, the gRPC port minus 10000).

The SRV record may return several master instances in order to join a HA setup. A comma-separated list of SRV records pointing to several master instances **is not valid**.