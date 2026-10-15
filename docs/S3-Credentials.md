---
id: S3-Credentials
title: "S3 Credentials"
sidebar_label: "S3 Credentials"
---

# S3 Credentials

> **This page covers basic S3 credentials** using the `-s3.config` / `-config` option.
> 
> For advanced IAM features (OIDC, STS, IAM policies), see [OIDC Integration](./OIDC-Integration.md) which uses the `-s3.iam.config` / `-iam.config` option.
>
> For a comparison of both options, see [S3 Configuration](./S3-Configuration.md).

---

SeaweedFS S3 API supports multiple authentication methods with a clear priority system. This page explains how to configure S3 credentials for your SeaweedFS setup.

## Authentication Methods

### 1. Configuration File (Highest Priority)

Create a JSON configuration file and use the `-config` option:

```json
{
  "identities": [
    {
      "name": "admin_user",
      "credentials": [
        {
          "accessKey": "admin_access_key",
          "secretKey": "admin_secret_key"
        }
      ],
      "actions": ["Admin", "Read", "Write"]
    },
    {
      "name": "read_only_user",
      "credentials": [
        {
          "accessKey": "readonly_access_key",
          "secretKey": "readonly_secret_key"
        }
      ],
      "actions": ["Read"]
    }
  ]
}
```

Start S3 server with config file:
```bash
weed s3 -config=/path/to/s3.json -filer=localhost:8888
```

### 2. Filer Configuration (Medium Priority)

Store configuration in the filer using the credential manager. This allows dynamic configuration updates without restarting the S3 server.

### 3. Admin UI (Web Interface)

Use the SeaweedFS Admin UI to manage S3 credentials through a web interface:

```bash
# Start the admin interface (separate from filer)
weed admin -masters=localhost:9333

# Access the admin UI (default port 23646)
http://localhost:23646
```

Navigate to **Object Store → Users** (`/object-store/users`) to:
- **Create Users**: Add new S3 users with email and permissions
- **Edit Permissions**: Modify existing user access levels
- **Manage Access Keys**: Generate and delete access key pairs
- **View User Details**: Check user activity and current permissions

The Admin UI stores credentials in the filer using the same filer configuration method, so changes are automatically synchronized across all S3 servers connected to the same filer.

### 4. Environment Variables (Fallback)

Use AWS standard environment variables as a fallback when no other configuration is available:

```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export S3_ENDPOINT=http://localhost:8333
weed s3 -filer=localhost:8888
```

**Important**: Environment variables are only used when:
- No `-config` option is provided
- No configuration is available from the filer
- Both `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are set

## Priority System

SeaweedFS uses the following priority order for S3 credentials:

1. **Configuration File** (if `-config` option is provided)
2. **Filer Configuration** (if available and no config file)
3. **Admin UI** (web interface that stores in filer configuration)
4. **Environment Variables** (fallback only)

Higher priority methods completely override lower priority methods - there is no merging or supplementing.

**Important**: Admin UI and Filer Configuration both use the same underlying storage (filer), so they have the same effective priority. The Admin UI provides a user-friendly interface for managing what is stored as filer configuration.

## Configuration Examples

### Production Setup
```bash
# Use dedicated configuration file
weed s3 -config=/etc/seaweedfs/s3.json -filer=filer1:8888,filer2:8888
```

### Development Setup
```bash
# Use environment variables for quick setup
export AWS_ACCESS_KEY_ID=dev_access_key
export AWS_SECRET_ACCESS_KEY=dev_secret_key
weed s3 -filer=localhost:8888
```

### Docker Compose
```yaml
version: '3.9'
services:
  s3:
    image: chrislusf/seaweedfs:latest
    ports:
      - 8333:8333
    environment:
      AWS_ACCESS_KEY_ID: s3admin
      AWS_SECRET_ACCESS_KEY: s3secret
    entrypoint: weed
    command: s3 -filer=filer:8888
    depends_on:
      - filer
