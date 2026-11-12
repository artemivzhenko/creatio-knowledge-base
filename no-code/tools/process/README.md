---
description: Creatio business processes of 8.x as package files - create a process, add parameters, elements (read/add/modify/delete data, formula, script, gateways, sub-process, timers, signals, user tasks), flows and conditions, captions per culture; rename a schema across a workspace (refactor.py rename-schema); test a process - start it with parameters, assert its result parameters and the records it left (process cases of the UI test utility, proc.py test-config).
---

# Business-process tools and schema rename

Scripts that change Creatio business processes as **package files**, so an agent can build
and refactor processes without the designer and without clio's process tools (which need
CrtProcessBuilder and do not work on Creatio 8.x). Pure Python standard library.

| File | What it does |
| --- | --- |
| `proc.py` | CLI (the commands are listed under Commands) |
| `refactor.py` | `rename-schema`: rename any schema across a workspace and fix every reference |
| [`../creatio_schemas/process/`](../creatio_schemas/README.md) | the library behind both (`ProcessSchema`, element kinds, expression codec); import it for anything the CLI does not cover |
| `../creatio_schemas/process/assets/keymap.json` | the 569 obfuscated metadata keys (`BK4` = FlowElements, `CI2` = TargetRefUId ...) |
| `../creatio_schemas/process/assets/user_tasks.json` | 18 designer user tasks of 8.2.3: parameters, types, defaults, captions in 28 cultures |
| `tests/` | `python tests/test_process_tools.py` - round-trip and build checks on two real processes |

Verified on Creatio 8.2.3 (the test environment): processes built only with these scripts were pushed with
`clio push-pkg` and executed by the platform - a formula (`Counter + 41` → 42), a gateway
branching on an input (`Counter=-100` → "small"), a Read data task counting a table (→ 1),
and a schema rename that kept its UId. 235 designer-made processes (8.2.3 and 8.3.x)
round-trip through the library byte-for-byte.

## Commands

<!-- commands:start -->
```
python proc.py inspect   <package> <Process>
python proc.py new       <package> <Process> --caption "..." [--cultures en-US ru-RU]
python proc.py caption   <package> <Process> <target> en-US="..." [ru-RU="..."]   target: Process | Element | Element.Param | Parameter:Name
python proc.py captions  <package> <Process> [--missing] [--from en-US]
python proc.py fill-captions <package> <Process> [--from en-US]
python proc.py param     <package> <Process> add <Name> --type Text [--direction In|Out|Variable] [--caption ..] [--default ..] [--ref-schema Contact]
python proc.py param     <package> <Process> rename <Old> <New> | remove <Name>
python proc.py element   <package> <Process> add <Name> --kind readData --after X [--before Y] [--caption ..] [--entity UsrOrder] [--set Param=value ..]
python proc.py element   <package> <Process> rename <Old> <New> | remove <Name> | set <Name> Param=value .. [--expr]
python proc.py element   <package> <Process> formula <Name> "<expression>" --result <ProcessParam>
python proc.py element   <package> <Process> values <Name> Column=value .. [--expr]     Add / Modify data: the columns it writes
python proc.py element   <package> <Process> map <Name> Param=value .. [--expr]        sub-process: the called process's parameters
python proc.py element   <package> <Process> filter <Name> "<Column> = {Parameter:X}; <Column> is not null"   Read / Modify / Delete data
python proc.py flow      <package> <Process> add <Src> <Dst> [--condition "{Parameter:X} > 0"] [--name ..] [--caption ..]
python proc.py flow      <package> <Process> remove <Name> | condition <Name> "<expr>"
python proc.py script    <package> <Process> get <Element> [--out file] | set <Element> --file body.cs
python proc.py validate  <package> <Process>
```

| command | what it does |
| --- | --- |
| `new` | create a process: one lane, start -> terminate |
| `inspect` | elements, parameters, flows and problems, with decoded names |
| `validate` | problems only; exit code 1 when there are any |
| `test-config` | write the process's parameters as a Configuration/processes file of the UI test utility |
| `caption` | set a caption: Process | Element | Element.Param | Parameter:Name | a raw key |
| `captions` | list captions of a culture, or those missing in the others |
| `fill-captions` | copy captions missing in a culture from --from |
| `param` | process parameters |
| `element` | process elements |
| `flow` | sequence and conditional flows |
| `script` | script task bodies |
<!-- commands:end -->

## The loop

```bash
clio pull-pkg UsrPkg -e dev --unzip true        # into a scratch folder, or use the workspace copy
python proc.py inspect UsrPkg UsrOrder_Process    # what is there, with decoded names
python proc.py element UsrPkg UsrOrder_Process add ... --dry-run   # see the diff
python proc.py element UsrPkg UsrOrder_Process add ...             # write
clio push-pkg UsrPkg -e dev                       # install
clio call-service -e dev --method GET --service-path "ServiceModel/ProcessEngineService.svc/UsrOrder_Process/Execute?ResultParameterName=Total"
```

