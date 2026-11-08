"""The package index: the project's knowledge-base file, one JSON per package.

For every schema, SQL script and data binding it stores the kind, caption, summary line, the
parent or target, every file that belongs to it (with size and mtime) and the other schemas
of the workspace it refers to. `describe_package` and `find_schema` answer from it, so a
package of 500 schemas is listed in milliseconds instead of being parsed again, and an agent
gets the files of a schema without searching. The index checks itself on every use: a file
that changed, a schema that appeared (after `clio pull-pkg`) or disappeared is re-read before
the answer, so there is no refresh hook to forget.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from ..csharp import csharp_files
from ..files import read_text
from ..workspace import Workspace
from .core import _caption, kind_of, open_item, summary

INDEX_DIR = ".creatio-index"
TYPE_NAME_RE = re.compile(r"\b(?:class|interface|struct|enum|record)\s+(\w+)")
# Identifiers and GUIDs: the two ways a file names another schema.
TOKEN_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}|[A-Za-z_][A-Za-z0-9_]{2,}")  # GUID first: one may start with a letter
SCAN_SUFFIXES = {".json", ".cs", ".js", ".sql", ".less", ".css"}  # resource XML is captions, not references


def index_path(package: Path) -> Path:
    """<workspace>/.creatio-index/<Package>.json in a clio workspace; next to the package folder otherwise."""
    package = Path(package)
    root = package.parent.parent if package.parent.name == "packages" else package.parent
    return root / INDEX_DIR / f"{package.name}.json"


def packages_of(path: Path | str) -> list[Path]:
    """The package folders a path means: a package, a clio workspace root, or a folder of packages."""
    path = Path(path)
    if (path / "descriptor.json").is_file():
        return [path]
    root = path / "packages" if (path / "packages").is_dir() else path
    pkgs = sorted(p for p in root.iterdir() if (p / "descriptor.json").is_file()) if root.is_dir() else []
    if not pkgs:
        raise FileNotFoundError(f"{path} is neither a package nor a folder with packages")
    return pkgs


def _stat(path: Path) -> list[int]:
    st = path.stat()
    return [st.st_size, st.st_mtime_ns]


class PackageIndex:
    """One package's index: load, check against the disk, answer."""

    def __init__(self, package: Path | str):
        self.package = Path(package)
        self.path = index_path(self.package)
        self.data: dict = {"schemas": {}, "data": {}}
        if self.path.is_file():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
            except ValueError:
                pass
        self._names: dict[str, str] = {}  # lower-case name and uid -> schema name, whole workspace

    # -- disk -------------------------------------------------------------- #

    def _items_on_disk(self) -> dict[str, str]:
        """{name: "Schemas" | "SqlScripts" | "Files"} - every item folder with a descriptor, plus every plain C# file under
        Files (named by its package-relative path: it has no descriptor, no resources, nothing but the one file)."""
        found = {}
        for folder in ("Schemas", "SqlScripts"):
            if (self.package / folder).is_dir():
                for d in (self.package / folder).iterdir():
                    if (d / "descriptor.json").is_file():
                        found[d.name] = folder
        for cs in csharp_files(self.package):
            found[cs.relative_to(self.package).as_posix()] = "Files"
        return found

    def _item_files(self, name: str, folder: str) -> dict[str, list[int]]:
        if folder == "Files":
            return {name: _stat(self.package / name)}
        files = {}
        dirs = [self.package / folder / name] + list((self.package / "Resources").glob(f"{name}.*")) if (self.package / "Resources").is_dir() else [self.package / folder / name]
        for d in dirs:
            for p in sorted(d.rglob("*")):
                if p.is_file():
                    files[p.relative_to(self.package).as_posix()] = _stat(p)
        return files

    def _data_files(self, name: str) -> dict[str, list[int]]:
        return {p.relative_to(self.package).as_posix(): _stat(p) for p in sorted((self.package / "Data" / name).rglob("*")) if p.is_file()}

    def _stale(self, entry: dict, files_now: dict[str, list[int]]) -> bool:
        return entry.get("files") != files_now

    # -- building ------------------------------------------------------------ #

    def _load_names(self) -> None:
        ws = Workspace(self.package)
        self._names = {}
        for s in ws.schemas:
            self._names[s["name"].lower()] = s["name"]
            self._names[s["uid"]] = s["name"]
            self._names[s["base"]] = s["name"]  # a lookup points at the base UId of a replacing schema
        for pkg in self.package.parent.iterdir():
            if (pkg / "SqlScripts").is_dir():
                for d in (pkg / "SqlScripts").iterdir():
                    if (d / "descriptor.json").is_file():
                        self._names[d.name.lower()] = d.name
            for cs in csharp_files(pkg):  # a plain C# file is referred to by the types it declares
                item = cs.relative_to(pkg).as_posix()
                try:
                    text = read_text(cs)[0]
                except (OSError, UnicodeDecodeError):
                    continue
                for type_name in TYPE_NAME_RE.findall(text):
                    self._names.setdefault(type_name.lower(), item)

    def _refs(self, files: dict[str, list[int]], own: str) -> list[str]:
        """Schemas of the workspace named (by identifier or UId) in the item's text files, itself excluded."""
        hits = set()
        for rel in files:
            if Path(rel).suffix.lower() not in SCAN_SUFFIXES:
                continue
            try:
                text = read_text(self.package / rel)[0]
            except (OSError, UnicodeDecodeError):
                continue
            for tok in TOKEN_RE.findall(text):
                name = self._names.get(tok.lower())
                if name and name != own:
                    hits.add(name)
        return sorted(hits)

    def _build_schema(self, name: str, files: dict[str, list[int]]) -> dict:
        entry = {"kind": "?", "caption": "", "summary": "", "parent": None, "files": files, "refs": self._refs(files, name)}
        try:
            item = open_item(self.package, name)
            entry["kind"] = kind_of(item)
            entry["caption"] = _caption(item)
            entry["summary"] = summary(item)
            entry["parent"] = _parent_of(item)
            desc = getattr(item, "descriptor", None)
            data = desc.data if hasattr(desc, "data") else (desc or {})
            entry["manager"] = data.get("ManagerName") if isinstance(data, dict) else None
        except Exception as e:  # one broken schema must not stop the index
            entry["error"] = f"{type(e).__name__}: {e}"
        return entry

    def _build_data(self, name: str, files: dict[str, list[int]]) -> dict:
        target = None
        try:
            target = json.loads(read_text(self.package / "Data" / name / "descriptor.json")[0])["Descriptor"].get("Schema", {}).get("Name")
        except (OSError, ValueError, KeyError):
            pass
        return {"schema": target, "files": files, "refs": self._refs(files, name)}

    def refresh(self, rebuild: bool = False) -> dict:
        """Bring the index in line with the disk; returns {"added": [...], "changed": [...], "removed": [...]}."""
        t0 = time.time()
        on_disk = self._items_on_disk()
        data_on_disk = sorted(d.name for d in (self.package / "Data").iterdir() if d.is_dir()) if (self.package / "Data").is_dir() else []
        schemas, data = self.data.get("schemas", {}), self.data.get("data", {})
        changes = {"added": [], "changed": [], "removed": []}
        changes["removed"] = sorted(set(schemas) - set(on_disk)) + sorted(f"Data/{n}" for n in set(data) - set(data_on_disk))
        todo_schemas, todo_data = [], []
        files_now: dict[str, dict] = {}
        for name, folder in on_disk.items():
            entry = schemas.get(name)
            files_now[name] = self._item_files(name, folder)
            if rebuild or entry is None or self._stale(entry, files_now[name]):
                todo_schemas.append((name, folder))
                changes["added" if entry is None else "changed"].append(name)
        for name in data_on_disk:
            entry = data.get(name)
            files_now[f"Data/{name}"] = self._data_files(name)
            if rebuild or entry is None or self._stale(entry, files_now[f"Data/{name}"]):
                todo_data.append(name)
                changes["added" if entry is None else "changed"].append(f"Data/{name}")
        if not any(changes.values()):
            return changes
        self._load_names()
        for name in changes["removed"]:
            (data if name.startswith("Data/") else schemas).pop(name.removeprefix("Data/"), None)
        for name, folder in todo_schemas:
            schemas[name] = self._build_schema(name, files_now[name])
        for name in todo_data:
            data[name] = self._build_data(name, files_now[f"Data/{name}"])
        if rebuild or changes["added"] or changes["removed"]:
            # The set of names changed: every item may now refer to a new name, or to one that is gone.
            for name, entry in schemas.items():
                if name not in dict(todo_schemas):
                    entry["refs"] = self._refs(entry["files"], name)
            for name, entry in data.items():
                if name not in todo_data:
                    entry["refs"] = self._refs(entry["files"], name)
        desc = json.loads(read_text(self.package / "descriptor.json")[0])["Descriptor"]
        self.data = {"package": desc.get("Name", self.package.name), "version": desc.get("PackageVersion"),
                     "depends_on": [d["Name"] for d in desc.get("DependsOn", [])],
                     "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "seconds": round(time.time() - t0, 2),
                     "schemas": dict(sorted(schemas.items())), "data": dict(sorted(data.items()))}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=1, ensure_ascii=False), encoding="utf-8")
        return changes

    # -- answering ------------------------------------------------------------- #

    @property
    def schemas(self) -> dict:
        return self.data.get("schemas", {})

    def referrers(self, name: str) -> list[tuple[str, str]]:
        """(kind, name) of every schema or data binding in this package that refers to `name`."""
        hits = [(e["kind"], n) for n, e in self.schemas.items() if name in e.get("refs", [])]
        hits += [("data", n) for n, e in self.data.get("data", {}).items() if name in e.get("refs", []) or e.get("schema") == name]
        return hits

    def lines(self, kind: str = "") -> list[str]:
        """The describe_package lines, from the index."""
        out = []
        for name, e in self.schemas.items():
            if "error" in e:
                if kind and kind != "schema":
                    continue
                out.append(f"  {'?':<9} {name:<36} {'':<34} cannot read: {e['error']}")
            elif not kind or e["kind"] == kind:
                out.append(f"  {e['kind']:<9} {name:<36} {e['caption']!r:<34} {e['summary']}")
        return out


