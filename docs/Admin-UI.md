---
id: Admin-UI
title: "Admin UI"
sidebar_label: "Admin UI"
---

# This is still work in progress. Some features work, some not. Everything is subject to change.

# Weed Admin

The `weed admin` command starts a modern web-based administration interface for SeaweedFS cluster management.

## Overview

The admin interface provides a comprehensive web UI for managing SeaweedFS clusters, including:
- **Cluster topology visualization and monitoring**
- **Volume management and operations**
- **File browser and management**
- **System metrics and performance monitoring**
- **Configuration management**

The admin interface automatically discovers filers from the master servers and runs a gRPC server for worker connections on HTTP port + 10000.

## Usage

```bash
weed admin [options]
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `-port` | 23646 | Admin server port |
| `-masters` | localhost:9333 | Comma-separated master servers |
| `-dataDir` | "" | Directory to store admin configuration and data files |
| `-adminUser` | admin | Admin interface username |
| `-adminPassword` | "" | Admin interface password (if empty, auth is disabled) |
| `-readOnlyUser` | "" | Read-only user username (optional) |
| `-readOnlyPassword` | "" | Read-only user password (optional; requires adminPassword) |
| `-urlPrefix` | "" | URL path prefix for subdirectory deployment (e.g. `/seaweedfs`) |

## Examples

### Basic Usage

```bash
# Start admin interface on default port (23646)
weed admin -masters=localhost:9333

# Start with custom port and multiple masters
weed admin -port=8080 -masters="master1:9333,master2:9333"

# Start with specific data directory
weed admin -port=23646 -masters="localhost:9333" -dataDir="/var/lib/seaweedfs-admin"

# Start with home directory expansion
weed admin -port=23646 -masters="localhost:9333" -dataDir="~/seaweedfs-admin"
```

### With Authentication

```bash
# Enable authentication
weed admin -adminUser=admin -adminPassword=secret123 -masters="localhost:9333"
```

### Behind a Reverse Proxy (Subdirectory)

```bash
# Serve the admin UI under /seaweedfs/ subdirectory
weed admin -masters="localhost:9333" -urlPrefix=/seaweedfs
```

With this configuration, the admin UI is accessible at `http://localhost:23646/seaweedfs/admin`. All static assets, API endpoints, navigation links, and session cookies are automatically scoped to the prefix.

Example nginx reverse proxy configuration:

```nginx
location /seaweedfs/ {
    proxy_pass http://localhost:23646/seaweedfs/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### Production Deployment

```bash
# Production setup with data persistence and authentication
weed admin \
  -port=23646 \
  -masters="master1:9333,master2:9333,master3:9333" \
  -dataDir="/var/lib/seaweedfs-admin" \
  -adminUser=admin \
  -adminPassword=strongpassword123
```

## Data Directory

The data directory (`-dataDir`) is used to persist admin configuration data:

- **If specified**: Configuration and data are persisted to disk
- **If not specified**: All configuration is kept in memory only
- **Path expansion**: Supports tilde (`~`) expansion for home directory
- **Auto-creation**: Directory is automatically created if it doesn't exist
- **Format**: Configuration files are stored in JSON format for easy editing

## Maintenance Task Configuration

Maintenance task settings (vacuum, balance, erasure coding) are edited in the admin UI and persisted under `&lt;dataDir&gt;/conf`. To manage them declaratively — from Helm values or other version-controlled manifests — declare them in an optional `admin.toml`:

```toml
[maintenance.vacuum]
enabled = true
garbage_threshold = 0.3        # vacuum volumes with more deleted content than this ratio
scan_interval_seconds = 7200
max_concurrent = 2
min_volume_age_seconds = 86400 # rounded up to whole hours

[maintenance.balance]
imbalance_threshold = 0.2
scan_interval_seconds = 1800
max_concurrent = 1
min_server_count = 2

