---
id: Filer-Server-API
title: "Filer Server API"
sidebar_label: "Filer Server API"
---

You can append to any HTTP API with &pretty=y to see a formatted json output.
## Filer server
### POST/PUT/GET files
```bash
# Basic Usage:
  //create or overwrite the file, the directories /path/to will be automatically created
  POST /path/to/file
  PUT /path/to/file
  //create or overwrite the file, the filename in the multipart request will be used
  POST /path/to/
  //create or append the file
  POST /path/to/file?op=append
  PUT /path/to/file?op=append
  //get the file content
  GET /path/to/file

  //return a json format subdirectory and files listing
  GET /path/to/
  Accept: application/json

# options for POST a file:
  // set file TTL
  POST /path/to/file?ttl=1d
  // set file mode when creating or overwriting a file
  POST /path/to/file?mode=0755
```
| POST/PUT Parameter | Description | Default |
| ---- | -- | -- |
| dataCenter | data center | empty |
| rack | rack | empty |
| dataNode | data node | empty |
| collection | collection | empty |
| replication | replication | empty |
| fsync | if "true", the file content write will incur an fsync operation (though the file metadata will still be separate) | false |
| saveInside | if "true", the file content will write to metadata| false |
| ttl | time to live, examples, 3m: 3 minutes, 4h: 4 hours, 5d: 5 days, 6w: 6 weeks, 7M: 7 months, 8y: 8 years | empty |
| maxMB | max chunk size | empty |
| mode | file mode | 0660 |
| offset | incompatible with `op=append`. Defines the number of bytes from the file beginning to insert the uploaded chunk | empty |
| op | file operation, currently only support "append", incompatible with `offset=`. | empty |
| skipCheckParentDir | Ensuring parent directory exists cost one metadata API call. Skipping this can reduce network latency. | false |
| header: `Content-Type` | used for auto compression | empty |
| header: `Content-Disposition` | used as response content-disposition | empty |
| prefixed header: `Seaweed-` | example: `Seaweed-name1: value1`. Returned as `Seaweed-Name1: value1` in GET/HEAD response header. | empty |

| GET Parameter | Description | Default |
| ---- | -- | -- |
| metadata | get file/directory metadata | false |
| resolveManifest | resolve manifest chunks | false |
### notice
* It is recommended to add retries when writing to Filer.
* When appending to a file, each append will create one chunk and added to the file metadata. If there are too many small appends, there could be too many chunks. So try to keep each append size reasonably big.

