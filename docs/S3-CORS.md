---
id: S3-CORS
title: "S3 CORS"
sidebar_label: "S3 CORS"
---

# S3 Cross-Origin Resource Sharing (CORS)

SeaweedFS supports S3-compatible Cross-Origin Resource Sharing (CORS) configuration, allowing web applications to make cross-origin requests to your S3 buckets. CORS is essential for web applications that need to access resources from different domains.

## Overview

CORS defines a way for web applications running at one domain to access resources at another domain. When a web application tries to access your S3 bucket from a different domain, the browser will first send a preflight OPTIONS request to check if the cross-origin request is allowed.

SeaweedFS handles CORS through:
- **Global CORS configuration**: Server-wide default CORS settings
- **Bucket-level CORS configuration**: Each bucket can have its own CORS rules
- **Persistent storage**: CORS configurations are stored in bucket metadata
- **Automatic header handling**: CORS middleware automatically applies appropriate headers
- **Preflight request support**: Proper handling of OPTIONS requests

## Quick Start: Global CORS Configuration

The simplest way to enable CORS for all buckets is using the `-s3.allowedOrigins` parameter:

```bash
# Allow all origins (useful for development)
weed server -s3 -s3.allowedOrigins=*

# Allow specific origins
weed server -s3 -s3.allowedOrigins=https://app.example.com,https://admin.example.com

# Docker Compose example
services:
  seaweedfs:
    image: chrislusf/seaweedfs:latest
    command: "server -s3 -s3.allowedOrigins=*"
```

This global configuration:
- Works immediately without additional setup
- Applies to all buckets by default
- Can be overridden by bucket-level CORS configuration
- Supports GET, PUT, POST, DELETE, and HEAD methods
- Allows all headers (*)

### CORS Configuration Priority

SeaweedFS uses the following priority order:

1. **Bucket-level CORS** (if configured via `aws --endpoint-url $S3_ENDPOINT s3api put-bucket-cors`) - highest priority
2. **Global CORS** (from `-s3.allowedOrigins` parameter) - fallback if no bucket config
3. **No CORS** (if neither is configured) - no CORS headers applied

This means you can set a permissive global default and override it with stricter rules for specific buckets.

## Advanced: Bucket-Level CORS Configuration

### Basic CORS Rule Structure

A CORS configuration consists of one or more CORS rules. Each rule defines:

```xml
<CORSConfiguration>
    <CORSRule>
        <ID>rule-id</ID>
        <AllowedOrigin>http://example.com</AllowedOrigin>
        <AllowedMethod>GET</AllowedMethod>
        <AllowedMethod>POST</AllowedMethod>
        <AllowedHeader>Content-Type</AllowedHeader>
        <ExposeHeader>ETag</ExposeHeader>
        <MaxAgeSeconds>3600</MaxAgeSeconds>
    </CORSRule>
</CORSConfiguration>
```

### CORS Rule Elements

- **ID** (optional): A unique identifier for the rule
- **AllowedOrigin** (required): Specifies which origins are allowed to access the bucket
- **AllowedMethod** (required): HTTP methods that are allowed (GET, PUT, POST, DELETE, HEAD)
  - **Note**: Do NOT include `OPTIONS` in AllowedMethods - it is automatically handled for preflight requests
- **AllowedHeader** (optional): Headers that are allowed in the actual request
- **ExposeHeader** (optional): Headers that browsers can access from the response
- **MaxAgeSeconds** (optional): How long browsers can cache the preflight response

## Managing CORS Configuration

### Set CORS Configuration

Use the `PutBucketCors` API to set CORS configuration for a bucket:

```bash
# Ensure $S3_ENDPOINT is set (e.g., export S3_ENDPOINT=http://localhost:8333)
aws --endpoint-url $S3_ENDPOINT s3api put-bucket-cors \
    --bucket my-bucket \
    --cors-configuration file://cors-config.json
```

Example `cors-config.json`:
```json
{
    "CORSRules": [
        {
            "ID": "allow-all-origins",
            "AllowedOrigins": ["*"],
            "AllowedMethods": ["GET", "POST", "PUT", "DELETE", "HEAD"],
            "AllowedHeaders": ["*"],
            "ExposeHeaders": ["ETag", "x-amz-version-id"],
            "MaxAgeSeconds": 3600
        }
    ]
}
```

