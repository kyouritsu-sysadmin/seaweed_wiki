---
id: nodejs-with-Seaweed-S3
title: "nodejs with Seaweed S3"
sidebar_label: "nodejs with Seaweed S3"
---

### Requirements & features
- Use `node@12.0.0+`
- Code with `javascript` or `typescript`
- Seaweedfs with `-s3` running at `:8333`

### Installation
Install [AWS S3 client](https://www.npmjs.com/package/@aws-sdk/client-s3)
```bash
npm i @aws-sdk/client-s3
```

### Client initialization
```javascript
import { S3Client } from "@aws-sdk/client-s3"

const s3client = new S3Client({
  // specify endpoint with http://hostname:port
  endpoint: `http://127.0.0.1:8333`,
  // specify region since it is mandatory, but it will be ignored by seaweedfs
  region: `us-east-1`, 
  // force path style for compatibility reasons
  forcePathStyle: true,
  // dual stack endpoint is not supported by seaweed
  useDualstackEndpoint: false,
  // checksum validation should be disabled, overwise `x-amz-checksum` will be injected directly into files
  responseChecksumValidation: `WHEN_REQUIRED`,
  requestChecksumCalculation: 'WHEN_REQUIRED',
  // credentials is mandatory and s3 authorization should be enabled with `s3.configure`
  credentials: {
    accessKeyId: `same as -accesskey`,
    secretAccessKey: `same as -secretkey`,
  }
})
```

### Execute commands

```javascript
// List buckets example
import { ListBucketsCommand } from "@aws-sdk/client-s3"
const response = await s3client.send(new ListBucketsCommand({}))
console.log(response.Buckets)
```
More commands: [API Reference](https://docs.aws.amazon.com/AWSJavaScriptSDK/v3/latest/clients/client-s3/index.html)

