"""Packages and the workspace around them: schema lookup by name or UId, entity columns, page models."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .files import DATA_VALUE_TYPES, is_uid, read_text

# Columns every entity inherits from BaseEntity; a package copy of an entity does not list them.
BASE_COLUMNS = {"Id": ("Guid", None), "CreatedOn": ("DateTime", None), "CreatedBy": ("Lookup", "Contact"), "ModifiedOn": ("DateTime", None),
                "ModifiedBy": ("Lookup", "Contact"), "ProcessListeners": ("Integer", None)}
DIFF_LINE_RE = re.compile(r"^([=+\-~]) (MetaData\.Schema\S*)(?: (.*))?$")

_CACHE: dict[Path, tuple[tuple, list[dict]]] = {}


def _fingerprint(root: Path) -> tuple:
    """Fingerprint of root folder and every */Schemas folder under it (based on directory mtimes)."""
    root = root.resolve()
    try:
        fp = [os.stat(root).st_mtime_ns]
    except (OSError, AttributeError):
        return None
    for schemas_dir in sorted(root.glob("*/Schemas")):
        try:
            fp.append(os.stat(schemas_dir).st_mtime_ns)
        except (OSError, AttributeError):
            return None
    return tuple(fp)


def parse_diff(text: str) -> list[tuple[str, str, str]]:
    """Lines of a replacing schema's metadata.json (`op path value`, values may span lines) as (op, path, value); CRLF expected."""
    ops = []
    for line in text.split("\r\n"):
        m = DIFF_LINE_RE.match(line)
        if m:
            ops.append([m.group(1), m.group(2), [m.group(3) or ""]])
        elif ops:
            ops[-1][2].append(line)
    return [(op, path, "\r\n".join(v)) for op, path, v in ops]


class Package:
    """A package folder: descriptor.json, Schemas/, Resources/."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.descriptor = json.loads(read_text(self.path / "descriptor.json")[0])["Descriptor"]

    @property
    def uid(self) -> str:
        return self.descriptor["UId"]

    @property
    def name(self) -> str:
        return self.descriptor["Name"]

    def created_in_uid(self) -> str:
        """A5 (CreatedInPackageId) as the package's existing schemas carry it; the package UId when it has none."""
        for meta in self.path.glob("Schemas/*/metadata.json"):
            hit = re.search(r'"A5": "([0-9a-f-]{36})"|MetaData\.Schema\.A5 "([0-9a-f-]{36})"', read_text(meta)[0][:2000])
            if hit:
                return hit.group(1) or hit.group(2)
        return self.uid


