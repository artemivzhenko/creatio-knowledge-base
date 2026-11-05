---
command: logout
block: clio-basics
source: clio 8.1.0.145, clio/docs/commands/logout.md (MIT)
---
# logout - Revokes the cached OAuth refresh token and deletes the local token file

Revokes the cached OAuth refresh token and deletes the local token file. Local cleanup is performed even if server-side revocation fails; the command is idempotent.

Aliases: `signout`

```bash
clio logout -e work
```
