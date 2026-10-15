---
id: Docker-Compose-for-S3
title: "Docker Compose for S3"
sidebar_label: "Docker Compose for S3"
---

To use SeaweedFS S3 API, here is the simplest form:

```
services:
  seaweedfs-s3:
    image: chrislusf/seaweedfs
    container_name: seaweedfs-s3
    ports:
      - "8333:8333"
    entrypoint: /bin/sh -c
    command: |
      "echo '{
        \"identities\": [
          {
            \"name\": \"anonymous\",
            \"actions\": [
              \"Read\"
            ]
          },
          {
            \"name\": \"some_admin_user\",
            \"credentials\": [
              {
                \"accessKey\": \"some_access_key1\",
                \"secretKey\": \"some_secret_key1\"
              }
            ],
            \"actions\": [
              \"Admin\",
              \"Read\",
              \"List\",
              \"Tagging\",
              \"Write\"
            ]
          }
        ]
      }' > /etc/seaweedfs/config.json && \
      weed server -s3 -s3.config /etc/seaweedfs/config.json"
    restart: unless-stopped
```

## Notes
- To enable advanced IAM (STS, OIDC providers), mount a JSON and add `-iam.config=/etc/seaweedfs/iam.json` to the S3 command. See [OIDC Integration](./OIDC-Integration.md).
- To use SSE-KMS (with OpenBao/Vault, AWS KMS, GCP KMS), mount KMS config (e.g. `s3_kms.json`) and start with `-config=/etc/seaweedfs/s3_kms.json`. See [Server-Side-Encryption-SSE-KMS](./Server-Side-Encryption-SSE-KMS.md).
- SSE-S3 and bucket default encryption work without external KMS; see [Server-Side-Encryption](./Server-Side-Encryption.md).