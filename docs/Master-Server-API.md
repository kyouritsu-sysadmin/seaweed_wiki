---
id: Master-Server-API
title: "Master Server API"
sidebar_label: "Master Server API"
---

## Master server

You can append to any HTTP API with &pretty=y to see a formatted json output.

### Assign a file key
This operation is very cheap. Just increase a number in master server's memory.

```bash
# Basic Usage:
curl http://localhost:9333/dir/assign
{"count":1,"fid":"3,01637037d6","url":"127.0.0.1:8080",
 "publicUrl":"localhost:8080"}
# To assign with a specific replication type:
curl "http://localhost:9333/dir/assign?replication=001"
# To specify how many file ids to reserve
curl "http://localhost:9333/dir/assign?count=5"
# To assign a specific data center
curl "http://localhost:9333/dir/assign?dataCenter=dc1"
```

| Parameter | Description | Default |
| ---- | -- | -- |
| count | how many file ids to assign. Use `&lt;fid&gt;_1`, `&lt;fid&gt;_2` for the assigned additional file ids. e.g. 3,01637037d6_1, 3,01637037d6_2 | 1 |
| collection | required collection name | empty |
| dataCenter | preferred data center | empty |
| rack | preferred rack | empty |
| dataNode | preferred volume server, e.g. 127.0.0.1:8080 | empty |
| replication | replica placement strategy | master defaultReplicaPlacement| 
| ttl | file expiration time limit, example: 3m for 3 minutes. units: m-minute, h-hour, d-day, w-week, M-month, y-year | never expire| 
| preallocate | If no matching volumes, pre-allocate this number of bytes on disk for new volumes.  | master preallocateSize |
| memoryMapMaxSizeMb | Only implemented for windows. Use memory mapped files with specified size for new volumes.  | 0 |
| writableVolumeCount | If no matching volumes, create specified number of new volumes.  | master preallocateSize |
| disk | If you have disks labelled, this must be supplied to specify the disk type to allocate on. | empty |



### Lookup volume

We would need to find out whether the volumes have moved.

```bash
curl "http://localhost:9333/dir/lookup?volumeId=3&pretty=y"
{
  "locations": [
    {
      "publicUrl": "localhost:8080",
      "url": "localhost:8080"
    }
  ]
}
# Other usages:
# You can actually use the file id to lookup, if you are lazy to parse the file id.
curl "http://localhost:9333/dir/lookup?volumeId=3,01637037d6"
# If you know the collection, specify it since it will be a little faster
curl "http://localhost:9333/dir/lookup?volumeId=3&collection=turbo"
```

| Parameter | Description | Default |
| ---- | -- | -- |
| volumeId | volume id | empty |
| collection | optionally to speed up the lookup | empty |
| fileId | If provided, this returns the fileId location and a JWT to update or delete the file. | empty |
| read | works together with "fileId", if read=yes, JWT is generated for reads. | empty |

### Force garbage collection

If your system has many deletions, the deleted file's disk space will not be synchronously re-claimed. There is a background job to check volume disk usage. If empty space is more than the threshold, default to 0.3 which is 30%, the vacuum job will make the volume readonly, create a new volume with only existing files, and switch on the new volume. If you are impatient or doing some testing, vacuum the unused spaces this way.

Currently the garbage collection is hard coded in master to run every 15 minutes. 

```bash
curl "http://localhost:9333/vol/vacuum"
curl "http://localhost:9333/vol/vacuum?garbageThreshold=0.4"
```
| Parameter | Description | Default |
| ---- | -- | -- |
| garbageThreshold | minimum garbage ratio | 0.3, which is 30% from master `-garbageThreshold` option|

The garbageThreshold=0.4 is optional, and will not change the default threshold. You can start volume master with a different default garbageThreshold.

This operation is not trivial. It will try to make a copy of the .dat and .idx files, skipping deleted files, and switch to the new files, removing the old files.

### Pre-Allocate Volumes

One volume serves one write a time. If you need to increase concurrency, you can pre-allocate lots of volumes. Here are examples. You can combine all the different options also.

```bash
# specify a specific replication
curl "http://localhost:9333/vol/grow?replication=000&count=4"
{"count":4}
# specify a collection
curl "http://localhost:9333/vol/grow?collection=turbo&count=4"
# specify data center
curl "http://localhost:9333/vol/grow?dataCenter=dc1&count=4"
# specify ttl
curl "http://localhost:9333/vol/grow?ttl=5d&count=4"
```