`push-pkg` reports designer-edited schemas as "modified locally" and skips them; the
scripted ones install. Run the result through `ProcessEngineService.svc/<Name>/Execute`
(inputs as query parameters, one output via `ResultParameterName`): clio's `run-process` and
`get-process-signature` fail with "FromJson" on any non-trivial schema because clio's own
reader, not the platform, cannot parse it. The run log is `SysProcessLog` /
`SysProcessElementLog` (`ErrorDescription` holds the stack trace).

## Element kinds, expressions and rename

`--kind`: events `start startSignal startTimer startMessage end terminate catchTimer
catchMessage catchSignal throwMessage throwSignal`; gateways `exclusiveGateway
inclusiveGateway parallelGateway`; `formula script subProcess eventSubProcess`; the data
tasks `readData changeData addData deleteData`; `performTask sendEmail openEditPage
preconfiguredPage approval changeAccessRights callWebService userQuestion`; or
`userTask:<SchemaName>` for any of the 18 bundled task definitions. `--entity` binds a data
task or a record-signal start to an object, `--calls` names the process a sub-process
calls, `--message` names the message of a message/signal event.

Every kind was put into one process (`UsrShowcase_Process`: 38 nodes, 37 flows, 18 user
tasks, three alternative starts, a called sub-process, an event sub-process) and read back
through the designer's own `ProcessSchemaRequest` service with every type recognised.

`--after X --before Y` inserts the element between two connected ones (the X→Y flow is
re-pointed to X→new, and new→Y is added); `--after X` alone just adds X→new.

