"""The designer's meta paths <-> readable names, for any schema that can name its pieces (`Names`).

    [#[IsOwnerSchema:false].[IsSchema:false].[Parameter:{uid}]#]                        <->  {Parameter:Name}
    [#...[Element:{uid}].[Parameter:{uid}]#]                                             <->  {Element:El.Parameter:P}
    [#...[Element:{uid}].[Parameter:{uid}].[EntityColumn:{uid}]#]                        <->  {Element:El.Parameter:P.EntityColumn:<uid or Column>}
    [#Lookup.<schema uid>.<record id>#]                                                  a lookup record (`lookup`)

`encode` refuses a `{...}` it cannot turn into a meta path: the platform reads an unencoded one as
"Expression expected" at run time, after `validate` said ok.
"""

from __future__ import annotations

import re
from typing import Protocol

META_PATH_RE = re.compile(r"\[(Element|Parameter|EntityColumn|IsOwnerSchema|IsSchema):\{?([^\]}]+)\}?\]")
SUGAR_RE = re.compile(r"\{(Parameter|Element):([A-Za-z0-9_]+)(?:\.Parameter:([A-Za-z0-9_]+))?(?:\.EntityColumn:([A-Za-z0-9_-]+))?\}")
# anything that still looks like a name reference after encoding: a form this codec does not know, or a typo in it
LEFTOVER_RE = re.compile(r"\{(?:Parameter|Element|Record|EntityColumn)[^{}]*\}")
PREFIX = "[#[IsOwnerSchema:false].[IsSchema:false]"


class Names(Protocol):
    """What a schema tells the codec about itself; the owner raises its own error for a name it does not have."""

    def uid_of(self, kind: str, name: str, parent: str | None = None) -> str:
        """The UId of a `Parameter` (of the schema, or of the element named by `parent`), an `Element`, or an `EntityColumn`
        (`name` is the UId or the column name, `parent` is `Element.Parameter`)."""

    def name_of(self, uid: str) -> str | None:
        """The name of an element or parameter UId, or None."""


def encode(text: str, names: Names) -> str:
    """{Parameter:Name} / {Element:El.Parameter:P[.EntityColumn:C]} -> meta paths; the rest of the text is kept.
    A `{...}` reference the codec cannot resolve raises - it would reach the platform as text."""

    def repl(m):
        kind, name, pname, column = m.groups()
        if kind == "Parameter":
            return f"{PREFIX}.[Parameter:{{{names.uid_of('Parameter', name)}}}]#]"
        element = names.uid_of("Element", name)
        path = f"{PREFIX}.[Element:{{{element}}}].[Parameter:{{{names.uid_of('Parameter', pname, name)}}}]"
        if column:
            path += f".[EntityColumn:{{{names.uid_of('EntityColumn', column, f'{name}.{pname}')}}}]"
        return path + "#]"

    out = SUGAR_RE.sub(repl, text)
    left = LEFTOVER_RE.search(out)
    if left:
        raise ValueError(f"cannot encode {left.group(0)}: the forms are {{Parameter:X}}, {{Element:E.Parameter:P}}, "
                         "{Element:E.Parameter:P.EntityColumn:<uid or Column>}")
    return out


def decode(text, names: Names):
    """Meta paths -> {Element:Name.Parameter:Name}; unknown ids are kept; non-strings pass through."""
    if not isinstance(text, str):
        return text

    def repl(m):
        kind, uid = m.group(1), m.group(2)
        if kind in ("IsOwnerSchema", "IsSchema"):
            return ""
        return f"[{kind}:{names.name_of(uid) or uid}]"

    out = META_PATH_RE.sub(repl, text)
    return re.sub(r"\[#\.*", "{", out).replace("#]", "}").replace("].[", ".").replace("[", "").replace("]", "")


def lookup(schema: str, record: str, shown: str | None = None) -> str:
    """`[#Lookup.<schema>.<record>#]`; with `shown` (the schema's name) the display form `[#Lookup.<name>.<record>.<record>#]`."""
    return f"[#Lookup.{schema}.{record}#]" if shown is None else f"[#Lookup.{shown}.{record}.{record}#]"
