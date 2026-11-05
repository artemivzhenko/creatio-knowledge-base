---
name: clio-apps
description: Composable applications through clio - list and find installed apps, read an app's entities, create an app or a section, publish, download and deploy an application archive, ALM deploy. Use for "which app owns this", "create a section for the object", "install the app on another environment".
---

# clio: applications

Read on clio 8.1.0.145; only the read commands were verified on Creatio 8.2.3.
Command pages: [reference/](../reference/).

## Workflow

```bash
clio list-apps -e dev                        # installed applications
clio find-app <text> -e dev                  # by name / code / description, with sections
clio get-app-info <Code> -e dev              # package, entities, their columns
clio create-app ...                          # new application (returns the main entity)
clio create-app-section ...                  # a section over an entity inside an app
clio list-app-sections <Code> -e dev
clio download-application <Code> -e dev      # archive
clio deploy-application <archive> -e test    # install elsewhere
```

A new page from [clio-pages](../clio-pages/SKILL.md) becomes reachable only when an
application section (or a workplace entry) points at its entity; `create-app-section` does
that in one call and `place-section-in-workplace` (MCP) adds it to a workplace.

## Traps

- **`create-app` is destructive and bundles several steps** (package, entity, pages,
  section, registration); read its reference page before running it. Not verified on 8.2.3.
- **Find before create**: `find-app` matches a substring across name, code and description;
  an existing app with a similar code wins over a duplicate.

## Commands

<!-- commands:start -->

| Command | Purpose |
| --- | --- |
| [alm-deploy](../reference/alm-deploy.md) | Deploy and install package to Creatio environment via ALM |
| [create-app](../reference/create-app.md) | Create a new application in Creatio |
| [create-app-section](../reference/create-app-section.md) | Create a section inside an existing installed application |
| [delete-app-section](../reference/delete-app-section.md) | Delete a section from an existing installed application |
| [deploy-application](../reference/deploy-application.md) | Deploy app from current environment to destination environment |
| [download-application](../reference/download-application.md) | Download an application package from Creatio |
| [find-app](../reference/find-app.md) | Find installed applications and their sections in a Creatio environment by name, code, or substring pattern |
| [get-app-hash](../reference/get-app-hash.md) | Calculate hash for the app |
| [get-app-info](../reference/get-app-info.md) | Get information about an installed Creatio application |
| [list-app-sections](../reference/list-app-sections.md) | List sections of an existing installed application |
| [list-apps](../reference/list-apps.md) | List installed apps |
| [publish-app](../reference/publish-app.md) | Publish a workspace to a ZIP archive or hub folder |
| [set-app-icon](../reference/set-app-icon.md) | Set application icon |
| [set-app-version](../reference/set-app-version.md) | Set application version |
| [update-app-section](../reference/update-app-section.md) | Update metadata of a section inside an existing installed application |

<!-- commands:end -->
