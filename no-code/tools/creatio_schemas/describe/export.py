"""A snapshot of the tools' answers as text files, for reading without the tools: one file per package item, one per package.

    <out>/<Package>/_package.md       the describe_package lines, then the items that cannot be read
    <out>/<Package>/<Schema>.md       describe_schema, `## Depends on`, `## Dependents`, `## Files` (absolute paths)
    <out>/<Package>/Data/<Name>.md    a data binding;  <out>/<Package>/Files/cs/<X>.cs.md  a C# file

Nothing reads it back: the index stays the store, the snapshot is an export of it. The sections come from the
indexes loaded once (the same edges `dependencies` prints), not from one `find` / `deps` call per item - each of
those re-checks every index against the disk. Files of items that no longer exist are removed; other files in
the folder are not touched.
"""

from __future__ import annotations

from pathlib import Path

from .core import describe_package, describe_schema
from .deps import Edge
from .index import PackageIndex, packages_of

EXPORT_DIR = ".creatio-export"
PACKAGE_FILE = "_package.md"


def default_out(path: Path | str) -> Path:
    """<workspace>/.creatio-export, next to .creatio-index (a package path: its workspace)."""
    path = Path(path).resolve()
    if (path / "descriptor.json").is_file():
        path = path.parent.parent if path.parent.name == "packages" else path.parent
    return path / EXPORT_DIR


def _block(lines: list[str]) -> str:
    return "```text\n" + "\n".join(lines) + "\n```\n"


def _item_text(idx: PackageIndex, name: str, entry: dict, users: dict[str, list[str]]) -> str:
    if "error" in entry:
        return f"{name}: cannot read: {entry['error']}\n"
    package = idx.package.resolve()
    try:
        summary = describe_schema(package, name[len("Data/"):] if name.startswith("Data/") else name, 0)
    except (OSError, ValueError, KeyError) as e:  # the index read it, the toolkit does not now: the snapshot says so
        summary = f"{name}: {type(e).__name__}: {e}"
    edges = sorted((Edge.from_dict(d) for d in entry.get("deps", [])), key=lambda e: (e.to_kind, e.to_name.lower(), e.via))
    files = [f"{package / rel}  ({size} bytes)" for rel, (size, *_) in sorted(entry.get("files", {}).items())]
    return (f"# {name}\n\n" + _block(summary.splitlines())
            + "\n## Depends on\n\n" + (_block([e.line() for e in edges]) if edges else "nothing typed\n")
            + "\n## Dependents\n\n" + (_block(sorted(users.get(name.lower(), []))) if users.get(name.lower()) else "nothing typed in the workspace\n")
            + "\n## Files\n\n" + (_block(files) if files else "none\n"))


def export(path: Path | str, out: Path | str | None = None) -> str:
    """Write the snapshot of every package under `path` into `out` (default: default_out(path)); one summary line back."""
    out = Path(out) if out else default_out(path)
    indexes = [PackageIndex(p) for p in packages_of(path)]
    for idx in indexes:
        idx.refresh()
    users: dict[str, list[str]] = {}  # target name -> the dependents lines, over every package (as `dependencies` prints them)
    for idx in indexes:
        pkg = idx.data.get("package", idx.package.name)
        for n, e in idx.entries():
            for d in e.get("deps", []):
                edge = Edge.from_dict(d)
                users.setdefault(edge.to_name.lower(), []).append((pkg, f"{e.get('kind', 'data')} {n}", edge))
    written, removed = 0, 0
    for idx in indexes:
        pkg = idx.data.get("package", idx.package.name)
        folder = out / idx.package.name
        here = {k: [f"{who}{'' if p == pkg else ', ' + p}  {e.via}" + (": " + ", ".join(e.detail) if e.detail else "") + ("" if e.ref == "uid" else f"  [{e.ref}]")
                    for p, who, e in v] for k, v in users.items()}
        texts = {PACKAGE_FILE: _block(describe_package(idx.package, "", 0).splitlines())
                 + (("\n## Cannot read\n\n" + _block(idx.lines("error"))) if idx.lines("error") else "")}
        for name, entry in idx.entries():
            texts[f"{name}.md"] = _item_text(idx, name, entry, here)
        for rel, text in texts.items():
            target = folder / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))
            written += 1
        keep = {(folder / rel).resolve() for rel in texts}
        for old in sorted(folder.rglob("*.md")):  # an item that no longer exists: its file goes; anything else stays
            if old.resolve() not in keep:
                old.unlink()
                removed += 1
                parent = old.parent
                while parent != folder and not any(parent.iterdir()):  # a folder emptied by the removal (Data/, Files/cs/) goes too
                    parent.rmdir()
                    parent = parent.parent
    return f"{written} files written, {removed} removed, {len(indexes)} package(s) -> {out}"
