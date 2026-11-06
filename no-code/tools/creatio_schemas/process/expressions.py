"""Process expressions: the designer's UId meta paths <-> readable names.

    [#[IsOwnerSchema:false].[IsSchema:false].[Parameter:{uid}]#]   <->  {Parameter:Name}
    [#...[Element:{uid}].[Parameter:{uid}]#]                       <->  {Element:El.Parameter:P}
"""

from __future__ import annotations

import re

_META_PATH_RE = re.compile(r"\[(Element|Parameter|EntityColumn|IsOwnerSchema|IsSchema):\{?([^\]}]+)\}?\]")
SUGAR_RE = re.compile(r"\{(Parameter|Element):([A-Za-z0-9_]+)(?:\.Parameter:([A-Za-z0-9_]+))?\}")


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

    def decode(self, text):
        """Meta paths -> {Element:Name.Parameter:Name}; unknown ids are kept; non-strings pass through."""
        if not isinstance(text, str):
            return text
        names = self._names()

        def repl(m):
            kind, uid = m.group(1), m.group(2)
            if kind in ("IsOwnerSchema", "IsSchema"):
                return ""
            return f"[{kind}:{names.get(uid, uid)}]"
        out = _META_PATH_RE.sub(repl, text)
        return re.sub(r"\[#\.*", "{", out).replace("#]", "}").replace("].[", ".").replace("[", "").replace("]", "")

    def encode(self, text: str) -> str:
        """{Parameter:Name} / {Element:El.Parameter:P} -> meta paths; the rest of the text is kept."""
        p = self.proc
        by_name = {x["A2"]: x["UId"] for x in p.params}

        def repl(m):
            kind, name, pname = m.group(1), m.group(2), m.group(3)
            if kind == "Parameter":
                if name not in by_name:
                    raise KeyError(f"no process parameter {name!r}")
                return f"[#[IsOwnerSchema:false].[IsSchema:false].[Parameter:{{{by_name[name]}}}]#]"
            el = p.element(name)
            ep = p.element_param(el, pname)
            return f"[#[IsOwnerSchema:false].[IsSchema:false].[Element:{{{el['UId']}}}].[Parameter:{{{ep['UId']}}}]#]"
        return SUGAR_RE.sub(repl, text)

    @staticmethod
    def has_names(text) -> bool:
        return isinstance(text, str) and bool(SUGAR_RE.search(text))
