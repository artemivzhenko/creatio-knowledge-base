# What was actually run

Every row below was executed against a real environment, not read from the docs.

- Environment: Creatio **8.2.3.1351**, .NET Framework host, PostgreSQL, cliogate **2.0.0.43**, no CrtProcessBuilder (it does not compile on 8.2.3), no CrtDataForge.
- Tooling: clio **8.1.0.145** (`clio ver`), its MCP server over stdio, called through `clio-run` unless the tool is resident.
- Date: 2026-11-05 (business rules, columns, pages: 2026-10-30).
- Writes went into the disposable package `iaTest`; nothing was run that destroys an environment.

Status legend: **works** - did what the contract says and the result was read back through the platform; **fails on 8.2.3** - the platform lacks the service or type, the tool reports it; **needs gate ≥ 2.0.0.47** - refused until cliogate is updated; **by design** - the tool refused for a reason an agent must satisfy first; **not run** - destructive or environment-level, deliberately skipped.

## clio MCP tools that have no CLI counterpart (96)

| Tool | Status | What happened |
| --- | --- | --- |
| add-item-model | works | 920 C# entity models generated into a folder in 14 s |
| advise-theme-palette | works | `operation: triage` with 4 colours; operations are triage, adapt-primary, derive-secondary, accent-*, validate-color, preview - `check` is refused |
| assert-infrastructure | works | reports k8=fail, local=fail, filesystem=pass on a plain dev box; 15 s |
| check-settings-health | works | reported the broken `ActiveEnvironmentKey` before the fix, `healthy` after |
| check-theming-access | fails on 8.2.3 | server answers "Access is denied" (theming service is 10.x) after a 36 s wait |
| clear-redis-db-by-credentials / -by-environment | not run | the CLI `clear-redis-db` is the same operation |
| clio-run | works | the executor used for every hidden tool here |
| clio-run-destructive | deprecated alias | |
| compile-creatio | works | `package-name: iaTest`: returns after 47 s with an operation-id while the build continues |
| compile-status | works | polled every 15 s; `running` → `succeeded` after 5 min 12 s, `exit-code 0` |
| configure-knowledge-feedback-policy | not run | user decision |
| create-business-process, modify-business-process, modify-business-process-as-new-version, describe-business-process, validate-process-graph, list-user-tasks, set-active-business-process-version | fails on 8.2.3 | "install CrtProcessBuilder" - and that package does not compile on 8.2.3 |
| create-entity-business-rules / read / update / delete | works | create, full-replacement update by `name`, read-back, delete; see the operator trap in clio-pages |
| create-page-business-rules / read / update / delete | works | hide-element rule on `iaTests_FormPage`: create → read → update caption → read → delete, all `succeeded: 1` |
| create-sys-setting, get-sys-setting, update-sys-setting, list-sys-settings | works | Text setting created with `v1`, updated to `v2`, read back each time; list returns code, type, value, flags |
| create-user-task | fails (clio 8.1.0.145) | prefix dead end: CLI demands `Usr`, site demands `ia`; with parameters `Item with name "Enum" not found` |
| dataforge-* (8 tools) | fails on 8.2.3 | "require Creatio platform version 10.0.0 or later" |
| delete-app | not run | destructive, no disposable app |
| describe-environment | works | core version, culture, maintainer, framework kind |
| download-configuration-by-build | not run | needs an unpacked build folder |
| download-configuration-by-environment | works | `workspace-path` must be an existing workspace (a scratch folder is refused "Workspace path not found"); copied the NetFramework core into `C:\Creatio\workspaces\ti823` in 4 s |
| execute-esq, execute-esq-to-file | works | SelectQuery must sit in `query`; returned the `iaTest` row; file variant wrote the JSON |
| find-empty-iis-port | works | reported IIS port discovery unavailable on this host (range 40000-42000) |
| finish-hotfix, unlock-for-hotfix | works | hotfix state on `iaTest` enabled then disabled |
| get-component-info-to-file, get-request-info, get-request-info-to-file | works | local catalogs; `crt.Input` and `crt.SaveRecordRequest` |
| get-email-template | fails on 8.2.3 | HTML page instead of JSON (`'<' is an invalid start of a value`) for an existing template id |
| get-fsm-mode | works | `mode: off`, static file content paths |
| get-guidance | works | ~170 articles; `name=list` for the catalog |
| get-knowledge-feedback-policy, get-telemetry-consent | works | read-only |
| get-mobile-page-conversion-guide | fails on 8.2.3 | mobile template `MobilePageWithTabsFreedomTemplate` is absent |
| get-package-file, list-package-files | needs gate ≥ 2.0.0.47 | refused with the exact version and the `install-gate` hint |
| get-schema-name-prefix, get-target-package | works | `ia`, `iaTest` |
| inspect-user, inspect-role | works | `action: list` with filters (`user-login`, `name`), paged |
| inspect-access | works | `action` must be one of ip-list, delegations, operations, operation-grants (`list` refused) |
| inspect-license | works | `action` user-list or role-list and a GUID `user-id` / `role-id`; returned `[]` for Supervisor |
| link-from-repository-* (3) | not run | FSM-only |
| list-creatio-builds | works | reports the configured products folder is missing |
| list-db-templates | not run | needs a PostgreSQL server name |
| list-entity-client-schemas-to-file | works | sections, cards and lists bound to `iaTest` |
| list-printables | works | 0 printables on this environment |
| odata-create, odata-read, odata-read-to-file, odata-update, odata-delete | works | full CRUD on `iaTest`: create (`rows`), update (`id` + `confirm: true` + `data`), read with structured `filters`, delete, read-back `count: 0` |
| page-smoke | by design | asks once which Chromium to use; declined on this machine |
| place-section-in-workplace | works | `section-code` is `SysModule.Code` (`iaTest`, not the caption); created workplace "Clio test workplace" for "All employees", bound into `iaTest` |
| restart-by-environment-name, restart-status | works | `waitReady: true`: site back in 30 s, status `ready` |
| restart-by-credentials | not run | same as above with inline credentials |
| restore-db-* (3), start-creatio, stop-creatio, stop-all-creatio, set-fsm-mode | not run | environment-level |
| run-process | not run | no disposable process on the environment |
| send-telemetry, withdraw-telemetry-consent | not run | user decision |
| show-passing-infrastructure | works | 1 local database, 0 Redis, filesystem available |
| trigger-smoke | by design | creates the record and waits 15 s for a process run; without a signal process on `iaTest` it reports no run (the record is created and cleaned up) |
| update-email-template | not run | `get-email-template` already fails on this version |
| validate-page | works | offline; warns on every template container (use `update-page --dry-run`) |
| get-record-rights (also CLI) | fails on 8.2.3 | `RightsService/GetRecordRights` answers an HTML page |

