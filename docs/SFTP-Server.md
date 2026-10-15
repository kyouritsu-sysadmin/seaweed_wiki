---
id: SFTP-Server
title: "SFTP Server"
sidebar_label: "SFTP Server"
---

# SFTP Server

SeaweedFS includes a built-in SFTP (SSH File Transfer Protocol) server that allows users to interact with the filer using standard SFTP clients. The SFTP server bridges between standard SSH/SFTP protocols and the SeaweedFS filer, enabling secure file operations over SSH.

## Overview

The SFTP server provides:
- **SSH/SFTP access** to your SeaweedFS filer
- **User authentication** via passwords, SSH public keys, or CA-signed certificates
- **JWT integration** for secure filer authentication
- **File operations** including upload, download, rename, delete, and directory management
- **Home directory enforcement** with chroot-like behavior for security
- **Keep-alive support** for long-running connections

## Quick Start

### Starting the SFTP Server (Standalone)

```bash
weed sftp -filer=localhost:8888 -port=2022 -userStoreFile=/path/to/users.json
```

### Starting SFTP with Filer

The SFTP server can run alongside the filer:

```bash
weed filer -sftp.port=2022 -sftp.userStoreFile=/path/to/users.json
```

## Configuration

### User Store File

Create a JSON file containing user credentials. Example: `users.json`

```json
[
  {
    "Username": "alice",
    "Password": "secure_password_here",
    "HomeDir": "/home/alice",
    "Uid": 1000,
    "Gid": 1000
  },
  {
    "Username": "bob",
    "Password": "another_password",
    "HomeDir": "/home/bob",
    "Uid": 1001,
    "Gid": 1001
  }
]
```

**Important Notes:**
- `HomeDir`: The user's root directory within the filer (e.g., `/home/alice` means the user sees that as their `/`)
- `Uid` and `Gid`: User and group IDs for file ownership (currently must be 0 for proper functioning)
- `Password`: Will be used for password-based authentication

### Command-Line Options

#### Common Options

| Flag | Default | Description |
|------|---------|-------------|
| `-filer` | `localhost:8888` | Filer server address (ip:port) |
| `-port` | `2022` | SFTP server listen port |
| `-ip.bind` | `0.0.0.0` | IP address to bind to |
| `-userStoreFile` | (required) | Path to JSON file with user credentials |

#### SSH Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `-sshPrivateKey` | (empty) | Path to SSH private key file for host authentication |
| `-hostKeysFolder` | (empty) | Path to folder with SSH private key files for multiple algorithms |
| `-authMethods` | `password,publickey` | Comma-separated auth methods: password, publickey, certificate |
| `-trustedUserCAKeysFile` | (empty) | Path to trusted user CA public keys (OpenSSH `authorized_keys` format); required when `certificate` is in `-authMethods` |
| `-maxAuthTries` | `6` | Maximum authentication attempts per connection |
| `-bannerMessage` | SeaweedFS default | Message displayed before authentication |
| `-loginGraceTime` | `2m` | Timeout for authentication |

#### Connection Management

| Flag | Default | Description |
|------|---------|-------------|
| `-clientAliveInterval` | `5s` | Interval for sending keep-alive messages |
| `-clientAliveCountMax` | `3` | Max missed keep-alives before disconnect |

#### Cluster Options

| Flag | Default | Description |
|------|---------|-------------|
| `-dataCenter` | (empty) | Prefer to read/write to volumes in this data center |
| `-localSocket` | `/tmp/seaweedfs-sftp-&lt;port&gt;.sock` | Unix socket for local connections (Unix only) |

### Complete Example

```bash
weed sftp \
  -filer=filer.example.com:8888 \
  -port=2022 \
  -ip.bind=0.0.0.0 \
  -userStoreFile=/etc/seaweedfs/sftp-users.json \
  -sshPrivateKey=/etc/seaweedfs/ssh_host_key \
  -authMethods=password,publickey \
  -maxAuthTries=5 \
  -clientAliveInterval=60s \
  -clientAliveCountMax=5 \
  -dataCenter=dc1
```

## SSH User Certificate Authentication

Instead of registering every user's public key in the user store, the SFTP server can trust an SSH **certificate authority (CA)** and accept short-lived, CA-signed user certificates. This is the same model as OpenSSH's `TrustedUserCAKeys` directive: you sign each user a certificate with a central CA key, and the server accepts any certificate that CA vouches for. Issuing or rotating access no longer means editing the server's user store on every key change.

