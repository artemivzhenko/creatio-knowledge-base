#!/usr/bin/env python3
"""Captions of a whole package: Resources/<Schema>.<Kind>/resource.<culture>.xml (library: ../creatio_schemas/resources.py).

    python resources.py cultures   <package>
    python resources.py missing    <package> [--culture ru-RU] [--kind page] [--from en-US] [--keys]
    python resources.py fill       <package> --to ru-RU [--from en-US] [--schema X] [--dry-run]
    python resources.py set        <package> <Schema> <Key> en-US="..." [ru-RU="..."] [--dry-run]
    python resources.py rename-key <package> <Schema> <Old> <New> [--dry-run]
    python resources.py remove-key <package> <Schema> <Key> [--dry-run]

The package's cultures are those any of its schemas carries. `missing` compares every schema with
--from (en-US): a key of en-US absent in a culture the package ships, a culture file the schema lacks
counting as all of its keys. `fill` copies those values from --from into --to (the platform then shows
the copied text). `rename-key` and `remove-key` act on the key and the keys under it (`Key.`), in every
culture. Only files whose text changes are written; --dry-run prints their diff.
"""

from __future__ import annotations

import difflib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from creatio_schemas.cli import CommandLine, parse_assignments  # noqa: E402
from creatio_schemas.files import read_text, write_text  # noqa: E402
from creatio_schemas.resources import Resources, package_resources  # noqa: E402
from creatio_schemas.schema import Descriptor  # noqa: E402

KINDS = {"object": "Entity", "page": "ClientUnit", "client": "ClientUnit", "process": "Process", "dcm": "Dcm", "user-task": "ProcessUserTask",
         "source": "SourceCode", "addon": "Addon"}


def cultures_of(all_res: dict[str, Resources]) -> list[str]:
    return sorted({c for r in all_res.values() for c in r.cultures})


def missing_keys(res: Resources, culture: str, source: str) -> list[str] | None:
    """Keys of `source` that `culture` lacks; None when the schema has no `source` culture."""
    if source not in res.cultures:
        return None
    have = res.cultures.get(culture, {})
    return [k for k in res.ordered_keys(source) if k not in have]


def write(package: Path, all_res: list[Resources], dry_run: bool, extra: dict[Path, tuple[str, bool]] | None = None) -> int:
    """Write (or diff) only the files whose text changed."""
    changed = {}
    for res in all_res:
        for path, (text, bom) in res.files().items():
            if not path.is_file() or read_text(path) != (text, bom):
                changed[path] = (text, bom)
    for path, (text, bom) in (extra or {}).items():
        if read_text(path) != (text, bom):
            changed[path] = (text, bom)
    for path, (text, bom) in changed.items():
        if dry_run:
            old = read_text(path)[0] if path.is_file() else ""
            rel = path.relative_to(package).as_posix()
            sys.stdout.write("".join(difflib.unified_diff(old.splitlines(True), text.splitlines(True), f"a/{rel}", f"b/{rel}")) + "\n")
        else:
            write_text(path, text, bom)
    print(f"{len(changed)} file(s) {'would change (dry run: nothing written)' if dry_run else 'written'}")
    return 0


def one(package: Path, schema: str) -> Resources:
    res = package_resources(package).get(schema)
    if res is None:
        raise KeyError(f"no resources of {schema} in {package}")
    return res


# -- commands ------------------------------------------------------------------ #

def cultures(_, a):
    all_res = package_resources(Path(a.package))
    groups: dict[tuple[str, ...], list[str]] = {}
    for name, r in all_res.items():
        groups.setdefault(tuple(sorted(r.cultures)), []).append(name)
    print(f"{Path(a.package).name}: {len(cultures_of(all_res))} culture(s) over {len(all_res)} schema(s): {', '.join(cultures_of(all_res))}")
    for cs, names in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        shown = ", ".join(names[:8]) + (f" ... (+{len(names) - 8})" if len(names) > 8 else "")
        print(f"  {len(names):>4} schema(s) in {', '.join(cs) or '(no culture)'}: {shown}")


