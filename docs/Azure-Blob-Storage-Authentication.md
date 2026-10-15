---
id: Azure-Blob-Storage-Authentication
title: "Azure Blob Storage Authentication"
sidebar_label: "Azure Blob Storage Authentication"
---

SeaweedFS reaches Azure Blob Storage from two places, and both authenticate the same way:

* the backup sink, `[sink.azure]` in `replication.toml`, used by `weed filer.backup` — see [Async Backup](./Async-Backup.md)
* remote storage, `remote.configure -type=azure` — see [Configure Remote Storage](./Configure-Remote-Storage.md)

There are two ways to authenticate: a storage account key, or Entra ID.

# Storage account key

The original method. Give the account name and one of its access keys:

```toml
[sink.azure]
enabled = true
account_name = "myaccount"
account_key = "base64key=="
container = "mycontainer"
directory = "/"
```

```
> remote.configure -name=cloud3 -type=azure -azure.account_name=myaccount -azure.account_key=base64key==
```

Remote storage also reads `AZURE_STORAGE_ACCOUNT` and `AZURE_STORAGE_ACCESS_KEY` from the environment when the configuration leaves them out. The sink does not; it only reads `replication.toml`.

Account keys are account-wide and grant full control, so they have to be distributed to every process that backs up, and rotated everywhere at once. Entra ID avoids that.

# Entra ID

Leave `account_key` empty and SeaweedFS authenticates through the Azure identity chain instead, granting access by RBAC role rather than by key. The chain tries, in order: credentials in the environment, a workload identity, a managed identity, then a developer login such as `az login`.

```toml
[sink.azure]
enabled = true
account_name = "myaccount"
account_key = ""
container = "mycontainer"
directory = "/"
```

```
> remote.configure -name=cloud3 -type=azure -azure.account_name=myaccount
```

The identity needs a data-plane role on the container or the account. **Storage Blob Data Contributor** covers the backup sink and read-write remote storage; **Storage Blob Data Reader** is enough for a read-only mount. Owner and Contributor are control-plane roles and do not by themselves grant access to blob data.

## Workload identity on Kubernetes

This is the usual setup for a fleet: no secret is mounted anywhere, and nothing has to be rotated. Label the pod for the Azure workload identity webhook and the webhook projects `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_AUTHORITY_HOST` and a federated token file into the container. SeaweedFS picks them up on its own, so `account_name` stays the only Azure setting.

```yaml
spec:
  serviceAccountName: seaweedfs
  template:
    metadata:
      labels:
        azure.workload.identity/use: "true"
```

The service account carries the identity:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: seaweedfs
  annotations:
    azure.workload.identity/client-id: 11111111-1111-1111-1111-111111111111
```

The federated credential on the Entra application has to trust that service account, and the managed identity needs the storage role above. This works the same on Azure Arc-enabled clusters as it does on AKS.

## Managed identity on a VM

On a VM or a VM scale set with a system-assigned identity, an empty `account_key` is again all that is needed. When the host carries more than one user-assigned identity, name the one to use:

```toml
account_key = ""
client_id = "11111111-1111-1111-1111-111111111111"
```

```
> remote.configure -name=cloud3 -type=azure -azure.account_name=myaccount -azure.client_id=11111111-1111-1111-1111-111111111111
```

`client_id` also pins the identity for workload identity, where it overrides the client id the webhook projected. Setting it tells remote storage that Entra ID is intended, so `AZURE_STORAGE_ACCESS_KEY` in the environment is then ignored rather than quietly taking the request back to shared key auth.

# Troubleshooting

A missing role shows up as `AuthorizationPermissionMismatch` or `403` on the first blob operation, not at startup. Check that the role is assigned to the identity that actually authenticated, and that it is a Storage Blob Data role.

`no tenant ID specified` or `no client ID specified` means workload identity was selected but the environment is incomplete — usually the pod is missing the `azure.workload.identity/use` label, so the webhook never projected anything.

`ManagedIdentityCredential authentication failed` on a host with no managed identity means the chain reached the end without finding one. Either assign an identity to the host, or go back to an account key.

Entra ID logs a line when it is selected. The glog flags are global, so they go before the subcommand: `weed -v=1 filer.backup`.

# Limitations

The blob service url is `https://&lt;account_name&gt;.blob.core.windows.net/`, so Azure Government, Azure China and private endpoints are not reachable yet.
