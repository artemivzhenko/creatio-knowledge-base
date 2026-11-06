---
description: Creatio business processes of 8.x as package files - create a process, add parameters, elements (read/add/modify/delete data, formula, script, gateways, sub-process, timers, signals, user tasks), flows and conditions, captions per culture; rename a schema across a workspace (refactor.py rename-schema); proven by running the process on an environment.
---

# Business-process tools and schema rename

Scripts that change Creatio business processes as **package files**, so an agent can build
and refactor processes without the designer and without clio's process tools (which need
CrtProcessBuilder and do not work on Creatio 8.x). Pure Python standard library.

| File | What it does |
| --- | --- |
| `proc.py` | CLI: inspect, create, captions, parameters, elements, flows, formulas, scripts, validate |
| `refactor.py` | `rename-schema`: rename any schema across a workspace and fix every reference |
| [`../creatio_schemas/process/`](../creatio_schemas/README.md) | the library behind both (`ProcessSchema`, element kinds, expression codec); import it for anything the CLI does not cover |
| `../creatio_schemas/process/assets/keymap.json` | the 569 obfuscated metadata keys (`BK4` = FlowElements, `CI2` = TargetRefUId ...) |
| `../creatio_schemas/process/assets/user_tasks.json` | 18 designer user tasks of 8.2.3: parameters, types, defaults, captions in 28 cultures |
| `tests/` | `python tests/test_process_tools.py` - round-trip and build checks on two real processes |

Verified on Creatio 8.2.3 (ti823): processes built only with these scripts were pushed with
`clio push-pkg` and executed by the platform - a formula (`Counter + 41` → 42), a gateway
branching on an input (`Counter=-100` → "small"), a Read data task counting a table (→ 1),
and a schema rename that kept its UId. 235 designer-made processes (8.2.3 and 8.3.x)
round-trip through the library byte-for-byte.

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

## Commands

```
inspect       <pkg> <Process>                       elements, parameters, flows, captions, problems
new           <pkg> <Process> --caption ".." [--cultures en-US ru-RU]
caption       <pkg> <Process> <target> en-US=".." ru-RU=".."     target: Process | Element | Element.Param | Parameter:Name
captions      <pkg> <Process> [--missing] [--from en-US]
fill-captions <pkg> <Process> [--from en-US]        copy missing keys from one culture into the others
param         <pkg> <Process> add <Name> --type Integer [--direction In|Out|Variable] [--caption ..] [--default ..]
param         <pkg> <Process> rename <Old> <New> | remove <Name>
element       <pkg> <Process> add <Name> --kind <kind> [--after X] [--before Y] [--caption ..] [--entity UsrOrder] [--set P=v ..]
element       <pkg> <Process> rename <Old> <New> | remove <Name> | set <Name> P=v .. [--expr]
element       <pkg> <Process> formula <Name> "<expression>" --result <ProcessParam>
flow          <pkg> <Process> add <Src> <Dst> [--condition ".."] [--name ..] [--caption ..]
flow          <pkg> <Process> remove <Name> | condition <Name> ".."    (a plain flow is promoted to a conditional one)
script        <pkg> <Process> get <Element> [--out f] | set <Element> --file body.cs
validate      <pkg> <Process>
```

`--kind`: events `start startSignal startTimer startMessage end terminate catchTimer
catchMessage catchSignal throwMessage throwSignal`; gateways `exclusiveGateway
inclusiveGateway parallelGateway`; `formula script subProcess eventSubProcess`; the data
tasks `readData changeData addData deleteData`; `performTask sendEmail openEditPage
preconfiguredPage approval changeAccessRights callWebService userQuestion`; or
`userTask:<SchemaName>` for any of the 18 bundled task definitions. `--entity` binds a data
task or a record-signal start to an object, `--calls` names the process a sub-process
calls, `--message` names the message of a message/signal event.

Every kind was put into one process (`iaShowcase_Process`: 38 nodes, 37 flows, 18 user
tasks, three alternative starts, a called sub-process, an event sub-process) and read back
through the designer's own `ProcessSchemaRequest` service with every type recognised.

`--after X --before Y` inserts the element between two connected ones (the X→Y flow is
re-pointed to X→new, and new→Y is added); `--after X` alone just adds X→new.

Expressions (conditions, formulas, `--set --expr`) use `{Parameter:Name}` for a process
parameter and `{Element:El.Parameter:P}` for an element output; the rest is passed
through. `inspect` shows the stored meta paths in the same notation.

`rename-schema <workspace-or-package> <Old> <New> [--apply]` moves the schema and resource
folders, rewrites the name in descriptor and metadata, and replaces whole-word occurrences
in every text file under the root (page JS, C#, data). Dry run by default.

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

Column values of Add/Modify data (`RecordColumnValues`, a nested serialised list), signal
start filters, sub-process parameter wiring, script tasks on an environment whose
configuration does not compile, lanes beyond the first, diagram layout (positions are a
plain left-to-right row; the designer re-arranges on save). Each is a `set` with a raw
value today.

## Regenerating the assets

`creatio_schemas/process/assets/keymap.json` comes from the `DesignModeProperty` attributes and serializer code of
the platform assemblies; `user_tasks.json` next to it from `SysSchema.MetaData` and
`SysLocalizableValue` of a Creatio 8.2.3 site (package CrtProcessDesigner). Re-export them
from the target version when element parameters differ; the tests pin the 8.2.3 shapes.
