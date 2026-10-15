---
id: S3-Bucket-Quota
title: "S3 Bucket Quota"
sidebar_label: "S3 Bucket Quota"
---

# Efficient Usage Collection

To manage quota, the system first needs to know how much storage currently used. Usually this would need some relatively complicated counting, rolling up the directory tree. One way is to count during write time, but the upper tree nodes would become hot spots. This would slow down the normal write operations.

Since SeaweedFS uses one collection for each bucket, the usage can be efficiently collected from the volumes used by the collection. So the usage collection is very cheap and does not interfere with write operations.

> This page covers **server-side** bucket quota, enforced by an admin script that flips an over-quota bucket to read-only. It is distinct from the FUSE mount's [`-collectionQuotaMB`](./FUSE-Mount.md#enforcing-a-collection-quota--collectionquotamb) (used by the [SeaweedFS CSI driver](https://github.com/seaweedfs/seaweedfs-csi-driver)), which is enforced mount-side and fails writes with `ENOSPC`.

# How it works

There are two aspects of quota management: "quota configuration" and "quota enforcement".

* "Quota Configuration" is done in by an admin script in `weed shell`, where you can set/remove/enable/disable bucket quota for each bucket.
* "Quota Enforcement" is actually also an admin script, which you can run it periodically by adding it to `master.toml`. It will check whether all the buckets are over their limit or not. If one bucket is over quota, it will set the bucket to read only.

The bucket's "readOnly" flag is checked when the filer processes write requests. If a bucket is readOnly, the creation and update requests on the bucket will be denied, except deletion. The read operations are not be affected.

# Quota Configuration and Enforcement

**1. View current bucket usage**

Here there are 3 example buckets created. The bucket sizes and file counts are listed. The bucket size is the actual disk space used, including replicated copies.

```
> s3.bucket.list
  b1	size:527971104	file:151
  b2	size:468432	file:6
  b3	size:10280	file:3
```

**2. Set bucket "b1" to a low quota**

```
> s3.bucket.quota -name b1 -sizeMB 15
updated quota for bucket b1
> s3.bucket.list
  b1	size:527971104	file:151	quota:15728640	usage:3356.75%
  b2	size:468432	file:6
  b3	size:10280	file:3
```

**3. Enforce the quota, and found it should be set to read only.**

```
> s3.bucket.quota.enforce -apply
  b1	size:527971104	quota:15728640	usage:3356.75%
    changing bucket b1 to read only!
```

Note: Internally this readOnly flag is saved into filer configuration for `locationPrefix="/buckets/b1/"`. So you could directly check the bucket `readOnly` property with `fs.configure` also.
```
> fs.configure
{
  "locations": [
    {
      "locationPrefix": "/buckets/b1/",
      "collection": "b1",
      "readOnly": true
    }
  ]
}
```

# Schedule Quota Enforcement

`s3.bucket.quota.enforce -apply` should be run regularly. You can add it to the `master.toml` file, or add it to some shell scripts. The frequency depends on how much you trust your users. :)

# S3 API Extension (`?seaweedfs-quota`)

In addition to `weed shell`, bucket quota can be configured via the S3 API using a SeaweedFS-specific subresource. This is useful for programmatic integration (e.g., Apache CloudStack) where the integrator can sign SigV4 requests but cannot run `weed shell`.

## API

```
PUT /{bucket}?seaweedfs-quota    — set bucket quota (IAM: s3:PutBucketQuota)
GET /{bucket}?seaweedfs-quota    — get bucket quota (IAM: s3:GetBucketQuota)
```

Request/response body (JSON):
```json
{"quota_size": 100, "quota_unit": "GB", "quota_enabled": true}
```

Supported `quota_unit` values: `B`, `KB`, `MB`, `GB`, `TB` (case-insensitive).

`quota_enabled: false` with a positive `quota_size` stores the quota as disabled but retains the size. `quota_size: 0` removes the quota entirely. When quota is cleared, the bucket's read-only flag is also lifted.

## Authentication

Uses standard S3 SigV4 — the same credentials used for other S3 operations. No separate admin token is needed.

## Authorization

Two dedicated IAM permissions:
- `s3:PutBucketQuota` — required to set/clear quota
- `s3:GetBucketQuota` — required to read quota

This allows scoping a credential to quota management only, without granting bucket deletion, user management, or other admin capabilities.

## Example (curl with SigV4)

Since `?seaweedfs-quota` is a SeaweedFS extension and not part of the AWS S3 API, standard AWS tools (`aws s3api`, `s3cmd`, `rclone`) do not support it directly. Use any SigV4-capable HTTP client or sign the request manually:

```bash
# Set a 100GB quota on bucket "mybucket"
curl -X PUT \
  -H "Content-Type: application/json" \
  -H "Authorization: AWS4-HMAC-SHA256 ..." \
  -d '{"quota_size":100,"quota_unit":"GB","quota_enabled":true}' \
  http://localhost:8333/mybucket?seaweedfs-quota

# Get the current quota
curl -H "Authorization: AWS4-HMAC-SHA256 ..." \
  http://localhost:8333/mybucket?seaweedfs-quota
```

## Comparison with MinIO and Ceph

| Provider | Quota endpoint | Auth | CLI tool | `aws s3api`? |
|---|---|---|---|---|
| SeaweedFS | S3 API (`?seaweedfs-quota`) | S3 SigV4 | `weed shell` | No |
| MinIO | Admin API (separate) | Admin credentials | `mc admin bucket quota` | No |
| Ceph RGW | Admin Ops API (`/admin/`) | Admin capabilities | `radosgw-admin quota set` | No |

None of the three use standard AWS S3 API for quota. SeaweedFS's approach is the closest to standard S3 because it uses the same endpoint and same SigV4 credentials, just with a custom query parameter.
