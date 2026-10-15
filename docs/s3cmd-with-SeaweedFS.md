---
id: s3cmd-with-SeaweedFS
title: "s3cmd with SeaweedFS"
sidebar_label: "s3cmd with SeaweedFS"
---

### Installation
See https://s3tools.org/download 

1. Download the zip, unzip, cd into the folder.
1. python setup.py install

### Configuration
Answer questions with the following answers:
```
s3cmd --configure

...

New settings:
  Access Key: any_no_empty_key
  Secret Key: any_no_empty_key
  Default Region: US
  S3 Endpoint: localhost:8333
  DNS-style bucket+hostname:port template for accessing a bucket: localhost:8333
  Encryption password:
  Path to GPG program: /usr/local/bin/gpg
  Use HTTPS protocol: False
  HTTP Proxy server name:
  HTTP Proxy server port: 0

```

Make sure the `.s3cfg` file has these values
```
# Setup endpoint
host_base = localhost:8333
host_bucket = localhost:8333
use_https = False
# Enable S3 v4 signature APIs
signature_v2 = False
```

### Reverse proxy sub-path configuration

This is undefined behavior as AWS S3 servers always have sub-domains instead of sub-paths. \
Use this only if you can't create (sub-)domain and use other port!

For s3cmd, `X-Forwarded-Host` is required to be `your.server/s3` but not for other utils
so it's better to use `signature_v2 = True` in s3cfg

Example for Caddy web server
```
redir /s3 /s3/
handle_path /s3/* {
	reverse_proxy localhost:8333 {
		header_up X-Forwarded-Host your.server/s3
		header_up X-Forwarded-Prefix /s3
	}
}
```

### Execute commands
```
$ s3cmd mb s3://newbucket
Bucket 's3://newbucket/' created

$ s3cmd ls s3://
2019-01-01 01:30  s3://newbucket

$ s3cmd put /etc/motd s3://newbucket
WARNING: Module python-magic is not available. Guessing MIME types based on file extensions.
upload: '/etc/motd' -> 's3://newbucket/motd'  [1 of 1]
 6804 of 6804   100% in    0s    87.93 kB/s  done

$ s3cmd get s3://newbucket/motd
download: 's3://newbucket/motd' -> './motd'  [1 of 1]
 6804 of 6804   100% in    0s   595.33 kB/s  done

# change the file
$ vi motd

$ s3cmd sync motd s3://newbucket/
WARNING: Module python-magic is not available. Guessing MIME types based on file extensions.
upload: 'motd' -> 's3://newbucket/motd'  [1 of 1]
 22 of 22   100% in    0s     6.45 kB/s  done
Done. Uploaded 22 bytes in 1.0 seconds, 22.00 B/s.

$ s3cmd ls s3://newbucket/
2019-01-01 01:32         22   s3://newbucket/motd

$ s3cmd del s3://newbucket/motd
delete: 's3://newbucket/motd'

$ s3cmd rb s3://newbucket
Bucket 's3://newbucket/' removed

```