Examples:
```bash
# Basic Usage:
> curl -F file=@report.js "http://localhost:8888/javascript/"
{"name":"report.js","size":866}
> curl  "http://localhost:8888/javascript/report.js"   # get the file content
> curl -I "http://localhost:8888/javascript/report.js" # get only header
...
> curl -F file=@report.js "http://localhost:8888/javascript/new_name.js"    # upload the file to a different name
{"name":"report.js","size":5514}
> curl -T test.yaml http://localhost:8888/test.yaml                         # upload file by PUT
{"name":"test.yaml","size":866}
> curl -F file=@report.js "http://localhost:8888/javascript/new_name.js?op=append"    # append to an file
{"name":"report.js","size":5514}
> curl -T test.yaml http://localhost:8888/test.yaml?op=append                         # append to an file by PUT
{"name":"test.yaml","size":866}
> curl -H "Accept: application/json" "http://localhost:8888/javascript/?pretty=y"            # list all files under /javascript/
{
  "Path": "/javascript",
  "Entries": [
    {
      "FullPath": "/javascript/jquery-2.1.3.min.js",
      "Mtime": "2020-04-19T16:08:14-07:00",
      "Crtime": "2020-04-19T16:08:14-07:00",
      "Mode": 420,
      "Uid": 502,
      "Gid": 20,
      "Mime": "text/plain; charset=utf-8",
      "Replication": "000",
      "Collection": "",
      "TtlSec": 0,
      "UserName": "",
      "GroupNames": null,
      "SymlinkTarget": "",
      "Md5": null,
      "Extended": null,
      "chunks": [
        {
          "file_id": "2,087f23051201",
          "size": 84320,
          "mtime": 1587337694775717000,
          "e_tag": "32015dd42e9582a80a84736f5d9a44d7",
          "fid": {
            "volume_id": 2,
            "file_key": 2175,
            "cookie": 587534849
          },
          "is_gzipped": true
        }
      ]
    },
    {
      "FullPath": "/javascript/jquery-sparklines",
      "Mtime": "2020-04-19T16:08:14-07:00",
      "Crtime": "2020-04-19T16:08:14-07:00",
      "Mode": 2147484152,
      "Uid": 502,
      "Gid": 20,
      "Mime": "",
      "Replication": "000",
      "Collection": "",
      "TtlSec": 0,
      "UserName": "",
      "GroupNames": null,
      "SymlinkTarget": "",
      "Md5": null,
      "Extended": null
    }
  ],
  "Limit": 100,
  "LastFileName": "jquery-sparklines",
  "ShouldDisplayLoadMore": false
}

# get directory metadata
> curl 'http://localhost:8888/javascript/?metadata=true&pretty=yes'
{
    "FullPath": "/javascript",
    "Mtime": "2022-03-17T11:34:51+08:00",
    "Crtime": "2022-03-17T11:34:51+08:00",
    "Mode": 2147484141,
    "Uid": 1001,
    "Gid": 1001,
    "Mime": "",
    "TtlSec": 0,
    "UserName": "",
    "GroupNames": null,
    "SymlinkTarget": "",
    "Md5": null,
    "FileSize": 0,
    "Rdev": 0,
    "Inode": 0,
    "Extended": null,
    "HardLinkId": null,
    "HardLinkCounter": 0,
    "Content": null,
    "Remote": null,
    "Quota": 0
}

# get file metadata
> curl 'http://localhost:8888/test01.py?metadata=true&pretty=yes'
{
  "FullPath": "/test01.py",
  "Mtime": "2022-01-09T19:11:18+08:00",
  "Crtime": "2022-01-09T19:11:18+08:00",
  "Mode": 432,
  "Uid": 1001,
  "Gid": 1001,
  "Mime": "text/x-python",
  "Replication": "",
  "Collection": "",
  "TtlSec": 0,
  "DiskType": "",
  "UserName": "",
  "GroupNames": null,
  "SymlinkTarget": "",
  "Md5": "px6as5eP7tF5YcgAv5m60Q==",
  "FileSize": 1992,
  "Extended": null,
  "chunks": [
    {
      "file_id": "17,04fbb55507b515",
      "size": 1992,
      "mtime": 1641726678984876713,
      "e_tag": "px6as5eP7tF5YcgAv5m60Q==",
      "fid": {
        "volume_id": 17,
        "file_key": 326581,
        "cookie": 1426568469
      },
      "is_compressed": true
    }
  ],
  "HardLinkId": null,
  "HardLinkCounter": 0,
  "Content": null,
  "Remote": null,
  "Quota": 0
}
```
### GET files

```bash
  //get file with a different content-disposition
  GET /path/to/file?response-content-disposition=attachment%3B%20filename%3Dtesting.txt
```
| GET Parameter | Description | Default |
| ---- | -- | -- |
| response-content-disposition | used as response content-disposition | empty |


### PUT/DELETE file tagging (Custom Attributes)

The Filer provides a tagging API to attach custom metadata to files and directories using `Seaweed-` prefixed headers. This is useful for storing application-specific attributes like expiration dates, ownership, or classification tags.

#### Setting Custom Attributes

```bash
# Add custom attributes to an existing file
curl -X PUT \
    -H "Seaweed-Expire: 2025-12-01" \
    -H "Seaweed-Author: john" \
    -H "Seaweed-Project: demo" \
    "http://localhost:8888/path/to/file?tagging"

# You can also set attributes during file upload
curl -F "file=@myfile.txt" \
    -H "Seaweed-Expire: 2025-12-01" \
    "http://localhost:8888/path/to/myfile.txt"
```

#### Reading Custom Attributes

Custom attributes are returned as response headers when you HEAD or GET a file:

```bash
curl -I "http://localhost:8888/path/to/file"
# Response includes:
# Seaweed-Expire: 2025-12-01
# Seaweed-Author: john
# Seaweed-Project: demo
```