class Workspace:
    """Every schema descriptor in the packages folder that holds a package (the clio workspace layout)."""

    scans: int = 0

    def __init__(self, package: Path):
        self.root = Path(package).parent
        fp = _fingerprint(self.root)
        
        if fp and fp in _CACHE:
            cached_schemas, _ = _CACHE[fp]
            self.schemas = list(cached_schemas)
        else:
            self.schemas: list[dict] = []
            for desc in sorted(self.root.glob("*/Schemas/*/descriptor.json")):
                try:
                    d = json.loads(read_text(desc)[0])["Descriptor"]
                except (ValueError, KeyError):
                    continue
                uid = d["UId"].lower()
                self.schemas.append({"name": d["Name"], "uid": uid, "manager": d.get("ManagerName"), "dir": desc.parent,
                                     "base": (d.get("Parent") or {}).get("UId", uid).lower() if d.get("ExtendParent") else uid,
                                     "caption": d.get("Caption", d["Name"])})
            Workspace.scans += 1
            if fp:
                _CACHE[fp] = (self.schemas, fp)

    @staticmethod
    def forget(root: Path | None = None) -> None:
        """Clear the cache (all roots when root is None)."""
        global _CACHE
        if root is None:
            _CACHE.clear()
        else:
            root = Path(root).resolve()
            fp = _fingerprint(root)
            if fp and fp in _CACHE:
                del _CACHE[fp]

    # -- schemas ------------------------------------------------------------- #

    def find(self, name_or_uid: str, manager: str | None = None) -> list[dict]:
        """Every copy of a schema (own and replacing), matched by name, UId or base UId."""
        key = name_or_uid.lower()
        return [s for s in self.schemas if key in (s["name"].lower(), s["uid"], s["base"]) and (manager is None or s["manager"] == manager)]

    def name_of(self, uid: str | None) -> str | None:
        hits = self.find(uid) if uid else []
        return hits[0]["name"] if hits else None

    def uid_of(self, name_or_uid: str, manager: str) -> str:
        """The base UId of a schema (what references store); a UId is returned as given."""
        if is_uid(name_or_uid):
            return name_or_uid.lower()
        hits = self.find(name_or_uid, manager)
        if not hits:
            raise KeyError(f"{manager} schema {name_or_uid} not found in {self.root}; pass its UId instead "
                           f"(select \"UId\" from \"SysSchema\" where \"Name\" = '{name_or_uid}' and \"ExtendParent\" = false)")
        return hits[0]["base"]

    def cultures_of(self, name: str) -> list[str]:
        """Cultures the resource files of a schema exist in, over all its copies."""
        return sorted({p.name[len("resource."):-len(".xml")] for h in self.find(name)
                       for p in (h["dir"].parent.parent / "Resources").glob(f"{h['name']}.*/resource.*.xml")})

    # -- entities ------------------------------------------------------------ #

    def columns(self, entity: str) -> dict[str, tuple[str, str | None]]:
        """name -> (data value type name, reference schema name), over every copy of the entity."""
        out = dict(BASE_COLUMNS)
        for s in self.find(entity, "EntitySchemaManager"):
            text = read_text(s["dir"] / "metadata.json")[0]
            if text.startswith("{"):
                cols = json.loads(text)["MetaData"]["Schema"].get("D2", [])
            else:
                cols = [json.loads(v) for op, path, v in parse_diff(text) if op in "+=" and path == "MetaData.Schema.D2" and v.startswith("{")]
            for c in cols:
                out[c["A2"]] = (DATA_VALUE_TYPES.get(c.get("S2", ""), c.get("S2")), self.name_of(c.get("S4")))
        return out

    def column_uids(self, entity: str) -> dict[str, str]:
        """name -> column UId, over every copy of the entity (what a signal's changed-column list stores)."""
        out = {}
        for s in self.find(entity, "EntitySchemaManager"):
            text = read_text(s["dir"] / "metadata.json")[0]
            if text.startswith("{"):
                cols = json.loads(text)["MetaData"]["Schema"].get("D2", [])
            else:
                cols = [json.loads(v) for op, path, v in parse_diff(text) if op in "+=" and path == "MetaData.Schema.D2" and v.startswith("{")]
            for c in cols:
                if c.get("UId"):
                    out[c["A2"]] = c["UId"].lower()
        return out

    def is_complete(self, name: str, manager: str) -> bool:
        """True when every copy is an own schema: the workspace then sees all of its members."""
        copies = self.find(name, manager)
        return bool(copies) and all(s["uid"] == s["base"] for s in copies)

    # -- Freedom UI pages ----------------------------------------------------- #

    def page_model(self, page: str) -> tuple[dict, dict, set]:
        """(attributes {name: "DS.Column"}, data sources {DS: entity}, element names) over every copy of the page."""
        attrs, sources, elements = {}, {}, set()
        for s in self.find(page, "ClientUnitSchemaManager"):
            for js in s["dir"].glob("*.js"):
                text = read_text(js)[0]
                for marker, value in re.findall(r"/\*\*(SCHEMA_[A-Z_]+)\*/(.*?)/\*\*\1\*/", text, re.S):
                    try:
                        data = json.loads(value)
                    except ValueError:
                        continue
                    if marker == "SCHEMA_VIEW_CONFIG_DIFF":
                        elements |= {i["name"] for i in data if isinstance(i, dict) and i.get("name")}
                    elif marker in ("SCHEMA_VIEW_MODEL_CONFIG", "SCHEMA_VIEW_MODEL_CONFIG_DIFF"):
                        blocks = [data.get("attributes", {})] if isinstance(data, dict) else [i.get("values", {}) for i in data if i.get("path") == ["attributes"]]
                        for block in blocks:
                            for name, cfg in block.items():
                                attrs[name] = ((cfg or {}).get("modelConfig") or {}).get("path")
                    elif marker in ("SCHEMA_MODEL_CONFIG", "SCHEMA_MODEL_CONFIG_DIFF"):
                        blocks = [data] if isinstance(data, dict) else [i.get("values", {}) for i in data if i.get("operation") in ("merge", "insert") and i.get("path", []) in ([], ["dataSources"])]
                        for block in blocks:
                            ds = block.get("dataSources", block) if isinstance(block, dict) else {}
                            for k, v in ds.items():
                                if isinstance(v, dict) and (v.get("config") or {}).get("entitySchemaName"):
                                    sources[k] = v["config"]["entitySchemaName"]
        return attrs, sources, elements
