---
description: Freedom UI page business rules and object (entity) business rules of Creatio 8.x as package files - create, edit, disable, remove; required, read-only, show/hide, set values, filter lookup; replacing addons of base objects; proof through the platform rule engine.
---

# Business-rule tools

Scripts that create and change Creatio **business rules** (object level and Freedom UI page
level) as **package files**, then prove them on an environment through the platform's own rule
engine. Pure Python standard library.

| File | What it does |
| --- | --- |
| `rules.py` | CLI (the commands are listed under Commands) |
| [`../creatio_schemas/rules/`](../creatio_schemas/README.md) | the library behind it (`RuleSchema`, spec builder, action registry, both storage forms, `RuleEngine`); import it for anything the CLI does not cover |
| `tests/` | `python tests/test_rules_tools.py` - round trip and build checks on a real 8.2.3 export |

Verified on Creatio 8.2.3 (the test environment): rules built only with these scripts were pushed with
`clio push-pkg`, loaded by the rule designer's own service, executed by the platform's rule
engine with the expected actions, and pulled back byte-identical (only the descriptor date
loses its milliseconds). The metadata of 134 rule schemas from real packages (8.2, 8.3, 10.0)
round-trips byte-for-byte; so do their resources, except one third-party repo whose git
checkout had turned them into LF.

## Commands

<!-- commands:start -->
```
python rules.py inspect  <package> <Target>
python rules.py new      <package> <Target> [--parent-uid U] [--target-uid U --kind entity|page] [--version 8.3.2.4199]
python rules.py add      <package> <Target> --spec rule.json        (one rule or a list; see README for the spec)
python rules.py replace  <package> <Target> <Rule> --spec rule.json (rebuild keeping UId, name and caption key)
python rules.py remove   <package> <Target> <Rule>
python rules.py enable   <package> <Target> <Rule> | disable <package> <Target> <Rule>
python rules.py remove-base <package> <Target> <BaseRuleUId>        (replacing addon only)
python rules.py caption  <package> <Target> <Rule> en-US=".." [ru-RU=".."]
python rules.py validate <package> <Target>
python rules.py probe    <package> <Target> Attr[:Type]=value .. --env dev [--trigger Attr ..] [--state Create]
                         entity: run the deployed rules in the platform engine; page: list the rules served to it
```

| command | what it does |
| --- | --- |
| `new` | create the addon <Target>BusinessRule (own, or replacing with --parent-uid) |
| `inspect` | the rules, decoded, and the changes to base rules |
| `validate` | problems; exit code 1 on errors (warnings do not count) |
| `add` | add rules from a spec file |
| `replace` | rebuild a rule from a spec keeping its UId, name and caption |
| `remove` | remove a rule with its generated rules |
| `enable` | enable a rule (a base rule by UId) |
| `disable` | disable a rule (a base rule by UId) |
| `remove-base` | replacing addon: delete a base rule by UId |
| `caption` | set a rule caption |
| `probe` | prove deployed rules on an environment |
<!-- commands:end -->

## Where rules live

One addon schema per target, `<Target>BusinessRule` (AddonSchemaManager, `AddonName`
`BusinessRule`):

```
Schemas/<Target>BusinessRule/{descriptor,metadata,properties}.json
Resources/<Target>BusinessRule.Addon/resource.<culture>.xml
```

`properties.json` binds it: `TargetSchemaManagerName` is `EntitySchemaManager` (object rules,
they apply on every page of the object) or `ClientUnitSchemaManager` (rules of one Freedom UI
page); `TargetSchemaUId` is the **base** schema's UId (for a replacing copy of `Contact`, the
UId of `Contact` itself).

`metadata.json` comes in two forms and the tools keep each as it is:

- **own addon** - full JSON, rules in `MetaData.Schema.AD4.BRS1`. Used when the target was
  created in the package, or a base target has no rules yet.
