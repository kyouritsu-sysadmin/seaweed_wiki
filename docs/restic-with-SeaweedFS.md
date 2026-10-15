---
id: restic-with-SeaweedFS
title: "restic with SeaweedFS"
sidebar_label: "restic with SeaweedFS"
---

### Installation
See https://restic.github.io

On mac: `brew install restic`

### Weed Configuration

Set the `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables in both your `weed` environment as well as your `restic` environment.

The key values do not matter _but they must be provided_, as `restic` expects (and effectively requires) non-anonymous access when communicating with an S3 bucket.

This may involve configuring your `weed` server similar to the following:

```bash
export AWS_ACCESS_KEY_ID="any-key-id"
export AWS_SECRET_ACCESS_KEY="any-access-key"

export WEED_S3_CONFIGURE_CMD="s3.configure \
  -access_key \"$AWS_ACCESS_KEY_ID\" \
  -secret_key \"$AWS_SECRET_ACCESS_KEY\" \
  -user iam \
  -actions Admin \
  -apply"
echo "$WEED_S3_CONFIGURE_CMD" | weed shell
```

### Execute Restic Commands

See: https://github.com/seaweedfs/seaweedfs/wiki/s3cmd-with-SeaweedFS

First, create the bucket:
```bash
s3cmd mb s3://resticbucket
```

Then, initialize the restic bucket and backup to it:
```console
$ export AWS_ACCESS_KEY_ID="any-key-id"
$ export AWS_SECRET_ACCESS_KEY="any-access-key"

$ restic -r s3:http://localhost:8333/resticbucket init

$ restic -r s3:http://localhost:8333/resticbucket backup /Users/chris/dev/gopath/bin/
open repository
enter password for repository:
repository 47edd0a2 opened successfully, password is correct
created new cache in /Users/chris/Library/Caches/restic

Files:          71 new,     0 changed,     0 unmodified
Dirs:            4 new,     0 changed,     0 unmodified
Added to the repo: 805.611 MiB

processed 71 files, 807.721 MiB in 0:05
snapshot 7436ec41 saved

```