#### Deleting Custom Attributes

```bash
# Delete all Seaweed-prefixed attributes
curl -X DELETE "http://localhost:8888/path/to/file?tagging"

# Delete specific attributes
curl -X DELETE "http://localhost:8888/path/to/file?tagging=Expire,Author"
```

#### Summary

| Method | Request | Header | Operation |
| ---- | ---- | -- | -- |
| PUT | `&lt;file_url&gt;?tagging` | Prefixed with "Seaweed-" | Set custom attributes |
| DELETE | `&lt;file_url&gt;?tagging` |  | Remove all "Seaweed-" prefixed attributes |
| DELETE | `&lt;file_url&gt;?tagging=Key1,Key2` |  | Remove specific attributes |

Notice that the attribute names follow HTTP header key convention, with the first character capitalized (e.g., `Seaweed-my-key` becomes `Seaweed-My-Key`).

#### Performance

Custom attributes are stored in the filer's metadata database alongside other file metadata. They are:
- Efficiently stored with no separate lookups required
- Replicated with other metadata for consistency
- Not indexed by default (queries by attribute require custom implementation)

### Move files and directories
```bash
# move(rename) "/path/to/src_file" to "/path/to/dst_file"
> curl -X POST 'http://localhost:8888/path/to/dst_file?mv.from=/path/to/src_file'
```
| POST Parameter | Description | Default |
| ---- | -- | -- |
| mv.from | move from one file or directory to another location | Required field |

### Copy files

SeaweedFS supports efficient file copying using the `cp.from` parameter. This operation creates a complete copy of a file while preserving the original file.

#### Basic Usage
```bash
# Copy a file to the same directory with a new name
> curl -X POST 'http://localhost:8888/documents/report_backup.pdf?cp.from=/documents/report.pdf'

# Copy a file to a different directory
> curl -X POST 'http://localhost:8888/backup/important.txt?cp.from=/projects/important.txt'

# Copy with automatic name resolution (uses source filename)
> curl -X POST 'http://localhost:8888/backup/?cp.from=/projects/important.txt'
# Creates: /backup/important.txt
```

#### Parameters
| POST Parameter | Description | Default |
| ---- | -- | -- |
| cp.from | Source file path to copy from. Must be a valid file path. | Required field |

#### How Copy Works

**Small Files (&lt; chunk size):**
- Content is stored directly in the filer metadata
- Copy operation duplicates the content bytes
- Very fast, only metadata operation required

**Large Files (chunked):**
- File data is stored as chunks on volume servers
- Copy operation reads data from source chunks and writes to new chunks
- Creates independent chunk copies (not shared references)
- Preserves file integrity and allows independent deletion

#### Examples

**Copy a configuration file:**
```bash
curl -X POST 'http://localhost:8888/config/app.conf.backup?cp.from=/config/app.conf'
```

**Copy a large media file:**
```bash
curl -X POST 'http://localhost:8888/media/backup/video.mp4?cp.from=/media/original/video.mp4'
```

**Copy with path resolution:**
```bash
# If destination ends with /, uses source filename
curl -X POST 'http://localhost:8888/backup/?cp.from=/important/data.json'
# Result: /backup/data.json
```

#### Response Codes

| HTTP Code | Description |
| ---- | -- |
| 204 No Content | Copy operation completed successfully |
| 400 Bad Request | Invalid source path, missing cp.from parameter, or directory copy attempt |
| 404 Not Found | Source file does not exist |
| 500 Internal Server Error | Volume server error or chunk copy failure |

#### Performance Characteristics

- **Small files**: Near-instant (metadata only)
- **Large files**: Proportional to file size (requires data transfer)
- **Network efficient**: Direct volume-to-volume transfer when possible
- **Atomic operation**: Either completes fully or fails with no partial state

#### Limitations

- **Directory copying**: Not supported (returns 400 error)
- **Cross-cluster copying**: Limited to same SeaweedFS cluster
- **Concurrent access**: Source file should not be modified during copy

#### Error Examples

**Attempting to copy a directory:**
```bash
curl -X POST 'http://localhost:8888/new_folder/?cp.from=/existing_folder/'
# Returns: 400 Bad Request - "directory copying not yet supported"
```

