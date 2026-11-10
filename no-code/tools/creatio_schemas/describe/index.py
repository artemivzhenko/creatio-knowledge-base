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
from ..files import LEGACY_ENCODED, read_text
from ..resources import Resources
from ..workspace import Workspace
from .core import DEFAULT_LIMIT, _caption, cut, kind_of, open_item, summary
from .deps import Edge, Resolver, deps_of

INDEX_DIR = ".creatio-index"
INDEX_FORMAT = 4  # 3: typed `deps` edges per item (describe/deps.py); 4: the text extractors (S20-T02)
TYPE_NAME_RE = re.compile(r"\b(?:class|interface|struct|enum|record)\s+(\w+)")
# Identifiers and GUIDs: the two ways a file names another schema.
TOKEN_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}|[A-Za-z_][A-Za-z0-9_]{2,}")  # GUID first: one may start with a letter
SCAN_SUFFIXES = {".json", ".cs", ".js", ".sql", ".less", ".css"}  # resource XML is captions, not references
UNREADABLE = (OSError, UnicodeDecodeError, ValueError, KeyError, IndexError)  # one bad item costs one line, never the answer


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
        self._format_mismatch = self.data.get("format") != INDEX_FORMAT
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
        self._resolver = Resolver(ws)
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
            if entry["summary"].startswith("unreadable: "):  # a reader that answers instead of raising (CSharpSource)
                entry["error"] = entry["summary"][len("unreadable: "):]
            if any((self.package / rel).resolve() in LEGACY_ENCODED for rel in files):
                entry["summary"] += " (cp1251)"
            entry["parent"] = _parent_of(item)
            from .registry import kind_for  # the registry name, not the renamed one: a GenericItem called "mobile" has no page body
            try:
                entry["deps"] = [e.as_dict() for e in deps_of(item, self._resolver, kind_for(item).name)]
            except Exception as e:  # the edges are an extra: a failing extractor costs them, not the item
                entry["deps"], entry["deps_error"] = [], f"{type(e).__name__}: {e}"
            desc = getattr(item, "descriptor", None)
            data = desc.data if hasattr(desc, "data") else (desc or {})
            entry["manager"] = data.get("ManagerName") if isinstance(data, dict) else None
            folders = sorted(p for p in (self.package / "Resources").glob(f"{name}.*") if p.is_dir())
            if folders:
                cultures = {}
                for folder in folders:
                    for culture, values in Resources(folder).cultures.items():
                        cultures.setdefault(culture, {}).update(values)
                base = cultures.get("en-US", {})
                entry["resources"] = {
                    "cultures": sorted(cultures),
                    "keys": len(base),
                    "missing": {culture: len(set(base) - set(values)) for culture, values in cultures.items() if culture != "en-US"},
                }
        except Exception as e:  # one broken schema must not stop the index
            entry["error"] = f"{type(e).__name__}: {e}"
        return entry

    def _json(self, path: Path):
        """A JSON file of a binding; the error names the file (an empty data.json, a missing descriptor)."""
        rel = path.relative_to(self.package).as_posix()
        if not path.is_file():
            raise ValueError(f"{rel}: missing")
        text = read_text(path)[0]
        if not text.strip():
            raise ValueError(f"{rel}: empty file")
        try:
            return json.loads(text)
        except ValueError as e:
            raise ValueError(f"{rel}: not JSON ({e})") from None

    def _build_data(self, name: str, files: dict[str, list[int]]) -> dict:
        desc = self._json(self.package / "Data" / name / "descriptor.json")["Descriptor"]
        columns = desc.get("Columns", [])
        by_uid = {str(c.get("ColumnUId", "")).lower(): c.get("ColumnName") for c in columns}
        key_name = next((candidate for candidate in ("Code", "Name") if any(c.get("ColumnName") == candidate for c in columns)), None)
        key_columns = [c["ColumnName"] for c in columns if c.get("IsKey")]

        def values(row):
            return {(cell.get("ColumnName") or by_uid.get(str(cell.get("SchemaColumnUId", "")).lower())): cell.get("Value")
                    for cell in row["Row"]}

        localized = {}
        loc_files = sorted((self.package / "Data" / name / "Localization").glob("data.*.json"),
                           key=lambda p: (p.name != "data.en-US.json", p.name))
        if key_columns and key_name:
            for path in loc_files:
                for row in self._json(path)["PackageData"]:
                    data = values(row)
                    if all(col in data for col in key_columns) and key_name in data:
                        localized.setdefault(tuple(str(data[col]).lower() for col in key_columns), data[key_name])
        rows, keys = 0, []
        for path in sorted((self.package / "Data" / name).rglob("data.json")):
            if "localization" in (part.lower() for part in path.relative_to(self.package / "Data" / name).parts):
                continue
            data_rows = self._json(path)["PackageData"]
            rows += len(data_rows)
            for row in data_rows:
                data = values(row)
                value = data.get(key_name)
                if value is None and key_columns and all(col in data for col in key_columns):
                    value = localized.get(tuple(str(data[col]).lower() for col in key_columns))
                if value is not None and len(keys) < DEFAULT_LIMIT:
                    keys.append(value)
        schema = desc.get("Schema", {}).get("Name")
        deps = [Edge("object", *self._resolver.entity(schema), "binds", "name", [c["ColumnName"] for c in columns]).as_dict()] if schema else []
        return {"schema": schema, "columns": [c["ColumnName"] for c in columns],
                "rows": rows, "keys": keys, "files": files, "refs": self._refs(files, name), "deps": deps}

    def refresh(self, rebuild: bool = False) -> dict:
        """Bring the index in line with the disk; returns {"added": [...], "changed": [...], "removed": [...]}."""
        t0 = time.time()
        from .registry import KINDS  # the kinds and their order: a registry change must re-read every item (R01 finding 1)

        registry_fp = "|".join(k.name for k in KINDS)
        rebuild = rebuild or self._format_mismatch or self.data.get("registry") != registry_fp
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
        if not any(changes.values()) and not self._format_mismatch:
            return changes
        self._load_names()
        for name in changes["removed"]:
            (data if name.startswith("Data/") else schemas).pop(name.removeprefix("Data/"), None)
        for name, folder in todo_schemas:
            schemas[name] = self._build_schema(name, files_now[name])
        for name in todo_data:
            try:
                data[name] = self._build_data(name, files_now[f"Data/{name}"])
            except UNREADABLE as e:  # an empty data.json, a folder without its descriptor
                data[name] = {"error": f"{type(e).__name__}: {e}", "files": files_now[f"Data/{name}"], "refs": []}
        if rebuild or changes["added"] or changes["removed"]:
            # The set of names changed: every item may now refer to a new name, or to one that is gone.
            for name, entry in schemas.items():
                if name not in dict(todo_schemas):
                    entry["refs"] = self._refs(entry["files"], name)
            for name, entry in data.items():
                if name not in todo_data:
                    entry["refs"] = self._refs(entry["files"], name)
        desc = json.loads(read_text(self.package / "descriptor.json")[0])["Descriptor"]
        self.data = {"format": INDEX_FORMAT, "registry": registry_fp, "package": desc.get("Name", self.package.name), "version": desc.get("PackageVersion"),
                     "depends_on": [d["Name"] for d in desc.get("DependsOn", [])],
                     "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "seconds": round(time.time() - t0, 2),
                     "schemas": dict(sorted(schemas.items())), "data": dict(sorted(data.items()))}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=1, ensure_ascii=False), encoding="utf-8")
        self._format_mismatch = False
        return changes

    # -- answering ------------------------------------------------------------- #

    @property
    def schemas(self) -> dict:
        return self.data.get("schemas", {})

    def entries(self) -> list[tuple[str, dict]]:
        """(name, entry) of every schema and data binding (`Data/<name>`)."""
        return list(self.schemas.items()) + [(f"Data/{n}", e) for n, e in self.data.get("data", {}).items()]

    def dependents(self, name: str) -> list[tuple[str, str, Edge]]:
        """(kind, name, edge) of every item whose typed edges point at `name`."""
        key = name.lower()
        out = []
        for n, e in self.entries():
            for d in e.get("deps", []):
                if d["name"].lower() == key:
                    out.append((e.get("kind", "data"), n, Edge.from_dict(d)))
        return out

    def referrers(self, name: str) -> list[tuple[str, str]]:
        """(kind, name) of every schema or data binding in this package that refers to `name`."""
        hits = [(e["kind"], n) for n, e in self.schemas.items() if name in e.get("refs", [])]
        hits += [("data", n) for n, e in self.data.get("data", {}).items() if name in e.get("refs", []) or e.get("schema") == name]
        return hits

    def lines(self, kind: str = "") -> list[str]:
        """The describe_package lines, from the index; `kind="error"` lists only the unreadable items."""
        out = []
        for name, e in self.schemas.items():
            if "error" in e:
                if kind and kind not in ("schema", "error"):
                    continue
                out.append(f"  {'?':<9} {name:<36} {'':<34} cannot read: {e['error']}")
            elif not kind or e["kind"] == kind:
                out.append(f"  {e['kind']:<9} {name:<36} {e['caption']!r:<34} {e['summary']}")
        if kind in ("", "error"):
            out += [f"  {'?':<9} {'Data/' + name:<36} {'':<34} cannot read: {e['error']}" for name, e in self.data.get("data", {}).items() if "error" in e]
        return out


