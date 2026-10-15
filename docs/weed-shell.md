---
id: weed-shell
title: "weed shell"
sidebar_label: "weed shell"
---

`weed shell` starts an interactive console to do some maintenance operations.

```
$ weed shell
> help
Type:	"help <command>" for help on <command>. Most commands support "<command> -h" also for options. 
  cluster.check                 	# check current cluster network connectivity 
  cluster.ps                    	# check current cluster process status 
  cluster.raft.add              	# add a server to the raft cluster 
  cluster.raft.ps               	# check current raft cluster status 
  cluster.raft.remove           	# remove a server from the raft cluster 
  cluster.raft.transferLeader   	# transfer raft leadership to another master server 
  cluster.status                	# outputs a quick overview of the cluster status 
  collection.delete             	# delete specified collection 
  collection.list               	# list all collections 
  ec.balance                    	# balance all ec shards among all racks and volume servers 
  ec.decode                     	# decode a erasure coded volume into a normal volume 
  ec.encode                     	# apply erasure coding to a volume 
  ec.rebuild                    	# find and rebuild missing ec shards among volume servers 
  ec.scrub                      	# scrubs EC volume contents on volume servers. 
  fs.cat                        	# stream the file content on to the screen 
  fs.cd                         	# change directory to a directory /path/to/dir 
  fs.configure                  	# configure and apply storage options for each location 
  fs.du                         	# show disk usage 
  fs.log.purge                  	# purge filer logs 
  fs.ls                         	# list all files under a directory 
  fs.mergeVolumes               	# re-locate chunks into target volumes and try to clear lighter volumes. 
  fs.meta.cat                   	# print out the meta data content for a file or directory 
  fs.meta.changeVolumeId        	# change volume id in existing metadata. 
  fs.meta.load                  	# load saved filer meta data to restore the directory and file structure 
  fs.meta.notify                	# recursively send directory and file meta data to notification message queue 
  fs.meta.save                  	# save all directory and file meta data to a local file for metadata backup. 
  fs.mkdir                      	# create a directory 
  fs.mv                         	# move or rename a file or a folder 
  fs.pwd                        	# print out current directory 
  fs.rm                         	# remove file and directory entries 
  fs.tree                       	# recursively list all files under a directory 
  fs.verify                     	# recursively verify all files under a directory 
  lock                          	# lock in order to exclusively manage the cluster 
  mount.configure               	# configure the mount on current server 
  mq.balance                    	# balance topic partitions 
  mq.topic.compact              	# compact the topic storage into parquet format 
  mq.topic.configure            	# configure a topic with a given name 
  mq.topic.describe             	# describe a topic 
  mq.topic.list                 	# print out all topics 
  mq.topic.truncate             	# clear all data from a topic while preserving topic structure 
  remote.cache                  	# comprehensive synchronization and caching between local and remote storage 
  remote.configure              	# remote storage configuration 
  remote.copy.local             	# copy local files to remote storage 
  remote.meta.sync              	# synchronize the local file meta data with the remote file metadata 
  remote.mount                  	# mount remote storage and pull its metadata 
  remote.mount.buckets          	# mount all buckets in remote storage and pull its metadata 
  remote.uncache                	# keep the metadata but remote cache the file content for mounted directories or files 
  remote.unmount                	# unmount remote storage 
  s3.accesskey.create           	# create an additional access key for an S3 IAM user 
  s3.accesskey.delete           	# delete an access key from an S3 IAM user 
  s3.accesskey.list             	# list access keys for an S3 IAM user 
  s3.accesskey.rotate           	# rotate an access key for an S3 IAM user 
  s3.anonymous.get              	# show anonymous access for a bucket 
  s3.anonymous.list             	# list all buckets with anonymous access 
  s3.anonymous.set              	# set anonymous (public) access on a bucket 
  s3.bucket.create              	# create a bucket with a given name
  s3.bucket.delete              	# delete a bucket by a given name
  s3.bucket.list                	# list all buckets 
  s3.bucket.lock                	# view or enable Object Lock for an S3 bucket 
  s3.bucket.owner               	# view or change the owner of an S3 bucket 
  s3.bucket.quota               	# set/remove/enable/disable quota for a bucket 
  s3.bucket.quota.enforce       	# check quota for all buckets, make the bucket read only if over the limit 
  s3.circuitBreaker             	# configure and apply s3 circuit breaker options for each bucket 
  s3.clean.uploads              	# clean up stale multipart uploads 
  s3.config.show                	# show a summary of the current S3 IAM configuration 
  s3.iam.export                 	# export the full S3 IAM configuration as JSON 
  s3.iam.import                 	# import S3 IAM configuration from a JSON file 
  s3.policy                     	# manage s3 policies 
  s3.policy.attach              	# attach a policy to an S3 IAM user 
  s3.policy.detach              	# detach a policy from an S3 IAM user 
  s3.serviceaccount.create      	# create a service account for an S3 IAM user 
  s3.serviceaccount.delete      	# delete a service account 
  s3.serviceaccount.list        	# list service accounts 
  s3.serviceaccount.show        	# show details of a service account 
  s3.user.create                	# create an S3 IAM user 
  s3.user.delete                	# delete an S3 IAM user 
  s3.user.disable               	# disable an S3 IAM user 
  s3.user.enable                	# enable a disabled S3 IAM user 
  s3.user.list                  	# list S3 IAM users 
  s3.user.provision             	# create a user with a bucket policy in one step 
  s3.user.show                  	# show details of an S3 IAM user 
  s3tables.bucket               	# manage s3tables table buckets 
  s3tables.namespace            	# manage s3tables namespaces 
  s3tables.table                	# manage s3tables tables 
  s3tables.tag                  	# manage s3tables tags 
  unlock                        	# unlock the cluster-wide lock 
  volume.balance                	# balance all volumes among volume servers 
  volume.check.disk             	# check all replicated volumes to find and fix inconsistencies. It is optional and resource intensive. 
  volume.configure.replication  	# change volume replication value 
  volume.copy                   	# copy a volume from one volume server to another volume server 
  volume.delete                 	# delete a live volume from one volume server 
  volume.deleteEmpty            	# delete empty volumes from all volume servers 
  volume.fix.replication        	# add or remove replicas to volumes that are missing replicas or over-replicated 
  volume.fsck                   	# check all volumes to find entries not used by the filer. It is optional and resource intensive. 
  volume.grow                   	# grow volumes 
  volume.list                   	# list all volumes 
  volume.mark                   	# Mark volume writable or readonly from one volume server 
  volume.mount                  	# mount a volume from one volume server 
  volume.move                   	# move a live volume from one volume server to another volume server 
  volume.scrub                  	# scrubs volume contents on volume servers. 
  volume.tier.download          	# download the dat file of a volume from a remote tier 
  volume.tier.move              	# change a volume from one disk type to another 
  volume.tier.upload            	# upload the dat file of a volume to a remote tier 
  volume.unmount                	# unmount a volume from one volume server 
  volume.vacuum                 	# compact volumes if deleted entries are more than the limit 
  volume.vacuum.disable         	# disable vacuuming request from Master, however volume.vacuum still works. 
  volume.vacuum.enable          	# enable vacuuming request from Master 
  volumeServer.evacuate         	# move out all data on a volume server 
  volumeServer.leave            	# stop a volume server from sending heartbeats to the master 
```