**Source file not found:**
```bash
curl -X POST 'http://localhost:8888/copy.txt?cp.from=/nonexistent.txt'
# Returns: 400 Bad Request - "failed to get src entry"
```

**Missing cp.from parameter:**
```bash
curl -X POST 'http://localhost:8888/copy.txt'
# Returns: Normal file upload behavior (not a copy operation)
```

#### Comparison with Move Operation

| Operation | Source File | Use Case | Speed |
| ---- | ---- | ---- | ---- |
| `mv.from` | Deleted | Rename/relocate files | Very fast (metadata only) |
| `cp.from` | Preserved | Backup/duplicate files | Depends on file size |

#### Best Practices

1. **Backup workflows**: Use copy for creating backups before modifications
2. **Template files**: Copy configuration templates to create new instances
3. **Data migration**: Copy files before cross-cluster transfers
4. **Testing**: Copy production files to staging environments

#### Shell Command Equivalent

The SeaweedFS copy operation is similar to:
```bash
# SeaweedFS copy
curl -X POST 'http://localhost:8888/dst?cp.from=/src'

# Unix equivalent
cp /src /dst
```

Note: Directory copying is not currently supported. Only individual files can be copied.

### Create an empty folder
Folders usually are created automatically when uploading a file. To create an empty file, you can use this:
```
curl -X POST "http://localhost:8888/test/"
```
### List files under a directory
Some folder can be very large. To efficiently list files, we use a non-traditional way to iterate files. Every pagination you provide a "lastFileName", and a "limit=x". The filer locate the "lastFileName" in O(log(n)) time, and retrieve the next x files.
```bash
curl -H "Accept: application/json" "http://localhost:8888/javascript/?pretty=y&lastFileName=jquery-2.1.3.min.js&limit=2"
{
  "Path": "/javascript",
  "Entries": [
    {
      "FullPath": "/javascript/jquery-sparklines",
      "Mtime": "2020-04-19T16:08:14-07:00",
      "Crtime": "2020-04-19T16:08:14-07:00",
      "Mode": 2147484152,
      "Uid": 502,
      "Gid": 20,
      "Mime": "",
      "Replication": "000",
      "Collection": "",
      "TtlSec": 0,
      "UserName": "",
      "GroupNames": null,
      "SymlinkTarget": "",
      "Md5": null,
      "Extended": null
    }
  ],
  "Limit": 2,
  "LastFileName": "jquery-sparklines",
  "ShouldDisplayLoadMore": false
}
```
| Parameter | Description | Default |
| ---- | -- | -- |
| limit | how many file to show | 100 |
| lastFileName | the last file in previous batch | empty |
| namePattern | match file names, case-sensitive wildcard characters '*' and '?' | empty |
| namePatternExclude | nagetive match file names, case-sensitive wildcard characters '*' and '?' | empty |

## Supported Name Patterns
The patterns are case-sensitive and support wildcard characters '*' and '?'.
| Pattern | Matches |
| ---- | -- |
| * | any file name |
| *.jpg | abc.jpg |
| a*.jp*g | abc.jpg, abc.jpeg |
| a*.jp?g | abc.jpeg |
# Deletion
## Delete a file
```bash
> curl -X DELETE http://localhost:8888/path/to/file
```
## Delete a folder
```bash
// recursively delete all files and folders under a path
> curl -X DELETE http://localhost:8888/path/to/dir?recursive=true
// recursively delete everything, ignoring any recursive error
> curl -X DELETE http://localhost:8888/path/to/dir?recursive=true&ignoreRecursiveError=true
// For Experts Only: remove filer directories only, without removing data chunks. 
// see https://github.com/seaweedfs/seaweedfs/pull/1153
> curl -X DELETE http://localhost:8888/path/to?recursive=true&skipChunkDeletion=true
```
| Parameter | Description | Default |
| ---- | -- | -- |
| recursive | if "recursive=true", recursively delete all files and folders | filer recursive_delete option from filer.toml |
| ignoreRecursiveError | if "ignoreRecursiveError=true", ignore errors in recursive mode | false |
| skipChunkDeletion | if "skipChunkDeletion=true", do not delete file chunks on volume servers | false |
