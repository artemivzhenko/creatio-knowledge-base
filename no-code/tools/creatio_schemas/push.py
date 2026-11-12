"""Install a package with drift, task ownership, compilation and probe checks."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

from .clio import Clio
from .files import read_text, write_text
from .schema import Descriptor


def _schemas(package: Path, manager: str):
    """Yield schema directories belonging to the requested manager."""
    for descriptor in sorted(package.glob("Schemas/*/descriptor.json")):
        data = json.loads(descriptor.read_text(encoding="utf-8-sig"))["Descriptor"]
        if data.get("ManagerName") == manager:
            yield descriptor.parent


def _needs_publish(package: Path) -> bool:
    """Identify processes containing script or user tasks."""
    for schema in _schemas(package, "ProcessSchemaManager"):
        text = (schema / "metadata.json").read_text(encoding="utf-8-sig")
        if "ProcessSchemaScriptTask" in text or "ProcessSchemaUserTask" in text:
            return True
    return False


def _git(package: Path, args: list[str], allow_not_repo: bool = False) -> str | None:
    """Run a read-only git command in the package's repository."""
    try:
        result = subprocess.run(["git", *args], cwd=package, capture_output=True, text=True, encoding="utf-8", check=False)
    except OSError as exc:
        raise RuntimeError(f"could not run git: {exc}") from exc
    if result.returncode:
        if allow_not_repo and "not a git repository" in result.stderr.lower():
            return None
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout


def _changed_files(package: Path) -> list[str]:
    """Return all changed package paths, including both sides of renames."""
    output = _git(package, ["status", "--porcelain=v1", "-z", "--untracked-files=all", "--", str(package)])
    parts = output.split("\0")
    paths = []
    i = 0
    while i < len(parts) and parts[i]:
        record = parts[i]
        status, name = record[:2], record[3:]
        paths.append(name.replace("\\", "/"))
        i += 1
        if "R" in status or "C" in status:
            if i >= len(parts) or not parts[i]:
                raise RuntimeError("git status returned an incomplete rename")
            paths.append(parts[i].replace("\\", "/"))
            i += 1
    root = Path(_git(package, ["rev-parse", "--show-toplevel"]).strip()).resolve()
    result = []
    for name in paths:
        try:
            result.append((root / name).resolve().relative_to(package).as_posix())
        except ValueError as exc:
            raise RuntimeError(f"git status returned a path outside the package: {name}") from exc
    return result


def _task_conflicts(tasks: Path, current: Path, paths: list[str]) -> list[str]:
    """Find changed files owned by other unfinished tasks."""
    tasks, current = tasks.resolve(), current.resolve()
    if not tasks.is_dir() or not current.is_dir() or current.parent != tasks:
        raise RuntimeError("the current task must be a folder directly under the tasks folder")
    conflicts = []
    for task in sorted(tasks.iterdir()):
        if not task.is_dir() or task.resolve() == current or (task / "success-report.md").exists():
            continue
        lock = task / "schemas.json"
        if not lock.is_file():
            continue
        data = json.loads(lock.read_text(encoding="utf-8-sig"))
        schemas = {str(n).casefold() for n in data["schemas"]}
        files = {str(n).replace("\\", "/").casefold() for n in data.get("files", [])}
        hits = []
        for path in paths:
            parts = path.split("/")
            schema = parts[1].split(".")[0].casefold() if len(parts) > 1 and parts[0] in ("Schemas", "Resources", "SqlScripts", "Data") else ""
            if schema in schemas or path.casefold() in files:
                hits.append(path)
        if hits:
            conflicts.append(f"{task.name}: {', '.join(hits)}")
    return conflicts


