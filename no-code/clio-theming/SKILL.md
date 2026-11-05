---
name: clio-theming
description: Branding through clio - custom themes (create, build, update, assign to a user, clear the cache), the product logo and the login background. Use for "change the logo", "create a theme", "brand colours".
---

# clio: themes and branding

Read on clio 8.1.0.145. **Themes need Creatio 10.0+**: on 8.2.3 `list-themes` refuses with
`[version-too-old]` and `check-theming-access` gets "Access is denied" from the server
(verified). `advise-theme-palette` is offline and works anywhere (`operation: triage` with
a `colors` list; the operations are triage, adapt-primary, derive-secondary, accent-*,
validate-color, preview). Command pages: [reference/](../reference/).

```bash
clio list-themes -e dev
clio create-theme ... / update-theme ... / build-theme ...
clio set-user-theme ...
clio clear-themes-cache -e dev
clio set-logo <file> -e dev
clio set-background-image <file> -e dev
```

The MCP side adds `advise-theme-palette` (colour verdicts) and `check-theming-access`
(whether the caller may manage themes). All theme operations are reversible: keep the
previous theme name and the original image files.

## Commands

<!-- commands:start -->

| Command | Purpose |
| --- | --- |
| [build-theme](../reference/build-theme.md) | build the artifacts of a Creatio theme from brand colours and fonts |
| [clear-themes-cache](../reference/clear-themes-cache.md) | refresh only the Creatio theme cache |
| [create-theme](../reference/create-theme.md) | create a custom Creatio theme on an environment |
| [delete-theme](../reference/delete-theme.md) | delete a custom Creatio theme from an environment |
| [get-theme](../reference/get-theme.md) | read the content (theme.css) and metadata of a custom Creatio theme |
| [list-themes](../reference/list-themes.md) | list the custom Creatio themes available on an environment |
| [set-background-image](../reference/set-background-image.md) | set an image as the environment's shell background |
| [set-logo](../reference/set-logo.md) | apply the product logos and the browser-tab favicon from local image files and bind them into a package |
| [set-user-theme](../reference/set-user-theme.md) | apply a theme to the current user's profile |
| [update-theme](../reference/update-theme.md) | overwrite an existing custom Creatio theme on an environment |

<!-- commands:end -->
