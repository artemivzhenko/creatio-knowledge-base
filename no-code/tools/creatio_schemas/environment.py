"""One Creatio site over HTTP: login, OData, services, processes; SQL through clio.

    env = Environment.from_clio("dev")              # url and credentials from clio's settings file
    env = Environment.from_project("project.json")  # or from the loop's project.json
    env.odata("Contact", select=["Id", "Name"], top=5)
    env.call_service("ServiceModel/UsrOrderService.svc/Recalc", {"orderId": "..."})
    env.run_process("UsrOrder_Process", {"OrderId": "..."}, results=["Total"])
    env.process_log(run["processId"])               # its SysProcessLog row: status, error, start, end (through SQL)
    env.sql('select "Name" from "SysPackage"')

Every request carries `ForceUseSession: true` and the `BPMCSRF` cookie as a header. A non-2xx answer
never raises from get/post/patch/delete - `Response.error` holds the reason in one line (the WCF
HTML fault page reduced to its exception message); the OData, service and process helpers raise
`RuntimeError` with that line. Credentials never appear in an error, a log line or `repr`.
`Clio` (clio.py) stays the way to run package commands.
"""

from __future__ import annotations

import html
import json
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any

AUTH_PATH = "ServiceModel/AuthService.svc/Login"  # at the site root on both platforms, never under 0/
RUN_PROCESS = "ServiceModel/ProcessEngineService.svc/RunProcess"
APP_PATHS = ("odata", "ServiceModel", "rest", "DataService")  # the paths that live under /0/ on .NET Framework


def clio_settings_path() -> Path:
    """clio's appsettings.json: %LOCALAPPDATA%/creatio/clio on Windows, ~/.local/share/creatio/clio elsewhere."""
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
    return Path(base) / "creatio" / "clio" / "appsettings.json"


def _clio_env(name: str, settings: Path | None = None) -> dict:
    path = settings or clio_settings_path()
    if not path.is_file():
        raise FileNotFoundError(f"clio settings not found: {path}")
    envs = json.loads(path.read_text(encoding="utf-8-sig")).get("Environments", {})
    if name not in envs:
        raise KeyError(f"clio has no environment {name!r}; it has {', '.join(sorted(envs)) or 'none'}")
    return envs[name]


def reduce_fault(text: str) -> str:
    """One line out of an error body: a JSON message, the WCF fault page's exception message, its title or first text."""
    try:
        data = json.loads(text)
    except ValueError:
        data = None
    if isinstance(data, dict):
        info = data.get("errorInfo") if isinstance(data.get("errorInfo"), dict) else {}
        for key in ("ExceptionMessage", "exceptionMessage", "Message", "message"):
            if data.get(key):
                return str(data[key]).strip()
        if info.get("message"):
            return str(info["message"]).strip()
        err = data.get("error") if isinstance(data.get("error"), dict) else None
        if err:  # OData: {"error": {"message", "innererror": {"message", "internalexception": {"message", ...}}}}
            messages, node = [], err
            while isinstance(node, dict):
                text = str(node.get("message") or "").strip()
                if text and text not in messages:
                    messages.append(text)
                node = node.get("innererror") or node.get("internalexception")
            if messages:
                return " <- ".join(messages)
    m = re.search(r"The exception message is '(.+?)'\.", text, re.S)
    if m:
        return " ".join(html.unescape(m.group(1)).split())
    m = re.search(r"<title>(.*?)</title>", text, re.S | re.I)
    if m and m.group(1).strip():
        return " ".join(html.unescape(m.group(1)).split())
    plain = html.unescape(re.sub(r"<[^>]+>", " ", text))
    first = next((" ".join(line.split()) for line in plain.splitlines() if line.strip()), "")[:500]
    return re.sub(r"\\u[0-9a-fA-F]{0,3}$", "", first)  # never cut inside a JSON escape


def unwrap_xml_string(text: str) -> str:
    """`<string xmlns="...">{json}</string>` (a WCF answer of type string) -> `{json}`; anything else unchanged."""
    m = re.fullmatch(r"\s*<string[^>]*>(.*)</string>\s*", text, re.S)
    return html.unescape(m.group(1)) if m else text


class Response:
    def __init__(self, status: int, text: str):
        self.status, self.text = status, text
        self.error = None if 200 <= status < 300 else f"{status}: {reduce_fault(text) or 'no body'}"

    @property
    def ok(self) -> bool:
        return self.error is None

    def json(self) -> Any | None:
        try:
            return json.loads(unwrap_xml_string(self.text)) if self.text.strip() else None
        except ValueError:
            return None

    def __repr__(self) -> str:
        return f"Response({self.status}, {len(self.text)} chars)"


def split_statements(text: str) -> list[str]:
    """Statements separated by a `;` at a line end; each runs alone."""
    parts = re.split(r";[ \t]*(?:\r?\n|$)", text)
    return [p.strip() for p in parts if p.strip() and not all(l.strip().startswith("--") for l in p.strip().splitlines())]