[maintenance.erasure_coding]
fullness_ratio = 0.95
quiet_for_seconds = 3600
scan_interval_seconds = 3600
max_concurrent = 1
min_size_mb = 30
collection_filter = ""
preferred_tags = ["fast", "ssd"]
replica_placement = ""
```

Keys set in `admin.toml` are applied every time the admin server starts and override values saved from the admin UI; keys left out keep their saved or default values. This makes the settings survive data directory loss, such as a recreated PVC. Requires `-dataDir`.

The file is read from the same locations as `security.toml`, and each value can also be set via environment variable:

```bash
export WEED_MAINTENANCE_VACUUM_GARBAGE_THRESHOLD=0.03
```

Generate a commented example:

```bash
weed scaffold -config=admin
```

## Security and Authentication

### Authentication

- **Disabled by default**: If `-adminPassword` is not set, no authentication is required
- **Session-based**: When enabled, uses secure session management with auto-generated session keys
- **User credentials**: Login with `-adminUser` and `-adminPassword`
- **Read-only access**: Optionally set `-readOnlyUser` and `-readOnlyPassword` for view-only access

### OIDC Single Sign-On (Enterprise)

For OIDC login (Keycloak, Okta, Azure AD, Auth0, Google, Cognito, …) on the admin UI, see [Admin UI OIDC](./Admin-UI-OIDC.md). OIDC is an Enterprise feature; the OSS `weed admin` binary supports only the local username/password flow described on this page.

### Credentials via Environment Variables / security.toml

Credentials can also be configured via the `[admin]` section in `security.toml` or environment variables, avoiding exposure in CLI flags or process listings.

**security.toml example:**
```toml
[admin]
user = "admin"
password = "secret"

[admin.readonly]
user = "viewer"
password = "viewpass"
```

**Environment variables** (via viper's `WEED_` prefix):

| security.toml key | Environment Variable |
|--------------------|----------------------|
| `admin.user` | `WEED_ADMIN_USER` |
| `admin.password` | `WEED_ADMIN_PASSWORD` |
| `admin.readonly.user` | `WEED_ADMIN_READONLY_USER` |
| `admin.readonly.password` | `WEED_ADMIN_READONLY_PASSWORD` |

**Precedence**: CLI flag > env var / security.toml > default value

```bash
# Start with credentials from environment variables (adminUser defaults to "admin")
WEED_ADMIN_PASSWORD=secret weed admin -master=localhost:9333
```

### TLS/HTTPS Configuration

The admin server reads TLS configuration from `security.toml`:

```toml
[https.admin]
cert = "/etc/ssl/admin.crt"
key = "/etc/ssl/admin.key"
ca = "/etc/ssl/ca.crt"     # optional, for mutual TLS
```

- **HTTPS**: Automatically enabled if `https.admin.key` is configured
- **Mutual TLS**: Enabled if `https.admin.ca` is configured
- **Certificate loading**: Certificates are loaded from the security configuration

### Security Best Practices

1. **Set strong passwords**: Use strong `-adminPassword` for production
2. **Configure TLS**: Use HTTPS for production deployments
3. **Firewall rules**: Restrict admin interface access to authorized networks
4. **Regular updates**: Keep SeaweedFS updated for security patches

## Worker Communication

The admin server also runs a gRPC server for worker connections:

- **Port**: HTTP port + 10000 (e.g., if admin runs on 23646, gRPC runs on 33646)
- **Purpose**: Handles worker connections and task distribution
- **TLS**: Uses `[grpc.admin]` configuration from `security.toml`
- **Fallback**: Workers fall back to insecure connections if TLS is unavailable

## Configuration File

The admin server reads configuration from `security.toml` and `admin.toml` in the following order:
1. Current directory (`.`)
2. `$HOME/.seaweedfs/`
3. `/usr/local/etc/seaweedfs/`
4. `/etc/seaweedfs/`

### Generate Example Configuration

```bash
# Generate example security.toml
weed scaffold -config=security