| Parameter | Description | Default |
| ---- | -- | -- |
| count | how many volumes to grow | required |
| collection | required collection name | empty |
| dataCenter | preferred data center | empty |
| rack | preferred rack | empty |
| dataNode | preferred volume server, e.g. 127.0.0.1:8080 | empty |
| replication | replica placement strategy | master defaultReplicaPlacement| 
| ttl | file expiration time limit, example: 3m for 3 minutes. units: m-minute, h-hour, d-day, w-week, M-month, y-year | never expire| 
| preallocate | Pre-allocate this number of bytes on disk for new volumes.  | master `-volumePreallocate` option |
| memoryMapMaxSizeMb | Only implemented for windows. Use memory mapped files with specified size for new volumes.  | 0 |


### Delete Collection

```bash
# delete a collection
curl "http://localhost:9333/col/delete?collection=benchmark&pretty=y"
```

| Parameter | Description | Default |
| ---- | -- | -- |
| collection | collection name | required |


### Check System Status

```bash
curl "http://10.0.2.15:9333/cluster/status?pretty=y"
{
  "IsLeader": true,
  "Leader": "10.0.2.15:9333",
  "Peers": [
    "10.0.2.15:9334",
    "10.0.2.15:9335"
  ]
}
```

### Check System Health

```bash
curl -I "http://10.0.2.15:9333/cluster/healthz"
HTTP/1.1 200 OK
Date: Sun, 31 Jul 2022 10:05:07 GMT
```

### Check Writable Volume Status

```
curl "http://localhost:9333/dir/status?pretty=y"
{
  "Topology": {
    "DataCenters": [
      {
        "Free": 3,
        "Id": "dc1",
        "Max": 7,
        "Racks": [
          {
            "DataNodes": [
              {
                "Free": 3,
                "Max": 7,
                "PublicUrl": "localhost:8080",
                "Url": "localhost:8080",
                "Volumes": 4
              }
            ],
            "Free": 3,
            "Id": "DefaultRack",
            "Max": 7
          }
        ]
      },
      {
        "Free": 21,
        "Id": "dc3",
        "Max": 21,
        "Racks": [
          {
            "DataNodes": [
              {
                "Free": 7,
                "Max": 7,
                "PublicUrl": "localhost:8081",
                "Url": "localhost:8081",
                "Volumes": 0
              }
            ],
            "Free": 7,
            "Id": "rack1",
            "Max": 7
          },
          {
            "DataNodes": [
              {
                "Free": 7,
                "Max": 7,
                "PublicUrl": "localhost:8082",
                "Url": "localhost:8082",
                "Volumes": 0
              },
              {
                "Free": 7,
                "Max": 7,
                "PublicUrl": "localhost:8083",
                "Url": "localhost:8083",
                "Volumes": 0
              }
            ],
            "Free": 14,
            "Id": "DefaultRack",
            "Max": 14
          }
        ]
      }
    ],
    "Free": 24,
    "Max": 28,
    "layouts": [
      {
        "collection": "",
        "replication": "000",
        "writables": [
          1,
          2,
          3,
          4
        ]
      }
    ]
  },
  "Version": "0.47"
}
```