For example:
```
$ weed shell
> fs.du /objects
block:2715	byte:  31895432	/objects
```

For most volume operations, you would need to prevent other possible concurrent operations. To do so, lock this way:
```
> lock
> volume.fix.replication
> volume.mount ...
> ...
> unlock
```

Another example: sometimes one of your volume server may go down, and a new volume server is added. Here is the command you can run to fix volumes that are under replicated:

```
# check any volume that are under replicated, and there are servers that meet the replica placement requirement
$ echo "lock; volume.fix.replication -n ; unlock" | weed shell
replicating volume 241 001 from localhost:8080 to dataNode 127.0.0.1:7823 ...

# found one, let's really do it
$ echo "lock; volume.fix.replication ; unlock" | weed shell
replicating volume 241 001 from localhost:8080 to dataNode 127.0.0.1:7823 ...

# all volumes are replicated now
$ echo "lock; volume.fix.replication -n ; unlock" | weed shell
no under replicated volumes

```

# Check and Fix chunks replication
if use see in logs filechunk **2480,09a6290e6159aedd** Not Found:
```
I0212 22:22:56.666094 filechunk_manifest.go:197 read http://fast-volume-1:8080/2480,09a6290e6159aedd failed, err: http://fast-volume-1:8080/2480,09a6290e6159aedd?readDeleted=true: 404 Not Found
```
1. `volume.check.disk`
```
> lock; volume.check.disk -v -apply -slow -volumeId 2480 -nonRepairThreshold 1 -syncDeleted
load collection logs-data volume 2480 index size 2621232 from fast-volume-3:8080 ...
load collection logs-data volume 2480 index size 2621232 from fast-volume-1:8080 ...
volume 2480 fast-volume-1:8080 has 163827 entries, fast-volume-3:8080 missed 0 and partially deleted 0 entries
volume 2480 fast-volume-3:8080 has 163827 entries, fast-volume-1:8080 missed 0 and partially deleted 0 entries
```
2. `volume.fsck`
Search for files that are in the filer, but there are no chunks on the volume servers
```
lock;volume.fsck -findMissingChunksInFiler -verifyNeedles -collection logs-data -volumeId 2480 -v
checking directory /buckets/logs-data/2023-02-13
total 128 directories, 5148091 files
find missing file chunks in dataNodeId fast-volume-1:8080 volume 2480 ...
/buckets/logs-data/2022-10-10/39228128_2022-10-10.log
find missing file chunks in dataNodeId fast-volume-3:8080 volume 2480 ...
/buckets/logs-data/2022-10-10/39228128_2022-10-10.log
```