- **replacing addon** - when a base package already has `<Target>BusinessRule`, the copy in
  your package is a line diff: `+ MetaData.Schema.AD4.BRS1 {rule}` adds a rule,
  `+ MetaData.Schema.AD4.BRS1.["<uid>"].BR4 false` disables a base rule,
  `- MetaData.Schema.AD4.BRS1.["<uid>"]` deletes one, `~ MetaData.Schema.AD4.BRS1 [...]` is
  the order. No BOM, CRLF, no final newline.

Rule captions are `AddonConfig.Rules.<rule uid>.Caption`, en-US only (as the designer writes
them); the addon's `Caption` is in every culture of the target.

## The loop

```bash
clio pull-pkg UsrPkg -e dev --unzip true                      # or use the workspace copy
python rules.py inspect  UsrPkg UsrOrder                       # rules of the object, decoded
python rules.py add      UsrPkg UsrOrder --spec rule.json --dry-run
python rules.py add      UsrPkg UsrOrder --spec rule.json
clio push-pkg UsrPkg -e dev
python rules.py probe    UsrPkg UsrOrder UsrStatus=<guid> UsrAmount=0 --env dev --trigger UsrStatus
python rules.py probe    UsrPkg UsrOrder_FormPage --env dev   # page rules: what the page receives
```

`<Target>` is the object or page name; the addon name works too. A rule is addressed by its
name (`BusinessRule_1a2b3c4`), UId or caption.

## The spec

One JSON object per rule (a file may hold a list):

```json
{
  "caption": "Amount required for big orders",
  "logic": "and",
  "conditions": [
    {"left": "UsrStatus", "op": "equal", "value": "<status guid>"},
    {"left": "UsrAmount", "op": "filled"},
    {"left": "UsrOwner", "op": "not-equal", "sys": "CurrentUserContact"},
    {"left": "UsrManager", "op": "equal", "attr": "UsrOwner"}
  ],
  "actions": [
    {"type": "required", "items": ["UsrComment"]},
    {"type": "set", "values": {"UsrPriority": "<guid>", "UsrNote": "auto", "UsrOwner": {"sys": "CurrentUserContact"}, "UsrCity": null}}
  ]
}
```

- `when`: the conditions as text in the shared grammar ([creatio_schemas/expressions/README.md](../creatio_schemas/expressions/README.md)),
  `"when": "UsrAmount > 100; UsrOwner = sys:CurrentUserContact"`; added after `conditions`, so a spec may use either or both. An unquoted number or
  `true`/`false` is a number or a boolean, `attr:X` / `{Record:X}` an attribute, `sys:X` a system value, `setting:X` a setting.
  `op` of a `conditions` entry takes the same spellings as the text. `inspect` prints the `when` line in this grammar (`is null`, `is not null`, `=`).
- `op`: `filled`, `empty`, `equal`, `not-equal`, `contain`, `not-contain`; `greater`,
  `greater-or-equal`, `less`, `less-or-equal` only on 8.3+ (validate flags them on 8.2).
- right side: `value` (constant; `null` = empty lookup), `attr` (another column, `A.B` paths
  through lookups work), `sys` (`CurrentUser`, `CurrentUserContact`, `CurrentUserAccount`,
  `CurrentDate`, `CurrentDateTime`, `CurrentTime`), `setting` (a system setting code).
- types and lookup reference schemas are read from the workspace (entity columns, the page's
  `viewModelConfig` and data sources). For a target outside the workspace give `"type":
  "ShortText"` and, for lookups, `"ref": "Account"` in the condition.
- actions: `required`, `optional`, `readonly`, `editable` (both kinds); `show`, `hide` (pages
  only; items are **element names** of `viewConfigDiff`); `set` (objects only; `values` as
  above); `filter-lookup` (objects only):
  `{"type": "filter-lookup", "column": "City", "by": "Country", "source": "Country",
  "column_ref": "City", "source_ref": "Country", "populate": true, "clear": true}` = show in
  City only cities whose Country equals the record's Country; it adds the designer's two
  generated rules (clear City when Country changes, fill Country from the chosen City);
  `static-filter` (objects): `{"type": "static-filter", "column": "UsrType", "filter": <filter
  JSON of the designer>}`.