```

## Credential Features

### Actions
Identities can have different permission levels:
- `Admin`: Full access to all S3 operations
- `Read`: Read-only access
- `Write`: Read and write access
- `Read_ACP`: Read access control permissions
- `Write_ACP`: Write access control permissions

### Multiple Credentials
Each identity can have multiple access key/secret key pairs:

```json
{
  "name": "multi_key_user",
  "credentials": [
    {
      "accessKey": "key1",
      "secretKey": "secret1"
    },
    {
      "accessKey": "key2", 
      "secretKey": "secret2"
    }
  ],
  "actions": ["Read", "Write"]
}
```

### Account Management
Identities can be associated with accounts for better organization and cross-account access control.

## Bucket-Specific Permissions

SeaweedFS supports restricting user access to specific buckets using bucket-scoped actions. This allows you to create users who have full access to one bucket but no access to other buckets.

### Single Bucket Full Access

To create a user with full access to only one specific bucket, use bucket-scoped actions:

```json
{
  "identities": [
    {
      "name": "bucket1_user",
      "credentials": [
        {
          "accessKey": "bucket1_access_key",
          "secretKey": "bucket1_secret_key"
        }
      ],
      "actions": [
        "Read:mybucket",
        "Write:mybucket",
        "List:mybucket",
        "Tagging:mybucket",
        "Admin:mybucket"
      ]
    }
  ]
}
```

This user can:
- ✅ Read, write, list, and tag objects in `mybucket`
- ✅ Create and delete objects in `mybucket`
- ✅ Manage bucket settings for `mybucket`
- ❌ Access any other buckets
- ❌ Create new buckets (requires global Admin action)

### Bucket-Specific Actions

Actions can be scoped to specific buckets using the format `Action:BucketName`:

| Action Format | Description | Example |
|--------------|-------------|---------|
| `Read:bucket1` | Read access to bucket1 only | Get objects from bucket1 |
| `Write:bucket1` | Write access to bucket1 only | Put/delete objects in bucket1 |
| `List:bucket1` | List access to bucket1 only | List objects in bucket1 |
| `Admin:bucket1` | Admin access to bucket1 only | Bucket management for bucket1 |
| `Tagging:bucket1` | Tagging access to bucket1 only | Manage object tags in bucket1 |

### Multiple Bucket Access

Users can have access to multiple specific buckets:

```json
{
  "name": "multi_bucket_user",
  "credentials": [{"accessKey": "key", "secretKey": "secret"}],
  "actions": [
    "Read:bucket1",
    "Write:bucket1",
    "List:bucket1",
    "Read:bucket2",
    "List:bucket2"
  ]
}
```

This user has:
- Full read/write access to `bucket1`
- Read-only access to `bucket2`
- No access to any other buckets

### Wildcard Support

SeaweedFS supports wildcard patterns for flexible bucket access:

```json
{
  "name": "prefix_user",
  "credentials": [{"accessKey": "key", "secretKey": "secret"}],
  "actions": [
    "Read:user-*",
    "Write:user-*",
    "List:user-*"
  ]
}
```

This user can access all buckets starting with `user-` (like `user-data`, `user-logs`, etc.).

### Object-Level Permissions

You can restrict access to specific paths within a bucket:

```json
{
  "name": "path_limited_user",
  "credentials": [{"accessKey": "key", "secretKey": "secret"}],
  "actions": [
    "Read:mybucket/uploads/*",
    "Write:mybucket/uploads/*",
    "List:mybucket"
  ]
}
```

This user can:
- Only read/write objects under `mybucket/uploads/` path
- List the bucket to see the directory structure
- Cannot access objects in other paths within the bucket

### Configuration Methods

Bucket-specific permissions work with all configuration methods:

#### Dynamic Configuration (weed shell)
```bash
# One-step: create user with a readwrite policy for a specific bucket
s3.user.provision -name bucket1_user -bucket mybucket -role readwrite

# Grant the same user access to another bucket (skips user creation, attaches policy)
s3.user.provision -name bucket1_user -bucket otherbucket -role readonly

# Or step-by-step:
s3.user.create -name bucket1_user
s3.policy -put -name mybucket-policy -file mybucket-policy.json
s3.policy.attach -policy mybucket-policy -user bucket1_user
```

#### Static Configuration File
Use the JSON examples shown above in your configuration file.

#### Admin UI
1. Navigate to **Object Store → Users**
2. Create a new user
3. In the permissions section, specify bucket-scoped actions like `Read:mybucket`

#### Kubernetes (SeaweedFS Operator)
On Kubernetes, the [SeaweedFS Operator](https://github.com/seaweedfs/seaweedfs-operator)
exposes these same operations as declarative custom resources — `S3Identity`
(user), `S3Credentials` (access key pair, written to a Secret), `S3Policy`, and
`S3PolicyBinding` (the declarative equivalents of `s3.user.create`, `s3.accesskey.create`,
`s3.policy -put`, and `s3.policy.attach`). See
[Declarative Buckets and IAM](./Deployment-to-Kubernetes-and-Minikube.md#declarative-buckets-and-iam).

#### Environment Variables
Environment variables create global admin access and cannot be scoped to specific buckets.

### Best Practices

1. **Principle of Least Privilege**: Grant only the minimum permissions needed
2. **Use Specific Bucket Names**: Avoid wildcards unless necessary for flexibility
3. **Separate Users for Different Buckets**: Create dedicated users for each bucket or application
4. **Test Permissions**: Verify users can only access intended buckets
5. **Monitor Access**: Use audit logs to track bucket access patterns

### Troubleshooting

**User can access other buckets:**
- Verify no global actions (`Read`, `Write`, `Admin`) are granted
- Check for wildcard patterns that might be too broad
- Ensure bucket names in actions match exactly

**User cannot access intended bucket:**
- Verify bucket name spelling in actions
- Check that all required actions are granted (e.g., `List` for listing objects)
- Test with AWS CLI: `aws --endpoint-url $S3_ENDPOINT s3 ls s3://mybucket`