def _unreadable(idx) -> int:
    return sum("error" in e for e in idx.schemas.values()) + sum("error" in e for e in idx.data.get("data", {}).values())


def _unreadable_line(indexes: list[PackageIndex]) -> list[str]:
    """The one line find_schema and lookups end with when items were skipped."""
    broken = [idx for idx in indexes if _unreadable(idx)]
    if not broken:
        return []
    n = sum(_unreadable(idx) for idx in broken)
    where = ", ".join(f"describe.py package {idx.package} --kind error" for idx in broken[:3]) + (" ..." if len(broken) > 3 else "")
    return [f"{n} items unreadable ({where} lists them)"]


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


from ..entity.catalog import STOCK_LOOKUPS  # noqa: E402  (stock_lookups_<version>.json: 8.3.2 when present, else 8.2.3)


def lookups(path: Path | str, limit: int = DEFAULT_LIMIT) -> str:
    """Every object of the workspace that is a lookup - its parent chain reaches BaseLookup, through the workspace's own
    objects or the stock ones (entity/assets/stock_lookups_<version>.json) - with package, caption, own columns, data bindings
    (rows bound) and how many items refer to it: the list a de-duplication or binding-check task starts from."""
    cut([], limit)
    pkgs = packages_of(path)
    indexes = [PackageIndex(p) for p in pkgs]
    for idx in indexes:
        idx.refresh()
    parents = {n: e.get("parent") for idx in indexes for n, e in idx.schemas.items() if e.get("kind") == "object"}

    def is_lookup(name: str, seen: frozenset = frozenset()) -> bool | None:
        """True / False, or None when the chain leaves the workspace into an object the stock list does not know."""
        if name == "BaseLookup" or name in STOCK_LOOKUPS:
            return True
        if name == "BaseEntity" or name in seen:
            return False
        parent = parents.get(name)
        if parent is None:
            return None if name in parents else (True if name in STOCK_LOOKUPS else None)
        return is_lookup(parent, seen | {name})

    rows, unknown = [], []
    for idx in indexes:
        pkg = idx.data.get("package", idx.package.name)
        for n, e in idx.schemas.items():
            if e.get("kind") != "object":
                continue
            verdict = is_lookup(n)
            if verdict is None:
                unknown.append(f"{n} (parent {parents.get(n)}, {pkg})")
                continue
            if not verdict:
                continue
            chain, cur = [], parents.get(n)
            while cur and cur not in chain and cur != "BaseLookup":
                chain.append(cur)
                cur = parents.get(cur)
            own = re.search(r"\((\d+) own\)", e.get("summary", ""))
            bindings = []
            for dn, de in idx.data.get("data", {}).items():
                if de.get("schema") == n and "error" not in de:
                    bindings.append(f"Data/{dn} ({de['rows']} rows)")
            users = sum(len(other.referrers(n)) for other in indexes)
            rows.append(f"  {n:<34} {e.get('caption', '')!r:<30} {pkg:<16} "
                        + ("replacing " if "replacing" in e.get("summary", "") else "parent ") + " -> ".join(chain + ["BaseLookup"])
                        + (f"  {own.group(1)} own columns" if own else "") + f"  bindings: {', '.join(bindings) if bindings else 'none'}  used by {users}")
    out = [f"{len(rows)} lookups in {', '.join(p.name for p in pkgs)}"] + cut(rows, limit)
    if unknown:
        out.append(f"  not decided ({len(unknown)}; parent outside the workspace and the stock list):")
        out.extend(cut([f"    {item}" for item in unknown], limit))
    return "\n".join(out + _unreadable_line(indexes))


