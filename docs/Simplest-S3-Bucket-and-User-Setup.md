---
id: Simplest-S3-Bucket-and-User-Setup
title: "Simplest S3 Bucket and User Setup"
sidebar_label: "Simplest S3 Bucket and User Setup"
---

# Simplest S3 Bucket and User Setup with `weed mini`

The fastest way to get a working S3 setup — a bucket, a user, and the right
permissions — is `weed mini` plus a single `weed shell` command.

## 1. Start `weed mini`

```bash
weed mini -dir=/data
```

This starts the master, volume, filer, S3 gateway, and admin UI in one process.
See [Quick Start with weed mini](./Quick-Start-with-weed-mini.md) for details.

## 2. Create a bucket, user, and policy in one step

In another terminal, open `weed shell` and run `s3.user.provision`:

```bash
weed shell
> s3.bucket.create -name my-bucket
> s3.user.provision -name alice -bucket my-bucket -role readwrite
```

`s3.user.provision` performs three steps in one command:

1. Creates an IAM policy scoped to `my-bucket`
2. Creates the user `alice` with a freshly generated access key and secret key
3. Attaches the policy to the user

The access key and secret key are printed in the shell output. You can also
view them any time from the Admin UI at http://localhost:23646.

### Available roles

| Role        | Object actions                                      | Bucket actions  |
|-------------|-----------------------------------------------------|-----------------|
| `readonly`  | `s3:GetObject`                                      | `s3:ListBucket` |
| `readwrite` | `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`   | `s3:ListBucket` |
| `admin`     | `s3:*`                                              | `s3:*`          |

Only the named bucket is granted — nothing else in the cluster is exposed.

## 3. Use the credentials

```bash
export AWS_ACCESS_KEY_ID=<printed access key>
export AWS_SECRET_ACCESS_KEY=<printed secret key>

aws --endpoint-url http://localhost:8333 s3 cp ./file.txt s3://my-bucket/
aws --endpoint-url http://localhost:8333 s3 ls s3://my-bucket/
```

As soon as any credential exists, the S3 gateway switches from "Allow All" mode
to authenticated mode — unauthenticated requests will be rejected.

## Anonymous (public) access

Use `s3.anonymous.set` to grant or revoke unauthenticated access on a bucket.

### Grant read-only public access

To serve public assets — anyone can `GET` and `LIST` without credentials:

```bash
> s3.anonymous.set -bucket my-bucket -access Read,List
```

Verify:

```bash
aws --endpoint-url http://localhost:8333 s3 ls s3://my-bucket/ --no-sign-request
curl http://localhost:8333/my-bucket/file.txt
```

### Revoke all anonymous access

To make the bucket private again:

```bash
> s3.anonymous.set -bucket my-bucket -access none
```

After this, unauthenticated requests to `my-bucket` are rejected; only users
with IAM credentials (see `s3.user.provision` above) can access it.

Supported actions: `Read`, `Write`, `List`, `Tagging`, `Admin` (combine with
commas), or `none` to revoke. Use `s3.anonymous.list` / `s3.anonymous.get
-bucket my-bucket` to inspect the current state.

## Adding more users later

Run `s3.user.provision` again with a different `-name` or `-role`. If the user
already exists, the new bucket policy is attached to the existing user instead
of creating a duplicate.

```bash
> s3.user.provision -name bob -bucket my-bucket -role readonly
> s3.user.provision -name alice -bucket another-bucket -role readwrite
```

## Speed check

Quick sanity test on an Apple Silicon laptop, `weed mini -dir=/tmp/weed-repro
-ip=127.0.0.1`, 1 GiB object over loopback:

| Operation                              | Time   | Throughput   |
|----------------------------------------|--------|--------------|
| `aws s3 cp` upload (1 GiB)             | ~2.0 s | ~500 MB/s    |
| `aws s3 cp` download (multipart-range) | ~1.7 s | ~600 MB/s    |
| Single-stream `curl` on a presigned URL| ~0.8 s | ~1343 MB/s   |

## Related

- [Quick Start with weed mini](./Quick-Start-with-weed-mini.md)
- [Amazon S3 API](./Amazon-S3-API.md)
- [Amazon IAM API](./Amazon-IAM-API.md)
- [Admin UI](./Admin-UI.md)
