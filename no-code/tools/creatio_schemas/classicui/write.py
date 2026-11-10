"""Writers of a Classic UI client schema (mixed into ClassicSchema).

Body edits splice one span the reader found - a section of the returned object, a member of it, the
define() dependency list - and re-parse; every byte outside the span stays, and new text takes the body's
own newline and indent. Localizable strings go into the diff metadata (`+ MetaData.Schema.B2 {...}`) and
the resources. New schemas follow the shapes surveyed in real packages: a replacing schema in the diff
form, a module (and a mixin module) in the full form.
"""

from __future__ import annotations

import difflib
import json
import re
import shutil
from pathlib import Path

from ..diff import SchemaDiff
from ..files import CRLF, dump_json, new_uid, read_text, write_text
from ..resources import Resources
from ..schema import Descriptor
from ..text import mask
from ..workspace import Package, Workspace

MANAGER = "ClientUnitSchemaManager"
MODULE_BASE_UID = "50e3acc0-26fc-4237-a095-849a1d534bd3"  # HD1 of every module and source code schema surveyed
MESSAGE_MODES = ("PTP", "BROADCAST")
MESSAGE_DIRECTIONS = ("SUBSCRIBE", "PUBLISH", "BIDIRECTIONAL")
_EMPTY = {"businessRules": "/**SCHEMA_BUSINESS_RULES*/{}/**SCHEMA_BUSINESS_RULES*/", "details": "/**SCHEMA_DETAILS*/{}/**SCHEMA_DETAILS*/",
          "diff": "/**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/"}
_QUOTED = {"businessRules", "messages", "details", "attributes"}  # sections whose member names the designer quotes

REPLACING_BODY = """define("@NAME@", [], function() {
\treturn {
@ENTITY_LINE@\t\tattributes: {},
\t\tmessages: {},
\t\tmixins: {},
\t\tdetails: /**SCHEMA_DETAILS*/{}/**SCHEMA_DETAILS*/,
\t\tbusinessRules: /**SCHEMA_BUSINESS_RULES*/{}/**SCHEMA_BUSINESS_RULES*/,
\t\tmethods: {},
\t\tdiff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
\t};
});
"""

MODULE_BODY = """define("@NAME@", [], function() {
\treturn {};
});
"""

MIXIN_BODY = """define("@NAME@", ["@NAME@Resources"], function(resources) {
\t/**
\t * @class Terrasoft.configuration.mixins.@NAME@
\t * A page lists it in `mixins: {@NAME@: "Terrasoft.@NAME@"}` and adds "@NAME@" to its define() dependencies;
\t * the mixin's methods then run as the page's own (`this` is the page's view model).
\t */
\tExt.define("Terrasoft.configuration.mixins.@NAME@", {
\t\talternateClassName: "Terrasoft.@NAME@",

\t\t/**
\t\t * Called by the page as this.init@NAME@().
\t\t */
\t\tinit@NAME@: function() {
\t\t}
\t});
\treturn Ext.create("Terrasoft.@NAME@");
});
"""


def _pairs_close(masked: str, at: int) -> int:
    from .schema import _close
    return _close(masked, at)


def _members_of(schema, at):
    return {k: (ka, va, vb) for k, ka, va, vb in schema._members(at)}


def _key(name: str, quoted: bool) -> str:
    return json.dumps(name) if quoted or not re.fullmatch(r"[A-Za-z_$][\w$]*", name) else name


def _name_ok(name: str) -> None:
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name):
        raise ValueError(f"{name!r} is not a valid schema name")


def _sql_hint(name: str) -> str:
    return (f"python env/sql.py -e <env> \"select \\\"UId\\\" from \\\"SysSchema\\\" where \\\"Name\\\" = '{name}' "
            f"and \\\"ExtendParent\\\" = false\"")