### Enabling

Add `certificate` to `-authMethods` and point `-trustedUserCAKeysFile` at a file holding the trusted CA public key(s):

```bash
weed sftp \
  -authMethods=password,certificate \
  -trustedUserCAKeysFile=/etc/seaweedfs/sftp/ca_user.pub \
  -userStoreFile=/etc/seaweedfs/sftp/users.json \
  -hostKeysFolder=/etc/seaweedfs/sftp/host_keys
```

The CA file uses OpenSSH `authorized_keys` format — one CA public key per line, with blank lines and `#` comments ignored. Listing more than one key lets you trust several CAs at once, which is handy during a CA rotation.

### Issuing certificates

```bash
# One-time: create the user CA keypair (keep ca_user private and offline)
ssh-keygen -t ed25519 -f ca_user

# Per user: sign a certificate valid for 1 hour, principal "alice"
ssh-keygen -s ca_user -I alice@host -n alice -V +1h alice.pub
```

`-n alice` sets the certificate principal. The principal must match the SSH login username, and a user with that name must still exist in the user store — the store still supplies the home directory, Uid/Gid, and permissions. The CA only vouches for identity; authorization continues to come from the user store.

### Connecting

```bash
sftp -P 2022 -i alice alice@localhost
```

OpenSSH automatically presents `alice-cert.pub` when it sits next to the `alice` private key. You can also point at it explicitly with `-o CertificateFile=alice-cert.pub`.

### Validation and behavior

When `certificate` is enabled, the server validates each presented certificate:

- signed by one of the trusted CA keys
- type is a **user** certificate (host certificates are rejected)
- the current time is inside the `ValidAfter`/`ValidBefore` window
- `ValidPrincipals` is non-empty and contains the login username
- the login username resolves to an existing user in the store

**Certificate auth takes over the public-key channel.** Once `certificate` is in `-authMethods`, plain (non-certificate) public keys are rejected even if `publickey` is also listed — matching OpenSSH behavior. Password authentication is independent and unaffected, so `-authMethods=password,certificate` keeps both. The defaults stay `password,publickey`, so existing deployments are untouched until you opt in.

> The CA can sign a certificate for any principal, which makes the CA private key as powerful as every user's key combined. Keep it offline, issue short-lived certificates with `-V`, and treat it like a root credential.

## JWT Authentication with Filer

When your filer is configured with JWT authentication, the SFTP server automatically uses JWT tokens for secure communication. This is **automatically configured** - no additional settings needed!

### Filer JWT Configuration

Ensure your `security.toml` includes JWT settings for the filer:

```toml
[jwt.filer_signing]
key = "your-filer-signing-secret-key"
expires_after_seconds = 10

[jwt.filer_signing.read]
key = "your-filer-signing-read-secret-key"
expires_after_seconds = 60
```

The SFTP server will:
1. Automatically load these JWT keys from security configuration
2. Generate temporary JWT tokens for each file operation
3. Include tokens in requests to the filer
4. Work seamlessly without additional configuration

This is **required** if your filer has JWT authentication enabled. Without it, file uploads will fail with "Failure" errors.

### Troubleshooting JWT Issues

If you see upload errors like "close remote: Failure":

1. **Verify filer JWT is enabled:** Check `security.toml` has `jwt.filer_signing.key` set
2. **Check JWT keys match:** The SFTP server must use the same keys as the filer
3. **Verify SFTP has JWT config:** Ensure `security.toml` is loaded when SFTP starts
4. **Check logs:** Look for JWT-related errors in verbose logs (`-glog.v=4`)

## Client Usage

### Using SFTP Client

```bash
sftp -P 2022 alice@localhost
```

### Common SFTP Commands

```bash
# List directory
ls

# Create directory
mkdir projects

# Upload file
put local-file.txt

# Download file
get remote-file.txt

# Rename file
rename old-name.txt new-name.txt

# Delete file
rm file.txt

# Change directory
cd projects

# Print working directory
pwd
```

### Using SSH/Fuse Mount

Mount the SFTP server using SSHFS (macOS/Linux):

```bash
mkdir ~/seaweedfs-mount
sshfs -P 2022 alice@localhost:/ ~/seaweedfs-mount
```