def _touch_sql_dates(package: Path, paths: list[str]) -> list[str]:
    """Stamp descriptors of changed SQL scripts without changing other bytes."""
    names = sorted({parts[1] for path in paths if len(parts := path.split("/")) >= 3 and parts[0] == "SqlScripts"})
    updates = []
    for name in names:
        path = package / "SqlScripts" / name / "descriptor.json"
        if not path.is_file():
            raise RuntimeError(f"changed SQL script {name} has no descriptor")
        text, bom = read_text(path)
        descriptor = Descriptor(path, text, root="SqlScript")
        previous = descriptor.data.get("ModifiedOnUtc")
        descriptor.touch()
        updated = descriptor.data.get("ModifiedOnUtc")
        old_match = re.fullmatch(r"/Date\((\d+)\)/", str(previous))
        new_match = re.fullmatch(r"/Date\((\d+)\)/", str(updated))
        if not old_match or not new_match or int(new_match.group(1)) <= int(old_match.group(1)):
            raise RuntimeError(f"could not advance ModifiedOnUtc for SQL script {name}; check its timestamp")
        updates.append((path, descriptor.text, bom))
    for path, text, bom in updates:
        write_text(path, text, bom)
    return names


def _csproj_references(text: str) -> set[str]:
    """Names of the <Reference>/<ProjectReference> items of a project file (the version part is dropped)."""
    return {m.split(",")[0].strip() for m in re.findall(r'<(?:Reference|ProjectReference)\s+Include="([^"]+)"', text)}


def _depends_on(text: str) -> set[str]:
    """`package:<Name>` of every DependsOn entry of a package descriptor."""
    return {"package:" + d["Name"] for d in json.loads(text.lstrip("\ufeff"))["Descriptor"].get("DependsOn") or []}


def dependency_changes(package: Path) -> tuple[list[str], list[str]] | str:
    """(dropped, added) against git HEAD: `package:<Name>` of descriptor.json DependsOn and `Files/<x>.csproj:<Reference>`
    of the project files; a reason string when there is nothing to compare with."""
    if _git(package, ["rev-parse", "--show-toplevel"], allow_not_repo=True) is None:
        return "skipped (no git)"
    try:
        _git(package, ["rev-parse", "--verify", "HEAD"])
        before = _depends_on(_git(package, ["show", "HEAD:./descriptor.json"]))
        listed = [n for n in _git(package, ["ls-tree", "--name-only", "HEAD", "Files/"]).splitlines() if n.endswith(".csproj")]
        for name in listed:
            before |= {f"{name}:{ref}" for ref in _csproj_references(_git(package, ["show", f"HEAD:./{name}"]))}
    except RuntimeError:
        return "skipped (the package is not committed)"
    now = _depends_on((package / "descriptor.json").read_text(encoding="utf-8-sig"))
    for csproj in package.glob("Files/*.csproj"):
        now |= {f"Files/{csproj.name}:{ref}" for ref in _csproj_references(csproj.read_text(encoding="utf-8-sig"))}
    return sorted(before - now), sorted(now - before)


ISCHANGED_TABLES = ("SysSchema", "SysPackageSchemaData", "SysPackageSqlScript")
BINDING_CHUNK = 50  # rows per `or` of keys


def _same(site, package) -> bool:
    """A site value and a binding value mean the same: empty = empty, numbers by value, the rest case-blind as text."""
    a, b = (("" if v is None or str(v).strip().lower() == "null" else str(v).strip()) for v in (site, package))
    try:
        return float(a) == float(b)
    except ValueError:
        return a.lower() == b.lower() or {a.lower(), b.lower()} <= {"true", "1"} or {a.lower(), b.lower()} <= {"false", "0", ""}


