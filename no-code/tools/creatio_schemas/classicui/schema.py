"""A Classic UI (7.x) client schema: Schemas/<Name>/<Name>.js (ClientUnitSchemaManager) and Resources/<Name>.ClientUnit/.

The body is an AMD module, `define("Name", ["Dep", ...], function(Dep, ...) { ... return { <sections> }; })`;
the returned object literal carries the sections: entitySchemaName, attributes, messages, mixins, details,
modules, diff (an array of operations: insert / merge / remove / move with name, parentName, propertyName,
values), methods, rules, businessRules, userCode, in any order and any of them missing. It is JavaScript,
not JSON (comments, trailing commas, Terrasoft.* constants, regex literals), so it is read by brace matching
over a copy with comments and literals masked (text.mask). Read-only: an untouched schema saves its bytes back.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..files import read_text
from ..schema import WARNING, Schema
from ..text import mask

_KEY_RE = re.compile(r'([A-Za-z_$][\w$]*|"[^"\n]*"|\'[^\'\n]*\')\s*:')
_STRING_RE = re.compile(r'"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'')
_PAIRS = {"{": "}", "[": "]", "(": ")"}
_KINDS = {"EditViewModelSchema": "edit page", "ModuleViewModelSchema": "section", "GridDetailViewModelSchema": "detail", "Module": "module"}
# diff value keys that bind to a method (click: {bindTo: "onSaveClick"}); visible / enabled bind to attributes as often
HANDLER_KEYS = ("click", "change", "prepareList", "afterrender", "afterrerender", "linkclick", "rightIconClick", "activeRowAction")


def _close(masked: str, at: int) -> int:
    """Index after the bracket that closes the one at `at` (len when unbalanced)."""
    opener, closer, depth = masked[at], _PAIRS[masked[at]], 0
    for i in range(at, len(masked)):
        if masked[i] == opener:
            depth += 1
        elif masked[i] == closer:
            depth -= 1
            if depth == 0:
                return i + 1
    return len(masked)


def _skip_space(masked: str, i: int) -> int:
    while i < len(masked) and masked[i].isspace():
        i += 1
    return i


def _rstrip(masked: str, i: int) -> int:
    while i > 0 and masked[i - 1].isspace():
        i -= 1
    return i


class ClassicSchema(Schema):
    RESOURCE_SUFFIX = "ClientUnit"

    def load_metadata(self, text: str) -> None:
        self.metadata_text = text
        self.body_path = self.dir / f"{self.name}.js"
        self.body, self.body_bom = read_text(self.body_path) if self.body_path.is_file() else ("", False)
        self.masked = mask(self.body)
        props = self.dir / "properties.json"
        self.schema_type = json.loads(read_text(props)[0]).get("Properties", {}).get("SchemaType") if props.is_file() else None
        self.module_name: str | None = None
        self.dependencies: list[str] = []
        self.sections: dict[str, tuple[int, int]] = {}
        self._parse()

    def render_metadata(self) -> str:
        return self.metadata_text

    def files(self):
        out = super().files()
        if self.body_path.is_file():
            out[self.body_path] = (self.body, self.body_bom)
        return out

    @staticmethod
    def is_classic(package: Path, name: str) -> bool:
        """True when the body is an AMD module (a Freedom UI page is told apart by its markers first)."""
        body = Path(package) / "Schemas" / name / f"{name}.js"
        return body.is_file() and bool(re.search(r"\bdefine\s*\(", mask(read_text(body)[0])))

    # -- parsing ------------------------------------------------------------- #

    def _parse(self) -> None:
        text, masked = self.body, self.masked
        m = re.search(r"\bdefine\s*\(", masked)
        if not m:
            return
        args_end = _close(masked, m.end() - 1)
        name = _STRING_RE.match(text, _skip_space(masked, m.end()))
        if name:
            self.module_name = name.group(1) if name.group(1) is not None else name.group(2)
        fn = re.compile(r"\bfunction\b").search(masked, m.end(), args_end)
        deps = masked.find("[", m.end(), fn.start() if fn else args_end)
        if deps >= 0:
            self.dependencies = [a or b for a, b in _STRING_RE.findall(text[deps:_close(masked, deps)])]
        if not fn:
            return
        body = masked.find("{", masked.find(")", fn.end()))
        body_end = _close(masked, body)
        ret, depth, i = None, 0, body + 1
        while i < body_end - 1:
            ch = masked[i]
            if ch in _PAIRS:
                depth += 1
            elif ch in "}])":
                depth -= 1
            elif depth == 0 and masked.startswith("return", i) and not (masked[i - 1].isalnum() or masked[i + 6].isalnum()):
                ret = i
            i += 1
        if ret is None:
            return
        obj = _skip_space(masked, ret + 6)
        if masked[obj] != "{":
            return  # `return Ext.apply(...)` and the like: no literal to read
        self.sections = {k: (a, b) for k, _, a, b in self._members(obj)}

    def _members(self, at: int) -> list[tuple[str, int, int, int]]:
        """(key, key offset, value start, value end) of the object literal whose "{" is at `at`."""
        text, masked = self.body, self.masked
        end = _close(masked, at) - 1
        out, depth, i, cur = [], 0, at + 1, None
        while i < end:
            ch = masked[i]
            if cur is None:
                if ch.isspace() or ch == ",":
                    i += 1
                    continue
                m = _KEY_RE.match(text, i)
                cur = [m.group(1).strip("\"'"), i, _skip_space(masked, m.end())] if m else ["", i, i]
                i = cur[2]
                continue
            if ch in _PAIRS:
                depth += 1
            elif ch in "}])":
                depth -= 1
            elif ch == "," and depth == 0:
                out.append((cur[0], cur[1], cur[2], _rstrip(masked, i)))
                cur = None
            i += 1
        if cur is not None:
            out.append((cur[0], cur[1], cur[2], _rstrip(masked, end)))
        return [o for o in out if o[0]]

    def _literal(self, a: int, b: int) -> str:
        """A string value unquoted; any other value as its source, on one line ({...} / [...] for nested literals)."""
        src = self.body[a:b]
        m = _STRING_RE.fullmatch(src)
        if m:
            return m.group(1) if m.group(1) is not None else m.group(2)
        if self.masked[a:a + 1] in ("{", "["):
            return self.masked[a] + "..." + _PAIRS[self.masked[a]]
        return " ".join(src.split())

    def _object(self, a: int) -> dict[str, tuple[int, int]]:
        return {k: (va, vb) for k, _, va, vb in self._members(a)} if self.masked[a:a + 1] == "{" else {}

    def _line(self, offset: int) -> int:
        return self.body.count("\n", 0, offset) + 1

    # -- reading ------------------------------------------------------------- #

    @property
    def parent(self) -> str | None:
        return (self.descriptor.data.get("Parent") or {}).get("Name")

    @property
    def replacing(self) -> bool:
        return bool(self.descriptor.data.get("ExtendParent"))

    @property
    def kind(self) -> str:
        if self.schema_type in _KINDS:
            return _KINDS[self.schema_type]
        p = self.parent or ""
        return ("section" if p.endswith("SectionV2") else "detail" if p.endswith(("DetailV2", "Detail")) else
                "edit page" if p.endswith(("PageV2", "Page")) else "client schema")

    @property
    def entity(self) -> str | None:
        span = self.sections.get("entitySchemaName")
        return self._literal(*span) if span else None

    def entries(self, section: str) -> dict[str, dict | str]:
        """The members of an object section: name -> {property: value} (a non-object member -> its value)."""
        span = self.sections.get(section)
        if not span:
            return {}
        out = {}
        for k, (a, b) in self._object(span[0]).items():
            props = self._object(a)
            out[k] = {pk: self._literal(pa, pb) for pk, (pa, pb) in props.items()} if props or self.masked[a] == "{" else self._literal(a, b)
        return out

    def messages(self) -> dict:
        return self.entries("messages")

    def attributes(self) -> dict:
        return self.entries("attributes")

    def details(self) -> dict:
        return self.entries("details")

    def mixins(self) -> dict:
        return self.entries("mixins")

    def diff_operations(self) -> list[dict]:
        """Each item of diff: operation, name (the item's or its values'), parentName, propertyName, index, the keys of values."""
        span = self.sections.get("diff")
        if not span or self.masked[span[0]] != "[":
            return []
        out, depth, i, end = [], 0, span[0] + 1, _close(self.masked, span[0]) - 1
        while i < end:
            ch = self.masked[i]
            if ch == "{" and depth == 0:
                item_end = _close(self.masked, i)
                members = self._object(i)
                values = self._object(members["values"][0]) if "values" in members else {}
                lit = {k: self._literal(*members[k]) for k in ("operation", "name", "parentName", "propertyName", "index") if k in members}
                handlers = {k: self._literal(*self._object(values[k][0])["bindTo"]) for k in HANDLER_KEYS
                            if k in values and "bindTo" in self._object(values[k][0])}
                out.append({"operation": lit.get("operation"), "name": lit.get("name") or (self._literal(*values["name"]) if "name" in values else None),
                            "parentName": lit.get("parentName"), "propertyName": lit.get("propertyName"), "index": lit.get("index"),
                            "values": list(values), "handlers": handlers, "line": self._line(i), "source": self.body[i:item_end]})
                i = item_end
                continue
            if ch in _PAIRS:
                depth += 1
            elif ch in "}])":
                depth -= 1
            i += 1
        return out

    def element(self, name: str) -> list[dict]:
        """The diff operations on one element."""
        ops = [op for op in self.diff_operations() if op["name"] == name]
        if not ops:
            raise KeyError(f"no element {name} in the diff of {self.name}")
        return ops

    def _method_spans(self) -> list[tuple[str, int, int]]:
        span = self.sections.get("methods")
        return [(k, ka, vb) for k, ka, _, vb in self._members(span[0])] if span and self.masked[span[0]] == "{" else []

    def methods(self) -> list[dict]:
        """name, line, size in lines."""
        return [{"name": k, "line": self._line(a), "size": self.body.count("\n", a, b) + 1} for k, a, b in self._method_spans()]

    def method(self, name: str) -> str:
        """One method's source, `name: function(...) {...}`."""
        for k, a, b in self._method_spans():
            if k == name:
                return self.body[a:b]
        raise KeyError(f"no method {name} in {self.name}; have {[k for k, _, _ in self._method_spans()]}")

    def find(self, needle: str) -> list[tuple[int, str, str]]:
        """(line, where - section or `methods.<name>`, the line) of each line holding `needle` (case-insensitive)."""
        out, low = [], needle.lower()
        methods = self._method_spans()
        offset = 0
        for n, line in enumerate(self.body.splitlines(True), 1):
            if low in line.lower():
                where = next((f"methods.{k}" for k, a, b in methods if a <= offset < b), None) or \
                    next((k for k, (a, b) in self.sections.items() if a <= offset < b), "")
                out.append((n, where, line.strip()))
            offset += len(line)
        return out

    def summary(self) -> str:
        if self.module_name is None:
            return f"no define() module ({len(self.body.splitlines())} lines)"
        of = f" of {self.entity}" if self.entity else ""
        return f"{self.kind}{of}, {len(self.diff_operations())} diff operations, {len(self.methods())} methods, {len(self.details())} details"

    def describe(self) -> str:
        lines = [f"{self.name}: {self.summary()}"]
        head = [f"parent {self.parent}" + (" (replacing)" if self.replacing else "")]
        if self.dependencies:
            head.append("depends on " + ", ".join(self.dependencies))
        lines.append("  " + ", ".join(head))
        counts = []
        for k, (a, _) in self.sections.items():
            if self.masked[a] == "[":
                counts.append(f"{k} {len(self.diff_operations()) if k == 'diff' else len(self._object(a))}")
            else:
                counts.append(f"{k} {len(self._object(a))}" if self.masked[a] == "{" else k)
        if counts:
            lines.append("  sections: " + ", ".join(counts))
        by_op: dict[str, list[str]] = {}
        for op in self.diff_operations():
            by_op.setdefault(op["operation"] or "?", []).append(op["name"] or f"(line {op['line']})")
        if by_op:
            lines.append("  diff: " + "; ".join(f"{op} {', '.join(names)}" for op, names in by_op.items()))
        problems = self.validate()
        if problems:
            lines.append("  problems:")
            lines += [f"    - {p}" for p in problems]
        return "\n".join(lines)

    # -- checks ---------------------------------------------------------------- #

    def _ancestors(self) -> list["ClassicSchema"]:
        """The parent chain as far as the workspace holds it (other copies of a replaced schema included)."""
        seen, out, todo = {self.dir}, [], [self.parent]
        while todo:
            name = todo.pop()
            for s in self.workspace.find(name, "ClientUnitSchemaManager") if name else []:
                if s["dir"] in seen:
                    continue
                seen.add(s["dir"])
                try:
                    anc = ClassicSchema(s["dir"].parent.parent, s["name"])
                except (FileNotFoundError, ValueError, KeyError):
                    continue
                out.append(anc)
                todo.append(anc.parent)
        return out

    def validate(self) -> list[str]:
        """Warnings only: what this file alone cannot prove (most names come from the platform's parent schemas)."""
        ops = self.diff_operations()
        problems = [f"{WARNING}diff item at line {op['line']}: {op['operation']} without a name" for op in ops if not op["name"]]
        ancestors = self._ancestors() if ops else []
        declared = {op["name"] for s in [self, *ancestors] for op in s.diff_operations()}
        outside = sorted({op["parentName"] for op in ops if op["parentName"] and op["parentName"] not in declared})
        if outside:
            problems.append(f"{WARNING}parentName not declared here or in the workspace parents (expected from {self.parent}): {', '.join(outside)}")
        methods = {m["name"] for s in [self, *ancestors] for m in s.methods()}
        missing = sorted({f"{k} -> {t}" for op in ops for k, t in op["handlers"].items() if t not in methods})
        if missing:
            problems.append(f"{WARNING}handlers bound to methods not defined here or in the workspace parents (expected from {self.parent}): "
                            + ", ".join(missing))
        return problems
