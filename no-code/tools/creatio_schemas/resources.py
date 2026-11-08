"""Localizable strings of a schema: Resources/<Schema>.<Kind>/resource.<culture>.xml."""

from __future__ import annotations

import re
from pathlib import Path
from xml.sax.saxutils import escape, unescape

from .files import CRLF, newline_of, read_text

# Name, then any other attributes (images carry Type, ContentType, FileExtension), then Value.
_ITEM_RE = re.compile(r'<Item Name="([^"]*)"((?: [A-Za-z]+="[^"]*")*?) Value="([^"]*)" />')
# the platform's XmlWriter: quotes as &quot;, line breaks and tabs inside a value as character references
_XML_ESCAPE = {'"': "&quot;", "\n": "&#xA;", "\r": "&#xD;", "\t": "&#x9;"}
_XML_UNESCAPE = {"&quot;": '"', "&apos;": "'", "&#xA;": "\n", "&#xD;": "\r", "&#x9;": "\t"}


class Resources:
    """{culture: {key: value}} of one schema; anything besides the String group is kept as raw text."""

    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self.cultures: dict[str, dict[str, str]] = {}
        self.extra: dict[str, str] = {}
        self.attrs: dict[str, dict[str, str]] = {}  # {culture: {key: ' Type="Image" ...'}} for items that are not plain strings
        self._read_order: dict[str, list[str]] = {}
        self._newline: dict[str, str] = {}
        for path in sorted(self.folder.glob("resource.*.xml")):
            culture = path.name[len("resource."):-len(".xml")]
            text = read_text(path)[0]
            found = _ITEM_RE.findall(text)
            self.cultures[culture] = {k: unescape(v, _XML_UNESCAPE) for k, mid, v in found}
            self.attrs[culture] = {k: mid for k, mid, v in found if mid}
            self._read_order[culture] = list(self.cultures[culture])
            self._newline[culture] = newline_of(text)  # a git checkout may have made them LF
            rest = re.sub(r'<Group Type="String">.*?</Group>\r?\n?', "", text, count=1, flags=re.S)
            rest = re.sub(r'<\?xml[^>]*>\r?\n?|<Resources[^>]*>\r?\n?|</Resources>\s*$', "", rest, flags=re.S)
            self.extra[culture] = rest.strip()

    @classmethod
    def empty(cls, folder: Path, cultures: list[str]) -> "Resources":
        res = cls(folder)
        for culture in cultures:
            res.cultures.setdefault(culture, {})
        return res

    # -- read ---------------------------------------------------------------- #

    def get(self, key: str, culture: str = "en-US") -> str | None:
        return self.cultures.get(culture, {}).get(key)

    def missing(self, source: str = "en-US") -> dict[str, list[str]]:
        """Keys of `source` absent in each other culture."""
        base = self.cultures.get(source, {})
        return {c: [k for k in base if k not in items] for c, items in self.cultures.items() if c != source}

    # -- change -------------------------------------------------------------- #

    def set(self, key: str, value: str, cultures: list[str] | None = None) -> None:
        """Set in the given cultures, or in every culture the schema has."""
        for culture in cultures or list(self.cultures):
            self.cultures.setdefault(culture, {})[key] = value

    def remove(self, predicate) -> int:
        n = 0
        for culture, items in self.cultures.items():
            for k in [k for k in items if predicate(k)]:
                del items[k]
                self.attrs.get(culture, {}).pop(k, None)
                n += 1
        return n

    def remove_prefix(self, prefix: str) -> int:
        """`prefix` itself and every key under `prefix.`."""
        return self.remove(lambda k: k == prefix or k.startswith(prefix + "."))

    def rename_prefix(self, old: str, new: str) -> int:
        n = 0
        for culture, items in self.cultures.items():
            for k in [k for k in items if k == old or k.startswith(old + ".")]:
                items[new + k[len(old):]] = items.pop(k)
                if k in self.attrs.get(culture, {}):
                    self.attrs[culture][new + k[len(old):]] = self.attrs[culture].pop(k)
                n += 1
        return n

    # -- write --------------------------------------------------------------- #

    def ordered_keys(self, culture: str) -> list[str]:
        """Keys in the file's own order (the platform sorts with .NET rules, not ordinal ones); a new key goes
        before the first existing key that sorts after it."""
        items = self.cultures[culture]
        out = [k for k in self._read_order.get(culture, []) if k in items]
        known = set(out)
        for k in sorted(k for k in items if k not in known):
            out.insert(next((i for i, x in enumerate(out) if x > k), len(out)), k)
        return out

    def render(self, culture: str) -> str:
        """The file text without its BOM (the files always carry one)."""
        lines = ['<?xml version="1.0" encoding="utf-8"?>', f'<Resources Culture="{culture}">', '\t<Group Type="String">', "\t\t<Items>"]
        for k in self.ordered_keys(culture):
            mid = self.attrs.get(culture, {}).get(k, "")
            lines.append(f'\t\t\t<Item Name="{escape(k, _XML_ESCAPE)}"{mid} Value="{escape(self.cultures[culture][k], _XML_ESCAPE)}" />')
        lines += ["\t\t</Items>", "\t</Group>"]
        if self.extra.get(culture):
            lines.append("\t" + self.extra[culture])
        lines.append("</Resources>")
        return self._newline.get(culture, CRLF).join(lines)

    def files(self) -> dict[Path, tuple[str, bool]]:
        return {self.folder / f"resource.{c}.xml": (self.render(c), True) for c in self.cultures}