def binding_overwrites(package: Path, rows_of) -> tuple[list[str], list[str]]:
    """([`<object> <key>: <Column> site <v> -> package <v>`], [notes]) for the rows of every `Data/<Name>` binding whose
    key exists on the site with another value in a column the binding writes. `rows_of(sql)` runs a select."""
    from .data.binding import LOOKUP_TYPES, DataBinding
    from .files import DVT_OF
    from .records import ident
    lines, notes = [], []
    for b in DataBinding.all(package):
        keys = b.key_columns or (["Id"] if "Id" in b.columns else [])
        if not keys:
            notes.append(f"{b.name}: no key column, not compared")
            continue
        db = {n: n + "Id" if c["type"] in LOOKUP_TYPES else n for n, c in b.columns.items()}
        compared = [n for n in b.columns if n not in keys and n not in b.localized and b.columns[n]["type"] != DVT_OF["Binary"]
                    and db[n] not in ("CreatedOn", "ModifiedOn", "CreatedById", "ModifiedById")]
        rows = [r for r in b.rows() if all(r.get(k) not in (None, "") for k in keys)]
        if not rows or not compared:
            continue
        table, site = ident(b.schema_name), {}
        try:
            for i in range(0, len(rows), BINDING_CHUNK):
                where = " or ".join("(" + " and ".join(f"\"{ident(db[k])}\" = '{str(r[k]).replace(chr(39), chr(39) * 2)}'" for k in keys) + ")"
                                    for r in rows[i:i + BINDING_CHUNK])
                cols = ", ".join(f'"{ident(db[n])}"' for n in dict.fromkeys(keys + compared))
                for s in rows_of(f'select {cols} from "{table}" where {where}'):
                    site["|".join(str(s.get(db[k], "")).lower() for k in keys)] = s
        except RuntimeError as exc:  # an object the site does not have yet: nothing there to overwrite
            notes.append(f"{b.name}: not compared ({str(exc)[:120]})")
            continue
        for r in rows:
            s = site.get(b.key_of(r))
            if s is None:
                continue
            for n in compared:
                if n in r and not _same(s.get(db[n]), r[n]):
                    lines.append(f"{b.schema_name} {b.key_of(r)}: {n} site {s.get(db[n])!r} -> package {r[n]!r}"
                                 + (" (force update)" if b.columns[n]["force_update"] else ""))
    return lines, notes