Find the chunk id **2480,09a6290e6159aedd**:
```
> fs.meta.cat /buckets/logs-data/2022-10-10/39228128_2022-10-10.log
{
  "name":  "39228128_2022-10-10.log",
  "isDirectory":  false,
  "chunks":  [
    {
      "fileId":  "2480,09a6290e6159aedd",
      "offset":  "0",
      "size":  "3884",
      "modifiedTsNs":  "1665409412570272776",
      "eTag":  "O5jilriNGhfJRBCCs+yU4g==",
      "sourceFileId":  "",
      "fid":  {
        "volumeId":  2480,
        "fileKey":  "161884430",
        "cookie":  1633267421
      },
      "sourceFid":  null,
      "cipherKey":  "",
      "isCompressed":  false,
      "isChunkManifest":  false
    }
  ],
  "attributes":  {
    "fileSize":  "3884",
    "mtime":  "1665409412",
    "fileMode":  504,
    "uid":  0,
    "gid":  0,
    "crtime":  "1665409412",
    "mime":  "",
    "ttlSec":  0,
    "userName":  "",
    "groupName":  [],
    "symlinkTarget":  "",
    "md5":  "",
    "rdev":  0,
    "inode":  "0"
  },
  "extended":  {},
  "hardLinkId":  "",
  "hardLinkCounter":  0,
  "content":  "",
  "remoteEntry":  null,
  "quota":  "0"
}chunks 1 meta size: 124 gzip:152
```

3. `fs.verify`
Check the status of all chunks uploaded in the last hour:
```
fs.verify -v -modifyTimeAgo 1h
...
total 807944 directories, 121461080 files
verified 53218 files, error 0 files 
```

