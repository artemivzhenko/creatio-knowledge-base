#!/usr/bin/env python3
"""
Rename a schema (process, page, object...) across a workspace or package and fix every
reference to the old name.

    python refactor.py rename-schema <root> <OldName> <NewName> [--apply]

<root> is a package folder or a workspace (its packages/* are scanned). Without --apply it
only reports. What changes:

- Schemas/<Old>/ -> Schemas/<New>/, the Name inside descriptor.json and metadata.json (A2),
  the schema's own generated .js/.cs file (<Old>.js -> <New>.js with the inner name);
- Resources/<Old>.<Kind>/ -> Resources/<New>.<Kind>/;
- every other text file under the root where the old name appears as a whole word
  (page JS, C#, data bindings, other schemas), each replaced occurrence is listed.

Schema UIds never change, so the environment treats the push as a rename. References by
UId (sub-process calls, mappings, bindings by SysSchemaUId) need no edit and are untouched.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TEXT_SUFFIXES = {".js", ".cs", ".json", ".xml", ".sql", ".md", ".txt", ".ts"}


def packages(root: Path) -> list[Path]:
    if (root / "descriptor.json").is_file():
        return [root]
    pk = root / "packages"
    return sorted(p for p in (pk.iterdir() if pk.is_dir() else root.iterdir()) if (p / "descriptor.json").is_file())


def read(path: Path) -> str:
    with open(path, encoding="utf-8", errors="surrogateescape", newline="") as fh:
        return fh.read()


def write(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8", errors="surrogateescape", newline="") as fh:
        fh.write(text)


def rename_schema(root: Path, old: str, new: str, apply: bool) -> list[str]:
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", new):
        raise SystemExit(f"{new!r} is not a valid schema name")
    word = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(old)}(?![A-Za-z0-9_])")
    report: list[str] = []
    owner = None
    for pkg in packages(root):
        if (pkg / "Schemas" / old).is_dir():
            owner = pkg
    if owner is None:
        raise SystemExit(f"no schema {old} under {root}")
    if (owner / "Schemas" / new).exists():
        raise SystemExit(f"{owner / 'Schemas' / new} already exists")

    # 1. text replacements everywhere (done before the moves so paths are stable)
    for pkg in packages(root):
        for path in sorted(pkg.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES or "node_modules" in path.parts:
                continue
            text = read(path)
            n = len(word.findall(text))
            if not n:
                continue
            report.append(f"{n:3} x  {path.relative_to(root)}")
            if apply:
                write(path, word.sub(new, text))

    # 2. moves inside the owning package
    moves = [(owner / "Schemas" / old, owner / "Schemas" / new)]
    for res in sorted((owner / "Resources").glob(f"{old}.*")) if (owner / "Resources").is_dir() else []:
        moves.append((res, res.with_name(new + res.name[len(old):])))
    for f in sorted((owner / "Schemas" / old).glob(f"{old}.*")):
        moves.append((f, f.with_name(new + f.name[len(old):])))
    for src, dst in moves:
        report.append(f"move   {src.relative_to(root)} -> {dst.relative_to(root)}")
    if apply:
        # inner files first, then folders
        for src, dst in sorted(moves, key=lambda m: -len(m[0].parts)):
            src.rename(dst if dst.parent.exists() else dst)
    return report


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["rename-schema"])
    ap.add_argument("root")
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    report = rename_schema(Path(a.root).resolve(), a.old, a.new, a.apply)
    print("\n".join(report))
    print(f"\n{'applied' if a.apply else 'dry run - add --apply to change files'}: {len(report)} item(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
