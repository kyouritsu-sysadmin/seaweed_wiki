---
id: Components
title: "Components"
sidebar_label: "Components"
---

# SeaweedFS Components

SeaweedFS comprises 3 main components. The master service and the volume service together provide a distributed object store, with user-configurable replication and redundancy. The optional filer and S3 service are additional layers on top of the object store. Each of these services may run as one or separate processes, on one or more operating systems.

## Master service

It represents a cluster of 1 (or 3 or n/2+1) that own a consistent view of the entire SeaweedFS cluster and communicate it to all participating nodes, through a leader elected via [Raft](https://raft.github.io/) protocol. 

The number of servers in the master service must always be odd, to ensure that a majority consensus can be formed. You're best off keeping this number down, a small number of stable servers is better than a large pool of flakey boxes. 1 or 3 is typical.

The leader is arbitrarily chosen from all available master servers, through a periodic raft election. It assigns file ids, appoints which volumes to store objects in, and also owns deciding which nodes are part of the cluster.

All other volume servers in SeaweedFS send heartbeats to the leader, which uses them to decide where to route traffic, and how to handle replication.
 
If the leader is unavailable, the raft consensus protocol ensures that a new leader is appointed, with the agreement of the entire cluster, and the existing absent leader is demoted until it is able to function correctly again.

## Volume service

It packs many objects (files and chunks of files) efficiently into larger individual volumes, which can be arbitrarily large blocks on disk. Redundancy and replication of data is managed at the volume level, not on a per-object level.

Each volume server sends periodic heartbeats with status and volume information back to the leader, via a master.

## Filer service

It organizes SeaweedFS volumes and objects into user-visible paths (like URLs or file systems) over HTTP or UNIX FUSE mounts.

Filer provides a convenient and common abstraction that can be used to provide normal looking filesystems, or web APIs for down/uploads, to existing applications without modification.

## S3 service

This optional service provides AWS style S3 buckets, similar to the filer service. It can be started separately, or together with the filer.

## Volume Concept

In SeaweedFS, a volume is a single file consisting of many small files. When a master server starts, it sets the volume file maximum size to 30GB (see: `-volumeSizeLimitMB`). At volume server initialization, it will create 8 of these volumes (see: `-max`).

Each volume has its own TTL and replication.

## Collection Concept

One collection is basically a group of volumes. Initially, if no volume is present within the collection, the volumes will be auto created. 

The TTL and replication options are for each volume, not for the collection. One collection can have volumes of different TTL or replication options.

The collection can be deleted quickly, since it is just simply removing all the volumes in the collection. 

If you want to use S3 service, each bucket has a dedicated collection. So removing a bucket is also fast.

Since one collection needs to have several volumes, and each volume is 30GB by default, you may run out of disk space quickly. You can reduce the volume size to 1GB or 512MB, to work around this restriction.