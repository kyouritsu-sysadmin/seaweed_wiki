---
id: Large-File-Handling
title: "Large File Handling"
sidebar_label: "Large File Handling"
---

In order to achieve high concurrency, SeaweedFS tries to read and write the whole file into memory. But this would not work for large files. 

The following is implemented in "weed upload" command. For 3rd party clients, here is the spec.

To support large files, SeaweedFS supports these two kinds of files:
* Chunk File. Each chunk file is actually just normal files to SeaweedFS.
* Chunk Manifest. A simple json file with the list of all the chunks. 

This piece of code shows the json file structure:

https://github.com/seaweedfs/seaweedfs/blob/master/weed/operation/chunked_file.go#L24

```
type ChunkInfo struct {
	Fid    string `json:"fid"`
	Offset int64  `json:"offset"`
	Size   int64  `json:"size"`
}

type ChunkList []*ChunkInfo

type ChunkManifest struct {
	Name   string    `json:"name,omitempty"`
	Mime   string    `json:"mime,omitempty"`
	Size   int64     `json:"size,omitempty"`
	Chunks ChunkList `json:"chunks,omitempty"`
}
```

When reading Chunk Manifest files, the SeaweedFS will find and send the data file based on the list of ChunkInfo.

## Create new large file

SeaweedFS delegates the effort to the client side. The steps are:

1. split large files into chunks
1. upload each file chunk as usual. Save the related info into ChunkInfo struct. Each chunk can be spread onto different volumes, possibly giving faster parallel access.
1. upload the manifest file with mime type "application/json", and add url parameter "cm=true". The FileId to store the manifest file is the entry point of the large file.


## Update large file

Usually we just append large files. Updating a specific chunk of file is almost the same.

The steps to append a large file:

1. upload the new file chunks as usual. Save the related info into ChunkInfo struct.
1. update the updated manifest file with mime type "application/json", and add url parameter "cm=true".

## Example
```
# split -n 2 sy.jpg   // split the file into two: xaa and xab

# curl -X POST -F "file=@xaa" http://localhost:9333/submit?pretty=yes
{
  "eTag": "809b2add",
  "fid": "6,1b70e99bcd",
  "fileName": "xaa",
  "fileUrl": "10.34.254.62:8080/6,1b70e99bcd",
  "size": 73433
}

# curl -X POST -F "file=@xab" http://localhost:9333/submit?pretty=yes
{
  "eTag": "9c6ca661",
  "fid": "3,1c863b4563",
  "fileName": "xab",
  "fileUrl": "10.34.254.62:8080/3,1c863b4563",
  "size": 73433
}

// get one fid for manifest file
# curl "10.34.254.62:9333/dir/assign?pretty=yes"
{
  "fid": "5,1ea9c7d93e",
  "url": "10.34.254.62:8080",
  "publicUrl": "10.34.254.62:8080",
  "count": 1
}

# cat manifest.json 
{
        "name": "sy.jpg",
        "mime": "image/jpeg",
        "size": 146866,
        "chunks": [{
                "fid": "6,0100711ab7",
                "offset": 0,
                "size": 73433
        }, {
                "fid": "3,1c863b4563",
                "offset": 73433,
                "size": 73433
        }]
}

// upload the manifest file
# curl -v -F "file=@manifest.json" "http://10.34.254.62:8080/5,1ea9c7d93e?cm=true&pretty=yes"
*   Trying 10.34.254.62...
* Connected to 10.34.254.62 (10.34.254.62) port 8080 (#0)
> POST /5,1ea9c7d93e?cm=true&pretty=yes HTTP/1.1
> Host: 10.34.254.62:8080
> User-Agent: curl/7.47.0
> Accept: */*
> Content-Length: 418
> Expect: 100-continue
> Content-Type: multipart/form-data; boundary=------------------------a872064c8f40903c
> 
< HTTP/1.1 100 Continue
< HTTP/1.1 201 Created
< Content-Type: application/json
< Etag: "2229f9b4"
< Date: Wed, 15 Jan 2020 03:12:18 GMT
< Content-Length: 66
< 
{
  "name": "manifest.json",
  "size": 213,
  "eTag": "2229f9b4"
}
* Connection #0 to host 10.34.254.62 left intact

// download the full file
# curl -v "http://10.34.254.62:8080/5,1ea9c7d93e" -o out.data
*   Trying 10.34.254.62...
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0* Connected to 10.34.254.62 (10.34.254.62) port 8080 (#0)
> GET /5,1ea9c7d93e HTTP/1.1
> Host: 10.34.254.62:8080
> User-Agent: curl/7.47.0
> Accept: */*
> 
< HTTP/1.1 200 OK
< Accept-Ranges: bytes
< Content-Disposition: inline; filename="sy.jpg"
< Content-Length: 146866
< Content-Type: image/jpeg
< Etag: "3e8ef528"
< Last-Modified: Wed, 15 Jan 2020 03:32:47 GMT
< X-File-Store: chunked
< Date: Wed, 15 Jan 2020 03:33:04 GMT
< 
{ [7929 bytes data]
100  143k  100  143k    0     0  47.2M      0 --:--:-- --:--:-- --:--:-- 70.0M
* Connection #0 to host 10.34.254.62 left intact

// check md5 of the downloaded files
# md5sum out.data 
836eababc392419580641a7b65370e82  out.data

# md5sum sy.jpg 
836eababc392419580641a7b65370e82  sy.jpg
```
## Notes
There are no particular limit in terms of chunk file size. Each chunk size does not need to be the same, even in the same file. The rule of thumb is to just being able to keep the whole chunk file in memory, and not to have too many small chunk files.

## weed filer and weed mount
The filer server and the FUSE implementation that uses filer server are automatically chunking large files into smaller chunks.

The list of chunks are stored in filer storage, and managed by filer or weed mount client.