def push(package: Path, env: str, clio: Clio, probe: bool = False, dry_run: bool = False, log=print, *,
         project: Path | None = None, tasks: Path | None = None, task: Path | None = None,
         force: bool = False, baseline: Path | None = None, skip_drift: bool = False,
         skip_foreign_files: bool = False, skip_sql_dates: bool = False,
         skip_compile_package: bool = False) -> int:
    """Push a package, stopping on the first failed step."""
    package = Path(package).resolve()
    try:
        descriptor = json.loads((package / "descriptor.json").read_text(encoding="utf-8-sig"))["Descriptor"]
        pkg_name, assembly = descriptor["Name"], descriptor.get("Type") == 1
    except (OSError, ValueError, KeyError) as exc:
        log(f"package: FAILED {str(exc)[:200]}")
        log("push FAILED at package")
        return 1
    start = time.monotonic()
    statements = [f'update "{table}" set "IsChanged"=false' for table in ISCHANGED_TABLES]
    commit, changed, compilation_log = None, None, ""

    def command(args, cwd=None):
        if dry_run:
            log("  " + subprocess.list2cmdline(["clio", *args]))
            return ""
        return clio.run(args, cwd=cwd)

    def git_context():
        nonlocal commit, changed
        if changed is not None:
            return
        root = _git(package, ["rev-parse", "--show-toplevel"], allow_not_repo=True)
        if root is None:
            changed = []
            return
        commit = _git(package, ["log", "-1", "--format=%cI", "--", str(package)]).strip()
        if not commit:
            raise RuntimeError("package has no git commit; drift cannot be checked")
        try:
            datetime.fromisoformat(commit.replace("Z", "+00:00"))
        except ValueError as exc:
            raise RuntimeError(f"invalid git commit timestamp: {commit}") from exc
        changed = _changed_files(package)

    def drift():
        if skip_drift:
            return "skipped"
        if dry_run:
            log(f"  git log -1 --format=%cI -- {package}")
            log(f'  clio execute-sql-script -f <drift.sql> -v json -d <result.json> -e {env}')
            return "dry run"
        git_context()
        if commit is None:
            return "skipped (no git)"
        try:
            uid = str(uuid.UUID(descriptor["UId"]))
        except (KeyError, ValueError, TypeError) as exc:
            raise RuntimeError("package descriptor has no valid UId") from exc
        # SysSchema has no PackageUId on 8.x: the package is SysPackageId -> SysPackage.Id, whose UId the descriptor holds.
        query = ('select s."Name", s."ModifiedOn" from "SysSchema" s join "SysPackage" p on p."Id" = s."SysPackageId" '
                 f'where p."UId" = \'{uid}\' and s."ModifiedOn" > \'{commit}\'')
        rows = clio.execute_sql_rows(query)
        if rows and not force:
            raise RuntimeError(", ".join(str(row["Name"]) for row in rows))
        return f"forced ({len(rows)} changed)" if rows else "ok"

    def bindings():
        if not (package / "Data").is_dir():
            return "not needed"
        if dry_run:
            log(f'  select <key and bound columns> from "<object>" where <binding keys> -e {env}  (each Data/<Name>)')
            return "dry run"
        lines, notes = binding_overwrites(package, clio.execute_sql_rows)
        for line in notes + lines:
            log(f"  {line}")
        if lines and not force:
            raise RuntimeError(f"{len(lines)} value(s) on the site would be overwritten (listed above); --force pushes anyway")
        return f"forced ({len(lines)} overwritten)" if lines else "ok"

    def dependencies():
        if dry_run:
            return "dry run"
        changes = dependency_changes(package)
        if isinstance(changes, str):
            return changes
        dropped = changes[0]
        if dropped and not force:
            raise RuntimeError("dropped " + ", ".join(sorted(d.split(":", 1)[1] for d in dropped)))
        return f"forced (dropped {len(dropped)})" if dropped else "ok"

    def foreign_files():
        if skip_foreign_files:
            return "skipped"
        folder = Path(tasks) if tasks else None
        if folder is None and project:
            project_path = Path(project).resolve()
            config = json.loads(project_path.read_text(encoding="utf-8-sig"))
            value = config["paths"]["tasks"]
            folder = Path(value)
            if not folder.is_absolute():
                folder = project_path.parent / folder
        if folder is None:
            return "skipped (no tasks folder)"
        if task is None:
            raise RuntimeError("--task is required when a tasks folder is configured")
        if dry_run:
            log(f"  git status --porcelain -- {package}")
            return "dry run"
        git_context()
        if commit is None:
            raise RuntimeError("cannot check uncommitted task files without git")
        conflicts = _task_conflicts(folder, Path(task), changed)
        if conflicts:
            raise RuntimeError("; ".join(conflicts))
        return "ok"

    def sql_dates():
        if skip_sql_dates:
            return "skipped"
        if dry_run:
            log(f"  git status --porcelain -- {package}")
            log("  update ModifiedOnUtc for changed SQL scripts")
            return "dry run"
        git_context()
        if commit is None:
            return "skipped (no git)"
        names = _touch_sql_dates(package, changed)
        return ", ".join(names) if names else "not needed"

    def clear():
        for statement in statements:
            if dry_run:
                command(["execute-sql-script", statement, "-e", env])
            else:
                clio.execute_sql(statement)
        return "dry run" if dry_run else "ok (" + ", ".join(ISCHANGED_TABLES) + ")"

    def install():
        command(["push-pkg", pkg_name, "-e", env], cwd=package.parent)
        return "dry run" if dry_run else "ok"

    def compilation():
        nonlocal compilation_log
        compilation_log = command(["last-compilation-log", "-e", env])
        if dry_run:
            return "dry run"
        summaries = [line for line in compilation_log.splitlines() if "Finished building project:" in line]
        if not summaries:
            raise RuntimeError("compilation summary not found")
        summary = summaries[-1]
        log(f"  {summary}")
        match = re.search(r"\bErrors:\s*(\d+)\b", summary)
        if not match:
            raise RuntimeError(summary)
        if int(match.group(1)) and baseline is None and not (assembly and not skip_compile_package):
            raise RuntimeError(summary)
        return "ok"

    def compile_package():
        if skip_compile_package:
            return "skipped"
        if not assembly:
            return "not needed"
        output = command(["compile-package", pkg_name, "-e", env, "--wait"])
        if output.strip():
            log(f"  {output.strip().splitlines()[-1]}")
        return "dry run" if dry_run else "ok"

    def check_baseline():
        if baseline is None:
            return "skipped"
        if dry_run:
            log(f"  compare compilation errors with {baseline}")
            return "dry run"
        errors = [line.strip() for line in compilation_log.splitlines()
                  if re.search(r"\berror\b", line, re.IGNORECASE) and not re.search(r"\bErrors:\s*\d+", line)]
        summary = next(line for line in reversed(compilation_log.splitlines()) if "Finished building project:" in line)
        count = int(re.search(r"\bErrors:\s*(\d+)\b", summary).group(1))
        if count and not errors:
            raise RuntimeError("compilation reported errors but no error lines were found")
        path = Path(baseline)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8", newline="\n") as out:
                out.write("\n".join(errors) + ("\n" if errors else ""))
            return f"created ({len(errors)} errors)"
        previous = set(path.read_text(encoding="utf-8-sig").splitlines())
        new = [line for line in errors if line not in previous]
        if new:
            raise RuntimeError("; ".join(new))
        return "ok"

    def publish():
        if not _needs_publish(package):
            return "not needed"
        if not dry_run:
            log("publish: started")
        output = command(["compile-configuration", "-e", env])
        if output.strip():
            log(f"  {output.strip().splitlines()[-1]}")
        return "dry run" if dry_run else "ok"

    steps = (("drift", drift), ("bindings", bindings), ("dependencies", dependencies), ("foreign files", foreign_files), ("sql dates", sql_dates),
                       ("clear IsChanged", clear), ("push-pkg", install), ("compilation log", compilation),
                       ("compile-package", compile_package), ("baseline", check_baseline), ("publish", publish))
    ran = 0
    for name, step in steps:
        try:
            result = step()
        except (RuntimeError, OSError, ValueError, KeyError) as exc:
            log(f"{name}: FAILED {str(exc)[:200]}")
            log(f"push FAILED at {name}")
            return 1
        log(f"{name}: {result}")
        ran += not str(result).startswith("skipped")

    if probe:
        try:
            _run_probes(package, env, dry_run, log)
        except RuntimeError as exc:
            log(f"probes: FAILED {str(exc)[:200]}")
            log("push FAILED at probes")
            return 1
        log("probes: ok")

    if dry_run:
        log(f"dry run of {pkg_name} -> {env}: {ran} of {len(steps)} steps would run, nothing sent")
        return 0
    log(f"pushed {pkg_name} to {env} in {int(time.monotonic() - start)} s")
    return 0


def _run_probes(package: Path, env: str, dry_run: bool, log) -> None:
    """Run object and SQL script probes for package items."""
    tools = Path(__file__).resolve().parent.parent
    items = [(tools / "objects" / "objects.py", p.name) for p in _schemas(package, "EntitySchemaManager")]
    items += [(tools / "sqlscripts" / "sqlscripts.py", p.parent.name)
              for p in sorted(package.glob("SqlScripts/*/descriptor.json"))]
    for script, name in items:
        args = [sys.executable, str(script), "probe", str(package), name, "--env", env]
        if dry_run:
            log("  " + subprocess.list2cmdline(args))
            continue
        try:
            result = subprocess.run(args, capture_output=True, text=True, check=False)
        except OSError as exc:
            raise RuntimeError(f"probe {name}: {exc}") from exc
        output = result.stdout + result.stderr
        for line in output.splitlines():
            log(f"  probe {name}: {line}")
        if result.returncode:
            raise RuntimeError(f"probe {name} exited {result.returncode}: {output[-500:]}")
