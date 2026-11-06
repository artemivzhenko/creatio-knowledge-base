"""Rename a schema (process, page, object...) across a workspace or package and fix every reference to the old name.

Schema UIds never change, so the environment treats the push as a rename. References by UId
(sub-process calls, mappings, bindings by SysSchemaUId) need no edit and are untouched.
"""

from __future__ import annotations

import re
from pathlib import Path

TEXT_SUFFIXES = {".js", ".cs", ".json", ".xml", ".sql", ".md", ".txt", ".ts"}


def packages(root: Path) -> list[Path]:
    """`root` itself when it is a package, else the packages of a workspace (root/packages/* or root/*)."""
    if (root / "descriptor.json").is_file():
        return [root]
    pk = root / "packages"
    return sorted(p for p in (pk.iterdir() if pk.is_dir() else root.iterdir()) if (p / "descriptor.json").is_file())


def _read(path: Path) -> str:
    with open(path, encoding="utf-8", errors="surrogateescape", newline="") as fh:
        return fh.read()


def _write(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8", errors="surrogateescape", newline="") as fh:
        fh.write(text)


def rename_schema(root: Path, old: str, new: str, apply: bool) -> list[str]:
    """Whole-word replacement of `old` in every text file, then the Schemas/ and Resources/ folders and the
    schema's own generated file are moved. Without `apply` only the report is returned."""
    root = Path(root)
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", new):
        raise ValueError(f"{new!r} is not a valid schema name")
    word = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(old)}(?![A-Za-z0-9_])")
    owner = next((pkg for pkg in reversed(packages(root)) if (pkg / "Schemas" / old).is_dir()), None)
    if owner is None:
        raise FileNotFoundError(f"no schema {old} under {root}")
    if (owner / "Schemas" / new).exists():
        raise FileExistsError(owner / "Schemas" / new)

    report: list[str] = []
    # 1. text replacements everywhere (before the moves, so the paths are stable)
    for pkg in packages(root):
        for path in sorted(pkg.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES or "node_modules" in path.parts:
                continue
            text = _read(path)
            n = len(word.findall(text))
            if n:
                report.append(f"{n:3} x  {path.relative_to(root)}")
                if apply:
                    _write(path, word.sub(new, text))

    # 2. moves inside the owning package
    moves = [(owner / "Schemas" / old, owner / "Schemas" / new)]
    res = owner / "Resources"
    moves += [(r, r.with_name(new + r.name[len(old):])) for r in (sorted(res.glob(f"{old}.*")) if res.is_dir() else [])]
    moves += [(f, f.with_name(new + f.name[len(old):])) for f in sorted((owner / "Schemas" / old).glob(f"{old}.*"))]
    report += [f"move   {src.relative_to(root)} -> {dst.relative_to(root)}" for src, dst in moves]
    if apply:
        for src, dst in sorted(moves, key=lambda m: -len(m[0].parts)):  # inner files first, then folders
            src.rename(dst)
    return report