class ClassicWriter:
    """The writing half of ClassicSchema; relies on its body, masked, sections, _members, _parse."""

    # -- splicing ---------------------------------------------------------------- #

    @property
    def _nl(self) -> str:
        return "\r\n" if "\r\n" in self.body else "\n"

    @property
    def _unit(self) -> str:
        return "    " if re.search(r"^ {2,}\S", self.body, re.M) and not re.search(r"^\t", self.body, re.M) else "\t"

    def _indent_at(self, offset: int) -> str:
        start = self.body.rfind("\n", 0, offset) + 1
        return re.match(r"[ \t]*", self.body[start:]).group(0)

    def _reindent(self, text: str, indent: str) -> str:
        lines = text.replace("\r\n", "\n").split("\n")
        return (self._nl).join([lines[0]] + [(indent + ln) if ln.strip() else "" for ln in lines[1:]])

    def _splice(self, a: int, b: int, text: str) -> None:
        self.body = self.body[:a] + text + self.body[b:]
        self.masked = mask(self.body)
        self.sections, self._return_at, self._deps_at, self.dependencies = {}, None, None, []
        self._parse()

    def _put_member(self, obj_at: int, key: str, value: str) -> None:
        """Add `key: value` as the last member of the object literal whose "{" is at obj_at."""
        members = self._members(obj_at)
        if members:
            last = members[-1]
            indent = self._indent_at(last[1])
            self._splice(last[3], last[3], f",{self._nl}{indent}{key}: {self._reindent(value, indent)}")
            return
        close = _pairs_close(self.masked, obj_at) - 1
        outer = self._indent_at(obj_at)
        indent = outer + self._unit
        self._splice(obj_at + 1, close, f"{self._nl}{indent}{key}: {self._reindent(value, indent)}{self._nl}{outer}")

    def _set_member(self, obj_at: int, name: str, value: str, quoted: bool) -> None:
        """Replace the value of member `name` or add it."""
        hit = _members_of(self, obj_at).get(name)
        if hit:
            self._splice(hit[1], hit[2], self._reindent(value, self._indent_at(hit[0])))
        else:
            self._put_member(obj_at, _key(name, quoted), value)

    def _section(self, key: str) -> int:
        """The offset of a section's value, the section added empty when the schema lacks it."""
        if self._return_at is None:
            raise ValueError(f"{self.name}: no returned object literal to write into")
        if key not in self.sections:
            self._put_member(self._return_at, key, _EMPTY.get(key, "{}"))
        a = self.sections[key][0]
        if self.masked[a] not in "{[":
            raise ValueError(f"{self.name}: section {key} is not a literal")
        return a

    def _block(self, lines: list[str]) -> str:
        """{ <lines> } with the body's indent unit, relative to column 0 (the caller re-indents it)."""
        return "{\n" + "".join(f"{self._unit}{ln}{',' if i < len(lines) - 1 else ''}\n" for i, ln in enumerate(lines)) + "}"

    # -- body writers ------------------------------------------------------------------ #

    def _rule_at(self, uid: str):
        span = self.sections.get("businessRules")
        if not span or self.masked[span[0]] != "{":
            return None
        for column, (_, ca, _) in _members_of(self, span[0]).items():
            if self.masked[ca] != "{":
                continue
            for rule, (_, ra, _) in _members_of(self, ca).items():
                if rule.lower() == uid.lower() and self.masked[ra] == "{":
                    return column, ra
        return None

    def _inherited_rule(self, uid: str):
        """(column, rule source) of the rule in a workspace parent of this schema."""
        for anc in self._ancestors():
            hit = anc._rule_at(uid)
            if hit:
                return hit[0], anc.body[hit[1]:_pairs_close(anc.masked, hit[1])]
        return None

    def set_rule(self, uid: str, enabled: bool | None = None, removed: bool | None = None, column: str | None = None) -> None:
        """Override a business rule by UId in `businessRules`: `enabled` / `removed`. A rule only a parent has is
        copied in first (whole, from the workspace parent) or, when no parent here has it, written as {uId} under `column`."""
        if enabled is None and removed is None:
            raise ValueError("set_rule needs enabled and/or removed")
        if not self._rule_at(uid):
            inherited = self._inherited_rule(uid)
            col = column or (inherited[0] if inherited else None)
            if not col:
                raise ValueError(f"rule {uid} is neither in {self.name} nor in its workspace parents: name its column")
            br = self._section("businessRules")
            if col not in _members_of(self, br):
                self._put_member(br, json.dumps(col), "{}")
            col_at = _members_of(self, self._section("businessRules"))[col][1]
            source = inherited[1] if inherited else self._block([f'"uId": {json.dumps(uid)}'])
            if inherited:  # back to column 0: the parent's lines carry its indent, the closing brace's is the base
                first, *rest = source.replace("\r\n", "\n").split("\n")
                base = len(re.match(r"[ \t]*", rest[-1]).group(0)) if rest else 0
                source = "\n".join([first] + [ln[base:] for ln in rest])
            self._put_member(col_at, json.dumps(uid), source)
        for prop, value in (("enabled", enabled), ("removed", removed)):
            if value is not None:
                self._set_member(self._rule_at(uid)[1], prop, json.dumps(value), quoted=True)

    def add_mixin(self, name: str, cls: str | None = None, module: str | None = None) -> None:
        """`mixins: {name: "cls"}` (default Terrasoft.<name>) and the module (default <name>) in define()'s dependencies."""
        self._set_member(self._section("mixins"), name, json.dumps(cls or f"Terrasoft.{name}"), quoted=False)
        self.add_dependency(module or name)

    def add_dependency(self, module: str) -> None:
        if module in self.dependencies:
            return
        if self._deps_at is None:
            raise ValueError(f"{self.name}: define() has no dependency list")
        close = _pairs_close(self.masked, self._deps_at) - 1
        inner = self.body[self._deps_at + 1:close]
        self._splice(close, close, (", " if inner.strip() else "") + json.dumps(module))

    def _source_of(self, name: str, source: str) -> str:
        src = source.strip()
        m = re.match(rf"{re.escape(name)}\s*:\s*", src)
        return src[m.end():] if m else src

    def add_method(self, name: str, source: str) -> None:
        """A new member of `methods`: `function(...) {...}` (or `name: function...`)."""
        if any(m["name"] == name for m in self.methods()):
            raise KeyError(f"method {name} exists in {self.name}: use replace_method")
        self._put_member(self._section("methods"), name, self._source_of(name, source))

    def replace_method(self, name: str, source: str) -> None:
        for k, ka, vb in self._method_spans():
            if k == name:
                value_at = _members_of(self, self.sections["methods"][0])[name][1]
                self._splice(value_at, vb, self._reindent(self._source_of(name, source), self._indent_at(ka)))
                return
        raise KeyError(f"no method {name} in {self.name}; have {[k for k, _, _ in self._method_spans()]}")

    def set_message(self, name: str, mode: str, direction: str) -> None:
        mode, direction = mode.upper(), direction.upper()
        if mode not in MESSAGE_MODES or direction not in MESSAGE_DIRECTIONS:
            raise ValueError(f"mode is one of {MESSAGE_MODES}, direction one of {MESSAGE_DIRECTIONS}")
        self._set_member(self._section("messages"), name, self._block([f"mode: Terrasoft.MessageMode.{mode}",
                                                                       f"direction: Terrasoft.MessageDirectionType.{direction}"]), quoted=True)

    # -- metadata and resources -------------------------------------------------------- #

    def _diff(self) -> SchemaDiff:
        if not self.metadata_text.lstrip("﻿").startswith(("=", "+", "-", "~")):
            raise ValueError(f"{self.name}: metadata is not in the diff form; strings of a full-form schema are not written here")
        return SchemaDiff(self.metadata_text, CRLF)

    def add_string(self, key: str, values: dict[str, str]) -> None:
        """A localizable string: the B2 item in the diff metadata (once) and `LocalizableStrings.<key>.Value` per culture."""
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ValueError(f"{key!r} is not a valid string name")
        if not values:
            raise ValueError("add_string needs at least one culture=value")
        diff = self._diff()
        if not any(i.get("A2") == key for i in diff.added_items("MetaData.Schema.B2")):
            uid = self.descriptor.data["UId"]
            a5 = diff.value("MetaData.Schema.A5") or Package(self.package).created_in_uid()
            item = {"UId": new_uid(), "A2": key, "A3": uid, "A4": uid, "A5": a5}
            if diff.find("MetaData.Schema.B2", "~"):
                diff.add_item("MetaData.Schema.B2", item)
            else:
                tops = [i for i, ln in enumerate(diff.lines) if ln[1].split(".")[2] in ("UId", "A2", "A5", "B2")]
                diff.lines.insert(tops[-1] + 1 if tops else 0, ["+", "MetaData.Schema.B2", None, item])
            self.metadata_text = diff.render()
        for culture, value in values.items():
            self.resources.set(f"LocalizableStrings.{key}.Value", value, [culture])

    # -- new schemas ------------------------------------------------------------------- #

    @classmethod
    def create_replacing(cls, package: Path, parent_name: str, cultures: list[str] | None = None, parent_uid: str | None = None,
                         caption: str | None = None, entity: str = "", version: str = "8.2.3.1351"):
        """A replacing schema of `parent_name` in `package`: descriptor (Parent, ExtendParent), the diff metadata, the
        designer's empty replacing body, resources with the caption."""
        _name_ok(parent_name)
        package = Path(package)
        sdir = package / "Schemas" / parent_name
        if sdir.exists():
            raise FileExistsError(f"{sdir} exists")
        ws = Workspace(package)
        own = [s for s in ws.find(parent_name, MANAGER) if s["dir"].parent.parent != package]
        if not parent_uid:
            if not own:
                raise ValueError(f"{parent_name} is not in the workspace: pass its UId (parent_uid / --parent-uid); {_sql_hint(parent_name)}")
            parent_uid = own[0]["base"]
        caption = caption or (own[0]["caption"] if own else parent_name)
        pkg, uid = Package(package), new_uid()
        meta = CRLF.join([f'= MetaData.Schema.UId "{uid}"', f'= MetaData.Schema.A5 "{pkg.created_in_uid()}"', f'= MetaData.Schema.B6 "{pkg.uid}"',
                          f'= MetaData.Schema.B8 "{version}"', "+ MetaData.Schema.B7 true", f'= MetaData.Schema.HD1 "{parent_uid}"'])
        write_text(sdir / "metadata.json", meta, False)
        entity_line = f"\t\tentitySchemaName: {json.dumps(entity)},\n" if entity else ""  # none named: the parent's object
        write_text(sdir / f"{parent_name}.js", REPLACING_BODY.replace("@NAME@", parent_name).replace("@ENTITY_LINE@", entity_line), False)
        desc = Descriptor.new(sdir / "descriptor.json", {"UId": uid, "Name": parent_name, "ModifiedOnUtc": "",
                                                         "Parent": {"UId": parent_uid, "Name": parent_name}, "ExtendParent": True,
                                                         "ManagerName": MANAGER, "Caption": caption, "DependsOn": []})
        write_text(desc.path, desc.text, True)
        write_text(sdir / "properties.json", dump_json({"Properties": {"CreatedInVersion": version}}), True)
        return cls._with_caption(package, parent_name, caption, cultures)

    @classmethod
    def create_module(cls, package: Path, name: str, caption: str | None = None, mixin: bool = False, cultures: list[str] | None = None,
                      version: str = "8.2.3.1351"):
        """A client module (SchemaType Module, full metadata, the one-space .less the designer adds); with `mixin` the
        Ext.define mixin that a page lists in `mixins`."""
        _name_ok(name)
        package = Path(package)
        sdir = package / "Schemas" / name
        if sdir.exists() or Workspace(package).find(name, MANAGER):
            raise FileExistsError(f"client schema {name} exists in the workspace")
        pkg, uid = Package(package), new_uid()
        schema = {"ManagerName": MANAGER, "UId": uid, "A2": name, "A5": pkg.created_in_uid(), "B1": [], "B2": [], "B3": [], "B6": pkg.uid,
                  "B8": version, "HD1": MODULE_BASE_UID, "HD4": 1, "HD6": "null", "HD5": [], "HD7": [], "HD8": [], "HD11": []}
        write_text(sdir / "metadata.json", dump_json({"MetaData": {"Schema": schema}}), True)
        write_text(sdir / f"{name}.js", (MIXIN_BODY if mixin else MODULE_BODY).replace("@NAME@", name), False)
        write_text(sdir / f"{name}.less", " ", False)
        desc = Descriptor.new(sdir / "descriptor.json", {"UId": uid, "Name": name, "ModifiedOnUtc": "", "ManagerName": MANAGER,
                                                         "Caption": caption or name, "DependsOn": []})
        write_text(desc.path, desc.text, True)
        write_text(sdir / "properties.json", dump_json({"Properties": {"CreatedInVersion": version, "SchemaType": "Module"}}), True)
        return cls._with_caption(package, name, caption or name, cultures)

    @classmethod
    def _with_caption(cls, package: Path, name: str, caption: str, cultures: list[str] | None):
        s = cls(package, name)
        known = sorted({p.name[len("resource."):-len(".xml")] for p in package.glob("Resources/*/resource.*.xml")})
        s.resources = Resources.empty(s.resources.folder, cultures or known or ["en-US"])
        s.resources.set("Caption", caption)
        for path, (text, bom) in s.files().items():
            write_text(path, text, bom)
        return cls(package, name)

    @classmethod
    def adopt(cls, package: Path, name: str, source: Path):
        """A client schema pulled from another package (its folder, or that package's folder), moved into `package`:
        a new UId, `A5` and `B6` of the target in its metadata, descriptor and strings; resources copied."""
        package, source = Path(package), Path(source)
        src = source if (source / "descriptor.json").is_file() and (source / "metadata.json").is_file() else source / "Schemas" / name
        if not (src / "descriptor.json").is_file():
            raise FileNotFoundError(f"no schema {name} in {source}")
        target = package / "Schemas" / name
        if target.exists():
            raise FileExistsError(f"{target} exists")
        desc = json.loads(read_text(src / "descriptor.json")[0])["Descriptor"]
        if desc.get("ManagerName") != MANAGER:
            raise ValueError(f"{name} is a {desc.get('ManagerName')} schema; adopt takes client schemas")
        meta = read_text(src / "metadata.json")[0]
        diff = SchemaDiff(meta) if meta.lstrip("﻿").startswith(("=", "+", "-", "~")) else None
        full = None if diff else json.loads(meta)["MetaData"]["Schema"]
        old_a5 = diff.value("MetaData.Schema.A5") if diff else full.get("A5")
        old_b6 = diff.value("MetaData.Schema.B6") if diff else full.get("B6")
        pkg = Package(package)
        swap = {desc["UId"]: new_uid(), **({old_a5: pkg.created_in_uid()} if old_a5 else {}), **({old_b6: pkg.uid} if old_b6 else {})}
        shutil.copytree(src, target)
        for f in (target / "descriptor.json", target / "metadata.json"):
            text, bom = read_text(f)
            for old, new in swap.items():
                text = re.sub(re.escape(old), new, text, flags=re.I)
            write_text(f, text, bom)
        res = (src.parent.parent / "Resources" / f"{name}.ClientUnit")
        if res.is_dir():
            shutil.copytree(res, package / "Resources" / f"{name}.ClientUnit", dirs_exist_ok=True)
        s = cls(package, name)
        s.descriptor.touch()
        write_text(s.descriptor.path, s.descriptor.text, True)
        return cls(package, name)

    def diff_against_parent(self) -> str | None:
        """Unified diff of this body against the parent's body when a workspace package holds the parent; None otherwise."""
        for anc in self._ancestors():
            if anc.body:
                return "".join(difflib.unified_diff(anc.body.splitlines(True), self.body.splitlines(True),
                                                    f"{anc.package.name}/{anc.name}.js", f"{self.package.name}/{self.name}.js"))
        return None