## CLI commands run on the same environment

| Command | Status | What happened |
| --- | --- | --- |
| ver, show-web-app-list, ping, healthcheck, get-info, get-user-culture, hosts, get-webservice-url, check-nuget-update | works | |
| auth-status | fails (clio 8.1.0.145) | `No service for type 'Clio.Command.AuthStatusCommand' has been registered` - DI bug in this build |
| get-build-info | fails (clio 8.1.0.145) | `Object reference not set to an instance of an object` with no arguments; the doc page has no example |
| show-local-envs | hangs | no output within 180 s; killed |
| list-packages, find-entity-schema `--search-pattern`, get-entity-schema-properties `--schema-name`, get-entity-schema-column-properties, get-page-hierarchy, get-related-page-addon, get-classic-list-columns, list-entity-client-schemas, get-client-unit-schema, list-pages, list-page-templates, list-apps, find-app, list-app-sections `--application-code`, get-object-rights `--entity-schema-name`, get-app-hash, get-component-info, last-compilation-log | works | every one needs named options; a positional schema or package name fails with "is required" |
| get-entity-connections | fails on 8.2.3 | `EntityConnections is not registered` (the add-on type is 10.x) |
| get-app-info `--code` | fails on 8.2.3 | `Column by path Package not found in schema ApplicationEntity` |
| get-schema on a page name | by design | `get-schema` reads C# source schemas only; pages are `get-client-unit-schema` / `get-page` |
| get-process-signature | by design | resolves by code or caption; a missing process returns `processResolutionFailed` |
| get-pkg-version `<path>` | crashes (clio 8.1.0.145) | exit 139 with a stack trace inside `ConsoleLogger` |
| list-themes | fails on 8.2.3 | `[version-too-old] requires Creatio 10.0.0 or later` |
| execute-sql-script (`-f`, `-v json -d`, inline from bash, `\|nl\|`) | works | see clio-sql-and-data |
| pull-pkg `--unzip true`, push via designer services, modify-entity-schema-column, create-entity-schema, create-lookup, create-page, update-page, install-process-builder, delete-pkg-remote | see the block skills | run on 2026-10-30 |