def find_schema(path: Path | str, name: str, limit: int = DEFAULT_LIMIT) -> str:
    """Where a schema lives and what touches it: package, kind, files (absolute), what it refers to, who refers to it, its data bindings."""
    cut([], limit)
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
            if "error" in e:  # the one asked for is broken: say so in one line, list nothing of it
                out.append(f"{n}  cannot read, in {idx.data.get('package', idx.package.name)}: {e['error']}")
                continue
            out.append(f"{n}  {e['kind']} in {idx.data.get('package', idx.package.name)}  ({idx.package})")
            parent = e.get("parent")
            out.append(f"  {e['summary']}" + (f"; caption {e['caption']!r}" if e["caption"] else "") + (f"; builds on {parent}" if parent and parent not in e["summary"] else "") + (f"; {e['error']}" if "error" in e else ""))
            resources = e.get("resources")
            if resources is not None:
                out.append(f"  resources: {', '.join(resources['cultures'])}; {resources['keys']} keys; missing: "
                           + (", ".join(f"{c}={count}" for c, count in resources["missing"].items()) or "none"))
            bindings = [f"Data/{dn} ({de['rows']} rows, {other.package.name})"
                        for other in indexes for dn, de in other.data.get("data", {}).items() if de.get("schema") == n and "error" not in de]
            if bindings:
                shown = cut(bindings, limit)
                tail = shown.pop() if limit and len(shown) > limit else None
                out.append("  bindings: " + ", ".join(shown))
                if tail:
                    out.append(tail)
            out.append("  files:")
            out += _file_lines(idx.package, e["files"])
            typed = [Edge.from_dict(d).line() for d in e.get("deps", [])]
            if typed:
                shown = cut(typed, limit)
                tail = shown.pop() if limit and len(shown) > limit else None
                out.append("  depends on: " + "; ".join(shown))
                if tail:
                    out.append(tail)
            dependents = sorted(f"{fk} {fn}{'' if other is idx else ', ' + other.package.name} ({ed.via})" for other in indexes for fk, fn, ed in other.dependents(n))
            if dependents:
                shown = cut(dependents, limit)
                tail = shown.pop() if limit and len(shown) > limit else None
                out.append("  dependents: " + "; ".join(shown))
                if tail:
                    out.append(tail)
            if e.get("refs"):
                refs = cut(e["refs"], limit)
                tail = refs.pop() if len(refs) > limit and limit else None
                out.append(f"  refers to: {', '.join(refs)}")
                if tail:
                    out.append(tail)
            users = []
            for other in indexes:
                users += [f"{un} ({uk}{'' if other is idx else ', ' + other.package.name})" for uk, un in other.referrers(n)]
            limited_users = cut(users, limit)
            tail = limited_users.pop() if len(limited_users) > limit and limit else None
            out.append(f"  used by: {', '.join(limited_users)}" if users else "  used by: nothing in the workspace")
            if tail:
                out.append(tail)
    if not out:
        out = [f"no schema named {name} in {', '.join(p.name for p in pkgs)}"]
    return "\n".join(out + _unreadable_line(indexes))
