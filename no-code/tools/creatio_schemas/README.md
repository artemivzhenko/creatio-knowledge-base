---
description: Python library behind the process, business-rule and object tools - Schema base class over package files (descriptor, metadata, resources, diff, save), ProcessSchema, RuleSchema, EntitySchema, PageSchema, DcmSchema, UserTaskSchema, the parent-diff engine, element-kind and rule-action registries, workspace lookups; how to add a schema type, a process element or a rule action.
---

# creatio_schemas

The library under `tools/process/proc.py`, `tools/process/refactor.py`, `tools/rules/rules.py` and `tools/objects/objects.py`.
It reads Creatio schemas stored as package files (the clio workspace layout), changes them
and writes them back **byte for byte**: an unchanged schema saves to the bytes it was read
from, and reading (`describe`, `validate`) never changes anything. Pure standard library.

```
creatio_schemas/
  files.py        text I/O that keeps BOM and newlines, JSON dump, UIds, the WCF date, data value types
  resources.py    Resources: resource.<culture>.xml of one schema
  workspace.py    Package (descriptor, UIds); Workspace: schema lookup, entity columns, page models
  schema.py       PackageItem (anything a package installs: files, diff, save), Schema on top of it, Descriptor
  sqlscript.py    SqlScript: SqlScripts/<Name>/ (engine, install type, dependencies)
  diff.py         SchemaDiff: the `= + - ~` metadata of a schema with a parent - apply to the parent, change one path
  refactor.py     rename_schema across a workspace
  clio.py         Clio: call-service and SQL on a saved environment
  cli.py          the shared command-line skeleton (sub-commands, --dry-run, save + validate)
  process/        ProcessSchema, catalog (ElementKind per designer element, user tasks), expressions
  rules/          RuleSchema, model (keys and enums), actions (ActionType registry), builder (spec -> rule),
                  storage (own JSON / replacing diff), engine (the platform rule services)
  dcm/            DcmSchema: stages (lookup records, colours, alternatives), steps (sub-processes, conditions), moves, filter
  usertask/       UserTaskSchema: parameters (shared new_param with processes) and the partial C# class
  entity/         EntitySchema, catalog (column and object flags, BaseEntity/BaseLookup, designer templates,
                  stock object UIds), hierarchy (the merged base of a replacing object, fetched and cached),
                  database (metadata vs the table)
```

## Using it from Python

```python
import sys; sys.path.insert(0, "no-code/tools")
from creatio_schemas import ProcessSchema, RuleSchema

proc = ProcessSchema("packages/UsrPkg", "UsrOrder_Process")
proc.add_param("Total", "Integer", "Out", "Total")
el = proc.add_element("readData", "CountOrders", "Count orders", after="StartEvent1", before="TerminateEvent1")
proc.set_entity(el, "UsrOrder")
print(proc.diff())          # what save() would change
proc.save()

rs = RuleSchema("packages/UsrPkg", RuleSchema.name_for("packages/UsrPkg", "UsrOrder"))
rs.add({"conditions": [{"left": "UsrAmount", "op": "filled"}], "actions": [{"type": "required", "items": ["UsrComment"]}]})
assert not rs.errors()
rs.save()
```

Every schema type has the same surface, from `Schema`:

| Member | What it does |
| --- | --- |
| `Cls(package, name)` / `Cls.create(...)` | open an existing schema / write a new one |
| `files()` | `{path: (text, has BOM)}` - exactly what `save()` writes |
| `diff()` | unified diff of the pending changes against the disk (the CLIs' `--dry-run`) |
| `save()` | writes `files()` and stamps the descriptor's `ModifiedOnUtc` |
| `validate()` / `errors()` | problems; a `warning: ` prefix marks advisory ones, `errors()` drops them |
| `describe()` | the readable report of `inspect` |
| `descriptor`, `resources`, `workspace` | descriptor text, captions per culture, the schemas next to the package |

Elements, flows, parameters and rules stay the plain dicts of `metadata.json` (keys decoded in
`process/assets/keymap.json` and the docstring of `rules/model.py`); the methods keep the
cross-references between them in step (mappings, captions, flow endpoints, generated rules).

## Extending

**A package item that is not a schema** (a SQL script, a data binding): subclass `PackageItem`,
set `self.descriptor` (`Descriptor(path, root="SqlScript")` for another root key) and implement
`files()`; `diff`, `save` and the problem filter come with it.

**A new schema type** (a page, an object, a data binding...): subclass `Schema`, set
`RESOURCE_SUFFIX` (the `Resources/<Name>.<suffix>` folder), implement `load_metadata(text)`
and `render_metadata()` so that an unchanged schema renders to its input, then `validate`
and `describe`. Add a `create` classmethod that writes the files the way the designer does
(`Descriptor.new` gives the date format the push requires). Prove the round trip on real
exports before anything else - see the tests of the two existing types.

**A new process element kind**: add an `ElementKind` to `ELEMENT_KINDS` in
`process/catalog.py` - its class, toolbox UId (`BL7`), size and the keys the designer adds
(read them off a designer-made process). Subclass it and override `extend(proc, el)` when
the element needs parameters or values taken from the element (see `StartSignalEvent`,
`MessageEvent`). A new user task needs no code: re-export `user_tasks.json`.

**A new rule action**: subclass `ActionType` in `rules/actions.py` with `name` (the spec
`type`), `cls` (the platform type), `kinds` (page, entity), `build(builder, spec, rule_uid,
scope)` returning `(action, generated rules, trigger names)`, and `describe(action)`; add an
instance to `ACTIONS`. The builder, validation and `inspect` pick it up from the registry.

**A new column or object flag**: a row in `COLUMN_FLAGS` / `OBJECT_FLAGS` of
`entity/catalog.py` (key, value when on, value when off); the CLI options follow.

**Another schema with a parent** (a replacing page, a replacing process): parse its
metadata with `SchemaDiff`; `apply(parent)` gives the effective schema and `set` / `delete`
write the line the platform would.

**A new rule operand** (formula, 8.3): extend `RuleBuilder.value` in `rules/builder.py` and
`format_expr` in `rules/model.py`.

## Checks

```bash
python no-code/tools/process/tests/test_process_tools.py
python no-code/tools/rules/tests/test_rules_tools.py
python no-code/tools/objects/tests/test_objects_tools.py
python no-code/tools/pages/tests/test_pages_tools.py
python no-code/tools/sqlscripts/tests/test_sqlscripts_tools.py
python no-code/tools/dcm/tests/test_dcm_tools.py
python no-code/tools/usertask/tests/test_usertask_tools.py
```

The fixtures are real 8.2.3 exports; the round trip must stay byte-identical, and reading
must leave `files()` unchanged.
