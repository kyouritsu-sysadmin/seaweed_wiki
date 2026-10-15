---
id: Helm-Chart-Recipes
title: "Helm Chart Recipes"
sidebar_label: "Helm Chart Recipes"
---

Copy-paste `values.yaml` files for the shapes people ask about most. Every recipe renders against the current chart. Install any of them with:

```bash
helm repo add seaweedfs https://seaweedfs.github.io/seaweedfs/helm
helm install seaweedfs seaweedfs/seaweedfs -n seaweedfs --create-namespace -f values.yaml
```

The chart README in [k8s/charts/seaweedfs](https://github.com/seaweedfs/seaweedfs/tree/master/k8s/charts/seaweedfs) lists every key. For the operator instead of the chart, see [Deployment to Kubernetes and Minikube](./Deployment-to-Kubernetes-and-Minikube.md).

## Three-node S3 cluster

Three masters for Raft failover, three volume servers, two filers, two S3 gateways, every write stored twice, and a bucket ready to use.

```yaml
global:
  seaweedfs:
    enableReplication: true
    replicationPlacement: "001"   # one extra copy on another server; "002" for two

master:
  replicas: 3
  data:
    type: persistentVolumeClaim   # the cluster's default storage class; add storageClass to pick one
    size: 1Gi

volume:
  replicas: 3                     # at least 1 + the sum of the replication digits
  dataDirs:
    - name: data
      type: persistentVolumeClaim
      size: 500Gi
      maxVolumes: 0               # size the volume count from the disk

filer:
  replicas: 2
  data:
    type: persistentVolumeClaim
    size: 20Gi

s3:
  enabled: true
  replicas: 2
  enableAuth: true
  credentials:
    admin:
      accessKey: admin
      secretKey: change-me
  createBuckets:
    - name: app-storage
```

How the pieces fit:

* `replicationPlacement` is three digits, `XYZ`: X extra copies in other data centers, Y in other racks of the same data center, Z on other servers of the same rack. Total copies are 1 + X + Y + Z, and you need at least that many volume servers in the matching places. Without rack or data center labels every volume server is in the same rack, so `001` needs two volume servers and `002` needs three. `enableReplication` sets both `master.defaultReplication` and `filer.defaultReplicaPlacement` to this value. See [Replication](./Replication.md).
* `volume.replicas` is the number of volume server pods, one per node with the chart's default anti-affinity. It is independent of the replication digits except for the minimum above.
* `maxVolumes: 0` lets each volume server compute how many volumes fit on its disk. The chart's master defaults to 1000MB volumes (`master.volumeSizeLimitMB`); raise it to `30000` for large disks with few buckets, keep it small when you expect many buckets, since each bucket grows its own volumes.
* Master and filer data on claims keep the cluster identity and the metadata when a pod is rescheduled. The chart defaults both to `hostPath`, which does not follow the pod. The older `filer.enablePVC` key is ignored once `filer.data` is set, so use `filer.data`.
* Claims use the cluster's default storage class. Add `storageClass` under a `data` block or a `dataDirs` entry to choose another, for example `local-path` on k3s.
* Two filers on the default LevelDB store [sync with each other](./Filer-Store-Replication.md). For three or more filers, or a lot of metadata, put the store in a database (next recipes).
* `s3.enableAuth` with `s3.credentials` writes the identities into the S3 config secret; the `read` identity gets random keys unless you set it too. `createBuckets` runs once as a post-install hook.

The endpoint inside the cluster is `seaweedfs-s3.seaweedfs.svc:8333`. From a laptop:

```bash
kubectl -n seaweedfs port-forward svc/seaweedfs-s3 8333:8333
AWS_ACCESS_KEY_ID=admin AWS_SECRET_ACCESS_KEY=change-me \
  aws --endpoint-url http://localhost:8333 s3 ls s3://app-storage/
```

Expose it with `s3.ingress` or a `LoadBalancer` under `s3.service.type`. Grow the cluster by raising `volume.replicas`; new volume servers take new writes and nothing moves until you run `volume.balance` in [weed shell](./weed-shell.md).

## Single node for development

One of everything, no authentication.

```yaml
master:
  data:
    type: persistentVolumeClaim
    size: 1Gi

volume:
  dataDirs:
    - name: data
      type: persistentVolumeClaim
      size: 20Gi
      maxVolumes: 0

filer:
  data:
    type: persistentVolumeClaim
    size: 5Gi

s3:
  enabled: true
  createBuckets:
    - name: test
```

For a laptop without Kubernetes, `weed mini` or the Docker image does the same in one process, see [Quick Start with weed mini](./Quick-Start-with-weed-mini.md).

## Lakehouse: S3 Tables with the Iceberg REST catalog

The three-node recipe plus the catalog port on the S3 gateway. Table buckets are created through the S3 Tables API rather than `createBuckets`.

```yaml
global:
  seaweedfs:
    enableReplication: true
    replicationPlacement: "001"

master:
  replicas: 3
  data:
    type: persistentVolumeClaim   # the cluster's default storage class; add storageClass to pick one
    size: 1Gi

volume:
  replicas: 3
  dataDirs:
    - name: data
      type: persistentVolumeClaim
      size: 500Gi
      maxVolumes: 0

filer:
  replicas: 2
  data:
    type: persistentVolumeClaim
    size: 20Gi

s3:
  enabled: true
  replicas: 2
  enableAuth: true
  icebergPort: 8181
  credentials:
    admin:
      accessKey: admin
      secretKey: change-me
```

Create a table bucket, then point engines at the S3 endpoint and the catalog:

```bash
export S3_ENDPOINT=http://seaweedfs-s3.seaweedfs.svc:8333
aws s3tables --region us-east-1 --endpoint-url $S3_ENDPOINT create-table-bucket --name warehouse
```

The Iceberg REST catalog is `http://seaweedfs-s3.seaweedfs.svc:8181`, or set `s3.icebergIngress` to reach it from outside. Engine setup is in [Spark Iceberg Integration](./Spark-Iceberg-Integration.md), [Trino Iceberg Integration](./Trino-Iceberg-Integration.md), [DuckDB Iceberg Integration](./DuckDB-Iceberg-Integration.md), and the other pages under [S3 Table Bucket](./S3-Table-Bucket.md). `s3.lancePort` (default 9101) serves the [SeaweedFS Lance Catalog](./SeaweedFS-Lance-Catalog.md) the same way.

## Filer metadata on PostgreSQL

For three or more filers, or when metadata outgrows a local LevelDB, keep it in a database the filers share. Any store from [Filer Stores](./Filer-Stores.md) works the same way through `WEED_&lt;STORE&gt;_*` environment variables; this is `postgres2`.

```yaml
filer:
  replicas: 3
  extraEnvironmentVars:
    WEED_LEVELDB2_ENABLED: "false"
    WEED_POSTGRES2_ENABLED: "true"
    WEED_POSTGRES2_HOSTNAME: "postgres.database.svc"
    WEED_POSTGRES2_PORT: "5432"
    WEED_POSTGRES2_DATABASE: "seaweedfs"
    WEED_POSTGRES2_SSLMODE: "disable"
  secretExtraEnvironmentVars:
    WEED_POSTGRES2_USERNAME:
      secretKeyRef:
        name: postgres-credentials
        key: username
    WEED_POSTGRES2_PASSWORD:
      secretKeyRef:
        name: postgres-credentials
        key: password

s3:
  enabled: true
  replicas: 3
```

The filer creates its table on first start. `WEED_LEVELDB2_ENABLED` must be turned off, since the chart enables it by default and two enabled stores is an error. The filers no longer need a claim, so `filer.data` can stay at its default.

## Bare metal: node-local disks

Skip the storage class and write straight to each node's disks. One volume server per node, every listed directory becomes a `-dir` on that pod.

```yaml
volume:
  replicas: 3
  dataDirs:
    - name: nvme0
      type: hostPath
      hostPathPrefix: /mnt/nvme0
      maxVolumes: 0
    - name: hdd0
      type: hostPath
      hostPathPrefix: /mnt/hdd0
      maxVolumes: 0
```

The chart mounts `&lt;hostPathPrefix&gt;/object_store/` for each entry. Pin the pods with `volume.nodeSelector` if only some nodes have the disks. To steer buckets between disk types, tag the directories in the same order with `volume.extraArgs: ["-disk", "ssd,hdd"]`, see [Tiered Storage](./Tiered-Storage.md). Master and filer data default to `hostPath` too; give them claims as in the recipes above, or accept that they stay on the node they started on.

## Cross-cluster replication

Two clusters from any recipe above can replicate to each other continuously with `weed filer.sync`, active-active or active-passive, from any pod or host that reaches both filers. The command, the operator sidecar form, and the topology rules are in [Filer Active Active cross cluster continuous synchronization](./Filer-Active-Active-cross-cluster-continuous-synchronization.md).
