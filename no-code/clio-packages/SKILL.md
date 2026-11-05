---
name: clio-packages
description: Move Creatio packages between a local folder and an environment with clio - create a package, push it to the site, pull it back, lock and unlock, versions, dependencies, hotfix, delete. Use for "install the package", "download the package from the environment", "which packages are installed".
---

# clio: packages

Verified on clio 8.1.0.145, Creatio 8.2.3. Command pages: [reference/](../reference/).

## Workflow

```bash
clio list-packages -e dev                     # what the environment has
clio new-pkg UsrMyPackage                     # scaffold locally (descriptor.json, folders)
clio push-pkg UsrMyPackage -e dev             # install the folder (or a .gz) into the site
clio pull-pkg UsrMyPackage -e dev --unzip true   # download the package from the site
clio lock-package / unlock-package UsrMyPackage -e dev
clio set-pkg-version UsrMyPackage 1.0.2       # local descriptor
clio add-package-dependency ...               # see the reference page
clio delete-pkg-remote UsrMyPackage -e dev    # remove from the site
```

The package folder is the unit of exchange: `descriptor.json`, `Schemas/`, `Resources/`,
`Data/`, `Files/`, `Assemblies/`. `push-pkg` installs and (for packages with C#) compiles;
read `clio last-compilation-log -e dev` when it fails.

## Keeping the environment and the files in sync

No-code tools (schemas, pages, business rules - see the other skills) write straight into
the environment's database, not into the local folder. After any such change, **pull the
package and diff it** before touching the files again, or the next `push-pkg` overwrites
the no-code change:

```bash
clio pull-pkg UsrMyPackage -e dev --unzip true     # into a scratch folder
# diff scratch/UsrMyPackage against the workspace copy, then copy the changed files over
```

What a pull after a no-code change looks like on 8.2.3 (verified):

- a new column: `Schemas/<Entity>/metadata.json` (+50 lines per column), a caption line in
  every `Resources/<Entity>.Entity/resource.<culture>.xml`;
- a business rule: a new `Schemas/<Entity>BusinessRule/` folder (3 files) plus its resource
  folder;
- a page edit: the page's `descriptor.json`, `metadata.json` and `<Page>.js`.

## Traps (verified)

- **`Files/<Package>.csproj` differs between the server copy and a workspace copy** (about
  750 lines of churn: imports, property groups). Do not copy it back from a pull; keep the
  workspace one.
- **A pull can drop resource lines the designer no longer needs** (observed:
  `EventsProcessSchema.Caption` vanished from all 28 cultures after a column was added).
  Review the resource diff instead of treating every deleted line as a loss.
- **A package installed from an archive cannot be deleted with `delete-pkg-remote`**
  ("installed from the file archive"); deactivate it in the Installed applications UI or
  remove it through the platform instead.
- **`list-packages` filter argument is `filter`** on clio's MCP (`search` is refused).
- **`pull-pkg --unzip true`** leaves the `.gz` next to the folder; pass a scratch directory
  as the working directory.
- **`get-package-file` and `list-package-files` (MCP) need cliogate 2.0.0.47+**; with the
  2.0.0.43 gate they refuse and name `install-gate`. Updating the gate installs a package
  and compiles the configuration.
- **`unlock-for-hotfix` / `finish-hotfix` (MCP) toggle the package's hotfix state** and
  return at once (verified); `get-pkg-version <path>` crashes in clio 8.1.0.145 - read
  `descriptor.json` directly.

## Commands

<!-- commands:start -->

| Command | Purpose |
| --- | --- |
| [activate-pkg](../reference/activate-pkg.md) | Activate a package in Creatio |
| [add-package](../reference/add-package.md) | Add a package; --as-app also creates a localization schema and injectable resolver |
| [add-package-dependency](../reference/add-package-dependency.md) | Add one or more package dependencies to a package |
| [compressApp](../reference/compressApp.md) | Archive an application directory into ZIP |
| [create-package](../reference/create-package.md) | Create a new package in a Creatio environment |
| [deactivate-pkg](../reference/deactivate-pkg.md) | Deactivate a package in Creatio |
| [delete-pkg-remote](../reference/delete-pkg-remote.md) | delete package from application |
| [extract-pkg-zip](../reference/extract-pkg-zip.md) | extract-pkg-zip |
| [generate-pkg-zip](../reference/generate-pkg-zip.md) | generate-pkg-zip |
| [get-pkg-version](../reference/get-pkg-version.md) | Get package version |
| [install-application](../reference/install-application.md) | Install an application package into a Creatio environment |
| [list-packages](../reference/list-packages.md) | Get list of packages installed in Creatio environment |
| [lock-package](../reference/lock-package.md) | Locks one or more packages in a Creatio environment to prevent modifications and unintended changes |
| [new-pkg](../reference/new-pkg.md) | create new package in a web application |
| [pkg-hotfix](../reference/pkg-hotfix.md) | Enable or disable package hotfix state |
| [pull-pkg](../reference/pull-pkg.md) | download package to local file system from default a web application |
| [push-pkg](../reference/push-pkg.md) | Install package from directory you can use the next command: |
| [remove-package-dependency](../reference/remove-package-dependency.md) | Remove one or more package dependencies from a package |
| [set-pkg-version](../reference/set-pkg-version.md) | set package version |
| [show-package-file-content](../reference/show-package-file-content.md) | List or read compiled package files |
| [uninstall-app-remote](../reference/uninstall-app-remote.md) | Uninstall application |
| [unlock-package](../reference/unlock-package.md) | Unlocks one or more packages in a Creatio environment to enable editing and modifications |

<!-- commands:end -->
