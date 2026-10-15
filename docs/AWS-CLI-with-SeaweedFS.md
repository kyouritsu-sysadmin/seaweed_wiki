---
id: AWS-CLI-with-SeaweedFS
title: "AWS CLI with SeaweedFS"
sidebar_label: "AWS CLI with SeaweedFS"
---

### Installation
See https://aws.amazon.com/cli/

On mac or linux: `pip install awscli`

### Configuration
Configure for AWS. The key values do not matter.
```
$ aws configure
AWS Access Key ID [None]: any
AWS Secret Access Key [None]: any
Default region name [None]: us-east-1
Default output format [None]:
```

Also, make sure using AWS signature version 4:
```
$ aws configure set default.s3.signature_version s3v4
```

And configure the S3 endpoint:
```bash
export S3_ENDPOINT=http://localhost:8333
```

### Reverse proxy sub-path configuration

This is undefined behavior as AWS S3 servers always have sub-domains instead of sub-paths. \
Use this only if you can't create (sub-)domain and use other port!

AWS CLI appends sub-path before actual path so need to add `X-Forwarded-Prefix` header (set to `/s3` for example)

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
```
# list buckets
$ aws --endpoint-url $S3_ENDPOINT s3 ls
2019-01-02 01:59:25 newbucket

# list files inside the bucket
$ aws --endpoint-url $S3_ENDPOINT s3 ls s3://newbucket
2019-01-02 12:52:44       6804 password

# make a bucket
$ aws --endpoint-url $S3_ENDPOINT s3 mb s3://newbucket3
make_bucket: newbucket3

# add an object
$ aws --endpoint-url $S3_ENDPOINT s3 cp /etc/passwd s3://newbucket3
upload: ../../../../../etc/passwd to s3://newbucket3/passwd

# copy an object
$ aws --endpoint-url $S3_ENDPOINT s3 cp s3://newbucket3/passwd s3://newbucket3/passwd.txt
copy: s3://newbucket3/passwd to s3://newbucket3/passwd.txt

# remove an object
$ aws --endpoint-url $S3_ENDPOINT s3 rm s3://newbucket3/passwd
delete: s3://newbucket3/passwd

# remove a bucket
$ aws --endpoint-url $S3_ENDPOINT s3 rb s3://newbucket3
remove_bucket: newbucket3

```


# Presigned URL

If [authentication](https://github.com/seaweedfs/seaweedfs/wiki/Amazon-S3-API#authentication) is enabled, the url is not accessible without proper credentials. But you can presign a url and access it.

```

# presign url, default to 1 hour
$ aws --endpoint-url $S3_ENDPOINT s3 presign s3://newbucket/t.txt
http://localhost:8333/newbucket/t.txt?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=some_access_key1%2F20200726%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20200726T161749Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=e0cc153209e414ca8168661f57827aa03ab84e7041ef9270ff639bcc519d24f5

# access the url
$ curl "http://localhost:8333/newbucket/t.txt?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=some_access_key1%2F20200726%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20200726T161749Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=e0cc153209e414ca8168661f57827aa03ab84e7041ef9270ff639bcc519d24f5"
```

## Server-Side Encryption with AWS CLI

### SSE-KMS
```bash
aws --endpoint-url $S3_ENDPOINT s3 cp file.txt s3://bucket/kms.txt \
  --sse aws:kms \
  --sse-kms-key-id "test-key-123"
```

### SSE-C
```bash
# Generate a 256-bit key
openssl rand -base64 32 > key.b64
aws --endpoint-url $S3_ENDPOINT s3 cp file.txt s3://bucket/ssec.txt \
  --sse-c AES256 \
  --sse-c-key fileb://key.b64
```

### SSE-S3 (Server-managed)
```bash
aws --endpoint-url $S3_ENDPOINT s3 cp file.txt s3://bucket/sse-s3.txt \
  --sse AES256
```

## OIDC/JWT to S3
For Keycloak and other OIDC providers, you can obtain a JWT and access S3 directly (or use STS to assume a role). See [OIDC Integration](./OIDC-Integration.md).

## STS (Security Token Service)

### Get Caller Identity
Verify your credentials and see who you are authenticated as:
```bash
aws --endpoint-url $S3_ENDPOINT sts get-caller-identity
```

### Get Federation Token
Obtain temporary credentials scoped down with an optional session policy (only long-term IAM users can call this):
```bash
aws --endpoint-url $S3_ENDPOINT sts get-federation-token \
  --name my-session \
  --duration-seconds 3600
```

With an inline session policy to restrict permissions:
```bash
aws --endpoint-url $S3_ENDPOINT sts get-federation-token \
  --name my-session \
  --policy '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"s3:GetObject","Resource":"arn:aws:s3:::my-bucket/*"}]}'
```

For `AssumeRole` and `AssumeRoleWithWebIdentity`, see [OIDC Integration](./OIDC-Integration.md).
