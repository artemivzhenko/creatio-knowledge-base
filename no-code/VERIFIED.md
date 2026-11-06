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

## Processes built as files (tools/process)

| What | Status | What happened |
| --- | --- | --- |
| `proc.py new` + `push-pkg` | works | start → end process installed; `run-process` and `get-process-signature` read it |
| parameters (Integer, Text; In/Out/Variable) | works | `ProcessEngineService.svc/<P>/Execute?Counter=100&ResultParameterName=Counter` → 141 |
| formula task into a process parameter | works | `{Parameter:Counter} + 41` → 42 |
| exclusive gateway + conditional and default flows | works | `Counter=-100` → "small", `5` → "big" |
| Read data (count mode) over a package entity | works | `ResultCount` → 1, equal to `select count(*)` |
| captions in en-US / ru-RU / uk-UA | works | stored as UTF-8, visible in `SysLocalizableValue` after the push |
| `refactor.py rename-schema` + push | works | `iaDemoA` → `iaDemoRenamed`, same `SysSchema.UId`, executes |
| clio `run-process` on a schema with activities | fails (clio) | "FromJson - Error deserializing process schema" from clio's reader; the platform runs it |
| round-trip of designer-made processes | works | 235 processes (8.2.3 + 8.3.x), 1338 files byte-identical |

## Business rules built as files (tools/rules)

| What | Status | What happened |
| --- | --- | --- |
| own object addon: 4 rules added to `iaTestBusinessRule` + `push-pkg` | works | designer service loads 7 rules with captions; engine: required, set values (text, integer, `CurrentUserContact`), lookup filter, read-only with reset |
| lookup filter + its two generated rules | works | engine returns `crt.FilterLookup`; changing the source returns ClearValue `crt.SetValue ... = null` |
| set values on an existing record | by design | skipped (`skip: true`) on "data loaded" of an existing record; fires on a change or `--state Create` |
| own page addon: hide two elements, required via `PDS.iaNumber` | works | `GetBusinessRules` serves both rules to the page; execution is client-side (not run here) |
| replacing addon of a base object (`ContactAddressBusinessRule`, base in CrtBase) | works | new rule fires; base generated rule disabled by `BR4 false`: `PopulateValue` fired before, not after |
| pull after push | works | metadata, properties, resources identical; descriptor date loses milliseconds |
| push over an addon saved by the designer / clio MCP | skipped | "modified locally" (`IsChanged`, `IsLocked`); pulled first, cleared the two flags, pushed |
| round trip of real rule schemas | works | 134 schemas (8.2 / 8.3 / 10.0, own and replacing) metadata byte-identical |

## Objects built as files (tools/objects)

| What | Status | What happened |
| --- | --- | --- |
| object flags off (`virtual`, `db-view`) on a designer-changed `iaOrder` + `push-pkg` | works | before: the table kept none of the designer's changes; after: index on `iaAmount` / `iaContactId`, `SysiaOrderRight`, `RecordInactive` created |
| add Integer (required, default), MediumText, Lookup to `Contact`; `iaContact` weak reference off | works | columns, index, foreign keys `NO ACTION` / `CASCADE` as the metadata says; `probe` 27 ok, 0 mismatches |
| new lookup (`BaseLookup`) + new object with ShortText, Lookup, Lookup with cascade, Date, Float2, Boolean default | works | tables built on push, `probe` 21 + 13 ok; DataService reads `iaShippedOn` as Date (8), not DateTime |
| pull after push | works | `iaOrder` files byte-identical to what the scripts wrote |
| designer-made replacing `Account` (base columns changed) read against the fetched base | works | base merged from 5 packages with the platform's hierarchy function; every line resolves; `EG1.BK8` equals the events process of the copy merged last; decoded required, ShortText > LongText, caption - each confirmed by clio's column view |
| new replacing `Contact`: base index on / off, text widened, base default, base caption, own column | works | push applied all: `varchar(250)`, index created / dropped, runtime default True, caption; `probe` 108 ok; pull identical except the descriptor date the install stamps |
| round trip of real objects | works | 344 schemas (8.1-10.0, own and replacing) byte-identical; 292 resolve their parent |

## SQL scripts built as files (tools/sqlscripts)

| What | Status | What happened |
| --- | --- | --- |
| function + view depending on it (view sorts first by name) + `push-pkg` | works | install log: the function ran first, then the view; `"iaFnShipmentLabel"('42')` = `SHP-42`, the view exists |
| MSSQL script in a PostgreSQL install | by design | skipped, recorded in `SysPackageSqlScript`, no error |
| re-push unchanged / after a body change | works | unchanged: nothing ran; changed: only that script ran (run log `v1,v2`) |
| `probe` | works | recorded engine, install type, no `LastError`, body MD5 equal to the file |
| round trip | works | 39 scripts (own packages + ProcessLibrary) byte-identical, descriptor re-dump identical |

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
