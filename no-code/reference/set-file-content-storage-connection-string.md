---
command: set-file-content-storage-connection-string
block: clio-sql-and-data
source: clio 8.1.0.145, clio/docs/commands/set-file-content-storage-connection-string.md (MIT)
---
# set-file-content-storage-connection-string - Set the connection string of a file content storage

## Name

set-file-content-storage-connection-string - Set the connection string of a file content storage


## Description

Updates the connection string of a file content storage (`SysFileContentStorage`) record using the
Creatio DataService. The change is applied through the ORM layer, which encrypts the value transparently
and triggers entity events — invalidating the file storage configuration cache without an application restart.

Alias: `set-fcs-connection-string`


## Options

```bash
Code (pos. 0)               File content storage code
ConnectionString (pos. 1)   New connection string value
```


## Example

```bash
set-file-content-storage-connection-string MyStorageCode "ServiceUrl=https://s3.example.com;AccessKey=...;SecretKey=...;ObjectBucketName=...;"
set-fcs-connection-string MyStorageCode "..." -e MyEnvironment
```


## Notes

The connection string is sensitive: this command never writes its value to the console or the log.