## File Operations

### Permissions and Ownership

- Files are created with ownership based on user Uid/Gid from the user store
- The filer maintains file permissions and ownership through gRPC calls
- Directory creation respects the user's home directory boundaries (chroot-like)

### Home Directory

Each user's home directory is configured in the user store:
- A user with `HomeDir: "/home/alice"` sees that as their root (`/`)
- Attempting to escape the home directory (e.g., `../..`) is blocked
- The home directory is automatically created if it doesn't exist

### File Upload with JWT

When a file is uploaded:
1. SFTP server generates a JWT token using the filer signing key
2. Token is included in the HTTP request to the filer
3. Filer validates the JWT before accepting the upload
4. File is stored in the filer with proper ownership

## Production Setup

### Host Keys

For production, generate proper SSH host keys:

```bash
# Generate RSA key
ssh-keygen -t rsa -N "" -f /etc/seaweedfs/ssh_host_key

# Run SFTP server
weed sftp -port=2022 -sshPrivateKey=/etc/seaweedfs/ssh_host_key ...
```

Or use multiple keys with `-hostKeysFolder`:

```bash
# Create keys folder
mkdir -p /etc/seaweedfs/ssh_keys

# Generate keys for different algorithms
ssh-keygen -t rsa -N "" -f /etc/seaweedfs/ssh_keys/ssh_host_rsa_key
ssh-keygen -t ed25519 -N "" -f /etc/seaweedfs/ssh_keys/ssh_host_ed25519_key

# Run SFTP server
weed sftp -port=2022 -hostKeysFolder=/etc/seaweedfs/ssh_keys ...
```

### Systemd Service

Create `/etc/systemd/system/seaweedfs-sftp.service`:

```ini
[Unit]
Description=SeaweedFS SFTP Server
After=network.target

[Service]
Type=simple
User=seaweedfs
ExecStart=/usr/local/bin/weed sftp \
  -filer=filer.example.com:8888 \
  -port=2022 \
  -userStoreFile=/etc/seaweedfs/sftp-users.json \
  -sshPrivateKey=/etc/seaweedfs/ssh_host_key
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
systemctl enable seaweedfs-sftp
systemctl start seaweedfs-sftp
systemctl status seaweedfs-sftp
```

## Security Considerations

### User Management

- Store user credentials securely in the user store file
- Restrict file permissions: `chmod 600 users.json`
- Use strong passwords or SSH keys
- Regularly rotate credentials

### Network Security

- Run SFTP on a non-standard port (not 22)
- Firewall SFTP port to trusted networks only
- Use [SSH user certificates](#ssh-user-certificate-authentication) for key-based auth in production
- Consider running behind a VPN or bastion host

### Home Directory Isolation

- Each user sees only their home directory
- Path traversal attempts are blocked
- Files outside user's home dir are inaccessible

### JWT Security

- Store JWT secrets securely in `security.toml`
- Use different keys for read and write operations
- Rotate JWT keys periodically
- Monitor JWT expiration settings to balance security and performance

## Troubleshooting

### Connection Refused

```
ssh: connect to host localhost port 2022: Connection refused
```

**Solution:** Ensure SFTP server is running and listening on the correct port:

```bash
netstat -tlnp | grep 2022
# or on macOS:
lsof -i :2022
```

### Authentication Failed

```
Permission denied (password).
```

**Solution:** 
1. Verify user exists in JSON file
2. Check password is correct
3. Ensure file format is valid JSON
4. Check user JSON again for syntax errors

### Upload Failures

```
Uploading file.txt to /file.txt
close remote: Failure
```

**Solution (with JWT enabled):**
1. Verify JWT key is configured in `security.toml`
2. Check JWT key matches between SFTP and filer
3. Enable verbose logging: `-glog.v=4`
4. Check filer logs for JWT validation errors

### Slow Connections

Increase keep-alive timeout:

```bash
weed sftp ... -clientAliveInterval=30s -clientAliveCountMax=10
```

## See Also

- [Filer-JWT-Use.md](./Filer-JWT-Use.md) - Detailed JWT authentication guide
- [Security-Configuration.md](./Security-Configuration.md) - Security configuration options
- [Filer-Commands-and-Operations.md](./Filer-Commands-and-Operations.md) - Filer operations reference
