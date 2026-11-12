"""Two states of a package in schema terms: the lines the describe layer prints, added, removed, changed.

The working copy against git HEAD (default), another revision, or another folder holding the package (a
pulled copy of the environment). Per item: the summary and every list topic of its kind are rendered for
both states (`limit=0`) and compared line by line, keyed by the first word - a column, an element, a
parameter, a rule - so an added column is one `+` line, a changed caption one `~` line, never a JSON hunk.
Items present in one state only are `+ ... (new)` / `- ... (removed)`. Nothing is written but a temporary
extraction of the git revision.
"""

from __future__ import annotations

import io
import json
import subprocess
import tarfile
import tempfile
from pathlib import Path

from ..csharp import csharp_files
from .core import QueryError, open_item
from .queries import answer, topics_of
from .registry import kind_name

# topics that are not a property of the schema (absolute paths, the workspace index, metadata key names), need a name,
# or print counts only (`resources` without a culture)
# shortcut: a changed caption shows through the line of its column / element, a localizable string nobody lists does not;
# compare `resources culture=<x>` per culture when that matters
SKIP_TOPICS = {"files", "uses", "used-by", "keys", "missing", "resource", "resources"}


def items_of(package: Path) -> list[str]:
    """Every item name of a package as the index names them: schema and SQL script folders, `Data/<Name>`, C# files."""
    names = []
    for folder in ("Schemas", "SqlScripts"):
        if (package / folder).is_dir():
            names += [d.name for d in (package / folder).iterdir() if (d / "descriptor.json").is_file()]
    if (package / "Data").is_dir():
        names += [f"Data/{d.name}" for d in (package / "Data").iterdir() if (d / "descriptor.json").is_file()]
    names += [cs.relative_to(package).as_posix() for cs in csharp_files(package)]
    return sorted(set(names), key=str.lower)


def sections_of(package: Path, name: str) -> tuple[str, dict[str, list[str]]]:
    """(kind, {section: lines}) of one item: the summary, then every topic it answers without a name."""
    item = open_item(package, name.removeprefix("Data/"))
    sections = {"summary": item.describe().splitlines()}
    for topic in sorted(topics_of(item)):
        if topic in SKIP_TOPICS:
            continue
        try:
            sections[topic] = answer(item, topic, None, {"limit": "0"}).splitlines()
        except QueryError:  # the topic needs a name (`column <name>`)
            continue
    return kind_name(item), sections


def _key(line: str) -> str:
    return line.split()[0] if line.split() else ""


def diff_lines(old: list[str], new: list[str]) -> list[str]:
    """`+`/`-`/`~` lines between two line lists. A line is keyed by its first word; a key on both sides with a
    different rest is one `~ key  old -> new` line. Keys that repeat on a side fall back to whole-line `+`/`-`.
    Header lines (ending with `:`) and blank lines are not compared."""
    def table(lines):
        rows, seen = {}, {}
        for raw in lines:
            s = " ".join(raw.split())
            if not s or s.endswith(":"):
                continue
            k = _key(s)
            seen[k] = seen.get(k, 0) + 1
            rows[k] = s
        return rows, seen

    o_rows, o_seen = table(old)
    n_rows, n_seen = table(new)
    o_all, n_all = {" ".join(l.split()) for l in old if l.strip()}, {" ".join(l.split()) for l in new if l.strip()}
    out = []
    for k in sorted(set(o_rows) | set(n_rows), key=str.lower):
        unique = o_seen.get(k, 0) <= 1 and n_seen.get(k, 0) <= 1
        if unique and k in o_rows and k in n_rows:
            if o_rows[k] != n_rows[k]:
                out.append(f"~ {k}  {o_rows[k][len(k):].strip()} -> {n_rows[k][len(k):].strip()}")
        elif unique:
            out.append(("+ " if k in n_rows else "- ") + (n_rows.get(k) or o_rows[k]))
        else:  # a key that repeats (flows, rows): whole lines
            out += [f"- {l}" for l in old if l.strip() and _key(l) == k and " ".join(l.split()) not in n_all]
            out += [f"+ {l}" for l in new if l.strip() and _key(l) == k and " ".join(l.split()) not in o_all]
    return out