def _file_lines(package: Path, files: dict[str, list[int]]) -> list[str]:
    """One line per file, the per-culture files of a folder (resource.*.xml, data.*.json) folded into one."""
    cultures: dict[str, list[int]] = {}
    lines = []
    for rel, (size, _) in files.items():
        m = re.fullmatch(r"(.*/)(resource|data)\.[a-z]{2}-[A-Z]{2}\.(xml|json)", rel)
        if m:
            key = f"{m.group(1)}{m.group(2)}.*.{m.group(3)}"
            cultures.setdefault(key, [0, 0])
            cultures[key][0] += 1
            cultures[key][1] += size
        else:
            lines.append(f"    {(package / rel).as_posix()}  ({size} bytes)")
    for key, (n, size) in cultures.items():
        lines.append(f"    {(package / key).as_posix()}  ({n} cultures, {size} bytes)")
    return lines


def _parent_of(item) -> str | None:
    """What the schema builds on: the object's parent or replaced base, the page's entity or parent page, the rules' target."""
    for attr in ("parent_name", "target", "entity"):
        value = getattr(item, attr, None)
        if value:
            return value
    desc = getattr(item, "descriptor", None)
    data = desc.data if hasattr(desc, "data") else (desc or {})
    if isinstance(data, dict) and data.get("ExtendParent") and data.get("Parent"):
        return data["Parent"].get("Name")
    return None


