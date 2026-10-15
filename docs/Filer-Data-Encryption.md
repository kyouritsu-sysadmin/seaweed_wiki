---
id: Filer-Data-Encryption
title: "Filer Data Encryption"
sidebar_label: "Filer Data Encryption"
---


For filer,
* The metadata is stored in filer store.
* The actual data is stored in volume servers.

However, there could be many volume servers. And the volumes may be tiered to the cloud. What if some of them are hacked?

### Encrypt data on volume servers
`weed filer -encryptVolumeData` is an option to encrypt the data on volume servers. 

The encryption keys are randomly generated during write time, and are different for different files. The encryption keys are stored as metadata in filer store.

So the volume data on the volume servers are encrypted. As long as the filer store is not exposed, it is nearly impossible to guess the encryption keys for all the files.

### Safe Data Storage
Actually the volume servers do not have any concept of encryption. The encrypted data blocks are treated just as any other data blocks. The volume servers are not visible to any unencrypted data, for either storage or transmission. With the file content encrypted, it is safe to put volume servers any where you want. 

### Safely Forget Data
Another side is, with GDPR, companies are required to "forget" customer data after some time. If the volume data is stored on a glacial storage system, it is cumbersome to dig them out and destroy them. It is much easier to just delete the metadata, and the volume data is automatically "destroyed".

### Encryption Algorithm
The encryption is through AES256-GCM https://en.wikipedia.org/wiki/Galois/Counter_Mode

There is one randomly generated cipher key of 256 bits for each file chunk. The cipher code is here https://github.com/seaweedfs/seaweedfs/blob/master/weed/util/cipher.go
