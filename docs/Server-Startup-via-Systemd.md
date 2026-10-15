---
id: Server-Startup-via-Systemd
title: "Server Startup via Systemd"
sidebar_label: "Server Startup via Systemd"
---

This is a sample setup to run the services using Systemd.

It involves:
1. Creating a service file (.service) in */etc/systemd/system/*
2. Enabling it


# Master Server

1. Create the service file:

```shell
sudo nano /etc/systemd/system/seaweedmaster.service
```

2. Insert the following text

```
[Unit]
Description=SeaweedFS Server
After=network.target

[Service]
Type=simple
User=root
Group=root

ExecStart=/usr/local/bin/weed master -ip=192.168.1.31
WorkingDirectory=/usr/local/bin
SyslogIdentifier=seaweedfs-master

[Install]
WantedBy=multi-user.target
```
3. Start it and enable it

```
systemctl start seaweedmaster.service
systemctl enable seaweedmaster.service
```
# Volume Server

1. Create the service file:

```shell
sudo nano /etc/systemd/system/seaweedvolume.service
```

2. Insert the following text

```
[Unit]
Description=SeaweedFS Volume
After=network.target media-jmn-LENOVO.mount

[Service]
Type=simple
User=root
Group=root
ExecStartPre=/bin/sleep 30

ExecStart=/usr/local/bin/weed volume -dir="/media/jmn/HDD/SeaweedFS"
WorkingDirectory=/usr/local/bin/
SyslogIdentifier=seaweedfs-volume

[Install]
WantedBy=multi-user.target
```

- Please, notice how I'm introducing a delay here for the mount to become available. Replace -dir= by your own directory for the Volume Server.:
- Also, please notice that I'm using "After" for the .mount file related with the directory I want the Volume Server to use. This won't be necessary if your data directory doesn't need to be mounted.

3. Start it and enable it

```
systemctl start seaweedvolume.service
systemctl enable seaweedvolume.service
```

# Filer

1. Create the service file:

```shell
sudo nano /etc/systemd/system/seaweedfiler.service
```

2. Insert the following text

```
[Unit]
Description=SeaweedFS Filer
After=network.target media-jmn-LENOVO.mount

[Service]
Type=simple
User=root
Group=root
ExecStartPre=/bin/sleep 30
ExecReload=/bin/kill -HUP $MAINPID

ExecStart=/usr/local/bin/weed filer
WorkingDirectory=/media/jmn/HDD/
SyslogIdentifier=seaweedfs-filer

[Install]
WantedBy=multi-user.target

```

- Please, notice how I'm introducing a delay here for the mounted partition to become available. 
- Also, please notice that I'm using "After" for the .mount file related with the directory I want the Filer to use. This won't be necessary if your data directory doesn't need to be mounted.
- Keep in mind that I'm setting the **WorkingDirectory** to a directory in my HDD and that has a filer.toml inside it with my desired configuration.

3. Start it and enabled it

```
systemctl start seaweedfiler.service
systemctl enable seaweedfiler.service
```