def missing(_, a):
    all_res = package_resources(Path(a.package))
    kind = KINDS.get(a.kind, a.kind) if a.kind else None
    targets = [a.culture] if a.culture else [c for c in cultures_of(all_res) if c != a.source]
    total = 0
    for name, r in all_res.items():
        if kind and r.kind.lower() != kind.lower():
            continue
        parts, listed = [], []
        for culture in targets:
            keys = missing_keys(r, culture, a.source)
            if keys is None:
                parts = [f"no {a.source}"]
                break
            if keys:
                parts.append(f"{culture} {len(keys)}" + ("" if culture in r.cultures else " (no file)"))
                listed += [f"      {culture}: {k}" for k in keys]
                total += len(keys)
        if parts:
            print(f"{name} [{r.kind}]: " + ", ".join(parts))
            if a.keys:
                print("\n".join(listed))
    print(f"{total} key(s) missing" + (f" in {a.culture}" if a.culture else "") + f" against {a.source}")


def fill(_, a):
    package = Path(a.package)
    all_res = [one(package, a.schema)] if a.schema else list(package_resources(package).values())
    n = 0
    for r in all_res:
        for k in missing_keys(r, a.to, a.source) or []:
            r.set(k, r.get(k, a.source), [a.to])
            if k in r.attrs.get(a.source, {}):
                r.attrs.setdefault(a.to, {})[k] = r.attrs[a.source][k]  # an image item keeps its attributes
            n += 1
    print(f"copy {n} value(s) from {a.source} to {a.to}")
    return write(package, all_res, a.dry_run)


def set_(_, a):
    package = Path(a.package)
    r = one(package, a.schema)
    if not all("=" in v for v in a.values):
        raise ValueError('give culture=value pairs, e.g. en-US="Order"')
    values = parse_assignments(a.values)
    for culture, value in values.items():
        r.set(a.key, value, [culture])
    extra = {}
    desc = package / "Schemas" / a.schema / "descriptor.json"
    if a.key == "Caption" and "en-US" in values and desc.is_file():  # descriptor.json repeats the en-US caption
        d = Descriptor(desc)
        d.set_caption(values["en-US"])
        extra[desc] = (d.text, read_text(desc)[1])
    return write(package, [r], a.dry_run, extra)


def rename_key(_, a):
    package = Path(a.package)
    r = one(package, a.schema)
    if any(a.new in items for items in r.cultures.values()):
        raise ValueError(f"{a.schema} already has a key {a.new}")
    n = r.rename_prefix(a.old, a.new)
    if not n:
        raise KeyError(f"{a.schema} has no key {a.old}")
    print(f"rename {n} item(s)")
    return write(package, [r], a.dry_run)


def remove_key(_, a):
    package = Path(a.package)
    r = one(package, a.schema)
    n = r.remove_prefix(a.key)
    if not n:
        raise KeyError(f"{a.schema} has no key {a.key}")
    print(f"remove {n} item(s)")
    return write(package, [r], a.dry_run)


def build() -> CommandLine:
    c = CommandLine(__doc__, "schema")
    pkg_cmd = lambda name, fn, help_: c.command(name, fn, help_, target=False)  # noqa: E731
    p = pkg_cmd("cultures", cultures, "the package's cultures and which schemas carry which")
    p.add_argument("package")
    p = pkg_cmd("missing", missing, "keys of --from absent in the other cultures, one line per schema")
    p.add_argument("package")
    p.add_argument("--culture", help="only this culture")
    p.add_argument("--kind", help=f"only this kind: {', '.join(KINDS)} or a folder suffix")
    p.add_argument("--from", dest="source", default="en-US")
    p.add_argument("--keys", action="store_true", help="list the keys")
    p = pkg_cmd("fill", fill, "copy missing values from --from into --to")
    p.add_argument("package")
    p.add_argument("--to", required=True)
    p.add_argument("--from", dest="source", default="en-US")
    p.add_argument("--schema", help="only this schema")
    for name, fn, help_, args in (("set", set_, "set a key in cultures", ("key", "values")), ("rename-key", rename_key, "rename a key and its subkeys", ("old", "new")),
                                  ("remove-key", remove_key, "remove a key and its subkeys", ("key",))):
        p = pkg_cmd(name, fn, help_)
        p.add_argument("package")
        p.add_argument("schema")
        for arg in args:
            p.add_argument(arg, nargs="+", metavar="culture=value") if arg == "values" else p.add_argument(arg)
    for sub in c.commands.choices.values():
        if sub.prog.split()[-1] in ("fill", "set", "rename-key", "remove-key"):
            sub.add_argument("--dry-run", action="store_true", help="print the diff, write nothing")
    return c


def main(argv=None) -> int:
    return build().run(sys.argv[1:] if argv is None else argv, lambda a: None)


if __name__ == "__main__":
    sys.exit(main())
