"""Calls into a Creatio environment through the clio CLI (its saved environments carry the credentials)."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path


class Clio:
    def __init__(self, env: str):
        if not env:
            raise ValueError("a clio environment name is required")
        self.env = env

    def run(self, args: list[str], cwd: Path | None = None) -> str:
        """Run clio and return its output, raising on a non-zero exit."""
        try:
            result = subprocess.run(["clio", *args], cwd=cwd, capture_output=True, text=True, check=False)
        except OSError as e:
            raise RuntimeError(f"could not run clio: {e}") from e
        output = result.stdout + result.stderr
        if result.returncode:
            raise RuntimeError(f"clio exited {result.returncode}: {output[-500:]}")
        return output

    def call_service(self, path: str, body: dict) -> dict:
        """POST `body` to ServiceModel/... through `clio call-service`; the JSON answer."""
        with tempfile.TemporaryDirectory() as tmp:
            req, out = Path(tmp) / "req.json", Path(tmp) / "out.json"
            req.write_text(json.dumps(body), encoding="utf-8")
            run = subprocess.run(["clio", "call-service", "-e", self.env, "--service-path", path, "-f", str(req), "-d", str(out)],
                                 capture_output=True, text=True, check=False)
            if not out.is_file():
                raise RuntimeError(f"clio call-service wrote no response (environment {self.env!r}?): {run.stdout[-500:]}{run.stderr[-500:]}")
            return json.loads(out.read_text(encoding="utf-8-sig"))

    def sql(self, query: str) -> list[dict]:
        """Rows of a SELECT through `clio execute-sql-script` (the file form keeps quoted identifiers intact)."""
        with tempfile.TemporaryDirectory() as tmp:
            src, out = Path(tmp) / "q.sql", Path(tmp) / "out.json"
            src.write_text(query, encoding="utf-8")
            run = subprocess.run(["clio", "execute-sql-script", "-e", self.env, "-f", str(src), "-v", "json", "-d", str(out)],
                                 capture_output=True, text=True, check=False)
            if run.returncode or "[ERR]" in (run.stdout + run.stderr):
                raise RuntimeError(f"clio execute-sql-script failed: {(run.stdout + run.stderr)[-500:]}")
            if not out.is_file():
                raise RuntimeError(f"clio execute-sql-script wrote no result (environment {self.env!r}?): {run.stdout[-500:]}{run.stderr[-500:]}")
            text = out.read_text(encoding="utf-8-sig").strip()
            return json.loads(text) if text else []

    def execute_sql(self, sql: str) -> None:
        """Execute a SQL script without requiring a result file."""
        output = self.run(["execute-sql-script", sql, "-e", self.env])
        if "[ERR]" in output:
            raise RuntimeError(output[-500:])

    def execute_sql_rows(self, sql: str) -> list[dict]:
        """Return SQL result rows using the file and JSON export form."""
        return self.sql(sql)