def materialise(package: Path, against: str | None) -> tuple[Path, tempfile.TemporaryDirectory | None]:
    """The package folder of the other state: a folder (a package or a workspace holding one of the same name), or a
    git revision (default HEAD) extracted into a temporary folder the caller cleans up."""
    package = package.resolve()
    if against and Path(against).is_dir():
        other = Path(against).resolve()
        for candidate in (other, other / package.name, other / "packages" / package.name):
            if (candidate / "descriptor.json").is_file():
                return candidate, None
        raise QueryError(f"{against} holds no package {package.name}")
    rev = against or "HEAD"
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=package, capture_output=True, text=True, check=True).stdout.strip()
        rel = package.relative_to(Path(top).resolve()).as_posix()
        archive = subprocess.run(["git", "archive", "--format=tar", rev, "--", rel], cwd=top, capture_output=True, check=True).stdout
    except FileNotFoundError as e:
        raise QueryError("git is not on the PATH; name a folder with --against") from e
    except subprocess.CalledProcessError as e:
        raise QueryError(f"git cannot give {rev} of {package.name}: {(e.stderr or b'').decode(errors='replace').strip() or 'not a repository'}") from e
    tmp = tempfile.TemporaryDirectory(prefix="creatio-diff-")
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(tmp.name)  # noqa: S202 - our own repository's files
    return Path(tmp.name) / rel, tmp


def schema_diff(package: Path | str, names: list[str] | None = None, against: str | None = None) -> str:
    """The difference between the package on disk and `against` (git HEAD, a revision, or a folder), per item.
    `names` limits it to those items; otherwise the whole package."""
    package = Path(package)
    if not (package / "descriptor.json").is_file():
        raise FileNotFoundError(f"{package} is not a package folder (no descriptor.json)")
    old_pkg, tmp = materialise(package, against)
    try:
        return _diff_packages(old_pkg, package, names, against or "HEAD")
    finally:
        if tmp:
            tmp.cleanup()


def _uid(package: Path, name: str) -> str | None:
    """The UId of an item's descriptor (a schema, a SQL script, a data binding); None for a plain C# file."""
    folder = "Data" if name.startswith("Data/") else "SqlScripts" if (package / "SqlScripts" / name).is_dir() else "Schemas"
    path = package / folder / name.removeprefix("Data/") / "descriptor.json"
    if not path.is_file():
        return None
    try:
        return str(json.loads(path.read_text(encoding="utf-8-sig"))["Descriptor"]["UId"]).lower()
    except (ValueError, KeyError, TypeError):
        return None


def _diff_packages(old_pkg: Path, new_pkg: Path, names: list[str] | None, label: str) -> str:
    old_names, new_names = items_of(old_pkg), items_of(new_pkg)
    wanted = {n.lower() for n in names} if names else None
    lower = {n.lower(): n for n in old_names + new_names}
    if wanted:
        missing = [n for n in names if n.lower() not in lower]
        if missing:
            raise FileNotFoundError(f"{new_pkg.name} has no item named {', '.join(missing)} in either state")
    gone = {u: n for n in old_names if n not in new_names for u in [_uid(old_pkg, n)] if u}
    renamed = {n: gone[u] for n in new_names if n not in old_names for u in [_uid(new_pkg, n)] if u in gone}  # new -> old, same UId
    out, changed, added, removed, lines = [], 0, 0, 0, [0, 0, 0]
    for name in sorted(set(old_names) | set(new_names), key=str.lower):
        if (wanted and name.lower() not in wanted and renamed.get(name, "").lower() not in wanted) or name in renamed.values():
            continue
        in_old, in_new, old_name = name in old_names, name in new_names, renamed.get(name, name)
        try:
            kind, new_sec = sections_of(new_pkg, name) if in_new else sections_of(old_pkg, name)
            old_sec = sections_of(old_pkg, old_name)[1] if (in_old or name in renamed) and in_new else {}
        except (OSError, ValueError, KeyError, AttributeError) as e:
            out.append(f"? {name}  cannot compare: {type(e).__name__}: {e}")
            continue
        if not (in_old and in_new) and name not in renamed:
            out.append(f"{'+' if in_new else '-'} {name}  {kind} ({'new' if in_new else 'removed'})")
            added += in_new
            removed += in_old
            continue
        body, said = [], set()
        for section in [s for s in new_sec if s != "summary"] + ["summary"]:  # the summary repeats the lists: it adds only what they did not say
            d = [l for l in diff_lines(old_sec.get(section, []), new_sec[section]) if l not in said]
            if d:
                said.update(d)
                body.append(f"  {section}")
                body += [f"    {l}" for l in d]
                for l in d:
                    lines["+-~".index(l[0])] += 1
        if name in renamed:  # the same UId under a new name: compared as one item, the rename said once
            changed += 1
            out += [f"~ {old_name} -> {name}  {kind} (renamed)"] + body
        elif body:
            changed += 1
            out += [f"{name}  {kind}"] + body
    if not out:
        return f"{new_pkg.name}: no differences against {label}"
    tail = f"{new_pkg.name} against {label}: {changed} changed, {added} new, {removed} removed; lines +{lines[0]} -{lines[1]} ~{lines[2]}"
    return "\n".join(out + [tail])
