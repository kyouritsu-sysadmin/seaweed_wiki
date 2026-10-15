---
id: Failover-Master-Server
title: "Failover Master Server"
sidebar_label: "Failover Master Server"
---

## Introduction

Some user will ask for no single point of failure. Although google runs its file system with a single master for years, no SPOF seems becoming a criteria for architects to pick solutions.

Luckily, it's not too difficult to enable Weed File System with failover master servers.

## Cheat Sheet: Startup multiple servers

This section is a quick way to start 3 master servers and 3 volume servers. All done!

```bash
weed server -master.ip=localhost -master.port=9333 -dir=./1 -volume.port=8080 \ 
  -master.peers=localhost:9333,localhost:9334,localhost:9335
weed server -master.ip=localhost -master.port=9334 -dir=./2 -volume.port=8081 \ 
  -master.peers=localhost:9333,localhost:9334,localhost:9335
weed server -master.ip=localhost -master.port=9335 -dir=./3 -volume.port=8082 \ 
  -master.peers=localhost:9333,localhost:9334,localhost:9335
```

## How it works

The master servers are coordinated by Raft protocol, to elect a leader. The leader takes over all the work to manage volumes, assign file ids. All other master servers just simply forward requests to the leader.

If the leader dies, another leader will be elected. And all the volume servers will send their heartbeat together with their volumes information to the new leader. The new leader will take the full responsibility.

During the transition, there could be moments where the new leader has partial information about all volume servers. This just means those yet-to-heartbeat volume servers will not be writable temporarily.


## Master Identifier

When specifying the peers, the peers are identified by the hostname or IP, and port.
The hostname or IP should be consistent with the value from "-ip" option when starting the master.

## Startup multiple master servers

Now let's start the master and volume servers separately, the usual way.

Usually you would start several (3 or 5) master servers, then start the volume servers:

```bash
weed master -ip=localhost -port=9333 -mdir=./1 -peers=localhost:9333,localhost:9334,localhost:9335
weed master -ip=localhost -port=9334 -mdir=./2 -peers=localhost:9333,localhost:9334,localhost:9335
weed master -ip=localhost -port=9335 -mdir=./3 -peers=localhost:9333,localhost:9334,localhost:9335
# now start the volume servers, specifying any one of the master server
weed volume -dir=./1 -port=8080 -master=localhost:9333,localhost:9334,localhost:9335
weed volume -dir=./2 -port=8081 -master=localhost:9333,localhost:9334,localhost:9335
weed volume -dir=./3 -port=8082 -master=localhost:9333,localhost:9334,localhost:9335

# The full list of masters is recommended, but not required.
# You can only specify any master servers.
weed volume -dir=./3 -port=8082 -master=localhost:9333
weed volume -dir=./3 -port=8082 -master=localhost:9333,localhost:9334
```

These 6 commands will actually functioning the same as the previous 3 commands from the cheatsheet.

It is a best practice for volume servers to include as many master servers as possible. So when one of the masters failed, the volume server can switch to another one.

## FAQ
* Q: Is it possible to add an additional master server to an already running SeaweedFS cluster?

    A: Treat the masters as zookeeper nodes, and do not need to change often. To add a master server, you need to stop all existing masters, and start the new set of masters with the new master list. For volume servers, it is OK to just keep using with existing masters when adding new volume servers.
