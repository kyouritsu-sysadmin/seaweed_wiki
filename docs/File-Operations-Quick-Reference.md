---
id: File-Operations-Quick-Reference
title: "File Operations Quick Reference"
sidebar_label: "File Operations Quick Reference"
---

# File Operations Quick Reference

This page provides a quick reference for common file operations in SeaweedFS using the HTTP API.

## Basic File Operations

### Upload a File

**Small files (direct upload):**
```bash
# Upload with PUT
curl -X PUT "http://localhost:8888/path/to/file.txt" -d "file content"

# Upload with POST (multipart)
curl -X POST "http://localhost:8888/path/to/file.txt" -F "file=@localfile.txt"
```

### Download a File

```bash
# Get file content
curl "http://localhost:8888/path/to/file.txt"

# Download to local file
curl "http://localhost:8888/path/to/file.txt" -o localfile.txt
```

### Delete a File

```bash
# Delete single file
curl -X DELETE "http://localhost:8888/path/to/file.txt"

# Delete directory (recursive)
curl -X DELETE "http://localhost:8888/path/to/directory/?recursive=true"
```

## Advanced File Operations

### Move/Rename Files

```bash
# Move file to new location
curl -X POST "http://localhost:8888/new/path/file.txt?mv.from=/old/path/file.txt"

# Rename file in same directory
curl -X POST "http://localhost:8888/path/to/newname.txt?mv.from=/path/to/oldname.txt"
```

### Copy Files ⭐ **New Feature**

```bash
# Copy file (preserves original)
curl -X POST "http://localhost:8888/backup/file.txt?cp.from=/original/file.txt"

# Copy with automatic name resolution
curl -X POST "http://localhost:8888/backup/?cp.from=/original/file.txt"
# Result: /backup/file.txt
```

### List Directory Contents

```bash
# List directory
curl -H "Accept: application/json" "http://localhost:8888/path/to/directory/?pretty=y"

# List with pagination
curl -H "Accept: application/json" "http://localhost:8888/path/?limit=10&lastFileName=somefile.txt"
```

### Create Directory

```bash
# Create empty directory
curl -X POST "http://localhost:8888/path/to/new/directory/"
```

## File Metadata Operations

### Get File Information

```bash
# Get file metadata
curl -I "http://localhost:8888/path/to/file.txt"
```

### File Attributes and Tagging

```bash
# Set custom attributes
curl -X PUT "http://localhost:8888/path/to/file.txt" \
  -H "Seaweed-Custom-Attribute: value" \
  -F "file=@localfile.txt"

# Set TTL (time to live)
curl -X POST "http://localhost:8888/path/to/file.txt?ttl=3600" \
  -F "file=@localfile.txt"
```

## Response Codes

| HTTP Code | Operation | Meaning |
| --------- | --------- | ------- |
| 200 OK | GET | File retrieved successfully |
| 201 Created | POST/PUT | File uploaded successfully |
| 204 No Content | DELETE, COPY, MOVE | Operation completed successfully |
| 400 Bad Request | Any | Invalid parameters or unsupported operation |
| 404 Not Found | GET, DELETE | File or directory not found |
| 409 Conflict | POST/PUT | File already exists (when using exclusive creation) |

## Operation Comparison

| Operation | Source File | Use Case | Performance |
| --------- | ----------- | -------- | ----------- |
| **Upload** | External → SeaweedFS | Add new files | Network dependent |
| **Download** | SeaweedFS → External | Retrieve files | Network dependent |
| **Move** (`mv.from`) | Deleted | Rename/relocate | Very fast (metadata only) |
| **Copy** (`cp.from`) | Preserved | Backup/duplicate | Depends on file size |
| **Delete** | Deleted | Remove files | Fast |

## Best Practices

### When to Use Copy vs Move

**Use Copy (`cp.from`) when:**
- Creating backups before modifications
- Duplicating configuration templates  
- Staging files for testing
- Need to preserve original file

**Use Move (`mv.from`) when:**
- Renaming files
- Reorganizing file structure
- Moving files between directories
- Don't need original file

### Performance Tips

1. **Batch operations**: Group multiple operations when possible
2. **Small files**: Use direct PUT for files &lt; 1MB
3. **Large files**: POST with multipart automatically chunks files
4. **Copy operations**: Server-side copy is much faster than download + upload
5. **Directory operations**: Plan directory structure to minimize reorganization

### Error Handling

```bash
# Check operation status
if curl -X POST "http://localhost:8888/dest?cp.from=/src" -w "%{http_code}" -o /dev/null -s | grep -q "204"; then
    echo "Copy successful"
else
    echo "Copy failed"
fi
```

## Related Documentation

- [Filer Server API](./Filer-Server-API.md) - Complete API reference
- [Filer Commands and Operations](./Filer-Commands-and-Operations.md) - Command-line tools
- [Getting Started](./Getting-Started.md) - Installation and setup
- [FAQ](./FAQ.md) - Common questions and answers

## Examples Repository

For more complex examples and use cases, see:
- [SeaweedFS Examples](https://github.com/seaweedfs/seaweedfs/tree/master/examples) (if available)
- Community-contributed scripts and tools
- Language-specific client libraries

---

💡 **Tip**: Use the `?pretty=y` parameter with JSON responses to get formatted output for easier reading during development and testing.