# Generate example admin.toml (maintenance task settings)
weed scaffold -config=admin
```

## Features

### Automatic Service Discovery

- **Master discovery**: Connects to specified master servers
- **Filer discovery**: Automatically discovers filers from masters
- **Health monitoring**: Monitors cluster health and status

### Web Interface

The admin interface provides a comprehensive web-based management console with the following sections:

#### Dashboard
- **Cluster Overview**: Real-time cluster status and health metrics
- **System Statistics**: Total volumes, files, size, and volume size limits
- **Node Status**: Master, filer, volume server, and message broker status
- **Data Centers**: Geographic distribution of storage nodes

#### Object Store Management
- **S3 Buckets**: View, create, delete, and manage S3-compatible buckets
- **Bucket Details**: Quota management and configuration
- **User Management**: Create and manage S3 API users with permissions
- **Access Keys**: Generate and manage access/secret key pairs
- **Policies**: Manage bucket policies and user permissions

#### File Browser
- **Directory Navigation**: Browse filesystem hierarchy through web interface
- **File Operations**: Upload, download, delete, and manage files
- **File Properties**: View file metadata, permissions, and storage details
- **Bulk Operations**: Multi-select for batch operations

#### Cluster Management
- **Master Servers**: View master node status, leadership, and connectivity
- **Filer Servers**: Monitor filer instances and metadata operations
- **Volume Servers**: Track storage nodes, capacity, and health status
- **Volume Management**: View volume distribution, replication, and status
- **Collections**: Monitor data collections and their volume allocation

#### Message Queue Management
- **Brokers**: View message queue broker status and configuration
- **Topics**: Manage topics, partitions, and message retention
- **Subscribers**: Monitor subscriber connections and consumer lag
- **Topic Details**: View message statistics and partition distribution



### API Endpoints

The admin interface provides RESTful API endpoints for:
- Cluster status and topology
- Volume management
- File operations
- System metrics
- Configuration management

## Troubleshooting

### Common Issues

1. **No filers discovered**:
   - Check master server connectivity
   - Verify master addresses are correct
   - Ensure masters are running and accessible

2. **Authentication not working**:
   - Verify `-adminPassword` is set correctly
   - Check session cookie settings
   - Clear browser cache and cookies

3. **TLS/HTTPS issues**:
   - Verify certificate paths in `security.toml`
   - Check certificate validity and permissions
   - Ensure certificates are in PEM format

4. **Worker connections failing**:
   - Check if gRPC port (HTTP port + 10000) is accessible
   - Verify TLS configuration for worker connections
   - Check firewall rules for gRPC port

### Debug Information

Enable debug logging for detailed troubleshooting:

```bash
# Run with verbose logging
weed admin -v=4 -masters="localhost:9333"
```

## Related Commands


- [`weed master`](https://github.com/seaweedfs/seaweedfs/wiki/Master-Server): Start master servers
- [`weed filer`](https://github.com/seaweedfs/seaweedfs/wiki/Filer-Server): Start filer servers
- [`weed scaffold`](https://github.com/seaweedfs/seaweedfs/wiki/Scaffold): Generate configuration files

## Admin UI Pages Reference

### Accessing the Admin Interface

Once the admin server is running, access the web interface at:
```
http://localhost:23646
```

Or with custom port:
```
http://localhost:PORT
```

If `-urlPrefix` is configured, include the prefix in the URL:
```
http://localhost:23646/seaweedfs/admin
```

### Dashboard (/)

The main dashboard provides a comprehensive overview of your SeaweedFS cluster:

**Key Metrics**:
- Total volumes, files, and storage size
- Volume size limit configuration
- Cluster health status

**Cluster Topology**:
- Master server status and leader election
- Filer server instances and connections
- Volume server distribution and capacity
- Message broker status (if enabled)
- Data center geographic distribution

**Real-time Updates**: The dashboard automatically refreshes to show current cluster status.

### Object Store Management

#### S3 Buckets (/object-store/buckets)

Manage S3-compatible storage buckets:

**Features**:
- View all buckets with creation dates and sizes
- Create new buckets with Object Lock support
- Delete buckets (with confirmation)
- Set bucket quotas and limits
- Export bucket list to CSV

**Bucket Operations**:
- **Create Bucket**: Specify name and optional Object Lock enablement
- **Delete Bucket**: Remove empty buckets with confirmation dialog
- **Quota Management**: Set storage limits per bucket
- **Bucket Details**: View detailed statistics and configuration
- **Lifecycle rules**: View the lifecycle rules, and edit them with a rich web form

#### User Management (/object-store/users)

Manage S3 API users and their permissions:

**User Operations**:
- Create new users with email and permissions
- Edit existing user permissions and details
- Delete users with confirmation
- Generate and manage access keys
- View user activity and permissions

**Permission Types**:
- **Admin**: Full access to all buckets and operations
- **Read**: Read access to specified buckets
- **Write**: Write access to specified buckets  
- **List**: List bucket contents
- **Tagging**: Manage object tags
- **Object Lock Permissions**:
  - **BypassGovernanceRetention**: Override governance retention
  - **GetObjectRetention**: Read object retention settings
  - **PutObjectRetention**: Modify object retention
  - **GetObjectLegalHold**: Read legal hold status
  - **PutObjectLegalHold**: Set legal hold
  - **GetBucketObjectLockConfiguration**: Read bucket Object Lock config
  - **PutBucketObjectLockConfiguration**: Modify bucket Object Lock config

**Access Key Management**:
- Generate new access/secret key pairs
- View existing access keys (secret keys are masked)
- Delete unused access keys
- Copy keys to clipboard

#### Policies (/object-store/policies)

Manage bucket policies and access control:

**Policy Operations**:
- Create bucket policies using a rich web form UI or paste a JSON-based policy
- Edit existing policies with syntax validation
- Delete policies
- Validate policy syntax before saving
- View policy effects and permissions

### File Browser (/files)

Web-based file system interface:

**Navigation**:
- Browse directory hierarchy
- Navigate with breadcrumb navigation
- Search files and folders
- Sort by name, size, or modification date

**File Operations**:
- **Upload**: Single or multiple file upload with progress tracking
- **Download**: Direct file download or streaming
- **Delete**: Remove files and folders with confirmation
- **Create Folders**: New directory creation
- **Rename**: File and folder renaming
- **Copy/Move**: File management operations

**Advanced Features**:
- Drag-and-drop file upload
- Bulk selection for batch operations
- File property viewing (size, permissions, metadata)
- Preview for supported file types
- Export file listings to CSV

### Cluster Management

#### Master Servers (/cluster/masters)

Monitor master server cluster:

**Information Displayed**:
- Master server addresses and ports
- Leader election status
- Connection health and response times
- Configuration synchronization status
- Cluster membership changes

#### Filer Servers (/cluster/filers)

Track filer instances:

**Monitoring**:
- Filer server addresses and health
- Metadata store backend status
- Connected clients and operations
- Performance metrics and response times

#### Volume Servers (/cluster/volume-servers)

Manage storage nodes:

**Server Information**:
- Server addresses and capacity
- Free space and utilization
- Active volume counts
- Data center and rack assignment
- Health status and connectivity

#### Volume Management (/cluster/volumes)

Detailed volume tracking:

**Volume Details**:
- Volume ID and size information
- Replication status and factor
- Read/write statistics
- Storage location and server mapping
- Collection assignment

**Operations**:
- View volume distribution across servers
- Monitor replication health
- Track volume growth and utilization

#### Collections (/cluster/collections)

Monitor data collections:

**Collection Information**:
- Collection names and volume counts
- Replication configuration
- Storage distribution
- Growth patterns and capacity planning

### Workers / Plugin Management (/plugin)

Manage the plugin worker scheduler and job types:

**Overview Tab**:
- Connected workers with capabilities, last seen time, and health
- Scheduler status showing current phase and next detection times
- Recent activity stream across all job types

**Per-Job-Type Settings**:
- **Enabled**: Toggle scheduled detection on/off
- **Detection Interval (s)**: How often to check for new work (this is the primary interval that controls when the next run is scheduled)
- **Detection Timeout (s)**: Max time for a detection request
- **Job Type Max Runtime (s)**: Max total time for detection + execution per iteration
- **Max Jobs / Detection**: Limit proposals per detection run
- **Global Execution Concurrency**: Max jobs dispatched in parallel
- **Per-Worker Execution Concurrency**: Max jobs sent to a single worker
- **Retry Limit / Retry Backoff (s)**: Retry policy for failed jobs

**Job Type Tabs** (one per registered type):
- Admin and worker configuration forms (job-type-specific parameters)
- Run history with success/error counts
- Manual detection and execution triggers
- Activity log filtered to the job type

**Manual Operations**:
- **Trigger Detection**: Run detection immediately for a job type
- **Trigger Execution**: Submit a manual job with custom parameters

For details on the scheduling architecture, see [Plugin Worker Scheduling](./Plugin-Worker-Scheduling.md).

### Message Queue Management

#### Brokers (/mq/brokers)

Monitor message queue brokers:

**Broker Status**:
- Broker addresses and health
- Topic assignment and leadership
- Connection counts and throughput
- Configuration and settings

#### Topics (/mq/topics)

Manage message queue topics:

**Topic Operations**:
- Create new topics with partition configuration
- View topic statistics and message counts
- Manage topic retention policies
- Monitor consumer lag and throughput

#### Topic Details (/mq/topics/&#123;namespace&#125;/&#123;topic&#125;)

Detailed topic information:

**Statistics**:
- Message production and consumption rates
- Partition distribution and leadership
- Subscriber connections and lag
- Storage utilization per partition



**Configuration Options**:
- Task scheduling parameters
- Worker connection settings
- Retry policies and timeouts
- Resource allocation limits

## Navigation and UI Features

### Responsive Design
- Mobile-friendly interface
- Collapsible sidebar navigation
- Responsive tables and charts
- Touch-friendly controls

### Real-time Updates
- Live cluster status monitoring
- Automatic page refresh for dynamic content
- WebSocket connections for real-time data
- Progress indicators for long-running operations

### Security Features
- Session-based authentication
- CSRF protection
- Secure cookie handling
- TLS/HTTPS support

### Accessibility
- Keyboard navigation support
- Screen reader compatibility
- High contrast mode support
- Semantic HTML structure

## See Also

- [SeaweedFS Architecture](https://github.com/seaweedfs/seaweedfs/wiki/SeaweedFS-Architecture)
- [Security Configuration](https://github.com/seaweedfs/seaweedfs/wiki/Security-Configuration)

- [S3 Object Lock and Retention](./S3-Object-Lock-and-Retention.md)
- [S3 API FAQ](./S3-API-FAQ.md) 