In this case, you need a local incremental backup via [asynchronous replication](https://github.com/seaweedfs/seaweedfs/wiki/Async-Backup).

# Scrub EC volumes for bitrot

`ec.scrub` verifies erasure-coded shards on the volume servers. The `-mode checksum` flag compares each shard against its `.ecsum` checksum sidecar, which is the only path that exercises cold parity shards (never read during normal serving).

```
> ec.scrub -mode checksum
> ec.scrub -mode checksum -volumeId 7 -node 127.0.0.1:8080
```

It is read-only and never deletes anything. A flagged shard is arbitrated by Reed-Solomon before being reported, so a stale sidecar block cannot cause a healthy shard to be flagged. See [EC Bitrot Detection](./EC-Bitrot-Detection.md).

# S3 IAM Management

The shell provides a set of composable commands for managing S3 users, policies, credentials, service accounts, and anonymous access.

### Common workflow: create a user with a bucket policy

```
> s3.policy -put -name=photos-rw -file=photos-policy.json
> s3.user.create -name alice
{"name":"alice","access_key":"AKID..."}
> s3.policy.attach -policy photos-rw -user alice
{"policy":"photos-rw","user":"alice"}
```

The secret key is printed to stderr only (not in the JSON output).

Or use the one-step convenience command:
```
> s3.user.provision -name alice -bucket photos -role readwrite
{"name":"alice","access_key":"AKID...","policy":"photos-alice-readwrite"}
```

Roles: `readonly`, `readwrite`, `admin`. The bucket must be a literal name (no wildcards).
If the user already exists, the command skips user creation and attaches the new policy to the existing user (no new credentials are printed).

### Manage credentials
```
> s3.accesskey.create -user alice
> s3.accesskey.list -user alice
> s3.accesskey.rotate -user alice -access_key AKID...
> s3.accesskey.delete -user alice -access_key AKID...
```

### Manage anonymous (public) bucket access
```
> s3.anonymous.set -bucket photos -access Read,List
> s3.anonymous.get -bucket photos
> s3.anonymous.list
```

Actions are validated and case-insensitive (`read` and `Read` both work).
Supported actions: Read, Write, List, Tagging, Admin.

### Manage service accounts
```
> s3.serviceaccount.create -user alice -description "CI pipeline" -actions Read,List
> s3.serviceaccount.create -user alice -expiry 24h
> s3.serviceaccount.list -user alice
> s3.serviceaccount.show -id sa:alice:<uuid>
> s3.serviceaccount.delete -id sa:alice:<uuid>
```

Service account IDs use the form `sa:&lt;parent-user&gt;:&lt;uuid&gt;` (e.g.
`sa:alice:123e4567e89b12d3a456426614174000`). Copy the ID printed by
`s3.serviceaccount.create` or `s3.serviceaccount.list`.

Actions are validated (Read, Write, List, Tagging, Admin).
Use `-expiry` for time-limited credentials (must be positive; 0 = no expiration).

### User lifecycle
```
> s3.user.list
> s3.user.show -name alice
> s3.user.disable -name alice
> s3.user.enable -name alice
> s3.user.delete -name alice
```

### Backup and restore IAM state
```
> s3.iam.export -file iam-backup.json
> s3.iam.import -file iam-backup.json -apply
> s3.config.show
```

`s3.iam.export -file` writes with mode 0600 to protect credentials.
`s3.iam.import` requires `-apply` since it overwrites the entire IAM configuration.

# Scripting with weed shell

When stdin or stdout is piped, `weed shell` automatically suppresses the `> ` prompt and informational logs, making it easy to use in scripts and parse output with tools like `jq`.

### Heredoc for multiline commands
```bash
weed shell << EOF
lock
volume.fix.replication -n
unlock
EOF
```

### Pipe JSON output to jq
```bash
echo "s3.user.list" | weed shell | jq '.[] | select(.keys > 0)'
```

### Debug mode
Use `-debug` to re-enable informational logs on stderr:
```bash
echo "s3.user.list" | weed shell -debug 2>shell.log | jq
```

# One more trick
You can skip the "fs." prefix, for all "fs.*" commands:
```
> fs.ls
dd.dat
topics
> ls
dd.dat
topics
> ls -al topics
drwxr-xr-x   0 chrislu staff      0 /topics/.system
total 1

> fs.du
block: 515	byte:10039099653	/
> du
block: 515	byte:10039099653	/
```

# Run from Docker Image
`weed shell` commands can also be run via the docker image, allowing an operator to perform maintenance commands.

```
docker run \
  --rm \
  -e SHELL_FILER=localhost:8888 \
  -e SHELL_MASTER=localhost:9333 \
  chrislusf/seaweedfs:local \
  "shell" \
  "fs.configure -locationPrefix=/buckets/foo -volumeGrowthCount=3 -replication=002 -apply"
```

Here `shell` selects the [Docker image entrypoint](https://github.com/seaweedfs/seaweedfs/blob/master/docker/entrypoint.sh#L60-L64).

The arguments are `fs.configure -locationPrefix=/buckets/foo -volumeGrowthCount=3 -replication=002 -apply`
