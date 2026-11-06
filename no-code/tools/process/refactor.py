#!/usr/bin/env python3
"""
Rename a schema (process, page, object...) across a workspace or package and fix every
reference to the old name.

    python refactor.py rename-schema <root> <OldName> <NewName> [--apply]

<root> is a package folder or a workspace (its packages/* are scanned). Without --apply it
only reports. Library: ../creatio_schemas/refactor.py. What changes:

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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from creatio_schemas import rename_schema  # noqa: E402


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["rename-schema"])
    ap.add_argument("root")
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    try:
        report = rename_schema(Path(a.root).resolve(), a.old, a.new, a.apply)
    except (ValueError, FileNotFoundError, FileExistsError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print("\n".join(report))
    print(f"\n{'applied' if a.apply else 'dry run - add --apply to change files'}: {len(report)} item(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