### Get CORS Configuration

Retrieve the current CORS configuration for a bucket:

```bash
aws --endpoint-url $S3_ENDPOINT s3api get-bucket-cors --bucket my-bucket
```

Response:
```json
{
    "CORSRules": [
        {
            "ID": "allow-all-origins",
            "AllowedOrigins": ["*"],
            "AllowedMethods": ["GET", "POST", "PUT", "DELETE", "HEAD"],
            "AllowedHeaders": ["*"],
            "ExposeHeaders": ["ETag", "x-amz-version-id"],
            "MaxAgeSeconds": 3600
        }
    ]
}
```

### Delete CORS Configuration

Remove CORS configuration from a bucket:

```bash
aws --endpoint-url $S3_ENDPOINT s3api delete-bucket-cors --bucket my-bucket
```

## CORS Rule Examples

### Example 1: Allow Specific Domain

```json
{
    "CORSRules": [
        {
            "ID": "allow-example-domain",
            "AllowedOrigins": ["https://example.com"],
            "AllowedMethods": ["GET", "POST"],
            "AllowedHeaders": ["Content-Type", "Authorization"],
            "ExposeHeaders": ["ETag"],
            "MaxAgeSeconds": 1800
        }
    ]
}
```

### Example 2: Allow Multiple Domains

```json
{
    "CORSRules": [
        {
            "ID": "allow-multiple-domains",
            "AllowedOrigins": [
                "https://app.example.com",
                "https://staging.example.com",
                "https://localhost:3000"
            ],
            "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
            "AllowedHeaders": ["*"],
            "ExposeHeaders": ["ETag", "x-amz-version-id"],
            "MaxAgeSeconds": 3600
        }
    ]
}
```

### Example 3: Wildcard Domain Support

```json
{
    "CORSRules": [
        {
            "ID": "allow-subdomain-wildcard",
            "AllowedOrigins": ["https://*.example.com"],
            "AllowedMethods": ["GET", "POST"],
            "AllowedHeaders": ["Content-Type"],
            "MaxAgeSeconds": 1800
        }
    ]
}
```

### Example 4: Multiple Rules

```json
{
    "CORSRules": [
        {
            "ID": "read-only-rule",
            "AllowedOrigins": ["*"],
            "AllowedMethods": ["GET", "HEAD"],
            "AllowedHeaders": ["*"],
            "MaxAgeSeconds": 3600
        },
        {
            "ID": "write-rule",
            "AllowedOrigins": ["https://admin.example.com"],
            "AllowedMethods": ["PUT", "POST", "DELETE"],
            "AllowedHeaders": ["Content-Type", "Authorization"],
            "ExposeHeaders": ["ETag"],
            "MaxAgeSeconds": 1800
        }
    ]
}
```

## Web Application Integration

### JavaScript Example

```javascript
// Configure your S3 client
const AWS = require('aws-sdk');
const s3 = new AWS.S3({
    accessKeyId: 'your-access-key',
    secretAccessKey: 'your-secret-key',
    endpoint: 'http://localhost:8333',
    s3ForcePathStyle: true,
    region: 'us-east-1'
});

// Upload file from web application
const uploadFile = async (file, bucket, key) => {
    const params = {
        Bucket: bucket,
        Key: key,
        Body: file,
        ContentType: file.type
    };

    try {
        const result = await s3.upload(params).promise();
        console.log('Upload successful:', result);
        return result;
    } catch (error) {
        console.error('Upload failed:', error);
        throw error;
    }
};

// Download file from web application
const downloadFile = async (bucket, key) => {
    const params = {
        Bucket: bucket,
        Key: key
    };

    try {
        const result = await s3.getObject(params).promise();
        return result.Body;
    } catch (error) {
        console.error('Download failed:', error);
        throw error;
    }
};
```

### HTML Upload Form Example

