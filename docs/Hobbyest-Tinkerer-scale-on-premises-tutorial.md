---
id: Hobbyest-Tinkerer-scale-on-premises-tutorial
title: "Hobbyest Tinkerer scale on premises tutorial"
sidebar_label: "Hobbyest Tinkerer scale on premises tutorial"
---

Creating a hobbyist-scale storage network with heterogeneous commodity hardware is an exciting project that allows you to repurpose existing hardware resources, learn about distributed systems, and gain hands-on experience with networked storage solutions. This tutorial will guide you through the motivation behind building such a network, choosing appropriate hardware, configuring your environment, and operating the network using Ubuntu and SeaweedFS, a simple and highly scalable distributed file system.

### Motivation

1. **Cost Efficiency**: Utilizing heterogeneous commodity hardware allows for cost savings, as you can use existing or second-hand equipment rather than investing in expensive, purpose-built storage solutions.
2. **Learning and Experimentation**: Building and managing a storage network provides invaluable hands-on experience with networked storage, distributed systems, and software-defined storage solutions.
3. **Scalability and Flexibility**: A distributed file system like SeaweedFS enables you to scale out your storage capacity and performance by simply adding more nodes to the network.
4. **Data Redundancy and Availability**: Implementing a storage network can improve data redundancy, fault tolerance, and availability, protecting against data loss and ensuring that data is accessible when needed.

### Hardware Choices

1. **Computers**: You can use any mix of desktops, laptops, or even single-board computers like Raspberry Pis. The key is network connectivity and sufficient storage (HDD or SSD) capacity.  A reasonable choice for a storage node is a desktop using last generation technology.  I have found the Ryzen 5600G to be a nice mixture of cheap, fast and low power.  Power consumption is an important factor, as your storage will be on all the time.  A $600 system made I made from new parts measures just 20W at the wall socket when idle, yet can easily saturate a typical network.
2. **Storage Media**: Depending on your needs, you can use HDDs for larger, but slower, storage or SSDs for faster access. Ensure there's enough storage capacity for your needs.  It's helpful to have some idea of what access patterns you expect, as well as your willingness to accept data loss vs dollars.  A mixture of drive brands and ages is a good hedge against cascading failures.  The append-only nature of SeaweedFS is well aligned with the write characteristics of modern shingled and stacked hdds.
3. **Networking Equipment**: A reliable gigabit router and switches, plus enough Ethernet cables, are essential for connecting your hardware and ensuring good network performance.  A flaky network can lead to hard to debug errors as well as data loss.

### Configuration

#### Preparing Ubuntu

1. **Install Ubuntu**: Install Ubuntu Server on each of your hardware nodes. Ubuntu Server is preferred for its stability, large community support and lack of graphical interface, saving system resources for storage services.  Weed has been well tested on Ubuntu LTS releases.
2. **Network Configuration**: Configure static IP addresses for each node to ensure consistent network communication. You can do this by editing the `/etc/netplan/01-netcfg.yaml` file.
3. **Update and Upgrade**: Run `sudo apt update && sudo apt upgrade` to ensure all packages are up to date.

#### Installing SeaweedFS

1. **Download SeaweedFS**: Visit the [SeaweedFS GitHub releases page](https://github.com/chrislusf/seaweedfs/releases) and download the latest version of SeaweedFS for Linux.
2. **Extract and Install**: Extract the downloaded file and move the SeaweedFS binaries to a location in your system's PATH, such as `/usr/local/bin`.

### Operations

#### Starting the Master Server

1. Choose one node to act as the master server. This node will manage the metadata.
2. Start the master server with:
   ```
   weed master -ip=master_node_IP -mdir=/var/lib/seaweedfs/master -defaultReplication=001
   ```
   Replace `master_node_IP` with the IP address of your master node.  This will require all writes to be written to any two drives by default.  We will look at using erasure codes to increase reliability, but 2x writes is a reasonable starting point.

#### Starting Volume Servers

1. On each storage node, start a volume server that connects to the master:
   ```
   weed volume -master=master_node_IP:9333 -port=8080 -dir=/data1/seaweedfs/volume
   ```
   Adjust the directory as needed for your setup.  I typically have data drives mounted with a consistent naming strategy and separate from the operating system storage.

#### Storing and Accessing Data

- **Storing Data**: Use the `weed` command to store files. For example:
  ```
  weed upload -master=master_node_IP:9333 file_to_upload
  ```
- **Accessing Data**: Access files through the HTTP interface provided by SeaweedFS or through the file system mount.

### Conclusion

By following these steps, you've set up a scalable, flexible, and cost-efficient storage network using heterogeneous commodity hardware, Ubuntu, and SeaweedFS. This setup allows for learning and experimentation with distributed storage systems, providing a foundation that can be expanded or modified to suit your evolving needs. Remember, the configuration and operations can vary based on your specific hardware and network setup, so consider this guide a starting point for your customized storage solution.