- page conditions name **attributes**; `PDS.Column` is accepted and mapped to the attribute
  bound to it. Element names and attribute names of a page are different things.
- optional: `name` (default `BusinessRule_<7 hex>`), `enabled: false`, `scope` (a list data
  source of a list page: writes `BRX2` / `BRT3`).
- triggers are derived: every attribute in the conditions (and the filter source) plus
  "data loaded".

## Proving a rule: `probe`

Object rules run on the server: `ServiceModel/BusinessRulesEngineService.svc/Execute` is what
every Freedom UI page calls, so `probe` sends a record state and prints the actions:

```
BusinessRule_8c9965d: crt.SetValue UsrComment = "filled by rule"
BusinessRule_eb9103a: crt.SetReadonlyPropertyActionApplier UsrDate = true  (reset)
```

`(reset)` means the condition is false and the property returns to default. Give
`--trigger <Attr>` for "the user changed Attr" (default: the record was loaded) and
`--state Create` for a new record: **set-values are skipped when an existing record loads**,
they fire on a change or on a new record. Values: JSON literals or text; `Name:Type=value`
sets the type when the object is not in the workspace (a `null` without a type breaks the
engine with a NullReference).

Page rules execute in the browser. For a page `probe` calls
`BusinessRulesManagerService.svc/GetBusinessRules` and lists the rules the page will receive;
the behaviour itself needs a browser.

The designer's view of the same rules: `AddonSchemaDesignerService.svc/GetSchema` with
`{"addonName":"BusinessRule","targetSchemaUId":"<uid>","targetSchemaManagerName":"EntitySchemaManager","useFullHierarchy":true}`
(the hierarchy flag merges base rules with your overrides - that is where base rule UIds come
from).

## Traps (verified on 8.2.3)

- **A designer- or clio-saved addon is "modified locally"** (`SysSchema.IsChanged` and
  `IsLocked` true) and `push-pkg` skips it. Either keep editing it through the designer/clio,
  or pull it first, then clear the two flags for that schema and push the files. Never push
  an addon you did not pull after the last designer save: the push replaces it whole.
- **Base targets.** When a base package has `<Target>BusinessRule`, create a replacing addon:
  `rules.py new <pkg> Contact --parent-uid <base addon UId> --target-uid <Contact UId> --kind entity`
  (`select "UId", "Name", "ExtendParent" from "SysSchema" where "Name" in ('ContactBusinessRule', 'Contact')`).
  Without a base addon create an own one with `--target-uid` only. The package must depend on
  the base addon's package.
- **Comparisons 5-8 (greater, less ...) do not exist on 8.2** (`BusinessRuleExpressionComparisonType`
  of 8.2.3 stops at 0-3, 11, 12). The 8.2 designer shows such a rule with an empty condition.
- **Show/hide and set-values are split by kind**: show/hide only in page rules, set-values and
  filters only in object rules (the 8.x designers offer them that way).
- **Filter lookup brings two generated rules** (`Autogenerated_<parent>_ClearValue` /
  `_PopulateValue`, `BR5` parent rule, `BR6` the filter action). Disabling "populate" is
  `BR4 false` on the generated rule; removing the parent removes them.
- **Page rules point at elements and attributes by name.** Renaming a field on the page breaks
  them silently; `validate` warns about names it cannot find (also for names that come from a
  parent template - those are fine).
- Rule captions in other cultures are optional; the designer itself writes en-US only.

## Not covered

Formula expressions (`BusinessRuleFormulaExpression`, 8.3 designer) and system-setting
operands are passed through when present but not built from the spec beyond `setting`;
Classic UI (7.x) `businessRules` in page JS are a different mechanism (none in the corpus).
