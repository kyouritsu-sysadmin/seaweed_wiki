---
id: Docker-Image-Registry-with-SeaweedFS
title: "Docker Image Registry with SeaweedFS"
sidebar_label: "Docker Image Registry with SeaweedFS"
---

https://github.com/distribution/distribution is a core library for many registry operators including Docker Hub, GitHub Container Registry, GitLab Container Registry and DigitalOcean Container Registry, as well as the CNCF Harbor Project, and VMware Harbor Registry.

There are two ways to use SeaweedFS as a storage backend:
1. Use S3 storage backend with SeaweedFS S3.
2. Use file storage backend with SeaweedFS FUSE mount.

For better performance, using S3 API is recommended. This is because FUSE mount currently needs to save the file to a local folder, before uploading the file to SeaweedFS cluster.

# Configure Registry to use SeaweedFS S3
Assuming SeaweedFS S3 API is on `192.168.2.4:8333`, here is an example registry configuration. If you have checked out https://github.com/distribution/distribution, save this file as `cmd/registry/config-seaweedfs.yml`.

```
version: 0.1
log:
  level: debug
  fields:
    service: registry
    environment: development
  hooks:
    - type: mail
      disabled: true
      levels:
        - panic
      options:
        smtp:
          addr: mail.example.com:25
          username: mailuser
          password: password
          insecure: true
        from: sender@example.com
        to:
          - errors@example.com
storage:
    s3:
      region: default
      bucket: harbor
      accesskey: any
      secretkey: any
      regionendpoint: http://192.168.2.4:8333
      secure: false
      v4auth: true
      skipverify: true
      rootdirectory: "/"
    delete:
      enabled: true
    redirect:
      disable: true
http:
    addr: 192.168.2.4:5000
    debug:
        addr: 192.168.2.4:5001
        prometheus:
            enabled: true
            path: /metrics
    headers:
        X-Content-Type-Options: [nosniff]
redis:
  addr: localhost:6379
  pool:
    maxidle: 16
    maxactive: 64
    idletimeout: 300s
  dialtimeout: 10ms
  readtimeout: 10ms
  writetimeout: 10ms
notifications:
    events:
        includereferences: true
    endpoints:
        - name: local-5003
          url: http://localhost:5003/callback
          headers:
             Authorization: [Bearer <an example token>]
          timeout: 1s
          threshold: 10
          backoff: 1s
          disabled: true
        - name: local-8083
          url: http://localhost:8083/callback
          timeout: 1s
          threshold: 10
          backoff: 1s
          disabled: true 
health:
  storagedriver:
    enabled: true
    interval: 10s
    threshold: 3
```

# Start Registry

```
go cmd/registry/main.go serve cmd/registry/config-seaweedfs.yml
```

# Using Registry

Very likely you need to adjust your docker daemon configuration file, assuming the IP address is `192.168.2.4`:
```
{
  "insecure-registries":[
    "192.168.2.4:5000"
  ]
}
```

Now you can use the harbor running in your `&lt;ip&gt;:5000`.

```
$ docker pull nginx:1.13.5-alpine
$ docker tag nginx:1.13.5-alpine 192.168.2.4:5000/nginx:1.13.5-alpine
$ docker push 192.168.2.4:5000/nginx:1.13.5-alpine
```