### Check Volume Status
```
curl "localhost:9333/vol/status?pretty=y"
{
  "Version": "30GB 2.24 ",
  "Volumes": {
    "DataCenters": {
      "DefaultDataCenter": {
        "DefaultRack": {
          "volume1:8080": [
            {
              "Id": 1,
              "Size": 313888,
              "ReplicaPlacement": {
                "SameRackCount": 2,
                "DiffRackCount": 0,
                "DiffDataCenterCount": 0
              },
              "Ttl": {
                "Count": 0,
                "Unit": 0
              },
              "DiskType": "ssd1",
              "Collection": "",
              "Version": 3,
              "FileCount": 1,
              "DeleteCount": 0,
              "DeletedByteCount": 0,
              "ReadOnly": false,
              "CompactRevision": 0,
              "ModifiedAtSecond": 1612388794,
              "RemoteStorageName": "",
              "RemoteStorageKey": ""
            },
            {
              "Id": 3,
              "Size": 4724352,
              "ReplicaPlacement": {
                "SameRackCount": 0,
                "DiffRackCount": 0,
                "DiffDataCenterCount": 0
              },
              "Ttl": {
                "Count": 0,
                "Unit": 0
              },
              "DiskType": "ssd1",
              "Collection": "",
              "Version": 3,
              "FileCount": 2,
              "DeleteCount": 0,
              "DeletedByteCount": 0,
              "ReadOnly": false,
              "CompactRevision": 0,
              "ModifiedAtSecond": 1612386883,
              "RemoteStorageName": "",
              "RemoteStorageKey": ""
            },
            {
              "Id": 5,
              "Size": 1160,
              "ReplicaPlacement": {
                "SameRackCount": 0,
                "DiffRackCount": 0,
                "DiffDataCenterCount": 0
              },
              "Ttl": {
                "Count": 0,
                "Unit": 0
              },
              "DiskType": "ssd1",
              "Collection": "",
              "Version": 3,
              "FileCount": 1,
              "DeleteCount": 0,
              "DeletedByteCount": 0,
              "ReadOnly": false,
              "CompactRevision": 0,
              "ModifiedAtSecond": 1612386899,
              "RemoteStorageName": "",
              "RemoteStorageKey": ""
            },
            {
              "Id": 7,
              "Size": 114024,
              "ReplicaPlacement": {
                "SameRackCount": 0,
                "DiffRackCount": 0,
                "DiffDataCenterCount": 0
              },
              "Ttl": {
                "Count": 0,
                "Unit": 0
              },
              "DiskType": "ssd1",
              "Collection": "",
              "Version": 3,
              "FileCount": 2,
              "DeleteCount": 0,
              "DeletedByteCount": 0,
              "ReadOnly": false,
              "CompactRevision": 0,
              "ModifiedAtSecond": 1612386883,
              "RemoteStorageName": "",
              "RemoteStorageKey": ""
            },
            {
              "Id": 2,
              "Size": 86544,
              "ReplicaPlacement": {
                "SameRackCount": 0,
                "DiffRackCount": 0,
                "DiffDataCenterCount": 0
              },
              "Ttl": {
                "Count": 0,
                "Unit": 0
              },
              "DiskType": "ssd1",
              "Collection": "",
              "Version": 3,
              "FileCount": 2,
              "DeleteCount": 0,
              "DeletedByteCount": 0,
              "ReadOnly": false,
              "CompactRevision": 0,
              "ModifiedAtSecond": 1612386959,
              "RemoteStorageName": "",
              "RemoteStorageKey": ""
            }
          ],
          "volume2:8082": [
            {
              "Id": 4,
              "Size": 8,
              "ReplicaPlacement": {
                "SameRackCount": 0,
                "DiffRackCount": 0,
                "DiffDataCenterCount": 0
              },
              "Ttl": {
                "Count": 0,
                "Unit": 0
              },
              "DiskType": "ssd1",
              "Collection": "",
              "Version": 3,
              "FileCount": 0,
              "DeleteCount": 0,
              "DeletedByteCount": 0,
              "ReadOnly": false,
              "CompactRevision": 0,
              "ModifiedAtSecond": 1612386883,
              "RemoteStorageName": "",
              "RemoteStorageKey": ""
            },
            {
              "Id": 6,
              "Size": 3761664,
              "ReplicaPlacement": {
                "SameRackCount": 0,
                "DiffRackCount": 0,
                "DiffDataCenterCount": 0
              },
              "Ttl": {
                "Count": 0,
                "Unit": 0
              },
              "DiskType": "ssd1",
              "Collection": "",
              "Version": 3,
              "FileCount": 2,
              "DeleteCount": 0,
              "DeletedByteCount": 0,
              "ReadOnly": false,
              "CompactRevision": 0,
              "ModifiedAtSecond": 1612386883,
              "RemoteStorageName": "",
              "RemoteStorageKey": ""
            },
            {
              "Id": 1,
              "Size": 313888,
              "ReplicaPlacement": {
                "SameRackCount": 2,
                "DiffRackCount": 0,
                "DiffDataCenterCount": 0
              },
              "Ttl": {
                "Count": 0,
                "Unit": 0
              },
              "DiskType": "ssd1",
              "Collection": "",
              "Version": 3,
              "FileCount": 1,
              "DeleteCount": 0,
              "DeletedByteCount": 0,
              "ReadOnly": false,
              "CompactRevision": 0,
              "ModifiedAtSecond": 1612386883,
              "RemoteStorageName": "",
              "RemoteStorageKey": ""
            }
          ],
          "volume3:8083": [
            {
              "Id": 1,
              "Size": 313888,
              "ReplicaPlacement": {
                "SameRackCount": 2,
                "DiffRackCount": 0,
                "DiffDataCenterCount": 0
              },
              "Ttl": {
                "Count": 0,
                "Unit": 0
              },
              "DiskType": "",
              "Collection": "",
              "Version": 3,
              "FileCount": 1,
              "DeleteCount": 0,
              "DeletedByteCount": 0,
              "ReadOnly": false,
              "CompactRevision": 0,
              "ModifiedAtSecond": 1612388996,
              "RemoteStorageName": "",
              "RemoteStorageKey": ""
            }
          ]
        }
      }
    },
    "Free": 30,
    "Max": 39
  }
}
```