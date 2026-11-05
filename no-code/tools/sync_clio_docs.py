#!/usr/bin/env python3
"""
Builds no-code/reference/<command>.md for every clio command from the clio
repository's own command docs (MIT), and refreshes the command tables inside
each block's SKILL.md.

    python no-code/tools/sync_clio_docs.py <path-to-clio-repo>

Check out the tag that matches the installed clio first (`clio ver`): the docs
on the main branch describe commands the installed binary may not have yet.
Pure standard library.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NO_CODE = HERE.parent
REFERENCE = NO_CODE / "reference"

# Sections of the upstream docs that carry no information for an agent.
DROP_SECTIONS = {"Command Type", "Reporting Bugs", "See Also"}

# command -> block folder. Every doc file must be mapped; an unmapped one fails the run.
BLOCKS: dict[str, tuple[str, ...]] = {
    "clio-basics": (
        "reg-web-app", "unreg-web-app", "list-environments", "ping-app", "healthcheck",
        "login", "logout", "auth-status", "get-info", "get-user-culture", "open-web-app",
        "env-ui", "get-browser-session", "clear-browser-session", "config", "open-settings",
        "register", "unregister", "pin-certificate", "update-cli", "autoupdate",
        "externalLink", "ref-to", "hosts", "info", "get-build-info", "check-nuget-update",
        "show-local-envs", "get-webservice-url", "set-webservice-url",
    ),
    "clio-sql-and-data": (
        "execute-sql-script", "dataservice", "call-service", "execute-dataservice-batch",
        "install-dbhub", "sync-dbhub", "mock-data", "set-syssetting",
        "download-sys-setting-file", "set-feature", "add-data-binding-row",
        "remove-data-binding-row", "create-data-binding", "create-data-binding-db",
        "read-data-binding-db", "remove-data-binding-row-db", "upsert-data-binding-row-db",
        "upload-file", "upload-image", "set-file-content-storage-connection-string",
    ),
    "clio-packages": (
        "new-pkg", "create-package", "add-package", "list-packages", "push-pkg", "pull-pkg", "delete-pkg-remote",
        "generate-pkg-zip", "extract-pkg-zip", "compressApp", "get-pkg-version",
        "set-pkg-version", "activate-pkg", "deactivate-pkg", "lock-package", "unlock-package",
        "add-package-dependency", "remove-package-dependency", "pkg-hotfix",
        "show-package-file-content", "install-application", "uninstall-app-remote",
    ),
    "clio-workspace-and-build": (
        "create-workspace", "restore-workspace", "push-workspace", "build-workspace",
        "merge-workspaces", "cfg-worspace", "git-sync", "show-diff", "save-state",
        "apply-manifest", "compile-configuration", "compile-package", "last-compilation-log",
        "watch-compilation", "turn-fsm", "set-fsm-config", "pkg-to-file-system", "pkg-to-db",
        "set-dev-mode", "link-from-repository", "link-to-repository", "link-core-src",
        "link-package-store", "link-workspace-with-tide-repository", "restart-web-app",
        "clear-redis-db", "download-configuration", "restore-configuration",
        "generate-source-code", "install-nuget-pkg", "restore-nuget-pkg",
        "switch-nuget-to-dll-reference",
    ),
    "clio-schemas": (
        "create-entity-schema", "update-entity-schema", "modify-entity-schema-column",
        "get-entity-schema-properties", "get-entity-schema-column-properties",
        "set-entity-schema-properties", "find-entity-schema", "create-lookup",
        "get-entity-connections", "update-entity-connections", "list-entity-client-schemas",
        "create-schema", "get-schema", "update-schema", "add-schema",
        "create-client-unit-schema", "get-client-unit-schema", "update-client-unit-schema",
        "create-sql-schema", "get-sql-schema", "update-sql-schema", "install-sql-schema",
        "delete-schema", "export-schema", "import-schema", "add-item", "merge-creatio-artifact",
        "sync-schemas", "convert",
    ),
    "clio-pages": (
        "create-page", "get-page", "update-page", "sync-pages", "list-pages",
        "list-page-templates", "get-page-hierarchy", "localize-page",
        "create-related-page-addon", "get-related-page-addon", "get-classic-list-columns",
        "get-classic-page-sources", "get-component-info", "export-component-registry",
        "component-registry-refresh",
    ),
    "clio-apps": (
        "create-app", "list-apps", "find-app", "get-app-info", "get-app-hash",
        "create-app-section", "update-app-section", "delete-app-section", "list-app-sections",
        "set-app-icon", "set-app-version", "publish-app", "download-application",
        "deploy-application", "alm-deploy",
    ),
    "clio-processes": (
        "generate-process-model", "get-process-signature", "get-process-page-facts",
        "add-user-task", "create-user-task-page", "modify-user-task-parameters",
        "register-process-element", "install-process-builder", "enroll-sequence-participants",
        "get-sequence-context",
    ),
    "clio-security": (
        "manage-user", "manage-role", "manage-access", "manage-license", "distribute-license",
        "upload-license", "upload-licenses", "get-object-rights", "set-object-rights",
        "set-default-record-rights", "apply-default-record-rights", "get-record-rights",
        "set-record-rights", "create-oauth-technical-user", "create-server-to-server-oauth-app",
        "get-identity-service-config", "resolve-oauth-system-user", "verify-oauth-app",
        "check-auth-code-flow", "get-identity-assertion", "get-identity-public-jwk",
        "regenerate-identity-signing-key", "register-sso-provider", "idp-bind", "idp-delete",
        "idp-list", "idp-services", "idp-set-default", "idp-set-secret", "idp-unbind",
        "idp-upsert", "deploy-identity", "uninstall-identity", "CustomizeDataProtection",
    ),
    "clio-theming": (
        "build-theme", "clear-themes-cache", "create-theme", "delete-theme", "get-theme",
        "list-themes", "set-user-theme", "update-theme", "set-background-image", "set-logo",
    ),
    "clio-tests-and-devops": (
        "new-test-project", "new-integration-test-project", "new-ui-project", "run", "assert",
        "listen", "add-custom-logging", "pack-nuget-pkg", "push-nuget-pkg",
        "build-docker-image", "install-gate", "install-dashboards-migrator", "ring",
        "experimental", "quiz",
    ),
    "clio-mcp": (
        "mcp-server", "mcp-http", "install-toolkit", "update-toolkit", "delete-toolkit",
        "install-knowledge", "update-knowledge", "delete-knowledge", "info-knowledge",
        "add-knowledge-source", "remove-knowledge-source", "enable-knowledge-source",
        "disable-knowledge-source", "list-knowledge-sources", "list-knowledge-examples",
    ),
    "clio-infrastructure": (
        "deploy-creatio", "uninstall-creatio", "restore-db", "prune-db-templates",
        "clear-local-env", "create-k8-files", "open-k8-files", "deploy-infrastructure",
        "delete-infrastructure", "check-windows-features", "manage-windows-features", "start",
        "stop", "turn-farm-mode", "compare-web-farm-node", "clone-env",
    ),
}
BLOCK_OF = {cmd: block for block, cmds in BLOCKS.items() for cmd in cmds}

_SECTION_RE = re.compile(r"(?m)^## ")
_NAME_LINE_RE = re.compile(r"(?m)^([A-Za-z][\w-]*)\s+-\s+(.+?)\s*$")


def split_sections(text: str) -> list[tuple[str, str]]:
    """[(heading, body)] where the first heading is "" for the preamble."""
    parts = _SECTION_RE.split(text)
    out = [("", parts[0])]
    for chunk in parts[1:]:
        heading, _, body = chunk.partition("\n")
        out.append((heading.strip(), body))
    return out


def _first_sentence(text: str) -> str:
    sentence = re.split(r"(?<=[.!?])\s", text.strip(), maxsplit=1)[0].rstrip(".")
    return sentence if len(sentence) <= 120 else sentence[:117].rstrip() + "..."


def purpose(sections: list[tuple[str, str]], command: str) -> str:
    """One-line purpose: the '## Name' line when present, else the first prose sentence."""
    for heading, body in sections:
        if heading == "Name":
            m = _NAME_LINE_RE.search(body)
            if m:
                return _first_sentence(m.group(2))
    for heading, body in sections:
        if heading in ("", "Description", "Usage", "Synopsis"):
            for para in re.split(r"\n\s*\n", body):
                para = " ".join(para.split())
                if para and not para.startswith(("#", "```", "|", "-", "clio ", command)):
                    return _first_sentence(para)
    return command


def convert(doc: Path, version: str) -> tuple[str, str, str]:
    command = doc.stem
    block = BLOCK_OF[command]
    sections = split_sections(doc.read_text(encoding="utf-8"))
    summary = purpose(sections, command)
    kept = [
        f"## {h}\n{b}" if h else b
        for h, b in sections
        if h not in DROP_SECTIONS and not (h == "" and b.strip() == f"# {command}")
    ]
    body = "\n".join(kept)
    body = re.sub(r"(?m)^# .*\n", "", body, count=1)          # the upstream H1
    body = re.sub(r"(?m)^- \[Clio Command Reference\].*\n?", "", body)
    text = (
        "---\n"
        f"command: {command}\n"
        f"block: {block}\n"
        f"source: clio {version}, clio/docs/commands/{command}.md (MIT)\n"
        "---\n"
        f"# {command} - {summary}\n\n"
        + body.strip()
        + "\n"
    )
    return block, summary, text


_TABLE_START = "<!-- commands:start -->"
_TABLE_END = "<!-- commands:end -->"


def refresh_skill_table(block: str, rows: list[tuple[str, str]]) -> None:
    skill = NO_CODE / block / "SKILL.md"
    if not skill.is_file():
        return
    text = skill.read_text(encoding="utf-8")
    if _TABLE_START not in text or _TABLE_END not in text:
        return
    table = "\n".join(
        [_TABLE_START, "", "| Command | Purpose |", "| --- | --- |"]
        + [f"| [{c}](../reference/{c}.md) | {p} |" for c, p in sorted(rows)]
        + ["", _TABLE_END]
    )
    head, _, rest = text.partition(_TABLE_START)
    _, _, tail = rest.partition(_TABLE_END)
    skill.write_text(head + table + tail, encoding="utf-8", newline="\n")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    repo = Path(argv[1]).resolve()
    docs = repo / "clio" / "docs" / "commands"
    if not docs.is_dir():
        print(f"not a clio repository: {repo}")
        return 1
    version = subprocess.run(
        ["git", "-C", str(repo), "describe", "--tags", "--always"], capture_output=True, text=True
    ).stdout.strip() or "unknown"

    files = sorted(docs.glob("*.md"))
    unmapped = [d.stem for d in files if d.stem not in BLOCK_OF]
    if unmapped:
        print("unmapped commands, add them to BLOCKS:", " ".join(unmapped))
        return 1

    REFERENCE.mkdir(parents=True, exist_ok=True)
    for old in REFERENCE.glob("*.md"):
        old.unlink()
    rows: dict[str, list[tuple[str, str]]] = {b: [] for b in BLOCKS}
    for doc in files:
        block, summary, text = convert(doc, version)
        (REFERENCE / doc.name).write_text(text, encoding="utf-8", newline="\n")
        rows[block].append((doc.stem, summary))
    for block, items in rows.items():
        refresh_skill_table(block, items)
    print(f"{len(files)} command docs from clio {version} -> {REFERENCE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
