---
name: clio-pages
description: Freedom UI pages through clio - list pages, create a page from a template, read the page body, add fields and components, validate and save, localize, entity and page business rules, component metadata. Use for "add a field to the page", "create a form page", "business rule", "which components exist".
---

# clio: Freedom UI pages

Verified on clio 8.1.0.145, Creatio 8.2.3. Command pages: [reference/](../reference/).
The page tools are at their best through clio's MCP server
([clio-mcp](../clio-mcp/SKILL.md)); the CLI verbs exist for `create-page`, `get-page`,
`update-page`, `list-pages`, `list-page-templates`, `localize-page`.

## Editing a page

1. `list-pages --package-name <pkg>` - the schema names and their templates.
2. `get-page --schema-name <Page>` - writes `body.js` (own body, editable), `bundle.json`
   (merged hierarchy, read-only) and `meta.json` to `.clio-pages/<Page>/`. Read
   `meta.json` first: `designPackageName` is where the save will go.
3. Edit `body.js` **by parsing the marker sections as JSON**
   (`/**SCHEMA_VIEW_CONFIG_DIFF*/[...]/**SCHEMA_VIEW_CONFIG_DIFF*/` and the others),
   changing the arrays, and serialising back. String splicing produced an invalid body
   twice before the JSON route worked (verified).
4. `update-page --dry-run true` - the real validation against the environment.
5. `update-page --verify true` - save; the response lists the resulting operations and a
   checksum used for conflict detection on the next save.
6. Pull the package ([clio-packages](../clio-packages/SKILL.md)).

A bound field needs two entries: an `insert` in `viewConfigDiff` (`type`, `label:
"$Resources.Strings.<Column>"`, `control: "$<Column>"`, `layoutConfig`, `parentName`) and an
attribute in the view model config (`"<Column>": {"modelConfig": {"path": "PDS.<Column>"}}`).
Field captions come from the column captions automatically. Nine fields of six component
types (`crt.Input`, `crt.NumberInput`, `crt.Checkbox`, `crt.DateTimePicker`,
`crt.ComboBox`) were added this way and rendered correctly (verified).

## Creating a page

```bash
clio list-page-templates -e dev
clio create-page UsrOrder_FormPage --template PageWithTabsFreedomTemplate --package-name UsrPkg --entity-schema-name UsrOrder -e dev
clio create-page UsrOrder_ListPage --template ListPageV2Template ...
```

The page is bound to the entity and empty; it is not reachable until a section or an
application exposes it ([clio-apps](../clio-apps/SKILL.md)).

## Business rules

MCP tools: `create|read|update|delete-entity-business-rules` and the `-page-` family.
Read `get-guidance business-rules` and the full tool contract first (the short contract
drops the 25 examples). A rule is a condition group plus actions (`make-required`,
`make-read-only`, `set-values`, `apply-filter`, show/hide for page rules).

## Traps (verified)

- **The designer of 8.2.3 knows only six comparison operators**: filled, not filled,
  equal, not equal, contain, not contain (ids 0-3, 11, 12 in the client bundle). clio
  happily saves `greater-than` (id 7) and reads it back, but the designer shows the rule
  with an empty condition. Check the environment's operator set before using relational
  comparisons on 8.x.
- **The save goes to the "current package for development", not to the page's package**
  when they differ: `meta.json` says `designPackageName` and
  `willCreateReplacingInDesignPackage`. Set the system setting (or `target-package-uid`)
  before saving.
- **`validate-page` is offline and warns on every template container** ("unresolved
  parentName SideAreaProfileContainer"); use `update-page --dry-run true` instead.
- **Pages on 8.2.3 use `viewModelConfig` / `modelConfig`, not the `*Diff` arrays** that
  pages created from a template on the same site use. Keep whichever form the page has.
- **`page-smoke` needs a Chromium on the machine running clio and asks once** which one
  to use; without a browser there is no UI check.
- **Page-level rules work on 8.2.3** (verified): `create-page-business-rules
  {page-schema-name, rules:[{caption, condition, actions:[{type:"hide-element",
  items:["<element>"]}]}]}`, read returns `name` and block uIds, update is a full
  replacement by `name`, delete by `rule-names`.
- **A page is reachable only through a section in a workplace.** MCP
  `place-section-in-workplace {section-code, workplace-name, workplace-type, roles,
  package-name}` creates or reuses the workplace and binds the rows into the package;
  `section-code` is `SysModule.Code` (verified: the caption is refused). Get the code
  from `list-entity-client-schemas --entity-name <Entity>`.
- **`get-mobile-page-conversion-guide` fails on 8.2.3**: the mobile template it reads is
  absent on this version.

## Commands

<!-- commands:start -->

| Command | Purpose |
| --- | --- |
| [component-registry-refresh](../reference/component-registry-refresh.md) | Refresh the local Freedom UI component |
| [create-page](../reference/create-page.md) | Create a new Freedom UI page from a supported template |
| [create-related-page-addon](../reference/create-related-page-addon.md) | Bind Freedom UI pages to an object: which page opens by default for a record and which page is used to add a record (... |
| [export-component-registry](../reference/export-component-registry.md) | Write the full Freedom UI component registry for a resolved platform version to a file |
| [get-classic-list-columns](../reference/get-classic-list-columns.md) | Resolve the effective default columns of a Classic section list |
| [get-classic-page-sources](../reference/get-classic-page-sources.md) | Collect the Classic page sources for folding and write the manifest JSON to disk |
| [get-component-info](../reference/get-component-info.md) | Get curated Freedom UI component metadata by component |
| [get-page](../reference/get-page.md) | Read a Freedom UI page as a merged bundle plus raw schema body |
| [get-page-hierarchy](../reference/get-page-hierarchy.md) | Read the full Freedom UI page replacing-schema chain (root first) with each schema's raw body in one round-trip |
| [get-related-page-addon](../reference/get-related-page-addon.md) | Read an object's current RelatedPage configuration (the bound default/add pages per audience and type) |
| [list-page-templates](../reference/list-page-templates.md) | List Freedom UI page templates available for create-page |
| [list-pages](../reference/list-pages.md) | List Freedom UI page schemas in a Creatio environment |
| [localize-page](../reference/localize-page.md) | Add or update translations of a Freedom UI page's captions in one culture |
| [sync-pages](../reference/sync-pages.md) | Updates multiple Freedom UI page schemas in a single MCP call |
| [update-page](../reference/update-page.md) | Update the raw schema body of a Freedom UI page |

<!-- commands:end -->