def index_workspace(path: Path | str, rebuild: bool = False) -> str:
    """Refresh the index of every package under `path`; one line per package with what changed."""
    out = []
    for pkg in packages_of(path):
        idx = PackageIndex(pkg)
        ch = idx.refresh(rebuild)
        d = idx.data
        out.append(f"{pkg.name}: {len(d.get('schemas', {}))} schemas, {len(d.get('data', {}))} data bindings"
                   + (f"; +{len(ch['added'])} added, ~{len(ch['changed'])} changed, -{len(ch['removed'])} removed in {d.get('seconds', 0)} s" if any(ch.values()) else "; up to date")
                   + f"  -> {idx.path}")
        for key in ("added", "changed", "removed"):
            if ch[key]:
                out.append(f"    {key}: {', '.join(ch[key][:20])}" + (f" ... +{len(ch[key]) - 20}" if len(ch[key]) > 20 else ""))
    return "\n".join(out)


def find_schema(path: Path | str, name: str) -> str:
    """Where a schema lives and what touches it: package, kind, files (absolute), what it refers to, who refers to it, its data bindings."""
    pkgs = packages_of(path)
    indexes = [PackageIndex(p) for p in pkgs]
    for idx in indexes:
        idx.refresh()
    key = name.lower()
    out = []
    for idx in indexes:
        for n, e in idx.schemas.items():
            # a plain C# file answers to its path, its file name or its stem
            if n.lower() != key and not (e["kind"] == "csharp" and key in (Path(n).name.lower(), Path(n).stem.lower())):
                continue
            out.append(f"{n}  {e['kind']} in {idx.data.get('package', idx.package.name)}  ({idx.package})")
            parent = e.get("parent")
            out.append(f"  {e['summary']}" + (f"; caption {e['caption']!r}" if e["caption"] else "") + (f"; builds on {parent}" if parent and parent not in e["summary"] else "") + (f"; {e['error']}" if "error" in e else ""))
            out.append("  files:")
            out += _file_lines(idx.package, e["files"])
            if e.get("refs"):
                out.append(f"  refers to: {', '.join(e['refs'])}")
            users = []
            for other in indexes:
                users += [f"{un} ({uk}{'' if other is idx else ', ' + other.package.name})" for uk, un in other.referrers(n)]
            out.append(f"  used by: {', '.join(users)}" if users else "  used by: nothing in the workspace")
    if not out:
        return f"no schema named {name} in {', '.join(p.name for p in pkgs)}"
    return "\n".join(out)