```html
<!DOCTYPE html>
<html>
<head>
    <title>S3 Upload Example</title>
</head>
<body>
    <input type="file" id="fileInput" />
    <button onclick="uploadFile()">Upload</button>
    
    <script>
        async function uploadFile() {
            const fileInput = document.getElementById('fileInput');
            const file = fileInput.files[0];
            
            if (!file) {
                alert('Please select a file');
                return;
            }
            
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const response = await fetch('http://localhost:8333/my-bucket/' + file.name, {
                    method: 'PUT',
                    body: file,
                    headers: {
                        'Content-Type': file.type
                    }
                });
                
                if (response.ok) {
                    alert('Upload successful!');
                } else {
                    alert('Upload failed: ' + response.statusText);
                }
            } catch (error) {
                alert('Upload error: ' + error.message);
            }
        }
    </script>
</body>
</html>
```

## CORS Rule Evaluation

SeaweedFS evaluates CORS rules in the following order:

1. **Rule Matching**: The first rule that matches the request origin is used
2. **Origin Validation**: Check if the request origin matches any `AllowedOrigin`
3. **Method Validation**: For preflight requests, validate the requested method
4. **Header Validation**: For preflight requests, validate all requested headers
5. **Response Building**: Build appropriate CORS headers based on the matched rule

### Preflight Request Handling

For preflight requests (OPTIONS method), SeaweedFS:

1. Checks if the origin matches an allowed origin
2. Validates the requested method against allowed methods
3. Validates all requested headers against allowed headers
4. Returns appropriate CORS headers if all validations pass
5. Returns 403 Forbidden if any validation fails

### Actual Request Handling

For actual requests (GET, POST, PUT, DELETE, etc.), SeaweedFS:

1. Checks if the origin matches an allowed origin
2. Validates the request method against allowed methods
3. Applies appropriate CORS headers to the response
4. Continues with normal request processing

## Performance and Caching

### CORS Configuration Caching

- CORS configurations are cached in memory for 5 minutes
- Cache is automatically invalidated when configuration changes
- Multiple S3 nodes share the same cached configuration

### Browser Caching

- Use `MaxAgeSeconds` to control how long browsers cache preflight responses
- Longer cache times reduce preflight requests but delay configuration changes
- Recommended values: 1800-3600 seconds (30-60 minutes)

## Security Considerations

### Origin Validation

- Never use `*` for `AllowedOrigin` in production unless absolutely necessary
- Specify exact domains or use specific wildcard patterns
- Validate all origins against your application's requirements

### Method Restrictions

- Only allow necessary HTTP methods
- Restrict write operations (PUT, POST, DELETE) to trusted origins
- Consider separate rules for read-only vs. write operations

### Header Security

- Avoid using `*` for `AllowedHeaders` in production
- Only allow headers that your application actually needs
- Be cautious with authorization headers

## Troubleshooting

### Common Issues

1. **Invalid HTTP method: OPTIONS**: Do NOT include `OPTIONS` in `AllowedMethods` - it is automatically handled for CORS preflight requests. Only use: GET, PUT, POST, DELETE, HEAD
2. **CORS policy error**: Check that your origin is listed in `AllowedOrigins`
3. **Method not allowed**: Ensure the HTTP method is in `AllowedMethods`
4. **Header blocked**: Add required headers to `AllowedHeaders`
5. **Preflight failure**: Verify all preflight requirements are met

### Debugging Tips

- Use browser developer tools to inspect CORS headers
- Check server logs for CORS-related errors
- Test with simple requests first, then add complexity
- Verify bucket-level CORS configuration is correct

### Testing CORS Configuration

```bash
# Test preflight request
curl -X OPTIONS \
  -H "Origin: https://example.com" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Content-Type" \
  http://localhost:8333/my-bucket/test-object

# Test actual request
curl -X GET \
  -H "Origin: https://example.com" \
  http://localhost:8333/my-bucket/test-object
```

## Limitations

- Maximum 100 CORS rules per bucket
- Wildcard support is limited to `*` character
- Complex regex patterns in origins are not supported
- CORS configuration is per-bucket, not per-object

## Best Practices

1. **Specify exact origins** instead of using wildcards when possible
2. **Use appropriate MaxAgeSeconds** to balance performance and flexibility
3. **Implement proper error handling** in your web applications
4. **Test CORS configuration thoroughly** before deploying to production
5. **Monitor CORS usage** and adjust rules as needed
6. **Keep CORS rules simple** and well-documented
7. **Use separate rules** for different access patterns (read vs. write) 