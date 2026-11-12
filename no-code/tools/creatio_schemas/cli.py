"""Shared pieces of the command-line tools (tools/process/proc.py, tools/rules/rules.py)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .schema import WARNING, Schema


def parse_assignments(items: list[str]) -> dict[str, str]:
    """["A=1", "B=x"] -> {"A": "1", "B": "x"}."""
    out = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"expected Name=value, got {item!r}")
        k, v = item.split("=", 1)
        out[k] = v
    return out


def resolve_package(name: str, project: Path | None = None) -> Path:
    """A package folder given by path, or by name: packages/<name> under the current folder or the project's."""
    if Path(name).is_dir():
        return Path(name)
    for base in (Path.cwd(), Path(project).resolve().parent if project else None):
        if base is not None and (base / "packages" / name).is_dir():
            return base / "packages" / name
    raise FileNotFoundError(f"no package folder named {name}; give its path (packages/{name})")


def finish(schema: Schema, dry_run: bool) -> int:
    """After a writing command: print the diff (dry run) or save and report; 1 when validation finds errors."""
    if dry_run:
        sys.stdout.write(schema.diff())
        print("\n(dry run: nothing written)")
        return 0
    schema.save()
    problems = schema.validate()
    print(f"saved {schema.name}" + (f"; validation: {len(problems)} problem(s)" if problems else ""))
    for p in problems:
        print("  -", p)
    return 1 if any(not p.startswith(WARNING) for p in problems) else 0


class CommandLine:
    """argparse with one sub-parser per command; a writing command is saved (or diffed with --dry-run) by `finish`.

    Each handler is `handler(schema, args) -> int | None`; `open_schema(args)` gives it the schema.
    """

    def __init__(self, doc: str, target: str):
        self.parser = argparse.ArgumentParser(description=doc, formatter_class=argparse.RawDescriptionHelpFormatter)
        self.commands = self.parser.add_subparsers(dest="command", required=True, metavar="command")
        self.target = argparse.ArgumentParser(add_help=False)
        self.target.add_argument("package")
        self.target.add_argument(target)
        self.dry = argparse.ArgumentParser(add_help=False)
        self.dry.add_argument("--dry-run", action="store_true", help="print the diff, write nothing")

    def command(self, name: str, handler, help: str, writes: bool = False, under=None, target: bool = True) -> argparse.ArgumentParser:
        """A sub-command; `under` nests it below a group made with group()."""
        parents = ([self.target] if target and under is None else []) + ([self.dry] if writes else [])
        p = (under or self.commands).add_parser(name, parents=parents, help=help, description=help)
        p.set_defaults(handler=handler, writes=writes)
        return p

    def group(self, name: str, help: str):
        """A command with actions of its own: `tool <group> <package> <schema> <action> ...`."""
        p = self.commands.add_parser(name, parents=[self.target], help=help, description=help)
        return p.add_subparsers(dest="action", required=True, metavar="action")

    def run(self, argv: list[str], open_schema) -> int:
        a = self.parser.parse_args(argv)
        try:
            if getattr(a, "package", None):
                a.package = str(resolve_package(a.package))
            schema = open_schema(a)
            result = a.handler(schema, a)
        except (KeyError, ValueError, FileNotFoundError, FileExistsError, RuntimeError) as e:
            print(f"error: {e.args[0] if e.args else e}", file=sys.stderr)
            return 2
        if a.writes:
            return finish(schema, a.dry_run)
        return result or 0
