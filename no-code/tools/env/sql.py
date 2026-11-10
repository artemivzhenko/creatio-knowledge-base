#!/usr/bin/env python3
"""SQL on an environment through clio, rows as JSON or CSV (no table, no wrapped columns).

    python sql.py -e <env> "select ..."                 rows of every statement as JSON
    python sql.py -e <env> --file q.sql --csv           statements split on ';' at line ends, each run alone
    python sql.py --project project.json "update ..."   an update/insert prints "(no rows)"

Exit 1 when clio reports [ERR] (clio itself exits 0 then); 2 on a usage error.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from creatio_schemas.environment import open_environment, split_statements  # noqa: E402


def write_rows(rows: list[dict], as_csv: bool, out) -> None:
    if not as_csv:
        out.write(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
        return
    columns = list(dict.fromkeys(k for r in rows for k in r))
    w = csv.DictWriter(out, fieldnames=columns, lineterminator="\n")
    w.writeheader()
    w.writerows({k: ("" if v is None else v) for k, v in r.items()} for r in rows)


def main(argv=None, **env_kw) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("sql", nargs="?")
    p.add_argument("-e", "--env", help="clio environment name")
    p.add_argument("--project", help="project.json (its environment.clioName runs the SQL)")
    p.add_argument("--file", help="read the SQL from a file")
    fmt = p.add_mutually_exclusive_group()
    fmt.add_argument("--json", action="store_true", help="JSON rows (default)")
    fmt.add_argument("--csv", action="store_true", help="CSV with a header row")
    a = p.parse_args(argv)
    try:
        text = Path(a.file).read_text(encoding="utf-8-sig") if a.file else a.sql
        if not text:
            raise ValueError("give the SQL as an argument or --file")
        env = open_environment(a.env, a.project, **env_kw)
        statements = split_statements(text)
    except (ValueError, KeyError, FileNotFoundError) as e:
        print(f"error: {e.args[0] if e.args else e}", file=sys.stderr)
        return 2
    for i, statement in enumerate(statements):
        if len(statements) > 1:
            print(f"-- statement {i + 1}: {statement.splitlines()[0][:80]}")
        try:
            rows = env.sql(statement)
        except RuntimeError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        if rows:
            write_rows(rows, a.csv, sys.stdout)
        else:
            print("(no rows)")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
