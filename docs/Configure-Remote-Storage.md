---
id: Configure-Remote-Storage
title: "Configure Remote Storage"
sidebar_label: "Configure Remote Storage"
---

# Supported Vendors

Here are a list of vendors supported. For other S3 compatible vendors, you can use just s3, but usually you may need to tweak these parameters:
```
remote.configure -name=cloud1 -type=s3 -s3.access_key=xxx -s3.secret_key=yyy -s3.endpoint=zzzzz -s3.force_path_style=true -s3.v4_signature=false
```

| Name | Type  | Note | Reference |
| -- | -- | -- | -- |
| AWS S3 | s3 |  |  |
| Google Cloud Storage | gcs | Can use service account credentials json or application default credentials (ADC) | https://cloud.google.com/docs/authentication/getting-started |
| Azure Blob Storage | azure | Can use an account key, or Entra ID with a workload identity or managed identity. See [Azure Blob Storage Authentication](./Azure-Blob-Storage-Authentication.md) | https://docs.microsoft.com/en-us/azure/storage/common/storage-account-keys-manage |
| BackBlaze | b2 | Endpoint format: `s3.[region]. backblazeb2.com` | https://help.backblaze.com/hc/en-us/articles/360047425453-Getting-Started-with-the-S3-Compatible-API |
| Wasabi | wasabi | Endpoint format: `s3.[region].wasabisys.com` | https://wasabi-support.zendesk.com/hc/en-us/articles/360015106031-What-are-the-service-URLs-for-Wasabi-s-different-storage-regions- |
| Storj | storj |  |  |
| Filebase | filebase |  |  |
| Aliyun 对象存储 OSS | aliyun | Endpoint format: `oss-[region]-aliyuncs.com` | https://help.aliyun.com/document_detail/31837.htm |
| Tencent 对象存储 COS | tencent | Endpoint format: `cos.[region].myqcloud.com` | https://cloud.tencent.com/document/product/436/6224 |
| Baidu 对象存储 BOS | baidu | Endpoint format: `s3.[region].bcebos.com` | https://cloud.baidu.com/doc/BOS/s/ojwvyq973 |


# Configure Remote Storage
Remote Storage should be configured first before being used.

Run `remote.configure` in `weed shell`:
```
> help remote.configure
  remote.configure	# remote storage configuration

	# see the current configurations
	remote.configure

	# set or update a configuration
        # storage class default value is "STANDARD_IA"
	remote.configure -name=cloud1 -type=s3 -s3.access_key=xxx -s3.secret_key=yyy -s3.storage_class="STANDARD"
	remote.configure -name=cloud2 -type=gcs -gcs.appCredentialsFile=~/service-account-file.json
	remote.configure -name=cloud2 -type=gcs  # using application default credentials (ADC)
	remote.configure -name=cloud3 -type=azure -azure.account_name=xxx -azure.account_key=yyy
	remote.configure -name=cloud3 -type=azure -azure.account_name=xxx -azure.client_id=zzz

	# delete one configuration
	remote.configure -delete -name=cloud1

```

In the above example, a remote storage is configured to name `cloud1`, which is the name to reference files stored on this account.

The access key and secret key can be changed on the fly.
