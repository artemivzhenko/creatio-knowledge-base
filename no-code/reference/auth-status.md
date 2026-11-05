---
command: auth-status
block: clio-basics
source: clio 8.1.0.145, clio/docs/commands/auth-status.md (MIT)
---
# auth-status - Reports the configured authentication flow, whether a session is cached, and the access-token expiry

Reports the configured authentication flow, whether a session is cached, and the access-token expiry. It never opens a browser or refreshes interactively and never prints token material.

Alias: `whoami`

```bash
clio auth-status -e work
```

Exit code `0` means a session is cached (an expired access token is renewed by the next command without a browser); `1` means sign-in is required.
