"""Process expressions: the designer's UId meta paths <-> readable names (`{Parameter:Name}`, `{Element:El.Parameter:P}`).

The codec itself is `expressions.metapath`; `ExpressionCodec` is its `Names` for one process and adds `check`.
"""

from __future__ import annotations

from ..expressions import metapath
from ..expressions.metapath import LEFTOVER_RE, META_PATH_RE, SUGAR_RE
from ..files import GUID_RE


class ExpressionCodec:
    def __init__(self, proc):
        self.proc = proc

    def _names(self) -> dict[str, str]:
        p = self.proc
        names = {e["UId"]: e["A2"] for e in p.elements}
        names.update({x["UId"]: x["A2"] for x in p.params})
        for e in p.elements:
            for x in p.element_params(e):
                names[x["UId"]] = x["A2"]
        names[p.uid] = p.name
        return names

    def name_of(self, uid: str) -> str | None:
        return self._names().get(uid)

    def uid_of(self, kind: str, name: str, parent: str | None = None) -> str:
        """The `Names` of the codec: a process parameter, an element, an element's parameter, a column of the entity it reads."""
        p = self.proc
        if kind == "Parameter" and parent is None:
            by_name = {x["A2"]: x["UId"] for x in p.params}
            if name not in by_name:
                raise KeyError(f"no process parameter {name!r}")
            return by_name[name]
        if kind == "Element":
            return p.element(name)["UId"]
        if kind == "Parameter":
            return p.element_param(p.element(parent), name)["UId"]
        element, _, pname = parent.partition(".")
        el = p.element(element)
        return self._column_uid(el, p.element_param(el, pname), name)

    def decode(self, text):
        """Meta paths -> {Element:Name.Parameter:Name}; unknown ids are kept; non-strings pass through."""
        return metapath.decode(text, self)

    def _column_uid(self, element: dict, param: dict, ref: str) -> str:
        """A column of the entity a parameter reads: its UId as given, or its name resolved through the workspace."""
        if GUID_RE.fullmatch(ref):
            return ref.lower()
        entity = self.proc.workspace.name_of(param.get("L9")) if param.get("L9") else None
        uids = self.proc.workspace.column_uids(entity) if entity else {}
        if ref not in uids:
            raise KeyError(f"{element['A2']}.{param['A2']}: no column {ref!r}" + (f" on {entity}" if entity else "; the parameter names no entity, give the column's UId"))
        return uids[ref]

    def encode(self, text: str) -> str:
        """{Parameter:Name} / {Element:El.Parameter:P[.EntityColumn:C]} -> meta paths; the rest of the text is kept.
        A `{...}` reference the codec cannot resolve raises - it would reach the platform as text."""
        return metapath.encode(text, self)

    def check(self, text, where: str) -> list[str]:
        """Problems of a stored expression: a name reference left unencoded, a meta path to an element or parameter
        the process does not have (the platform fails at run time with "Expression expected")."""
        if not isinstance(text, str) or not text or text == "null":
            return []
        problems = [f"{where}: {m.group(0)} is not encoded (a meta path was expected)" for m in LEFTOVER_RE.finditer(text)]
        names = self._names()
        for m in META_PATH_RE.finditer(text):
            kind, uid = m.group(1), m.group(2)
            if kind in ("Element", "Parameter") and uid not in names:
                problems.append(f"{where}: [{kind}:{uid}] is not in the process")
            elif kind == "EntityColumn" and not GUID_RE.fullmatch(uid):
                problems.append(f"{where}: [EntityColumn:{uid}] is not a column UId")
        return problems

    @staticmethod
    def has_names(text) -> bool:
        return isinstance(text, str) and bool(SUGAR_RE.search(text))
