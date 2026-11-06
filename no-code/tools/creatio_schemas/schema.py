"""The base of every schema type: files on disk, descriptor, resources, dry-run diff, save."""

from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

from .files import CRLF, dump_json, newline_of, read_text, wcf_now, write_text
from .resources import Resources
from .workspace import Workspace

WARNING = "warning: "  # validate() problems with this prefix do not block a save


_WCF_DATE_RE = re.compile(r'"/Date\((\d+)\)/"')


class Descriptor:
    """descriptor.json kept as text, so a save changes only what was edited. `root` is "Descriptor" for
    schemas, "SqlScript" for SQL scripts."""

    def __init__(self, path: Path, text: str | None = None, root: str = "Descriptor"):
        self.path = Path(path)
        self.root = root
        self.text = read_text(self.path)[0] if text is None else text

    @classmethod
    def new(cls, path: Path, fields: dict, root: str = "Descriptor") -> "Descriptor":
        """`fields` in the platform's key order; ModifiedOnUtc is filled in (the push fails on any other date format)."""
        text = dump_json({root: dict(fields, ModifiedOnUtc="")}, CRLF)
        return cls(path, text.replace('"ModifiedOnUtc": ""', f'"ModifiedOnUtc": "{wcf_now()}"'), root)

    @property
    def data(self) -> dict:
        return json.loads(self.text)[self.root]

    def set(self, key: str, value) -> None:
        """Change one field; the text is re-dumped (keeping the WCF date literal) only when the value differs."""
        data = self.data
        if data.get(key) == value and key in data:
            return
        data[key] = value
        nl = CRLF if CRLF in self.text else "\n"
        self.text = _WCF_DATE_RE.sub(r'"\\/Date(\1)\\/"', dump_json({self.root: data}, nl))

    def set_caption(self, value: str) -> None:
        literal = json.dumps(value, ensure_ascii=False)[1:-1]
        self.text = re.sub(r'("Caption":\s*")[^"]*(")', lambda m: m.group(1) + literal + m.group(2), self.text, count=1)

    def touch(self) -> None:
        self.text = re.sub(r'"\\/Date\(\d+\)\\/"', lambda m: f'"{wcf_now()}"', self.text, count=1)


class PackageItem:
    """Anything a package stores as files and the platform installs: a schema, a SQL script...

    A subclass sets `self.descriptor` and implements `files()`; diff, save and the problem
    filter come from here. An unchanged item must render to the bytes it was read from.
    """

    def __init__(self, package: Path, name: str):
        self.package = Path(package)
        self.name = name
        self._workspace: Workspace | None = None
        self.descriptor: Descriptor

    def files(self) -> dict[Path, tuple[str, bool]]:
        """What save() writes: {path: (text, with BOM)}."""
        raise NotImplementedError

    def validate(self) -> list[str]:
        """Problems; those starting with WARNING are advisory."""
        return []

    def describe(self) -> str:
        return self.name

    @property
    def workspace(self) -> Workspace:
        """The other schemas next to this package (scanned once, on first use)."""
        if self._workspace is None:
            self._workspace = Workspace(self.package)
        return self._workspace

    def errors(self) -> list[str]:
        return [p for p in self.validate() if not p.startswith(WARNING)]

    def diff(self) -> str:
        """Unified diff of the pending changes against the files on disk."""
        chunks = []
        for path, (text, _) in self.files().items():
            old = read_text(path)[0] if path.is_file() else ""
            if old != text:
                rel = path.relative_to(self.package).as_posix()
                chunks += difflib.unified_diff(old.splitlines(True), text.splitlines(True), f"a/{rel}", f"b/{rel}")
        return "".join(chunks)

    def save(self) -> None:
        """Write files() and stamp the descriptor's ModifiedOnUtc."""
        self.descriptor.touch()
        for path, (text, bom) in self.files().items():
            write_text(path, text, bom)


class Schema(PackageItem):
    """One schema folder of a package: Schemas/<Name>/ plus Resources/<Name>.<RESOURCE_SUFFIX>/.

    A subclass parses metadata.json in `load_metadata` and renders it back in `render_metadata`.
    """

    RESOURCE_SUFFIX = ""

    def __init__(self, package: Path, name: str):
        super().__init__(package, name)
        self.dir = self.package / "Schemas" / name
        self.metadata_path = self.dir / "metadata.json"
        if not self.metadata_path.is_file():
            raise FileNotFoundError(f"no schema {name} in {self.package}")
        self.descriptor = Descriptor(self.dir / "descriptor.json")
        self.resources = Resources(self.package / "Resources" / f"{name}.{self.RESOURCE_SUFFIX}")
        text, self.metadata_bom = read_text(self.metadata_path)
        self.newline = newline_of(text)
        self.load_metadata(text)

    def load_metadata(self, text: str) -> None:
        raise NotImplementedError

    def render_metadata(self) -> str:
        raise NotImplementedError

    def files(self) -> dict[Path, tuple[str, bool]]:
        out = {self.metadata_path: (self.render_metadata(), self.metadata_bom), self.descriptor.path: (self.descriptor.text, True)}
        out.update(self.resources.files())
        return out
