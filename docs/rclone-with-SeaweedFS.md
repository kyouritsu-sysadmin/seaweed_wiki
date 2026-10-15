---
id: rclone-with-SeaweedFS
title: "rclone with SeaweedFS"
sidebar_label: "rclone with SeaweedFS"
---

### Installation
See https://rclone.org/install/

On mac: `brew install rclone`

### Configuration
See https://rclone.org/s3/

Set config ~/.config/rclone/rclone.conf:
```
[swfs]
type = s3
provider = Other
access_key_id = any-key-id
secret_access_key = any-access-key
endpoint = http://localhost:8333
upload_cutoff = 50Mi
chunk_size = 50Mi
force_path_style = true
```

### Reverse proxy sub-path configuration

This is undefined behavior as AWS S3 servers always have sub-domains instead of sub-paths. \
Use this only if you can't create (sub-)domain and use other port!

rclone (like AWS CLI) appends sub-path before actual path so need to add `X-Forwarded-Prefix` header (set to `/s3` for example)

Example for Caddy web server
```
redir /s3 /s3/
handle_path /s3/* {
	reverse_proxy localhost:8333 {
		header_up X-Forwarded-Prefix /s3
	}
}
```

### Execute commands

copy files
```
rclone  --log-level INFO copy  --checksum --fast-list /Users/kmlebedev/files swfs:/bucket-name/files
```


## Client-side encryption 

### Installation local KMS API
```
git clone https://github.com/kmlebedev/local-kms.git
cd local-kms
go install
```

run local-kms
```
local-kms 
INFO[2023-07-24 15:34:23.876] Local KMS Version Unknown (Commit Hash Unknown) 
INFO[2023-07-24 15:34:23.992] No file found at path /init/seed.yaml; skipping seeding. 
INFO[2023-07-24 15:34:23.992] Data will be stored in /tmp/local-kms        
INFO[2023-07-24 15:34:23.992] Local KMS started on 0.0.0.0:8080 
```

create master key
```
aws kms create-key --endpoint=http://localhost:8080
{
    "KeyMetadata": {
        "AWSAccountId": "111122223333",
        "KeyId": "5beb0309-d1ec-45ea-895a-52bbecbc8bde",
        "Arn": "arn:aws:kms:eu-west-2:111122223333:key/5beb0309-d1ec-45ea-895a-52bbecbc8bde",
        "CreationDate": "2023-07-03T14:24:36+05:00",
        "Enabled": true,
        "KeyUsage": "ENCRYPT_DECRYPT",
        "KeyState": "Enabled",
        "Origin": "AWS_KMS",
        "KeyManager": "CUSTOMER",
        "CustomerMasterKeySpec": "SYMMETRIC_DEFAULT",
        "KeySpec": "SYMMETRIC_DEFAULT",
        "EncryptionAlgorithms": [
            "SYMMETRIC_DEFAULT"
        ]
    }
}
```

### Copy files with encryption
```
rclone  --log-level INFO copy --cse-kms-master-key-id 5beb0309-d1ec-45ea-895a-52bbecbc8bde --kms-endpoint http://localhost:8080 --ignore-size --checksum --fast-list /Users/kmlebedev/files swfs:/bucket-name/files
```
