---
id: Deployment-to-Kubernetes-and-Minikube
title: "Deployment to Kubernetes and Minikube"
sidebar_label: "Deployment to Kubernetes and Minikube"
---

This page explains how to deploy SeaweedFS to Kubernetes. While the [Introduction](#intro) and [Yaml Files](#yaml-files) sections describe manual deployment with static YAMLs (useful for learning), the recommended approaches for production are using the **Helm Chart** or the **SeaweedFS Operator**.

# Recommended: SeaweedFS Operator

The SeaweedFS Operator simplifies the deployment and management of SeaweedFS clusters on Kubernetes.

## Installation

```bash
helm repo add seaweedfs-operator https://seaweedfs.github.io/seaweedfs-operator/helm
helm install seaweedfs-operator seaweedfs-operator/seaweedfs-operator
```

## IAM Configuration Example

When using the Operator to enable S3 and IAM, you may want to ensure that IAM changes (like creating users or policies via the API) are persistent. This requires enabling filer persistence and ensuring write access is allowed.

The following example shows a `Seaweed` custom resource configuration for IAM write access with persistence:

```yaml
apiVersion: seaweed.seaweedfs.com/v1
kind: Seaweed
metadata:
  name: seaweed1
spec:
  image: chrislusf/seaweedfs:latest
  volumeServerDiskCount: 1
  hostSuffix: seaweed.example.com
  master:
    replicas: 3
  volume:
    replicas: 3
    requests:
      storage: 2Gi
  filer:
    replicas: 2
    # Important: Enable persistence for the filer to store IAM metadata
    persistence:
      enabled: true
      storageClassName: standard # Use your storage class
      accessModes:
        - ReadWriteOnce
      resources:
        requests:
          storage: 2Gi
    # Important: Ensure IAM is enabled and write access is allowed
    extraArgs:
      - "-iam"
      - "-s3.iam.readOnly=false"
    s3:
      enabled: true
    iam: true
    config: |
      [leveldb2]
      enabled = true
      dir = "/data/filerldb2"
```

For more details, see the [IAM Support](https://github.com/seaweedfs/seaweedfs-operator/blob/master/IAM_SUPPORT.md) documentation in the operator repository.

## Bare-metal volume servers (DaemonSet + node-local disks)

By default the Operator runs volume servers as a `StatefulSet` backed by
dynamically-provisioned `PersistentVolumeClaim`s. On bare-metal / on-prem
clusters you often instead want **one volume server per node, writing directly
to that node's physical disks**. Set `volume.kind: DaemonSet` and list the
node-local directories in `volume.hostPath`:

```yaml
apiVersion: seaweed.seaweedfs.com/v1
kind: Seaweed
metadata:
  name: seaweed1
spec:
  image: chrislusf/seaweedfs:latest
  master:
    replicas: 3
  volume:
    kind: DaemonSet        # one volume server per matching node (replicas is ignored)
    hostPath:              # node-local data dirs, one per physical disk
      - path: /mnt/disks/ssd0
        maxVolumeCount: 100
      - path: /mnt/disks/ssd1
    nodeSelector:          # restrict to labelled storage nodes
      seaweedfs.com/storage: "true"
    tolerations:
      - key: seaweedfs.com/storage
        operator: Exists
        effect: NoSchedule
  filer:
    replicas: 1
```

Each `hostPath` entry is mounted at `/data&lt;index&gt;` and passed to
`weed volume -dir`, so a single server can span several disks; the optional
`maxVolumeCount` caps volumes per directory. `hostPath` is required in
DaemonSet mode (DaemonSets cannot use `volumeClaimTemplates`), but it also
works with the default `StatefulSet` — pair it with node anti-affinity so two
replicas never share a host directory. For rack/datacenter-aware placement
across multiple volume groups, see
[Topology Support](https://github.com/seaweedfs/seaweedfs-operator/blob/master/TOPOLOGY_SUPPORT.md).

## Scaling volume servers (graceful evacuation)

When you lower `volume.replicas` (or a `volumeTopology` group's `replicas`), the
Operator scales the volume servers down **gracefully** rather than deleting
their pods outright. Kubernetes removes the highest-ordinal pods first, so for
each volume server about to go away the Operator:

1. holds the `StatefulSet` at its current size so the doomed pod keeps serving,
2. runs `volumeServer.evacuate` to move that server's volumes and EC shards onto
   the remaining servers, and
3. deletes the pod only once the master confirms the server holds no data.

Servers drain and pods are removed one at a time, top ordinal first. If a volume
cannot be moved safely — for example a replicated volume with no
replication-compliant destination left — the evacuation fails and the
scale-down is **held** (the pod is kept) rather than risk losing data. The
Operator records `VolumeServerEvacuating` and `VolumeServerEvacuationFailed`
events on the `Seaweed` resource, so you can follow progress with
`kubectl describe seaweed &lt;name&gt;`.

This is automatic and needs no configuration, and it applies to both the flat
`volume` group and per-`volumeTopology` groups. Scaling **up** is unchanged —
new volume servers simply join the cluster.

## Declarative Buckets and IAM

Besides provisioning the cluster itself, the Operator can manage S3 buckets,
identities, credentials, and policies declaratively, so they can be GitOps-managed
(FluxCD, ArgoCD) alongside the `Seaweed` resource. These map to the same operations
as `weed shell`'s `s3.bucket.*`, `s3.user.*`, `s3.accesskey.*`, and `s3.policy*`
commands:

| CRD | Manages |
|-----|---------|
| `Bucket` | An S3 bucket (versioning, object lock, quota, owner/access, placement) |
| `S3Identity` | An IAM user |
| `S3Credentials` | An access key pair for an identity, mirrored into a Kubernetes `Secret` (generated or adopted) |
| `S3Policy` | An IAM policy (structured statements or a raw AWS-style document) |
| `S3PolicyBinding` | Attaches a policy to a set of identities |

For example, a user, a key pair stored in a Secret, a bucket, and a policy
attachment:

```yaml
apiVersion: seaweed.seaweedfs.com/v1
kind: S3Identity
metadata: { name: alice, namespace: default }
spec:
  seaweedRef: { name: seaweed1 }
---
apiVersion: seaweed.seaweedfs.com/v1
kind: S3Credentials
metadata: { name: alice-creds, namespace: default }
spec:
  seaweedRef: { name: seaweed1 }
  identityRef: { name: alice }
  secretRef: { name: alice-s3-secret }   # operator generates a key pair into this Secret
---
apiVersion: seaweed.seaweedfs.com/v1
kind: S3Policy
metadata: { name: rw-uploads, namespace: default }
spec:
  seaweedRef: { name: seaweed1 }
  statements:
    - effect: Allow
      actions: [s3:GetObject, s3:PutObject, s3:DeleteObject]
      resources: [my-bucket/uploads/*]
---
apiVersion: seaweed.seaweedfs.com/v1
kind: S3PolicyBinding
metadata: { name: alice-uploads, namespace: default }
spec:
  seaweedRef: { name: seaweed1 }
  policyRef: { name: rw-uploads }
  subjects:
    - { kind: S3Identity, name: alice }
```

These resources require the cluster's embedded IAM service to allow writes — see
the [IAM write access with persistence](#iam-configuration-example) example above.
For the full field reference, see the
[Declarative Buckets](https://github.com/seaweedfs/seaweedfs-operator#declarative-buckets)
and [Declarative IAM](https://github.com/seaweedfs/seaweedfs-operator#declarative-iam-identities-credentials-policies)
sections of the operator README.

## Mounting volumes via CSI

Besides the cluster and its S3/IAM configuration, the Operator can also deploy
the [seaweedfs-csi-driver](https://github.com/seaweedfs/seaweedfs-csi-driver) so
that pods mount a SeaweedFS filer as ordinary `PersistentVolume`s (a POSIX FUSE
mount), including `ReadWriteMany` volumes shared across nodes. This is the
filesystem alternative to the S3 API. The CSI driver is cluster infrastructure
(a controller `Deployment` plus per-node DaemonSets), not an application
sidecar — pods just request a `PersistentVolumeClaim`.

Because a CSI driver is node-global, it is managed through its own opt-in
`SeaweedCSIDriver` resource and the controller is disabled until you set
`ENABLE_CSI_DRIVER=true` on the operator:

```yaml
apiVersion: seaweed.seaweedfs.com/v1
kind: SeaweedCSIDriver
metadata:
  name: seaweedfs
spec:
  seaweedRef: { name: seaweed1 }   # or filerAddress: my-filer:8888
  storageClass:
    name: seaweedfs
    parameters:
      replication: "000"
```

For the full guide and field reference, see the
[CSI Support](https://github.com/seaweedfs/seaweedfs-operator/blob/master/CSI_SUPPORT.md)
documentation in the operator repository.

## Scheduled `weed shell` scripts (AdminScript)

The Operator can run `weed shell` administrative scripts on a cron schedule —
for recurring maintenance like `volume.balance`, `volume.fix.replication`, or
`volume.vacuum`. An `AdminScript` resource reconciles into a native Kubernetes
`CronJob` (same namespace, owned by the resource) whose pod runs
`weed shell -master=&lt;cluster masters&gt;` with the script piped to stdin. When the
referenced cluster has mTLS enabled, the job mounts the same
`security.toml`/TLS material so the shell authenticates to the masters over gRPC.

```yaml
apiVersion: seaweed.seaweedfs.com/v1
kind: AdminScript
metadata:
  name: nightly-balance
  namespace: default
spec:
  clusterRef: { name: seaweed1 }   # a Seaweed CR in the same namespace
  schedule: "0 2 * * *"            # daily at 02:00
  script: |
    lock
    volume.balance -force
    volume.fix.replication
    unlock
```

`concurrencyPolicy` defaults to `Forbid` so runs never overlap; `suspend: true`
pauses scheduling. The usual CronJob/Job knobs (`timeZone`, history limits,
`backoffLimit`, `activeDeadlineSeconds`, `resources`, scheduling) pass through.
For the full field reference, see the
[AdminScript](https://github.com/seaweedfs/seaweedfs-operator#scheduled-admin-scripts-adminscript)
section of the operator README.

> **`AdminScript` vs the [Admin Script Plugin](./Migrate-Maintenance-Scripts-to-Admin-Script-Plugin.md):**
> the `AdminScript` CRD schedules a standalone `weed shell` run as a Kubernetes
> `CronJob` — handy when you want maintenance expressed as plain, GitOps-managed
> manifests. The Admin Script Plugin instead runs maintenance on the admin
> server's `weed worker` processes with a `/plugin` UI, run history, and
> dedicated workers for erasure coding and volume balancing. If you run an admin
> server, the plugin is the richer option.

## Backup and restore

The Operator can back up a cluster's **filer metadata** as point-in-time
snapshots and continuously **mirror file data** to cloud object storage or a
PVC. Destinations, schedules, and mirrors are declared on the `Seaweed`
resource under `spec.backup`; on-demand backups and restores are separate
`SeaweedBackup` / `SeaweedRestore` resources. This maps to the underlying `weed`
primitives: a metadata snapshot is a one-shot `fs.meta.save` (restored with
`fs.meta.load`), so it is schedulable and retained; data replication is a
continuous `weed filer.backup`, so it runs as an always-on mirror `Deployment`.

```yaml
apiVersion: seaweed.seaweedfs.com/v1
kind: Seaweed
metadata:
  name: seaweed1
spec:
  image: chrislusf/seaweedfs:latest
  master: { replicas: 1 }
  volume: { replicas: 1, requests: { storage: 10Gi } }
  filer:  { replicas: 1 }
  backup:
    storages:
      s3-main:                              # an S3-compatible destination
        type: s3
        s3: { bucket: my-seaweedfs-backups, region: us-east-1 }
        credentialsSecret: s3-backup-creds  # AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
    schedule:                               # cron-driven metadata snapshots
      - name: nightly
        schedule: "0 2 * * *"
        storageName: s3-main
        keep: 7                             # retain the 7 most recent completed snapshots
    dataMirror:                             # continuous weed filer.backup to the sink
      - storageName: s3-main
---
apiVersion: seaweed.seaweedfs.com/v1
kind: SeaweedBackup                         # an on-demand metadata snapshot
metadata: { name: adhoc-1, namespace: default }
spec:
  clusterName: seaweed1
  storageName: s3-main
---
apiVersion: seaweed.seaweedfs.com/v1
kind: SeaweedRestore                        # restore a snapshot back into the cluster
metadata: { name: restore-1, namespace: default }
spec:
  clusterName: seaweed1
  backupName: adhoc-1
```

A storage can target S3, Google Cloud Storage, Azure Blob, Backblaze B2, or a
PersistentVolumeClaim (`type: filesystem`). The leader-elected scheduler creates
a `SeaweedBackup` each time a cron fires and prunes completed snapshots beyond
`keep`; restore reconstructs the filer namespace via `fs.meta.load`. When the
referenced cluster has mTLS enabled, the backup/restore jobs and the mirror
mount the same `security.toml`/TLS material. For the full field reference,
storage credential keys, and the metadata-vs-data model, see the
[Backup & Restore](https://github.com/seaweedfs/seaweedfs-operator/blob/master/BACKUP_SUPPORT.md)
documentation in the operator repository.

# Recommended: Helm Deployment

The SeaweedFS Helm chart is the most flexible and maintained way to deploy SeaweedFS on Kubernetes.

```bash
helm repo add seaweedfs https://seaweedfs.github.io/seaweedfs/helm
helm install seaweedfs seaweedfs/seaweedfs
```

For detailed configuration options, see the [Helm Chart README](https://github.com/seaweedfs/seaweedfs/tree/master/k8s/charts/seaweedfs).

# OpenShift Support

If you are deploying on **OpenShift** or any cluster with "restricted" Pod Security Standards, you must use the platform-specific overrides:

```bash
helm install seaweedfs seaweedfs/seaweedfs \
  -n seaweedfs --create-namespace \
  -f https://raw.githubusercontent.com/seaweedfs/seaweedfs/master/k8s/charts/seaweedfs/openshift-values.yaml
```

This configuration avoids `hostPath` volumes and root-owned processes, which are typically restricted on OpenShift.

# Manual Deployment (Educational)

`Kubernetes` is an open-source system for automating deployment, scaling, and management of containerized applications.

Developers normally don't setup Kubernetes locally. There is a lot of networking and operational detail to learn which could be overwhelming if one would want to stay productive and focused. Instead, Google built Minikube, which is a single node Kubernetes cluster running inside a VM. So you'll need a virtualisation infrastructure in your local dev environment. I personally use KVM on Linux which allows me to preserve the same IP for my VM between restarts.

This is a really good guideline on how to setup minikube: https://thenewstack.io/tutorial-configuring-ultimate-development-environment-kubernetes/

# Steps

The default docker image is based on alpine Linux which causes issues with the DNS addon in Minikubes (see https://github.com/seaweedfs/seaweedfs/issues/474). To get around this problem, I rebuilt the docker image from "scratch".

To do this I added (or modified) the following files to the local repository:

1. Modified the Dockerfile in the docker folder
2. Added a new bash script to build the image using the docker file
3. Added 2 yaml files to create master and volume "deployments" (which create PODs and containers)
4. Added an additional yaml file to expose both volume and master "deployments" through a "service"


## Dockerfile

The new docker file was changed to use `scratch` base image without anything but the application. You can always create different docker files for different needs. For instance, for troubleshooting purposes you could build development images containing other tools than just the application.

```dockerfile
FROM scratch
ADD weed /
ENTRYPOINT ["/weed"]
```

## Image building script

The script uses the docker file to build my image. Note the followings:
1. I'm building the application with `cgo` disabled which produces a static binary. This is why I can create the image from `scratch` without worrying about missing libraries on the operating system.
2. The image is built using the latest development code. You might want to pull the latest stable tag instead.
3. `192.168.42.23` is the IP of a private docker registry that I've setup from which the image is pulled and deployed to minikube cluster (later steps).

```bash
#!/bin/sh

go get github.com/seaweedfs/seaweedfs/weed/...
CGO_ENABLED=0 GOOS=linux go build github.com/seaweedfs/seaweedfs/weed 
docker build -t weed:latest -f ./Dockerfile .
docker tag weed:latest 192.168.42.23:80/weed:latest
docker push 192.168.42.23:80/weed:latest
rm -f weed
docker rmi $(docker images -qa -f 'dangling=true') 2>/dev/null
exit 0
```

## Yaml files

In order to deploy the docker image onto minikube in form of "pods" and "services", we need yaml files. Quickly explaining what POD and Service are:

* A POD is a group of containers that are deployed together on the same host. A given POD by default has 1 container. In this case, I have 2 PODs for master and volume containers (created through "deployment") each of which has 1 container.
* A service is a grouping of pods that are running on the cluster. In this case, I'm creating one service for both master and volume PODs.

**Create master POD**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: weedmasterdeployment
spec:
  selector:
    matchLabels:
      app: haystack
  template: # create pods using pod definition in this template
    metadata:
      labels:
        app: haystack
    spec:
      containers:
      - name: weedmaster
        image: 192.168.42.23:80/weed:latest
        args: ["-log_dir", "/var/containerdata/logs", "master", "-port", "9333", "-mdir", "/var/containerdata/haystack/master", "-ip", "haystackservice"]
        ports:
        - containerPort: 9333
        - containerPort: 19333
        volumeMounts:
        - mountPath: /var/containerdata
          name: vlm
      volumes:
      - name: vlm
        hostPath:
          path: '/data/vlm'
```

**Create volume POD**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: weedvolumedeployment
spec:
  selector:
    matchLabels:
      app: haystack
  template:
    metadata:
      labels:
        app: haystack
    spec:
      containers:
      - name: weedvol
        image: 192.168.42.23:80/weed:latest
        args: ["-log_dir", "/var/containerdata/logs", "volume", "-port", "8080", "-master", "haystackservice:9333", "-dir", "/var/containerdata/haystack/volume", "-ip", "haystackservice"]
        ports:
        - containerPort: 8080
        - containerPort: 18080
        volumeMounts:
        - mountPath: /var/containerdata
          name: vlm
      volumes:
      - name: vlm
        hostPath:
          path: '/data/vlm'
```

**Create a service exposing PODs**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: haystackservice
spec:
  selector:
    app: haystack
  ports:
  - name: mport
    protocol: TCP
    port: 9333
    nodePort: 30069
  - name: vport
    protocol: TCP
    port: 8080
    nodePort: 30070
  - name: vgport
    protocol: TCP
    port: 18080
    nodePort: 30071
  type: NodePort
```

Please note:
1. You'll need to slightly modify the yaml files that create deployments (the first 2 yaml files) if you intend to run them against an actual Kubernetes cluster. Essentially, in the `volumes` section of the yaml file, instead of using a `hostpath` you'd need to specify a `persistent volume` (`persistent volume claim` to be exact). For more information about PV and PVC see https://kubernetes.io/docs/concepts/storage/persistent-volumes/.
2. If you're however deploying the application to minikube, you'll have to make sure the `hostpath` exists in the cluster prior to deployment. `ssh` into minikube and create the folders:

```console
$ minikube ssh
$ sudo mkdir -p /data/vlm/logs && \
  sudo mkdir -p /data/vlm/haystack/master && \
  sudo mkdir  /data/vlm/haystack/volume && \
  sudo chown -R docker:root /mnt/sda1/data/
```
_`/data` is a softlink to `/mnt/sda1/data`, hence the use of full path in the last command._

## Deploy and test

You can then deploy everything using kubectl CLI tool (installed when you install minikube).

```console
$ kubectl create -f master_pod.yml
deployment "weedmasterdeployment" created
$ kubectl create -f volume_pod.yml
deployment "weedvolumedeployment" created
$ kubectl create -f service.yml
service "haystackservice" created
```

And eventually call the APIs from outside the cluster:

```
http://minikubecluster:30069/dir/assign
curl -F file=@/home/amir/Downloads/hardhat.png http://minikubecluster:30070/2,0333d4fea4
http://minikubecluster:30070/2,0333d4fea4
http://minikubecluster:30070/ui/index.html
```

`minikubecluster` in my environment resolves to the IP address of the minikube's VM which you can get using `minikube ip` command.
The port numbers in these commands are the `node ports` defined as part of the service spec which map to the internal container ports and to which they forward all the requests. For more information about Node Ports see https://kubernetes.io/docs/concepts/services-networking/service/#type-nodeport.
