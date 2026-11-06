"""A SQL script of a package: SqlScripts/<Name>/{descriptor.json, <Name>.sql}.

    descriptor  {"SqlScript": {UId, Name, DBEngineType, InstallType, ModifiedOnUtc, BackwardCompatibilityConfirmed, DependsOn}}
    DependsOn   [{"UId", "Name"}] of other scripts (any package) that must run first
    <Name>.sql  the body, UTF-8 without BOM

The platform runs a script while installing the package, at the point InstallType says, on the
database engine DBEngineType names (a script for another engine is skipped). Values from the
8.x configuration designer: DBEngineType MSSql 0, Oracle 1, PostgreSql 2; InstallType
BeforePackage 0, AfterPackage 1 (default), AfterSchemaData 2, UninstallApp 3.
"""

from __future__ import annotations

import re
from pathlib import Path

from .files import is_uid, new_uid, newline_of, read_text, write_text
from .schema import WARNING, Descriptor, PackageItem

ENGINES = {"mssql": 0, "oracle": 1, "postgresql": 2}
INSTALL_TYPES = {"before-package": 0, "after-package": 1, "after-data": 2, "uninstall-app": 3}
ENGINE_NAMES = {v: k for k, v in ENGINES.items()}
INSTALL_NAMES = {v: k for k, v in INSTALL_TYPES.items()}
NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
# engine words a name may end with (the platform's own scripts: ...MSSql / ...Oracle / ...PostgreSql)
_SUFFIX = {"mssql": 0, "oracle": 1, "postgresql": 2, "pgsql": 2, "postgres": 2, "pg": 2}


