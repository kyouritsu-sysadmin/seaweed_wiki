---
id: Data-Backup
title: "Data Backup"
sidebar_label: "Data Backup"
---

## A Simple Backup Strategy

The most important thing for storage is to keep data safe and not lose it. It gives you a comfort of thought that your data is safely backed up.

However, we do not always want to copy the all the data files over. We want to do it incrementally.

`weed backup` command is your friend.

Run `weed backup` command on any machine that has enough disk space. Assuming we want to backup volume 5:

```bash
weed backup -server=master:port -dir=. -volumeId=5
```

If local volume 5 does not exist, it will be created. All remote needle entries are fetched and compared to local needle entries. The delta is calculated, and local missing files are fetched from the volume server.

If you specify `-volumeId=87`, but volume 87 does not exist, it's ok. No files will be created locally. This gives the opportunity for you to create a backup script simply looping from 1 to 100. All existing volumes will be backed up. The non-existing volumes can also be backed up when they are created remotely.

The backup scripts are just one command, not a continuous running service though. High Availability servers will be added later.

## How to create a mirror of a cluster

### To Start

- Pause operations on cluster you want to back up. This is to avoid a mismatch in the two data sets (the volumes and the Filer metadata) you will be moving separately and combining in the backup cluster. 
- Install SeaweedFS on a new machine/cluster of machines. Use the same version of SeaweedFS if you can to avoid any issues that could otherwise come up. 
- *Do not start your volume servers yet!!* This is to avoid SeaweedFS creating it's own volumes (we will be using the volumes backed up from the current operational cluster).

### Prepare the New Cluster and Backup Your Data

- Create the data directory where the volumes will be stored on the volume servers. eg. `/etc/seaweedfs/data`
- If you have multiple volume servers in the cluster you are backing up ***to***, *try to mimic the structure of the cluster you are pulling the volumes from* - eg. if volume 1 is in volume server 1 on the host cluster, back volume 1 up to volume server 1 in the backup cluster.
- run `weed backup` on the backup cluster on the volume servers. The `-dir` flag should point to the data directory you created in the previous step. This is so that the volume server will see the volume as it's own when it starts. 

### Backup the Metadata

Run `fs.meta.save` on the cluster you are pulling from and save the output. This can look like:

```sh
# You will need permission to create a file in the destination directory
# I recommend changing the file name because the default naming convention is not very readable BUT it does show the date the file was created which can be good information to store and know.
fs.meta.save -o=[yourlocaldir]/[yourfilename].meta
```

then download the file on the Filer machine you are using in the backup cluster. This can look like:

```sh
# This tool requires that the remote machine be accessable via SSH and that you have the password
scp [hostmachineusername]@[hostmachineip]:/remote_directory/file /local/directory
```

run `fs.meta.load` in the backup cluster on the Filer:

```sh
fs.meta.load [filepath/filename.meta]
```

### Start up The Backup Cluster

- start the backup cluster's volume servers and use the `-dir` flag to specify where the backed up volumes you'd like to use reside.
- test the new cluster and make sure the files are loading properly and not corrupted. This can be done using the `volume.fsck` command in `weed shell`.

### Notes

- This guide assumes you understand the differences between a Volume and a Volume Server.
- This is not bullet proof. It was tested on a small deployment with a very small amount of data(a few Gigabytes). 
- The transfer of volumes when using `weed backup` can take a considerable amount of time depending on the volume server's speed, the network the data is passing over, etc.
- This example requires your entire cluster to pause(stop receiving writes) while the volumes are being backed up/transferred. This is because the metadata and volume data must match for the whole dataset to be rebuilt and usable in another cluster. In an environment where you backup volumes to place them back in the same cluster if one has an issue this is not so big a concern.

**If you have another way to perform a backup or do something similar please share it!**

## ToDo
_from @bmillemathias_
* how to do a consistent backup on a distributed environment (as backup is incremental and for instance done hourly, what is the strategy to restore data of 2 days ago (use filesystem snapshot ? again how to do on distributed environment) 
* does backing up master or filer make sense ?
* How to test a backup
* How to restore data (with indication on distributed environment)