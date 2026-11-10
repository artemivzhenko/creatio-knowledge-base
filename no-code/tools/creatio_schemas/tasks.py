"""The task folders of the author/tester loop (skill creatio-loop): which schemas active tasks change or affect."""

from __future__ import annotations

import json
from pathlib import Path


def active_tasks(tasks: Path | str) -> list[Path]:
    """Task folders under `tasks` without a success-report.md, sorted by name."""
    root = Path(tasks)
    return sorted(p for p in root.iterdir() if p.is_dir() and not (p / "success-report.md").is_file()) if root.is_dir() else []


def active_locks(tasks: Path | str, current: str | None = None) -> tuple[dict[str, str], dict[str, str]]:
    """(changes, affects): schema name (lower) -> task folder name, over every active task but `current`.

    `changes` are the `schemas` of each folder's schemas.json - the lock; `affects` are its `affects` -
    the dependents the author listed from `describe.py impact`, a heads-up for whoever changes them."""
    changes, affects = {}, {}
    for folder in active_tasks(tasks):
        if current and folder.name == current:
            continue
        lock = folder / "schemas.json"
        if not lock.is_file():
            continue
        try:
            data = json.loads(lock.read_text(encoding="utf-8-sig"))
        except ValueError:
            continue
        for name in data.get("schemas") or []:
            changes.setdefault(str(name).lower(), folder.name)
        for name in data.get("affects") or []:
            affects.setdefault(str(name).lower(), folder.name)
    return changes, affects