## Anonymous Access

By default, the SeaweedFS S3 gateway handles anonymous access differently depending on whether any credentials have been configured:

### Allow-All Mode

If no S3 credentials have been configured through any of the methods above (config files, filer, or environment variables), the S3 gateway defaults to **Allow-All Mode**. In this mode:
- All S3 operations are permitted without authentication.
- This is the default state for `weed mini` (and `weed s3`) when starting without any flags or environment variables.

### Authentication Required Mode

As soon as **at least one identity** is configured using any method:
1. **Authentication is automatically enabled** globally for the S3 gateway.
2. **Anonymous access is restricted**: All requests will require valid credentials by default.
3. To allow specific anonymous access to certain buckets after authentication is enabled, you must use [S3-CORS](./S3-CORS.md) or bucket-level policies.

### Toggling Behavior

- **Initial State**: If you start `weed mini` (or `weed s3`) with credentials, it starts in "Authentication Required" mode.
- **Dynamic Transition (One-Way)**: If you start without credentials (in "Allow-All" mode) and then add any identity, the server will **automatically and permanently transition** to "Authentication Required" mode. Once enabled, authentication will remain required even if all credentials are later removed.

## Configuration Reloading

SeaweedFS supports different reloading mechanisms depending on which authentication method you use:

| Configuration Method | Auto Reload | Manual Reload | Live Reload |
|---------------------|-------------|---------------|-------------|
| **Configuration File** (`-config` option) | ❌ No | ✅ SIGHUP | ❌ No |
| **Filer Configuration** (credential manager) | ✅ Yes | ✅ Yes | ✅ Yes |
| **Admin UI** (web interface) | ✅ Yes | ✅ Yes | ✅ Yes |
| **Environment Variables** | ❌ No | ❌ No | ❌ No |

### Static Configuration Files

When using the `-config` option, you can reload the configuration by sending a SIGHUP signal:

```bash
# Find the S3 server process ID
ps aux | grep "weed s3"

# Send SIGHUP signal to reload configuration
kill -HUP <seaweedfs_s3_pid>

# Or if using systemd
systemctl reload seaweedfs-s3
```

The server will log the reload:
```
I0723 12:34:56.789 s3api_server.go:98] Loaded 3 identities from config file /etc/seaweedfs/s3.json
```

### Filer-based Configuration

Filer-based configurations automatically reload when changes are detected:

```bash
# Changes are automatically applied
weed shell
> s3.user.create -name newuser
> s3.policy.attach -policy admin-policy -user newuser
```

The server will automatically detect and apply changes:
```
I0723 12:35:12.456 auth_credentials_subscribe.go:55] updated /etc/seaweedfs/iam/identity.json
```

### Admin UI Configuration

Admin UI changes are automatically applied in real-time since they use the same filer-based storage:

1. **Access Admin UI**: Navigate to `http://localhost:23646`
2. **Go to Users**: Click **Object Store → Users**
3. **Make Changes**: Create, edit, or delete users through the web interface
4. **Automatic Sync**: Changes are immediately applied to all connected S3 servers

The server will show the same automatic detection messages as filer-based configuration since they share the same underlying storage mechanism.

### Environment Variables

Environment variable changes require a complete restart of the S3 server:

```bash
# Update environment variables
export AWS_ACCESS_KEY_ID=new_access_key
export AWS_SECRET_ACCESS_KEY=new_secret_key

# Restart the S3 server
systemctl restart seaweedfs-s3
```

### Verifying Configuration Reloads

Monitor the logs to verify configuration updates:

```bash
# Watch for reload messages
tail -f /var/log/seaweedfs/s3.log | grep -E "updated|Loaded.*identities"

# Check current configuration via shell
weed shell
> s3.configure
```

## Troubleshooting

### Common Issues

**Environment variables not working:**
- Check that no `-config` option is provided
- Verify no configuration exists in the filer
- Ensure both `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are set

**Configuration file not loading:**
- Verify the file path is correct
- Check JSON syntax is valid
- Ensure the file is readable by the SeaweedFS process

**Invalid credentials error:**
- Verify access key and secret key are correct
- Check that the identity has the required actions/permissions
- Ensure the credential store is properly configured

### Debug Commands

Check current configuration:
```bash
# View current IAM configuration summary
weed shell
> s3.config.show

# List all users
> s3.user.list

# Export full configuration as JSON
> s3.iam.export
```

Test credentials:
```bash
# Test with AWS CLI
aws --endpoint-url $S3_ENDPOINT s3 ls
```

## Security Best Practices

1. **Use Configuration Files in Production**: Environment variables are visible in process lists
2. **Rotate Credentials Regularly**: Update access keys and secret keys periodically  
3. **Principle of Least Privilege**: Grant only the minimum required permissions
4. **Secure Storage**: Store configuration files with appropriate file permissions
5. **Monitor Access**: Enable audit logging to track S3 API usage 