---
id: Hardware
title: "Hardware"
sidebar_label: "Hardware"
---

This is a page for actual hardware used.

# From Aaron: 37 PiB raw storage

Currently, we are operating a cluster with 14 1U servers. Each server has two Seagate 5U 84-Bay SAS JBOD enclosures attached that are populated with 18TB 7.2k RPM drives. This yields about 37 PiB of raw capacity. Initially, the servers were deployed having one volume service per drive but was later changed to using a simple RAID 0 across 4 drives to improve edge cases around single threaded throughput which dramatically improved rebuilding and moving of volume files.

Everything is protected with `replication=010` and currently not leveraging erasure coding since it does not currently _(2023-01-18)_ support ensuring multiple fragments are stored on separate physical servers.

The cluster has experienced multiple drives fail across without any impacts. The biggest issue encountered to date is that cluster maintenance tasks like `volume.fix.replication`, `volume.check.disk`, `volume.vacuum`, etc. are only executed against a single volume file at a once and this results in very long times to complete across the cluster.


Details about the Seagate 5U 84-bay SAS JBOD enclosures can be found at [https://www.seagate.com/products/storage/data-storage-systems/jbod/exos-e-5u84/](https://www.seagate.com/products/storage/data-storage-systems/jbod/exos-e-5u84/)