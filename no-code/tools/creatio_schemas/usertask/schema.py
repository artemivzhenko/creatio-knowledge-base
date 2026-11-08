"""A user-task schema: Schemas/<Name>/metadata.json (ProcessUserTaskSchemaManager), <Name>.cs and Resources/<Name>.ProcessUserTask/.

A user task is a reusable process element: its parameters (FJ1, the same ProcessSchemaParameter
as a process has) and a partial C# class whose InternalExecute runs when a process reaches the
element. The platform generates the other half of the class from the parameters.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..files import DATA_VALUE_TYPES, dump_json, new_uid, read_text, write_text
from ..process.catalog import DIRECTION, new_param
from ..resources import Resources
from ..schema import WARNING, Descriptor, Schema
from ..workspace import Package

DEFAULT_VERSION = "8.2.3.1351"
DEFAULT_COLOR = "#839DC3"
METHOD_RE = re.compile(r"^[ \t]*((?:public|protected|private|internal)[^\n;{=]*?\b(\w+)\s*\([^)]*\))\s*(?:\{|=>)", re.M)
SOURCE_TEMPLATE = """namespace Terrasoft.Core.Process.Configuration
{{

\tusing System;
\tusing System.Collections.Generic;
\tusing Terrasoft.Common;
\tusing Terrasoft.Core;
\tusing Terrasoft.Core.DB;
\tusing Terrasoft.Core.Entities;
\tusing Terrasoft.Core.Process;
\tusing Terrasoft.Configuration;

\t#region Class: {name}

\t/// <exclude/>
\tpublic partial class {name}
\t{{

\t\t#region Methods: Protected

\t\tprotected override bool InternalExecute(ProcessExecutingContext context) {{
\t\t\t// TODO: the task's work; the parameters are properties of this class
\t\t\treturn true;
\t\t}}

\t\t#endregion

\t\t#region Methods: Public

\t\tpublic override bool CompleteExecuting(params object[] parameters) {{
\t\t\treturn base.CompleteExecuting(parameters);
\t\t}}

\t\tpublic override void CancelExecuting(params object[] parameters) {{
\t\t\tbase.CancelExecuting(parameters);
\t\t}}

\t\tpublic override string GetExecutionData() {{
\t\t\treturn string.Empty;
\t\t}}

\t\tpublic override ProcessElementNotification GetNotificationData() {{
\t\t\treturn base.GetNotificationData();
\t\t}}

\t\t#endregion

\t}}

\t#endregion

}}
"""


# C# type, default written by WritePropertiesData, reader call - per data value type name, as the platform generates them.
_TEXT = ("string", "null", "reader.GetStringValue()")
_DATE = ("DateTime", 'DateTime.ParseExact("01.01.0001 0:00", "dd.MM.yyyy H:mm", CultureInfo.InvariantCulture)', "reader.GetDateTimeValue()")
_DECIMAL = ("Decimal", "0m", "reader.GetValue<System.Decimal>()")
CSHARP_OF = {"Guid": ("Guid", "Guid.Empty", "reader.GetGuidValue()"), "Lookup": ("Guid", "Guid.Empty", "reader.GetGuidValue()"),
             "Integer": ("int", "0", "reader.GetIntValue()"), "Boolean": ("bool", "false", "reader.GetBoolValue()"),
             "DateTime": _DATE, "Date": _DATE, "Time": _DATE, "Money": _DECIMAL,
             **{t: _TEXT for t in ("ShortText", "MediumText", "LongText", "MaxSizeText", "Text", "PhoneText", "WebText", "EmailText",
                                   "RichText", "SecureText", "HashText", "DbObjectName", "MetaDataText")},
             **{t: _DECIMAL for t in ("Float", "Float1", "Float2", "Float3", "Float4", "Float8")}}
GENERATED_TEMPLATE = """﻿namespace Terrasoft.Core.Process.Configuration
{{

\tusing System;
\tusing System.Collections.Generic;
\tusing System.Collections.ObjectModel;
\tusing System.Globalization;
\tusing Terrasoft.Common;
\tusing Terrasoft.Core;
\tusing Terrasoft.Core.Configuration;
\tusing Terrasoft.Core.DB;
\tusing Terrasoft.Core.Entities;
\tusing Terrasoft.Core.Process;

\t#region Class: {name}

{attributes}\t/// <exclude/>
\tpublic partial class {name} : ProcessUserTask
\t{{

\t\t#region Constructors: Public

\t\tpublic {name}(UserConnection userConnection)
\t\t\t: base(userConnection) {{
\t\t\tSchemaUId = new Guid("{uid}");
\t\t}}

\t\t#endregion

\t\t#region Properties: Public
{properties}
\t\t#endregion

\t\t#region Methods: Public

\t\tpublic override void WritePropertiesData(DataWriter writer) {{
\t\t\twriter.WriteStartObject(Name);
\t\t\tbase.WritePropertiesData(writer);
\t\t\tif (Status == Core.Process.ProcessStatus.Inactive) {{
\t\t\t\twriter.WriteFinishObject();
\t\t\t\treturn;
\t\t\t}}
{writes}\t\t\twriter.WriteFinishObject();
\t\t}}

\t\t#endregion

\t\t#region Methods: Protected

\t\tprotected override void ApplyPropertiesDataValues(DataReader reader) {{
\t\t\tbase.ApplyPropertiesDataValues(reader);
\t\t\tswitch (reader.CurrentName) {{
{reads}\t\t\t}}
\t\t}}

\t\t#endregion

\t}}

\t#endregion

}}"""
_ATTRIBUTE = ('\t[DesignModeProperty(Name = "{p}", Group = "", ValuesProvider = "ProcessSchemaParameterValueProvider", '
              'Editor="xtype=processschemaparametervalueedit;dataProvider=processschemaparametervalueprovider", ResourceManager = "{rm}", '
              'CaptionResourceItem = "Parameters.{p}.Caption", DescriptionResourceItem = "Parameters.{p}.Caption", UseSolutionStorage = true)]\n')
_PROPERTY = "\n\t\tpublic virtual {t} {p} {{\n\t\t\tget;\n\t\t\tset;\n\t\t}}\n"
_WRITE = '\t\t\tif (UseFlowEngineMode) {{\n\t\t\t\tif (!HasMapping("{p}")) {{\n\t\t\t\t\twriter.WriteValue("{p}", {p}, {d});\n\t\t\t\t}}\n\t\t\t}}\n'
_READ = '\t\t\t\tcase "{p}":\n\t\t\t\t\tif (!UseFlowEngineMode) {{\n\t\t\t\t\t\tbreak;\n\t\t\t\t\t}}\n\t\t\t\t\t{p} = {r};\n\t\t\t\tbreak;\n'


class UserTaskSchema(Schema):
    RESOURCE_SUFFIX = "ProcessUserTask"

    def load_metadata(self, text: str) -> None:
        self.meta = json.loads(text)
        self.schema: dict = self.meta["MetaData"]["Schema"]
        if self.schema.get("ManagerName") != "ProcessUserTaskSchemaManager":
            raise ValueError(f"{self.name} is a {self.schema.get('ManagerName')}, not a user task")
        self.source_path = self.dir / f"{self.name}.cs"
        self.source, self.source_bom = read_text(self.source_path) if self.source_path.is_file() else ("", False)

    def render_metadata(self) -> str:
        return dump_json(self.meta, self.newline)

    def files(self) -> dict[Path, tuple[str, bool]]:
        out = super().files()
        if self.source or self.source_path.is_file():
            out[self.source_path] = (self.source, self.source_bom)
        generated = self.generated_source()
        if generated is not None:
            out[self.generated_path] = (generated.lstrip("﻿"), True)
        return out

    @property
    def generated_path(self) -> Path:
        """Where a clio workspace keeps the platform's half of the class (downloaded with the package)."""
        return self.package / "Autogenerated" / "Src" / f"{self.name}Schema.{self.package.name}.cs"

    def generated_source(self) -> str | None:
        """The platform's half of the partial class, as the configuration compiler emits it: the parameters as
        properties plus their (de)serialisation. Only for a package with a project (a workspace build needs it
        to compile the user's half) and only when every parameter type is one the template knows; otherwise None,
        and whatever the platform wrote stays untouched."""
        if not any(self.package.glob("Files/*.csproj")):
            return None
        kinds = [CSHARP_OF.get(DATA_VALUE_TYPES.get(p.get("L1"), "")) for p in self.params]
        if any(k is None for k in kinds):
            return None
        names = [p["A2"] for p in self.params]
        rm = self.uid.replace("-", "")
        return GENERATED_TEMPLATE.format(
            name=self.name, uid=self.uid,
            attributes="".join(_ATTRIBUTE.format(p=p, rm=rm) for p in names),
            properties="".join(_PROPERTY.format(t=k[0], p=p) for p, k in zip(names, kinds)),
            writes="".join(_WRITE.format(p=p, d=k[1]) for p, k in zip(names, kinds)),
            reads="".join(_READ.format(p=p, r=k[2]) for p, k in zip(names, kinds)))

    # ======================================================================= #
    # Reading
    # ======================================================================= #

    @property
    def uid(self) -> str:
        return self.schema["UId"]

    @property
    def package_uid(self) -> str:
        return self.schema.get("B6") or self.schema.get("A5")

    @property
    def params(self) -> list[dict]:
        return self.schema.get("FJ1", [])

    def param(self, name: str) -> dict:
        for p in self.params:
            if p["A2"].lower() == name.lower():
                return p
        raise KeyError(f"no parameter {name}; parameters: {', '.join(p['A2'] for p in self.params)}")

    @property
    def interactive(self) -> bool:
        props = self.dir / "properties.json"
        if props.is_file():
            try:
                return str(json.loads(read_text(props)[0]).get("Properties", {}).get("IsInteractive", "False")).lower() == "true"
            except ValueError:
                pass
        return False

    def methods(self) -> list[str]:
        """Method signatures of the C# half, one line each."""
        return [" ".join(m.group(1).split()) for m in METHOD_RE.finditer(self.source)]

    def method(self, name: str) -> str:
        """One method's text, by brace matching from its signature."""
        for m in METHOD_RE.finditer(self.source):
            if m.group(2).lower() != name.lower():
                continue
            start = m.start()
            i = self.source.find("{", m.end() - 1)
            if i < 0:
                return self.source[start:self.source.find("\n", m.end())]
            depth = 0
            for j in range(i, len(self.source)):
                ch = self.source[j]
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        return self.source[start:j + 1]
            return self.source[start:]
        raise KeyError(f"no method {name}; methods: {', '.join(m.split('(')[0].split()[-1] for m in self.methods())}")

    def describe_param(self, p: dict) -> str:
        t = DATA_VALUE_TYPES.get(p.get("L1"), p.get("L1"))
        d = DIRECTION.get(p.get("L12", 0))
        return (f"{p['A2']:<28} {t:<12} {d:<9}" + (" required" if p.get("L6") else "         ")
                + (f" -> {p['L16']}" if p.get("L16") else "") + f"  caption={self.resources.get(f'Parameters.{p['A2']}.Caption')!r}")

    def describe(self) -> str:
        r = self.resources
        lines = [f"{self.name}: {r.get('Caption')!r}  uid={self.uid}  user task" + (", interactive" if self.interactive else "")
                 + (f", color {self.schema['FK12']}" if self.schema.get("FK12") else ""), f"  cultures: {', '.join(r.cultures)}"]
        lines.append("  parameters:" if self.params else "  parameters: (none)")
        lines += [f"    {self.describe_param(p)}" for p in self.params]
        if self.source:
            lines.append(f"  source: {self.source_path.name}, {self.source.count(chr(10)) + 1} lines")
            lines += [f"    {m}" for m in self.methods()]
        else:
            lines.append("  source: (no .cs file)")
        problems = self.validate()
        if problems:
            lines.append("  problems:")
            lines += [f"    - {p}" for p in problems]
        return "\n".join(lines)

    def validate(self) -> list[str]:
        problems = []
        names = [p["A2"] for p in self.params]
        if len(names) != len(set(names)):
            problems.append("duplicate parameter names")
        for p in self.params:
            if p.get("L1") not in DATA_VALUE_TYPES:
                problems.append(f"parameter {p['A2']}: unknown data value type {p.get('L1')}")
            if self.resources.get(f"Parameters.{p['A2']}.Caption") is None:
                problems.append(f"{WARNING}parameter {p['A2']}: no caption")
        if self.source and "InternalExecute" not in self.source:
            problems.append(f"{WARNING}the C# half does not override InternalExecute")
        if self.source and f"class {self.name}" not in self.source:
            problems.append(f"the C# half does not declare partial class {self.name}")
        return problems

    # ======================================================================= #
    # Changing
    # ======================================================================= #

    def add_param(self, name: str, type_name: str, direction: str = "In", caption: str = "", required: bool = False,
                  ref_schema: str | None = None, cultures: list[str] | None = None) -> dict:
        if any(p["A2"].lower() == name.lower() for p in self.params):
            raise ValueError(f"parameter {name} exists")
        p = new_param(self.uid, self.package_uid, name, type_name, direction, None, ref_schema)
        if required:
            p["L6"] = True
        p["L11"] = False
        self.schema.setdefault("FJ1", []).append(p)
        self.resources.set(f"Parameters.{name}.Caption", caption or name, cultures)
        return p

    def rename_param(self, old: str, new: str) -> None:
        self.param(old)["A2"] = new
        self.resources.rename_prefix(f"Parameters.{old}", f"Parameters.{new}")

    def remove_param(self, name: str) -> None:
        self.params.remove(self.param(name))
        self.resources.remove_prefix(f"Parameters.{name}")

    def set_caption(self, value: str, cultures: list[str] | None = None) -> None:
        self.descriptor.set_caption(value)
        self.resources.set("Caption", value, cultures)

    def set_source(self, text: str) -> None:
        """Replace the C# half (the whole file)."""
        self.source = text

    # ======================================================================= #
    # New user task
    # ======================================================================= #

    @classmethod
    def create(cls, package: Path, name: str, caption: str, params: list[tuple] | None = None, cultures: list[str] | None = None,
               interactive: bool = False, version: str = DEFAULT_VERSION) -> "UserTaskSchema":
        """A user task with a C# skeleton; `params` are (name, type[, direction[, caption[, required]]]) tuples."""
        package = Path(package)
        sdir = package / "Schemas" / name
        if sdir.exists():
            raise FileExistsError(sdir)
        pkg_uid = Package(package).uid
        uid = new_uid()
        schema = {"ManagerName": "ProcessUserTaskSchemaManager", "UId": uid, "A2": name, "A5": pkg_uid, "B1": [], "B2": [], "B3": [], "B6": pkg_uid,
                  "B8": version, "FJ1": [], "FK7": True, "FK12": DEFAULT_COLOR, "FK16": True}
        write_text(sdir / "metadata.json", dump_json({"MetaData": {"Schema": schema}}), True)
        desc = Descriptor.new(sdir / "descriptor.json", {"UId": uid, "Name": name, "ModifiedOnUtc": "", "ManagerName": "ProcessUserTaskSchemaManager",
                                                          "Caption": caption, "DependsOn": []})
        write_text(desc.path, desc.text, True)
        write_text(sdir / "properties.json", dump_json({"Properties": {"CreatedInVersion": version, "IsInteractive": "True" if interactive else "False"}}), True)
        write_text(sdir / f"{name}.cs", SOURCE_TEMPLATE.format(name=name), False)
        task = cls(package, name)
        task.resources = Resources.empty(task.resources.folder, cultures or ["en-US"])
        task.resources.set("Caption", caption)
        for spec in params or []:
            pname, ptype = spec[0], spec[1]
            task.add_param(pname, ptype, spec[2] if len(spec) > 2 else "In", spec[3] if len(spec) > 3 else "", bool(spec[4]) if len(spec) > 4 else False)
        task.save()
        return task