Expressions (conditions, formulas, `--set --expr`) use `{Parameter:Name}` for a process
parameter, `{Element:El.Parameter:P}` for an element output and
`{Element:El.Parameter:P.EntityColumn:<Column or uid>}` for a column of the record an element
read (the column name resolves through the parameter's entity in the workspace); the rest is
passed through. A `{...}` reference in any other form is refused, never written: the platform
reads an unencoded one as "Expression expected" at run time. `validate` checks every stored
expression the same way - flow conditions, formulas, parameter values of the expression kind -
and flags a reference left as text or a meta path to an element or parameter the process does
not have. `inspect` shows the stored meta paths in the same notation.

`rename-schema <workspace-or-package> <Old> <New> [--apply]` moves the schema and resource
folders, rewrites the name in descriptor and metadata, and replaces whole-word occurrences
in every text file under the root (page JS, C#, data). Dry run by default.

## Conditions

A filter written as text (a signal's or a data element's, `--filter`) follows the shared grammar, and so does the
meta-path codec behind `{Parameter:X}` in a formula:
[creatio_schemas/expressions/README.md](../creatio_schemas/expressions/README.md). Every spelling of an operator works
(`=` / `==` / `equal`, `is not null` / `filled`, `not contains`); the codec is `expressions.metapath`, and
`ExpressionCodec` is its `Names` for one process.

## Signals

Two kinds of signal share the start and catch elements; the keys below are what `metadata.json`
stores (`assets/keymap.json` names them).

- **Record signal** - the process starts (or a catch element resumes) when a record of an
  object is added, modified or deleted. `FC2` (`CA6` on a catch) the entity UId; `DZ5` (`CA5`)
  `EntitySignal`, a bit mask: added 1, modified 2, deleted 4; `DZ12` (`CA11`)
  `EntityChangedColumns`, a JSON list of column UIds that must change for `modified`, with
  `DZ11` (`CA7`) `HasEntityColumnChange`; `DZ13` (`CA13`) `EntityFilters`, the conditions the
  record must meet, with `DZ8` (`CA8`) `HasEntityFilters`; `DZ3` (`CA3`) `WaitingEntitySignal`
  true. The event carries one parameter, `RecordId`, read in a script as
  `Get<Guid>("<Element>.RecordId")`.
- **Named signal** - `DZ1` (`CA1`) the name, `DZ2` (`CA2`) `WaitingRandomSignal` true, `DZ3`
  (`CA3`) false. Thrown by a `throwSignal` element (`CC1` the name) or by C#
  (`ProcessEngine.ThrowSignal`), so one process can wake another.

The filter is one object holding two serialisations of the same `Terrasoft.FilterGroup`: the
designer's (`serializedFilterEditData`, class names and captions on every node) and the
runtime's (`dataSourceFilters`, the bare tree). `creatio_schemas/filters.py` builds both from
`Column op value` conditions (`=`, `!=`, `>`, `>=`, `<`, `<=`, `starts with`, `contains`,
`ends with`, `is null`, `is not null`; `;` between conditions means AND; values are typed by
the column: Boolean, Integer, Money/Float, a lookup takes the record id) and summarises either
back into one line (`UsrOrder where UsrAmount > 100`), the same line DCM cases use.

```bash
python proc.py element UsrPkg UsrOrder_Process add OnBigAmount --kind startSignal --entity UsrOrder \
    --on modified --columns UsrAmount --filter "UsrAmount > 100; UsrStatus is not null"
python proc.py element UsrPkg UsrOrder_Process signal OnBigAmount --on added,modified     # change later
python proc.py element UsrPkg UsrOrder_Process add WaitClosed --kind catchSignal --message OrderClosed --after X
```

Verified on 8.2.3: a process with a `modified` signal on an order object (one column, one
condition) and a script that writes a mark into the record was pushed, published with
`clio compile-configuration` (see the trap below) and fired by an OData update above the
threshold: one run in `SysProcessLog`, no error, the mark written. An update below the
threshold started nothing, and the script's own save did not re-fire the signal because the
watched column did not change.

## Values and mappings

**Add data / Modify data** write the columns of one record. The list is one parameter,
`RecordDefValues` (Add) or `RecordColumnValues` (Modify), of type `EntityColumnMappingCollection`;
its `GS2` is a compact JSON `LocalizableParameterValuesList`:
`{"$type": ..., "$values": [{ItemUId, columnMetaPath {value: column UId}, schemaUId {value: object UId},
value {value}, displayValue {value}, parameterValue {value: a JSON ProcessSchemaParameterValue}}]}`.
The designer writes almost every value as a formula (`parameterValue.Source` 3): a number as is,
a string as a quoted literal, `[#BooleanValue.True#]`, a lookup constant as
`[#Lookup.<lookup object UId>.<record id>#]`, `[#SysVariable.CurrentUserContact#]`, or meta paths.
`element values` writes the same; the object must be set first (`--entity`), its columns come from
the workspace (inherited BaseEntity / BaseLookup columns included). A date constant and a
localizable text constant (the designer keeps those in the resources) are not written - pass an
expression.

**Sub-process** (`CK4` the called process): the element carries a copy of each parameter of the
called process (`A3` = the called UId) and one mapping per copy (`GT5` the called parameter,
`GT4` the called process); the value sits in the copy's `L8`. `element map` adds the copies the
element lacks, as the designer does on choosing the process, and sets the values. A sub-process
that runs once per record of a collection (`InputRecordCollection`, with the called parameters
nested in its `L18`; 68 of the 87 calls seen) is refused.

```bash
python proc.py element UsrPkg UsrOrder_Process add AddTask --kind addData --entity UsrTask --after StartEvent1
python proc.py element UsrPkg UsrOrder_Process values AddTask UsrTitle="Call back" UsrPriority=3 UsrOrder={Parameter:OrderId}
python proc.py element UsrPkg UsrOrder_Process add CallChild --kind subProcess --calls UsrChild_Process --after AddTask
python proc.py element UsrPkg UsrOrder_Process map CallChild RecordId={Parameter:OrderId}
```

`inspect` prints them as `values: UsrTitle = "Call back", UsrPriority = 3, UsrOrder = {Parameter:OrderId}`
and `calls UsrChild_Process with RecordId = {Parameter:OrderId}`; `validate` flags a value for a
column the object no longer has (when the workspace holds the whole object). Read from 259 real
processes: 434 Add / Modify elements with 1065 values, 87 sub-process calls; every value list
re-serialises byte for byte. Not yet run on an environment.

**Record filters** of Read data, Modify data and Delete data are the `DataSourceFilters` parameter: the same outer
filter object a signal stores (designer form + runtime form, compact JSON). `element filter` writes it from ANDed
conditions over the element's object (`--entity` first); a right side that is one `{Parameter:X}` or
`{Element:E.Parameter:P[.EntityColumn:C]}` reference becomes the designer's parameter form - `dataValueType` 26, the
value `{"value": "<meta path without [# #]>", "displayValue": "X"}` (runtime form: `{"value": ...}` only), as 1200 of
1200 designer-written filters of the local workspaces hold it. Modify data also gets `IsMatchConditions` true (318 of
318 designer ones have it). `inspect` prints `filter: UsrOrder where Id = OrderId and UsrAmount > 100`.

```bash
python proc.py element UsrPkg UsrOrder_Process filter ReadOrder "Id = {Parameter:OrderId}; UsrStatus is not null"
```

**Value and mapping agree.** An element parameter's value (`L8`) and its mapping row (`BK15`, matched by `GT3` = the
parameter UId) hold the same source; the runtime reads the mapping. Every command here writes both. `validate` reports
`element <El> parameter <P>: value and mapping differ (the platform reads the mapping)` when both carry a value and the
values differ - a filter or a value edited by hand in `L8` only. One side empty is the designer's own form and is not
reported (a localizable text lives in the mapping only; a mapping row without a value; the text of a localizable item in
a value list is in the mapping only, and is ignored in the comparison). Over the 244 processes of the local workspaces
the rule finds 9 parameters, in 2 processes, whose value is `false` and mapping `true`.

## Testing a process

A process is tested by the **process cases** of the UI test utility
(`automatic-creatio-tests`, `ProcessCases/*.act`): the backend tier, kept apart from the page
cases, with the same DSL, validation and report, and no browser. Three commands:

```
use Supervisor
start UsrOrder_Process with Amount=500;Contact=0c48c818-08f0-4f70-9b58-be512227f3bf
check-result Verdict eq "big"                      # an output or variable parameter
check-result Total ge "5"                          # numbers compare as numbers
check-record UsrOrder UsrName=Order 1 exists       # a side effect, read over OData
check-record UsrOrderLog UsrOrder=<guid> not exists
```

`start` and `check-result` are validated against a description of the process - its
parameters, their types and directions - which this toolkit writes from the package:

```bash
python proc.py test-config packages/UsrPkg UsrOrder_Process --out <tests>/Configuration/processes/UsrOrder_Process.json
```

So a process built as files describes itself for its tests, and a wrong parameter, an output
passed in or a value of the wrong type fails before anything is started.

**Process as a test**: when a backend rule is easiest to prove from inside the platform, build a
process whose input parameters are the case and whose result parameters are the verdict (a
formula or a script task sets them), and assert them with `check-result`. The engine runs the
process synchronously and returns the result parameters in the same call
(`ProcessEngineService.svc/RunProcess`, verified on 8.2.3: a formula, a gateway and a Read data
task; a variable parameter can be passed in and read back).

Trap: a process with user tasks (add / modify data) or a script task pushed as files answers
"Publish the process before starting it" (`SysProcessLog.ErrorDescription`) although the push
compiled with 0 errors: such a process has a compiled model, and the push's build does not
publish it. `clio compile-configuration -e <env>` (3-4 minutes on 8.2.3) does - the next start
ran clean. Formula, gateway and read-data processes run straight after `push-pkg`.

## Keep the schema UId

Never delete and re-create a process to change it: `new` mints a fresh UId, and pushing a
schema whose UId changed makes the platform replace its `SysSchema` row - the localizable
values imported by that same push are deleted with the old row, so every element shows an
empty caption until the next push (verified: 0 rows after the rebuild, 1136 after a
re-push of identical files). Edit the existing files; the UId then stays and captions
survive every push.

## Traps the scripts already handle (do not undo them)

- **Every node must precede every flow in `BK4`.** The platform resolves a flow's
  `TargetRefUId` while reading the array; a node that comes later raises
  `ItemNotFoundException` in `GetBaseElementByUId`. `add_element` inserts before the
  first flow.
- **`descriptor.json` dates are WCF literals** `"\/Date(1762330000000)\/"`; a plain string
  fails the push with "Invalid descriptor: Specified cast is not valid".
- **Filter JSON must be compact.** `ProcessUserTaskUtilities` recognises the data-contract
  filter by its text; the same JSON with spaces after `:` and `,` falls into the legacy
  converter and dies with a NullReference inside the task.
- **Read data keeps its entity in `ResultEntity.L9`**, not in an `EntitySchemaId`
  parameter like Add/Modify/Delete data. `--entity` handles both.
- Element parameters get **new UIds** (never the task schema's), and each gets a `BK15`
  mapping that mirrors its value; `set` keeps the two in sync.
- Element captions go to **en-US only**, parameter captions to **every culture** the
  package has (from the task's own translations), exactly as the designer does. The
  descriptor caption follows en-US.
- `metadata.json` is CRLF, 2-space, no BOM, non-ASCII unescaped; resources are
  BOM + CRLF + tabs, items sorted by key.

## Not covered yet

Date and localizable-text constants in Add/Modify data values, sub-processes that run per
record of a collection, OR groups and nested groups in signal and data element filters (only
ANDed conditions are built; any filter is read), script tasks on an environment whose
configuration does not compile, lanes beyond the first, diagram layout (positions are a
plain left-to-right row; the designer re-arranges on save). Each is a `set` with a raw
value today.

## Regenerating the assets

`creatio_schemas/process/assets/keymap.json` comes from the `DesignModeProperty` attributes and serializer code of
the platform assemblies; `user_tasks.json` next to it from `SysSchema.MetaData` and
`SysLocalizableValue` of a Creatio 8.2.3 site (package CrtProcessDesigner). Re-export them
from the target version when element parameters differ; the tests pin the 8.2.3 shapes.