def _run_clio(args: list[str]) -> tuple[int, str]:
    try:
        r = subprocess.run(["clio", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    except OSError as e:
        raise RuntimeError(f"could not run clio: {e}") from e
    return r.returncode, r.stdout + r.stderr


class Environment:
    """One Creatio site. `opener` (urllib-style `.open(request, timeout=)`) and `clio_run` are for tests."""

    def __init__(self, url: str, login: str, password: str, net_core: bool = False, clio_name: str | None = None,
                 opener=None, clio_run=None, timeout: int = 120):
        if not url:
            raise ValueError("an environment url is required")
        self.url = url.rstrip("/") + "/"
        self.login_name, self._password = login, password
        self.net_core, self.clio_name, self.timeout = net_core, clio_name, timeout
        self._opener = opener or urllib.request.build_opener()
        self._clio_run = clio_run or _run_clio
        self._cookies: dict[str, str] = {}
        self._logged_in = False

    def __repr__(self) -> str:
        return f"Environment({self.url!r}, login={self.login_name!r})"

    @classmethod
    def from_clio(cls, name: str, settings: Path | None = None, **kw) -> "Environment":
        e = _clio_env(name, settings)
        return cls(e.get("Uri", ""), e.get("Login", ""), e.get("Password", ""), bool(e.get("IsNetCore")), name, **kw)

    @classmethod
    def from_project(cls, path: Path | str, settings: Path | None = None, **kw) -> "Environment":
        e = json.loads(Path(path).read_text(encoding="utf-8-sig")).get("environment", {})
        net_core = e.get("isNetCore")
        if net_core is None and e.get("clioName"):
            try:
                net_core = bool(_clio_env(e["clioName"], settings).get("IsNetCore"))
            except (FileNotFoundError, KeyError):
                net_core = False
        return cls(e.get("url", ""), e.get("login", ""), e.get("password", ""), bool(net_core), e.get("clioName"), **kw)

    # -- HTTP ------------------------------------------------------------------ #

    def _path(self, path: str) -> str:
        """Site-relative; `0/` added (Framework) or dropped (.NET Core) for the application paths."""
        path = path.lstrip("/")
        bare = path[2:] if path.startswith("0/") else path
        if bare.split("/", 1)[0] in APP_PATHS:
            return bare if self.net_core else "0/" + bare
        return path

    def _send(self, method: str, path: str, body: Any = None, params: dict | None = None, literal: bool = False) -> Response:
        # a path typed by hand may hold spaces (`$filter=Name eq 'x'`); what is already percent-encoded stays as it is
        where = urllib.parse.quote(path if literal else self._path(path), safe="/?=&$'(),:;@+%#!*")
        url = self.url + where + ("?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote) if params else "")
        data = None if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode("utf-8"))
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json; charset=utf-8")
        req.add_header("Accept", "application/json")
        req.add_header("ForceUseSession", "true")
        if self._cookies:
            req.add_header("Cookie", "; ".join(f"{k}={v}" for k, v in self._cookies.items()))
        if "BPMCSRF" in self._cookies:
            req.add_header("BPMCSRF", self._cookies["BPMCSRF"])
        try:
            resp = self._opener.open(req, timeout=self.timeout)
            status = getattr(resp, "status", None) or resp.getcode()
        except urllib.error.HTTPError as e:
            resp, status = e, e.code
        except urllib.error.URLError as e:
            raise RuntimeError(f"{method} {self._path(path)}: {e.reason}") from None
        for header in (resp.headers.get_all("Set-Cookie") or []) if resp.headers else []:
            jar = SimpleCookie()
            jar.load(header)
            self._cookies.update({k: m.value for k, m in jar.items()})
        raw = resp.read() or b""
        return Response(status, raw.decode("utf-8-sig", errors="replace"))

    def login(self) -> None:
        """AuthService.svc/Login once; the session cookies and BPMCSRF are kept for every later call."""
        if self._logged_in:
            return
        r = self._send("POST", AUTH_PATH, {"UserName": self.login_name, "UserPassword": self._password}, literal=True)
        answer = r.json() if r.ok else None
        if not isinstance(answer, dict) or answer.get("Code") != 0:
            reason = r.error or (answer or {}).get("Message") or "unexpected answer"
            raise RuntimeError(f"login to {self.url} as {self.login_name!r} refused: {reason}")
        self._logged_in = True

    def request(self, method: str, path: str, body: Any = None, params: dict | None = None) -> Response:
        self.login()
        return self._send(method, path, body, params)

    def get(self, path: str, params: dict | None = None) -> Response:
        return self.request("GET", path, params=params)

    def post(self, path: str, body: Any = None) -> Response:
        return self.request("POST", path, {} if body is None else body)

    def patch(self, path: str, body: Any) -> Response:
        return self.request("PATCH", path, body)

    def delete(self, path: str) -> Response:
        return self.request("DELETE", path)

    @staticmethod
    def _need(r: Response, what: str) -> Response:
        if not r.ok:
            raise RuntimeError(f"{what}: {r.error}")
        return r

    # -- OData 4 ---------------------------------------------------------------- #

    def odata(self, entity: str, select=None, filter: str | None = None, top: int | None = None, orderby: str | None = None,
              skip: int | None = None, expand: str | None = None) -> list[dict]:
        params = {k: v for k, v in (("$select", ",".join(select) if select else None), ("$filter", filter),
                                    ("$top", None if top is None else str(top)), ("$orderby", orderby),
                                    ("$skip", None if skip is None else str(skip)), ("$expand", expand)) if v}
        return (self._need(self.get(f"odata/{entity}", params or None), f"odata {entity}").json() or {}).get("value", [])

    def odata_insert(self, entity: str, values: dict) -> str:
        answer = self._need(self.post(f"odata/{entity}", values), f"insert {entity}").json() or {}
        return str(answer.get("Id", ""))

    def odata_update(self, entity: str, id: str, values: dict) -> None:
        self._need(self.patch(f"odata/{entity}({id})", values), f"update {entity}({id})")

    def odata_delete(self, entity: str, id: str) -> None:
        self._need(self.delete(f"odata/{entity}({id})"), f"delete {entity}({id})")

    # -- services and processes --------------------------------------------------- #

    def call_service(self, path: str, body: Any = None, method: str = "POST") -> Response:
        """ServiceModel/<Svc>.svc/<Method> or rest/<Svc>/<Method>; the Response, not raised on non-2xx."""
        return self.request(method.upper(), path, ({} if body is None else body) if method.upper() != "GET" else None)

    def run_process(self, name: str, params: dict | None = None, results: list[str] | None = None) -> dict:
        """ProcessEngineService.svc/RunProcess -> {process, processId, success, error, results}."""
        body = {"schemaName": name, "parameterValues": [{"name": k, "value": v} for k, v in (params or {}).items()],
                "resultParameterNames": list(results or [])}
        answer = self._need(self.post(RUN_PROCESS, body), f"run {name}").json()
        if not isinstance(answer, dict):
            raise RuntimeError(f"run {name}: the engine's answer is not JSON")
        info = answer.get("errorInfo") if isinstance(answer.get("errorInfo"), dict) else {}
        return {"process": name, "processId": answer.get("processId", ""), "success": answer.get("success") is True,
                "error": None if answer.get("success") is True else (info.get("message") or json.dumps(info) if info else "not started"),
                "results": answer.get("resultParameterValues") or {}}

    def process_log(self, process_id: str, zone: str | None = None) -> dict | None:
        """The `SysProcessLog` row of a run (`processId` of `run_process`): {status, state, error, start, end, ...} or None."""
        from .runs import process_log
        return process_log(self, process_id, zone)

    # -- SQL through clio ------------------------------------------------------------ #

    def _need_clio(self) -> str:
        if not self.clio_name:
            raise ValueError("SQL runs through clio: the environment needs its clio name (from_clio, or project.json clioName)")
        return self.clio_name

    def sql(self, text: str) -> list[dict]:
        """Rows of every statement, one clio call each (the file form keeps quotes intact); `[ERR]` raises."""
        name, rows = self._need_clio(), []
        for statement in split_statements(text):
            with tempfile.TemporaryDirectory() as tmp:
                src, out = Path(tmp) / "q.sql", Path(tmp) / "out.json"
                src.write_text(statement, encoding="utf-8")
                code, output = self._clio_run(["execute-sql-script", "-e", name, "-f", str(src), "-v", "json", "-d", str(out)])
                if sql_failed(code, output):
                    raise RuntimeError(f"sql: {err_line(output)}")
                result = out.read_text(encoding="utf-8-sig").strip() if out.is_file() else ""
            parsed = json.loads(result) if result else []
            rows.extend(parsed if isinstance(parsed, list) else [])  # an update: clio writes the affected row count
        return rows

    def sql_exec(self, text: str) -> None:
        """A statement without a result (update, insert); `[ERR]` in clio's output raises."""
        code, output = self._clio_run(["execute-sql-script", text, "-e", self._need_clio()])
        if sql_failed(code, output):
            raise RuntimeError(f"sql: {err_line(output)}")


# a database error as some clio builds print it: the SQLSTATE and the message, then `Done` and exit 0 - no `[ERR]`
_SQLSTATE_RE = re.compile(r"^[0-9A-Z]{5}: \S")


def _is_error(line: str) -> bool:
    return "[ERR]" in line or bool(_SQLSTATE_RE.match(line.strip()))


def sql_failed(code: int, output: str) -> bool:
    return bool(code) or any(_is_error(l) for l in output.splitlines())


def err_line(output: str) -> str:
    lines = [l.strip() for l in output.splitlines() if l.strip()]
    return next((l for l in lines if _is_error(l)), lines[-1] if lines else "clio failed")[:500]


def open_environment(env: str | None = None, project: str | None = None, **kw) -> Environment:
    """The CLIs' `-e <clio name>` or `--project <project.json>`."""
    if project:
        return Environment.from_project(project, **kw)
    if env:
        return Environment.from_clio(env, **kw)
    raise ValueError("name the environment: -e <clio environment> or --project <project.json>")
