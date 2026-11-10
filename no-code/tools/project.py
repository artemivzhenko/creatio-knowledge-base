#!/usr/bin/env python3
"""Synchronize the test framework's environment configuration from project.json."""

import argparse
import json
import sys
from pathlib import Path


def read_json(path: Path) -> dict:
    text = path.read_text(encoding="utf-8-sig")
    # Framework configuration accepts comments; preserve strings while removing comments.
    result = []
    i = 0
    in_string = False
    escaped = False
    while i < len(text):
        ch = text[i]
        if in_string:
            result.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
        elif ch == '"':
            in_string = True
            result.append(ch)
            i += 1
        elif text[i:i + 2] == "//":
            end = text.find("\n", i + 2)
            i = len(text) if end < 0 else end
        elif text[i:i + 2] == "/*":
            end = text.find("*/", i + 2)
            if end < 0:
                raise ValueError(f"{path}: unterminated comment")
            result.append(" ")
            i = end + 2
        else:
            result.append(ch)
            i += 1
    text = "".join(result)
    result = []
    in_string = False
    escaped = False
    for i, ch in enumerate(text):
        if in_string:
            result.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
            result.append(ch)
        elif ch == "," and text[i + 1:].lstrip().startswith(("}", "]")):
            continue
        else:
            result.append(ch)
    value = json.loads("".join(result))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def sync(project_file: Path, framework: Path | None = None) -> list[str]:
    project = read_json(project_file)
    env = project.get("environment")
    if not isinstance(env, dict) or any(not isinstance(env.get(k), str) or not env[k].strip()
                                        for k in ("url", "login", "password")):
        raise ValueError("project.json must contain environment.url, login and password")
    paths = project.get("paths")
    configured = paths.get("testFramework") if isinstance(paths, dict) else None
    if framework is None:
        if not isinstance(configured, str) or not configured.strip():
            raise ValueError("supply --framework or paths.testFramework in project.json")
        framework = Path(configured)
        if not framework.is_absolute():
            framework = project_file.resolve().parent / framework
    if not framework.is_dir() or not (framework / "Configuration").is_dir():
        raise ValueError(f"framework Configuration directory not found: {framework}")
    target = framework / "Configuration" / "creatio.env.config.json"
    config = read_json(target) if target.exists() else {}
    updates = {
        "BaseUrl": env["url"],
        "Users": [{"Username": env["login"], "Password": env["password"]}],
        "CasesFolders": config.get("CasesFolders", ["./Cases"]),
    }
    if not isinstance(updates["CasesFolders"], list) or not all(isinstance(p, str) for p in updates["CasesFolders"]):
        raise ValueError(f"{target}: CasesFolders must be a list of strings")
    changed = [key for key, value in updates.items() if config.get(key) != value]
    if not target.exists() or changed:
        config.update(updates)
        target.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("sync", help="write the framework environment from project.json")
    command.add_argument("project", type=Path)
    command.add_argument("--framework", type=Path)
    args = parser.parse_args(argv)
    try:
        changed = sync(args.project, args.framework)
    except (OSError, ValueError) as exc:
        print(f"sync failed: {exc}", file=sys.stderr)
        return 1
    print("Updated: " + ", ".join(changed) if changed else "Already synchronized.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