class SqlScript(PackageItem):
    def __init__(self, package: Path, name: str):
        super().__init__(package, name)
        self.dir = self.package / "SqlScripts" / name
        if not (self.dir / "descriptor.json").is_file():
            raise FileNotFoundError(f"no SQL script {name} in {self.package}")
        self.descriptor = Descriptor(self.dir / "descriptor.json", root="SqlScript")
        self.body_path = self.dir / f"{name}.sql"
        self.body, self.body_bom = read_text(self.body_path) if self.body_path.is_file() else ("", False)

    # -- reading ------------------------------------------------------------- #

    @property
    def uid(self) -> str:
        return self.descriptor.data["UId"]

    @property
    def engine(self) -> str:
        return ENGINE_NAMES.get(self.descriptor.data.get("DBEngineType"), str(self.descriptor.data.get("DBEngineType")))

    @property
    def install_type(self) -> str:
        return INSTALL_NAMES.get(self.descriptor.data.get("InstallType"), str(self.descriptor.data.get("InstallType")))

    @property
    def depends_on(self) -> list[dict]:
        return self.descriptor.data.get("DependsOn") or []

    def files(self):
        return {self.descriptor.path: (self.descriptor.text, True), self.body_path: (self.body, self.body_bom)}

    # -- changing ------------------------------------------------------------ #

    def set_body(self, text: str) -> None:
        """The SQL text; its newlines follow the file's own style."""
        nl = newline_of(self.body) if self.body else "\r\n"
        self.body = text.replace("\r\n", "\n").replace("\n", nl)

    def set_engine(self, engine: str) -> None:
        if engine not in ENGINES:
            raise ValueError(f"unknown engine {engine}; one of {sorted(ENGINES)}")
        self.descriptor.set("DBEngineType", ENGINES[engine])

    def set_install_type(self, install: str) -> None:
        if install not in INSTALL_TYPES:
            raise ValueError(f"unknown install type {install}; one of {sorted(INSTALL_TYPES)}")
        self.descriptor.set("InstallType", INSTALL_TYPES[install])

    def set_backward_compatible(self, on: bool) -> None:
        self.descriptor.set("BackwardCompatibilityConfirmed", bool(on))

    def resolve(self, script: str, uid: str | None = None) -> dict:
        """{UId, Name} of a script by name: from the workspace, or the UId given."""
        if uid:
            return {"UId": uid.lower(), "Name": script}
        if is_uid(script):
            raise ValueError("give the script name; with --uid for a script outside the workspace")
        for desc in sorted(self.package.parent.glob(f"*/SqlScripts/{script}/descriptor.json")):
            return {"UId": Descriptor(desc, root="SqlScript").data["UId"], "Name": script}
        raise KeyError(f"SQL script {script} is not in the workspace; pass its UId "
                       f"(select \"UId\" from \"SysPackageSqlScript\" where \"Name\" = '{script}')")

    def add_dependency(self, script: str, uid: str | None = None) -> dict:
        dep = self.resolve(script, uid)
        deps = [d for d in self.depends_on if d["Name"] != dep["Name"]] + [dep]
        self.descriptor.set("DependsOn", deps)
        return dep

    def remove_dependency(self, script: str) -> None:
        if not any(d["Name"] == script for d in self.depends_on):
            raise KeyError(f"{self.name} does not depend on {script}")
        self.descriptor.set("DependsOn", [d for d in self.depends_on if d["Name"] != script])

    # -- checks ---------------------------------------------------------------- #

    def validate(self) -> list[str]:
        problems = []
        d = self.descriptor.data
        if d.get("DBEngineType") not in ENGINE_NAMES:
            problems.append(f"unknown DBEngineType {d.get('DBEngineType')}")
        if d.get("InstallType") not in INSTALL_NAMES:
            problems.append(f"unknown InstallType {d.get('InstallType')}")
        if not self.body.strip():
            problems.append("the script is empty")
        word = re.search(r"(mssql|oracle|postgresql|pgsql|postgres|pg)$", self.name, re.I)
        if word and _SUFFIX[word.group(1).lower()] != d.get("DBEngineType"):
            problems.append(f"{WARNING}the name ends with {word.group(1)!r} but DBEngineType is {self.engine}")
        if any(d2["Name"] == self.name for d2 in self.depends_on):
            problems.append("the script depends on itself")
        for dep in self.depends_on:
            if not is_uid(dep.get("UId", "")):
                problems.append(f"dependency {dep.get('Name')} has no valid UId")
        if self.engine == "postgresql" and re.search(r"\bGO\s*$", self.body, re.M):
            problems.append(f"{WARNING}'GO' is an MSSQL batch separator; PostgreSQL rejects it")
        if self.engine == "mssql" and re.search(r"\$\$|\bplpgsql\b", self.body, re.I):
            problems.append(f"{WARNING}the body looks like PostgreSQL ($$ / plpgsql) but DBEngineType is mssql")
        return problems

    def describe(self) -> str:
        d = self.descriptor.data
        lines = [f"{self.name}: {self.engine}, {self.install_type}, backward compatible={d.get('BackwardCompatibilityConfirmed')}, "
                 f"{len(self.body.splitlines())} line(s), uid={self.uid}"]
        if self.depends_on:
            lines.append("  runs after: " + ", ".join(dep["Name"] for dep in self.depends_on))
        problems = self.validate()
        if problems:
            lines.append("  problems:")
            lines += [f"    - {p}" for p in problems]
        return "\n".join(lines)

    # -- new ------------------------------------------------------------------- #

    @classmethod
    def create(cls, package: Path, name: str, body: str, engine: str = "postgresql", install: str = "after-package",
               backward_compatible: bool = False) -> "SqlScript":
        """A new script as the configuration designer writes it."""
        package = Path(package)
        if not NAME_RE.fullmatch(name):
            raise ValueError(f"{name!r} is not a valid script name")
        if engine not in ENGINES or install not in INSTALL_TYPES:
            raise ValueError(f"engine one of {sorted(ENGINES)}, install one of {sorted(INSTALL_TYPES)}")
        sdir = package / "SqlScripts" / name
        if sdir.exists():
            raise FileExistsError(sdir)
        desc = Descriptor.new(sdir / "descriptor.json", {"UId": new_uid(), "Name": name, "DBEngineType": ENGINES[engine],
                                                          "InstallType": INSTALL_TYPES[install], "ModifiedOnUtc": "",
                                                          "BackwardCompatibilityConfirmed": bool(backward_compatible), "DependsOn": []},
                              root="SqlScript")
        write_text(desc.path, desc.text, True)
        write_text(sdir / f"{name}.sql", "", False)
        script = cls(package, name)
        script.set_body(body)
        script.save()
        return script

    @classmethod
    def all(cls, package: Path) -> list["SqlScript"]:
        return [cls(package, d.name) for d in sorted((Path(package) / "SqlScripts").glob("*")) if (d / "descriptor.json").is_file()]
