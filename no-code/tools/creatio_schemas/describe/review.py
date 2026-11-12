"""A pulled package reviewed: the working copy against git HEAD sorted into what matters and what does not.

    review_download(package)                         the classes below, as text
    review_download(package, keep=["UsrOrder"])      + the files that would be restored from HEAD (every change outside
                                                       the kept items); `apply=True` runs `git checkout HEAD -- <path>`

Classes: files that differ from HEAD only in line endings or a BOM (read over the bytes - what `git diff -w
--ignore-cr-at-eol` would call empty); the items changed in content (`schema_diff`'s lines, renames by UId included);
dependencies dropped or added (descriptor.json `DependsOn`, the csproj references); resource folders with no schema;
files git does not track. Git is only read, except `apply`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

BOM = b"\xef\xbb\xbf"


def _git(cwd: Path, args: list[str], binary: bool = False):
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, check=False)
    except OSError as e:
        raise RuntimeError(f"could not run git: {e}") from e
    if r.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.decode(errors='replace').strip() or 'failed'}")
    return r.stdout if binary else r.stdout.decode("utf-8", errors="replace")


def _status(package: Path) -> list[tuple[str, str]]:
    """[(two-letter status, path relative to the package)] of every change under the package, renames as their new path."""
    parts = _git(package, ["status", "--porcelain=v1", "-z", "--untracked-files=all", "--", "."]).split("\0")
    top = Path(_git(package, ["rev-parse", "--show-toplevel"]).strip()).resolve()
    prefix = package.resolve().relative_to(top).as_posix()
    out, i = [], 0
    while i < len(parts) and parts[i]:
        status, path = parts[i][:2], parts[i][3:]
        i += 2 if ("R" in status or "C" in status) else 1  # a rename carries its old path as the next record
        out.append((status, path[len(prefix) + 1:] if prefix and path.startswith(prefix + "/") else path))
    return out


def _normal(raw: bytes) -> bytes:
    raw = raw[len(BOM):] if raw.startswith(BOM) else raw
    return raw.replace(b"\r\n", b"\n")


def owner_of(rel: str) -> str | None:
    """The item a package file belongs to: Schemas/<S>/.., Resources/<S>.<kind>/.., SqlScripts/<S>/.., Data/<S>/.. -> S."""
    parts = rel.split("/")
    if len(parts) > 2 and parts[0] in ("Schemas", "SqlScripts", "Data"):
        return parts[1]
    if len(parts) > 2 and parts[0] == "Resources":
        return parts[1].split(".", 1)[0]
    return None


def review(package: Path | str, keep: list[str] | None = None, apply: bool = False) -> dict:
    """{package, eol_only, content, dependencies {dropped, added} | reason, orphans, untracked, restore, applied}."""
    from ..push import dependency_changes
    from .diff import schema_diff
    package = Path(package).resolve()
    if not (package / "descriptor.json").is_file():
        raise FileNotFoundError(f"{package} is not a package folder (no descriptor.json)")
    changes = _status(package)
    eol_only, untracked, tracked = [], [], []
    for status, rel in changes:
        if status == "??":
            untracked.append(rel)
            continue
        tracked.append((status, rel))
        if "M" in status and (package / rel).is_file():
            try:
                head = _git(package, ["show", f"HEAD:./{rel}"], binary=True)
            except RuntimeError:
                continue
            if _normal(head) == _normal((package / rel).read_bytes()):
                eol_only.append(rel)
    deps = dependency_changes(package)
    schemas = {p.name for p in (package / "Schemas").iterdir() if p.is_dir()} if (package / "Schemas").is_dir() else set()
    orphans = sorted(p.name for p in (package / "Resources").iterdir()
                     if p.is_dir() and p.name.split(".", 1)[0] not in schemas) if (package / "Resources").is_dir() else []
    answer = {"package": package.name, "changed": len(changes), "eol_only": eol_only, "untracked": untracked, "orphans": orphans,
              "dependencies": {"dropped": [d.split(":", 1)[1] for d in deps[0]], "added": [d.split(":", 1)[1] for d in deps[1]]}
              if not isinstance(deps, str) else deps,
              "content": schema_diff(package), "restore": [], "applied": False}
    if keep is not None:
        kept = {k.lower() for k in keep}
        answer["restore"] = [rel for status, rel in tracked if (owner_of(rel) or "").lower() not in kept]
        if apply:
            for rel in answer["restore"]:
                _git(package, ["checkout", "HEAD", "--", rel])
            answer["applied"] = True
    return answer


MAX_STAGED = 5 * 1024 * 1024
ARCHIVES = (".rar", ".zip", ".7z", ".gz", ".bak")
BINARIES = (".dll", ".exe", ".pdb")
# what a clio workspace keeps beside packages/ (the loop's files included); anything else at the root is refused
KNOWN_ROOTS = (".gitignore", ".gitattributes", ".editorconfig", "README.md", "project.json", ".clio", ".vscode", "tasks", "docs")


def _assembly_package(workspace: Path, name: str) -> bool:
    import json
    try:
        return json.loads((workspace / "packages" / name / "descriptor.json").read_text(encoding="utf-8-sig"))["Descriptor"].get("Type") == 1
    except (OSError, ValueError, KeyError):
        return False


def precommit(workspace: Path | str) -> list[str]:
    """`<path>: <reason>` for each staged file (added, copied, modified, renamed) that must not be committed: over 5 MB,
    an archive, a binary outside `packages/<P>/Files/Bin` of an assembly package, a file outside `packages/` and the
    known roots. Paths are relative to the workspace; files outside it are not looked at."""
    workspace = Path(workspace).resolve()
    if not workspace.is_dir():
        raise FileNotFoundError(f"{workspace} is not a folder")
    staged = [p for p in _git(workspace, ["diff", "--cached", "--name-only", "-z", "--relative", "--diff-filter=ACMR"]).split("\0") if p]
    out = []
    for rel in staged:
        parts, low = rel.split("/"), rel.lower()
        size = int(_git(workspace, ["cat-file", "-s", f":./{rel}"]).strip() or 0)
        if size > MAX_STAGED:
            out.append(f"{rel}: {size / 1024 / 1024:.1f} MB (over 5 MB)")
        if low.endswith(ARCHIVES):
            out.append(f"{rel}: an archive")
        elif low.endswith(BINARIES) and not (len(parts) > 4 and parts[0] == "packages" and parts[2:4] == ["Files", "Bin"]
                                            and _assembly_package(workspace, parts[1])):
            out.append(f"{rel}: a binary outside Files/Bin of an assembly package")
        if parts[0] != "packages" and parts[0] not in KNOWN_ROOTS:
            out.append(f"{rel}: outside packages/ (known roots: {', '.join(KNOWN_ROOTS)})")
    return out


def render(answer: dict, limit: int = 0) -> str:
    """`limit` cuts the content lines (0 = all)."""
    from .core import cut
    lines = [f"{answer['package']}: {answer['changed']} changed file(s) against HEAD"]
    if answer["eol_only"]:
        lines.append(f"line endings or BOM only ({len(answer['eol_only'])}) - nothing changed:")
        lines += [f"  {p}" for p in answer["eol_only"]]
    deps = answer["dependencies"]
    if isinstance(deps, str):
        lines.append(f"dependencies: {deps}")
    elif deps["dropped"] or deps["added"]:
        lines.append("dependencies: " + "; ".join(x for x in (("dropped " + ", ".join(deps["dropped"])) if deps["dropped"] else "",
                                                              ("added " + ", ".join(deps["added"])) if deps["added"] else "") if x))
    if answer["orphans"]:
        lines.append("resource folders with no schema: " + ", ".join(f"Resources/{o}" for o in answer["orphans"]))
    if answer["untracked"]:
        lines.append(f"not tracked by git ({len(answer['untracked'])}):")
        lines += [f"  {p}" for p in answer["untracked"]]
    lines.append("content:")
    lines += [f"  {l}" for l in cut(answer["content"].splitlines(), limit, "lines")]
    if answer["restore"] or answer["applied"]:
        verb = "restored" if answer["applied"] else "would restore (run with --apply)"
        lines.append(f"{verb} from HEAD ({len(answer['restore'])}):")
        lines += [f"  git checkout HEAD -- {p}" for p in answer["restore"]]
    return "\n".join(lines)
