---
name: clio-security
description: Administration through clio - users, roles, operation permissions, licenses, object and record rights, OAuth applications and technical users, identity service and SSO providers. Use for "create a user", "grant rights on the object", "set record permissions", "OAuth client".
---

# clio: users, rights and identity

Read on clio 8.1.0.145; the read side was verified on Creatio 8.2.3, the writes were not.
Command pages: [reference/](../reference/).

Verified reads: `get-object-rights --entity-schema-name X` (CLI) and the MCP inspectors
`inspect-user` / `inspect-role` (`action: list` with `user-login` / `name` filters),
`inspect-access` (`action`: ip-list, delegations, operations, operation-grants - `list` is
refused), `inspect-license` (`action`: user-list / role-list plus a GUID `user-id` /
`role-id`). `get-record-rights` fails on 8.2.3 (`RightsService/GetRecordRights` answers an
HTML page), so record-level rights have to be read with SQL there.

## Workflow

```bash
clio manage-user --action list -e dev --limit 50
clio manage-user --action create --user-login jdoe --contact-id <guid> --password-env CLIO_ADMIN_PASSWORD_DEV --confirm -e dev
clio manage-role --action ...                      # organisational / functional roles
clio manage-access --action ...                    # system operation permissions
clio get-object-rights UsrOrder -e dev
clio set-object-rights ...                         # CRUD by role
clio set-default-record-rights ... / apply-default-record-rights ...
clio get-record-rights / set-record-rights ...     # one record
clio manage-license / upload-license ...
```

Rules from the docs that matter to an agent:

- Mutations need `--confirm`; without it the command prompts and a non-interactive agent
  hangs or fails.
- Passwords are never passed on the command line: `--password-env` names an environment
  variable `CLIO_ADMIN_PASSWORD_<SUFFIX>`.
- Object rights have three layers (operations, columns, records); `apply-default-record-rights`
  rewrites existing records' rights and is destructive.
- OAuth: `create-server-to-server-oauth-app` (client credentials), `verify-oauth-app`,
  `resolve-oauth-system-user`; identity-service commands (`idp-*`, `deploy-identity`) target
  the separate Identity Service, not the site.

## Commands

<!-- commands:start -->

| Command | Purpose |
| --- | --- |
| [CustomizeDataProtection](../reference/CustomizeDataProtection.md) | Toggle CustomizeDataProtection in appsettings.json |
| [apply-default-record-rights](../reference/apply-default-record-rights.md) | apply an object's default record rules to its existing records |
| [check-auth-code-flow](../reference/check-auth-code-flow.md) | check whether the environment can use the OAuth authorization code flow |
| [create-oauth-technical-user](../reference/create-oauth-technical-user.md) | Create a Creatio technical user for a server-to-server OAuth app via OAuthConfigService REST |
| [create-server-to-server-oauth-app](../reference/create-server-to-server-oauth-app.md) | Create a server-to-server (client_credentials) OAuth app in Creatio via OAuthConfigService REST |
| [deploy-identity](../reference/deploy-identity.md) | Deploy IdentityService to IIS and connect it to a Creatio environment |
| [distribute-license](../reference/distribute-license.md) | Add or remove users from a Creatio license package |
| [get-identity-assertion](../reference/get-identity-assertion.md) | issue a short-lived signed identity assertion (JWT) for the current user |
| [get-identity-public-jwk](../reference/get-identity-public-jwk.md) | get the instance public key (JWK) for Identity Service V3 |
| [get-identity-service-config](../reference/get-identity-service-config.md) | Read (or derive) the OAuth IdentityService configuration of a Creatio environment over REST |
| [get-object-rights](../reference/get-object-rights.md) | read object operation permissions (read/create/edit/delete per role) and record permissions for an object |
| [get-record-rights](../reference/get-record-rights.md) | read the record-level access rights of a single Creatio record |
| [idp-bind](../reference/idp-bind.md) | Bind an identity provider to an external service or feature code |
| [idp-delete](../reference/idp-delete.md) | Delete an identity provider |
| [idp-list](../reference/idp-list.md) | List identity providers configured in Creatio |
| [idp-services](../reference/idp-services.md) | List external services and their identity provider bindings |
| [idp-set-default](../reference/idp-set-default.md) | Set the default identity provider in Creatio |
| [idp-set-secret](../reference/idp-set-secret.md) | Set the client secret for an identity provider |
| [idp-unbind](../reference/idp-unbind.md) | Unbind an identity provider from an external service or feature code |
| [idp-upsert](../reference/idp-upsert.md) | Create or update an identity provider |
| [manage-access](../reference/manage-access.md) | Manage Creatio access administration through native services with explicit targets and readback |
| [manage-license](../reference/manage-license.md) | Manage Creatio license administration through native services with explicit targets and readback |
| [manage-role](../reference/manage-role.md) | Manage Creatio role administration through native services with explicit targets and readback |
| [manage-user](../reference/manage-user.md) | Manage Creatio user administration through native services with explicit targets and readback |
| [regenerate-identity-signing-key](../reference/regenerate-identity-signing-key.md) | regenerate the instance identity-assertion signing key pair |
| [register-sso-provider](../reference/register-sso-provider.md) | register a new OIDC SSO provider in Creatio |
| [resolve-oauth-system-user](../reference/resolve-oauth-system-user.md) | Resolve a Creatio system user (SysAdminUnit) by name or id over DataService REST |
| [set-default-record-rights](../reference/set-default-record-rights.md) | turn record permissions on/off for one object and grant or revoke one of its default |
| [set-object-rights](../reference/set-object-rights.md) | grant or revoke object operation permissions (read/create/edit/delete) for one role on one object, or turn an object'... |
| [set-record-rights](../reference/set-record-rights.md) | grant or revoke a record-level access right on a single Creatio record |
| [uninstall-identity](../reference/uninstall-identity.md) | Remove the local IdentityService attached to a Creatio environment |
| [upload-license](../reference/upload-license.md) | Load license to selected environment |
| [upload-licenses](../reference/upload-licenses.md) | Upload license files to Creatio |
| [verify-oauth-app](../reference/verify-oauth-app.md) | Verify a server-to-server OAuth app: acquire a client_credentials token and run a bearer DataService smoke test |

<!-- commands:end -->
