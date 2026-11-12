"""Checks for the environment layer:  python tests/test_env_tools.py  (a fake HTTP opener and a fake clio; no environment)."""

import contextlib
import email.message
import importlib.util
import io
import json
import sys
import tempfile
import urllib.error
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent.parent
sys.path.insert(0, str(TOOLS))

from creatio_schemas.environment import Environment, Response, reduce_fault, split_statements, unwrap_xml_string  # noqa: E402

SECRET = "pa55-secret"
WCF_FAULT = ("<html><head><title>Request Error</title></head><body><p>The server encountered an error processing the request. "
             "The exception message is 'Object reference not set to an instance of an object &amp; more'. See server logs.</p></body></html>")


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), HERE.parent / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeResponse:
    def __init__(self, status, body, cookies=()):
        self.status, self._body = status, body.encode("utf-8") if isinstance(body, str) else body
        self.headers = email.message.Message()
        for c in cookies:
            self.headers["Set-Cookie"] = c

    def read(self):
        return self._body


class FakeOpener:
    """Answers by (method, path); `routes` values are (status, body) or a callable(request) -> (status, body)."""

    LOGIN_OK = (200, json.dumps({"Code": 0, "Message": ""}))

    def __init__(self, routes=None, login=LOGIN_OK):
        self.routes = {("POST", "/ServiceModel/AuthService.svc/Login"): login, **(routes or {})}
        self.requests = []

    def open(self, req, timeout=None):
        url = urllib.parse.urlsplit(req.full_url)
        self.requests.append({"method": req.get_method(), "path": url.path, "query": url.query, "headers": dict(req.header_items()),
                              "body": json.loads(req.data) if req.data else None})
        answer = self.routes.get((req.get_method(), url.path), (404, "<html><title>Not Found</title></html>"))
        status, body = answer(req) if callable(answer) else answer
        cookies = ("BPMCSRF=csrf123; path=/", ".ASPXAUTH=auth456; path=/; HttpOnly") if url.path.endswith("AuthService.svc/Login") else ()
        if status >= 400:
            raise urllib.error.HTTPError(req.full_url, status, "error", FakeResponse(status, "", cookies).headers, io.BytesIO(body.encode("utf-8")))
        return FakeResponse(status, body, cookies)


def env(routes=None, **kw):
    opener = FakeOpener(routes, **{k: kw.pop(k) for k in ("login",) if k in kw})
    return Environment("https://site.example/", "Supervisor", SECRET, opener=opener, **kw), opener


def raises(fn, kind, text=""):
    try:
        fn()
    except kind as e:
        assert text in str(e), (text, str(e))
        return str(e)
    raise AssertionError(f"expected {kind.__name__}")


class FakeClio:
    """`clio_run`: records the args; writes `rows[i]` to the -d file of call i; `output` is clio's text."""

    def __init__(self, rows=(), output="Done"):
        self.rows, self.output, self.calls, self.scripts = list(rows), output, [], []

    def __call__(self, args):
        self.calls.append(args)
        if "-f" in args:
            self.scripts.append(Path(args[args.index("-f") + 1]).read_text(encoding="utf-8"))
        if "-d" in args and self.rows:
            rows = self.rows.pop(0)
            if rows is not None:
                Path(args[args.index("-d") + 1]).write_text(json.dumps(rows), encoding="utf-8")
        return 0, self.output


def test_login_once_and_csrf_echo():
    e, opener = env({("GET", "/0/odata/Contact"): (200, json.dumps({"value": [{"Id": "1"}]}))})
    assert e.odata("Contact") == [{"Id": "1"}] and e.odata("Contact") == [{"Id": "1"}]
    paths = [r["path"] for r in opener.requests]
    assert paths == ["/ServiceModel/AuthService.svc/Login", "/0/odata/Contact", "/0/odata/Contact"], paths  # login once
    assert opener.requests[0]["body"] == {"UserName": "Supervisor", "UserPassword": SECRET}
    h = opener.requests[1]["headers"]
    assert h["Bpmcsrf"] == "csrf123" and h["Forceusesession"] == "true" and "BPMCSRF=csrf123" in h["Cookie"] and ".ASPXAUTH=auth456" in h["Cookie"]
    assert SECRET not in repr(e)


def test_login_refused_hides_the_password():
    e, _ = env(login=(200, json.dumps({"Code": 1, "Message": "Invalid user name or password"})))
    msg = raises(lambda: e.get("odata/Contact"), RuntimeError, "Invalid user name or password")
    assert SECRET not in msg
    e, _ = env(login=(500, WCF_FAULT))
    msg = raises(e.login, RuntimeError, "500: Object reference")
    assert SECRET not in msg


def test_odata_crud_and_paths():
    def insert(req):
        return 201, json.dumps({"Id": "new-id", **json.loads(req.data)})
    e, opener = env({("GET", "/0/odata/Contact"): (200, json.dumps({"value": [{"Name": "A"}]})),
                     ("POST", "/0/odata/Contact"): insert,
                     ("PATCH", "/0/odata/Contact(new-id)"): (204, ""),
                     ("DELETE", "/0/odata/Contact(new-id)"): (204, "")})
    assert e.odata("Contact", select=["Id", "Name"], filter="Name eq 'A b'", top=2, orderby="Name") == [{"Name": "A"}]
    q = urllib.parse.parse_qs(opener.requests[-1]["query"])
    assert q == {"$select": ["Id,Name"], "$filter": ["Name eq 'A b'"], "$top": ["2"], "$orderby": ["Name"]}, q
    e.odata("Contact", ["Id", "AccountId"], top=500, orderby="Id", skip=500, expand="Account($select=Name)")
    q = urllib.parse.parse_qs(opener.requests[-1]["query"])
    assert q["$skip"] == ["500"] and q["$expand"] == ["Account($select=Name)"], q
    assert e.odata_insert("Contact", {"Name": "B"}) == "new-id" and opener.requests[-1]["body"] == {"Name": "B"}
    e.odata_update("Contact", "new-id", {"Name": "C"})
    assert opener.requests[-1]["method"] == "PATCH" and opener.requests[-1]["body"] == {"Name": "C"}
    e.odata_delete("Contact", "new-id")
    raises(lambda: e.odata_update("Contact", "missing", {}), RuntimeError, "update Contact(missing): 404: Not Found")
    # the application paths: 0/ added on Framework, dropped on .NET Core; other paths as given
    core = Environment("https://core.example", "u", "p", net_core=True)
    assert [e._path(p) for p in ("odata/X", "0/rest/S/M", "ServiceModel/A.svc/B", "/Shell/#Section")] == \
        ["0/odata/X", "0/rest/S/M", "0/ServiceModel/A.svc/B", "Shell/#Section"]
    assert [core._path(p) for p in ("odata/X", "0/rest/S/M", "0/Nui/ViewModule.aspx")] == ["odata/X", "rest/S/M", "0/Nui/ViewModule.aspx"]
    raises(lambda: Environment("", "u", "p"), ValueError, "url")


def test_fault_reduction_and_response():
    assert reduce_fault(WCF_FAULT) == "Object reference not set to an instance of an object & more"
    assert reduce_fault(json.dumps({"Message": "Bad thing"})) == "Bad thing"
    assert reduce_fault(json.dumps({"ExceptionMessage": "Inner"})) == "Inner"
    assert reduce_fault(json.dumps({"success": False, "errorInfo": {"message": "Process not found"}})) == "Process not found"
    assert reduce_fault("<html><title>Service Unavailable</title></html>") == "Service Unavailable"
    assert reduce_fault("<html><body><h1>Oops</h1>\n<p>more</p></body></html>") == "Oops"  # the first line of text
    assert reduce_fault("") == ""
    r = Response(500, WCF_FAULT)
    assert not r.ok and r.error.startswith("500: Object reference") and r.json() is None
    assert Response(400, "").error == "400: no body" and Response(204, "").json() is None
    wrapped = '<string xmlns="http://schemas.microsoft.com/2003/10/Serialization/">{&quot;a&quot;: 1}</string>'
    assert unwrap_xml_string(wrapped) == '{"a": 1}' and Response(200, wrapped).json() == {"a": 1} and Response(200, "plain").json() is None
    e, _ = env({("POST", "/0/rest/UsrSvc/Do"): (500, WCF_FAULT)})
    r = e.call_service("rest/UsrSvc/Do", {"x": 1})  # non-2xx never raises by itself
    assert r.status == 500 and "Object reference" in r.error
    e, _ = env()
    e._opener.open = lambda req, timeout=None: (_ for _ in ()).throw(urllib.error.URLError("no route"))
    e._logged_in = True
    raises(lambda: e.get("odata/X"), RuntimeError, "no route")


def test_run_process():
    def engine(req):
        body = json.loads(req.data)
        if body["schemaName"] == "UsrMissing":
            return 200, json.dumps({"success": False, "processId": "", "errorInfo": {"message": "Schema not found"}})
        return 200, json.dumps({"success": True, "processId": "p-1", "resultParameterValues": {"Total": 42}})
    e, opener = env({("POST", "/0/ServiceModel/ProcessEngineService.svc/RunProcess"): engine})
    run = e.run_process("UsrOrder_Process", {"OrderId": "o-1", "Qty": 3}, ["Total"])
    assert opener.requests[-1]["body"] == {"schemaName": "UsrOrder_Process", "parameterValues": [{"name": "OrderId", "value": "o-1"},
                                           {"name": "Qty", "value": 3}], "resultParameterNames": ["Total"]}
    assert run == {"process": "UsrOrder_Process", "processId": "p-1", "success": True, "error": None, "results": {"Total": 42}}
    failed = e.run_process("UsrMissing")
    assert failed["success"] is False and failed["error"] == "Schema not found"
    e, _ = env({("POST", "/0/ServiceModel/ProcessEngineService.svc/RunProcess"): (200, "not json")})
    raises(lambda: e.run_process("UsrX"), RuntimeError, "not JSON")


def test_sql_rows_keep_a_raw_newline_inside_a_value():
    class RawClio(FakeClio):  # clio writes a multi-line value (an error text) with the newline raw; json's strict mode refuses it
        def __call__(self, args):
            self.calls.append(args)
            Path(args[args.index("-d") + 1]).write_text('[{"ErrorDescription": "line one\nline two"}]', encoding="utf-8")
            return 0, "Done"
    e = Environment("https://s", "u", "p", clio_name="dev", clio_run=RawClio())
    assert e.sql("select 1")[0]["ErrorDescription"] == "line one\nline two"


def test_sql_splitting_and_rows():
    assert split_statements("select 1;\nselect ';' as x ;  \r\n-- a comment only\n;\nupdate t set a = 1") == ["select 1", "select ';' as x", "update t set a = 1"]
    clio = FakeClio(rows=[[{"Name": "A"}], [{"Name": "B"}, {"Name": "C"}]])
    e = Environment("https://s", "u", "p", clio_name="dev", clio_run=clio)
    assert e.sql('select "Name" from "SysPackage" where "Name" = \'A\';\nselect 2') == [{"Name": "A"}, {"Name": "B"}, {"Name": "C"}]
    assert clio.scripts == ['select "Name" from "SysPackage" where "Name" = \'A\'', "select 2"]  # the file form: quotes intact, one statement per call
    assert all(c[:3] == ["execute-sql-script", "-e", "dev"] and "-v" in c and c[c.index("-v") + 1] == "json" for c in clio.calls)
    assert Environment("https://s", "u", "p", clio_name="dev", clio_run=FakeClio(rows=[None])).sql("update t set a=1") == []  # no result file
    bad = FakeClio(output="[ERR] - column \"Nme\" does not exist\nDone")
    raises(lambda: Environment("https://s", "u", "p", clio_name="dev", clio_run=bad).sql("select Nme"), RuntimeError, 'column "Nme" does not exist')
    e = Environment("https://s", "u", "p", clio_name="dev", clio_run=FakeClio())
    e.sql_exec('update "SysSchema" set "IsChanged"=false')
    raises(lambda: Environment("https://s", "u", "p", clio_name="dev", clio_run=bad).sql_exec("x"), RuntimeError, "[ERR]")
    raises(lambda: Environment("https://s", "u", "p").sql("select 1"), ValueError, "clio name")


def settings_file(tmp: Path) -> Path:
    path = tmp / "appsettings.json"
    path.write_text(json.dumps({"Environments": {"dev": {"Uri": "https://dev.example", "Login": "Supervisor", "Password": SECRET, "IsNetCore": True}}}),
                    encoding="utf-8")
    return path


def test_from_clio_and_from_project():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        s = settings_file(tmp)
        e = Environment.from_clio("dev", settings=s)
        assert (e.url, e.login_name, e.net_core, e.clio_name) == ("https://dev.example/", "Supervisor", True, "dev")
        raises(lambda: Environment.from_clio("prod", settings=s), KeyError, "it has dev")
        raises(lambda: Environment.from_clio("dev", settings=tmp / "none.json"), FileNotFoundError)
        project = tmp / "project.json"
        project.write_text(json.dumps({"environment": {"clioName": "dev", "url": "https://p.example", "login": "U", "password": "x"}}), encoding="utf-8")
        p = Environment.from_project(project, settings=s)
        assert (p.url, p.net_core, p.clio_name) == ("https://p.example/", True, "dev")  # IsNetCore taken from clio when project.json omits it
        project.write_text(json.dumps({"environment": {"clioName": "other", "url": "https://p.example", "isNetCore": False}}), encoding="utf-8")
        assert Environment.from_project(project, settings=s).net_core is False
        project.write_text(json.dumps({"environment": {"clioName": "other", "url": "https://p.example"}}), encoding="utf-8")
        assert Environment.from_project(project, settings=s).net_core is False  # unknown to clio: Framework


def run_cli(name, argv, **env_kw):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = load(name).main(argv, **env_kw)
    return code, out.getvalue()


def test_sql_cli():
    with tempfile.TemporaryDirectory() as tmp:
        s = settings_file(Path(tmp))
        code, out = run_cli("sql", ["-e", "dev", "select 1;\nupdate t set a=1"], settings=s, clio_run=FakeClio(rows=[[{"A": "Ж", "B": None}], None]))
        assert code == 0 and '"A": "Ж"' in out and "(no rows)" in out and "-- statement 2: update t set a=1" in out, out
        q = Path(tmp) / "q.sql"
        q.write_text("select 1", encoding="utf-8")
        code, out = run_cli("sql", ["-e", "dev", "--file", str(q), "--csv"], settings=s, clio_run=FakeClio(rows=[[{"A": 1, "B": None}, {"A": 2, "C": "x"}]]))
        assert code == 0 and out == "A,B,C\n1,,\n2,,x\n", repr(out)
        code, out = run_cli("sql", ["-e", "dev", "select x"], settings=s, clio_run=FakeClio(output="[ERR] - bad"))
        assert code == 1 and "[ERR] - bad" in out
        assert run_cli("sql", ["select 1"], settings=s)[0] == 2 and run_cli("sql", ["-e", "dev"], settings=s)[0] == 2


def test_call_and_proc_run_cli():
    with tempfile.TemporaryDirectory() as tmp:
        s = settings_file(Path(tmp))
        opener = FakeOpener({("POST", "/rest/UsrSvc/Do"): (200, json.dumps({"total": 3})),
                             ("POST", "/rest/UsrSvc/Fail"): (500, WCF_FAULT),
                             ("GET", "/odata/Contact"): lambda req: (200, json.dumps({"q": urllib.parse.urlsplit(req.full_url).query})),
                             ("POST", "/ServiceModel/ProcessEngineService.svc/RunProcess"): lambda req: (200, json.dumps(
                                 {"success": json.loads(req.data)["schemaName"] != "UsrBad", "processId": "p", "errorInfo": {"message": "boom"},
                                  "resultParameterValues": {"Total": json.loads(req.data)["parameterValues"][0]["value"]}}))})
        code, out = run_cli("call", ["-e", "dev", "POST", "0/rest/UsrSvc/Do", '{"id": 1}'], settings=s, opener=opener)  # .NET Core: 0/ dropped
        assert code == 0 and "status: 200" in out and '"total": 3' in out and opener.requests[-1]["body"] == {"id": 1}, out
        code, out = run_cli("call", ["-e", "dev", "POST", "rest/UsrSvc/Fail"], settings=s, opener=opener)
        assert code == 1 and "error: 500: Object reference" in out
        code, out = run_cli("call", ["-e", "dev", "get", "odata/Contact?$top=1"], settings=s, opener=opener)
        assert code == 0 and "%24top=1" in out, out
        assert run_cli("call", ["-e", "dev", "POST", "rest/X", "{bad json"], settings=s, opener=opener)[0] == 2
        done = [[{"Id": "p", "Name": "Order", "Status": "Completed", "ErrorDescription": None, "StartDate": "2026-11-11T08:00:00",
                  "CompleteDate": "2026-11-11T08:00:02", "Process": "UsrOrder_Process"}]]
        clio = FakeClio(rows=done)
        code, out = run_cli("proc-run", ["-e", "dev", "UsrOrder_Process", "Qty=3", "--result", "Total"], settings=s, opener=opener, clio_run=clio)
        assert code == 0 and "UsrOrder_Process: ok" in out and "Total = 3" in out, out  # 3 sent as a number
        assert "log: not read - 'p' is not an Id (a guid)" in out and clio.calls == [], out  # a non-guid id never reaches SQL
        pid = "aaaaaaaa-0000-0000-0000-000000000002"
        done[0][0]["Id"] = pid
        engine = FakeOpener({("POST", "/ServiceModel/ProcessEngineService.svc/RunProcess"): (200, json.dumps({"success": True, "processId": pid}))})
        code, out = run_cli("proc-run", ["-e", "dev", "UsrOrder_Process"], settings=s, opener=engine, clio_run=FakeClio(rows=done))
        assert code == 0 and "log: Completed (completed)  started 2026-11-11 08:00:00 UTC" in out and "ended 2026-11-11 08:00:02 UTC" in out, out
        code, out = run_cli("proc-run", ["-e", "dev", "UsrBad", "Name=abc"], settings=s, opener=opener, clio_run=FakeClio(rows=done))
        assert code == 1 and "FAILED boom" in out
        assert run_cli("proc-run", ["-e", "dev", "UsrX", "novalue"], settings=s, opener=opener)[0] == 2


def test_unit_runner():
    unit = load("unit")
    xml = '<string xmlns="x">' + json.dumps({"Tests": [{"Name": "T1", "Success": True}, {"Name": "T2", "Success": False, "Message": "expected 3"}]}).replace('"', "&quot;") + "</string>"
    assert unit.rows_of(xml) == [{"name": "T1", "passed": True, "message": ""}, {"name": "T2", "passed": False, "message": "expected 3"}]
    assert unit.rows_of([{"test": "A", "status": "Passed"}, {"test": "B", "outcome": "Failed", "error": "x"}, {"Name": "C", "passed": "true"}]) == [
        {"name": "A", "passed": True, "message": ""}, {"name": "B", "passed": False, "message": "x"}, {"name": "C", "passed": True, "message": ""}]
    assert unit.rows_of({"count": 0}) is None and unit.rows_of("not json") is None and unit.rows_of([{"x": 1}])[0] == {"name": "?", "passed": False, "message": ""}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        s = settings_file(tmp)
        project = tmp / "project.json"
        project.write_text(json.dumps({"environment": {"clioName": "dev", "url": "https://p.example", "login": "U", "password": "x"},
                                       "tests": {"runner": "UsrRunTests_Process", "categoryParameter": "Category"}}), encoding="utf-8")
        opener = FakeOpener({("POST", "/ServiceModel/ProcessEngineService.svc/RunProcess"): (200, json.dumps(
                                 {"success": True, "processId": "p", "resultParameterValues": {"Result": xml}})),
                             ("POST", "/rest/UsrTests/Run"): (200, json.dumps([{"Name": "S1", "Success": True}])),
                             ("POST", "/rest/UsrTests/Odd"): (200, json.dumps({"total": 1}))})
        evidence = tmp / "result.json"
        code, out = run_cli("unit", ["run", "--project", str(project), "--category", "UsrOrders", "--evidence", str(evidence)], settings=s, opener=opener)
        assert code == 1 and out.splitlines()[:3] == ["FAIL  T2  - expected 3", "ok    T1", "1 passed, 1 failed"], out  # failures first
        assert opener.requests[-1]["body"]["parameterValues"] == [{"name": "Category", "value": "UsrOrders"}]
        assert json.loads(evidence.read_text(encoding="utf-8")) == xml  # the whole answer
        code, out = run_cli("unit", ["run", "-e", "dev", "--runner", "rest/UsrTests/Run", "--class", "UsrOrderTest"], settings=s, opener=opener)
        assert code == 0 and "1 passed, 0 failed" in out and opener.requests[-1]["body"] == {"Class": "UsrOrderTest"}, out
        code, out = run_cli("unit", ["run", "-e", "dev", "--runner", "rest/UsrTests/Odd", "--category", "X"], settings=s, opener=opener)
        assert code == 2 and "no list of tests" in out
        code, out = run_cli("unit", ["run", "-e", "dev", "--category", "X"], settings=s, opener=opener)
        assert code == 2 and "no in-Creatio test runner configured" in out
        code, out = run_cli("unit", ["run", "-e", "dev", "--runner", "rest/UsrTests/Missing", "--category", "X"], settings=s, opener=opener)
        assert code == 2 and "404" in out


def test_api_listing():
    api = load("api")
    output = ("TYPE\tTerrasoft.Core.DB.Select\tTerrasoft.Core.dll\tTerrasoft.Core.DB.Query\r\n"
              "M\tmethod\tColumn\tSelect (String sourceColumnAlias)\r\nM\tctor\tSelect\tUserConnection userConnection\r\n"
              "M\tproperty\tColumns\tQueryColumnExpressionCollection\r\nM\tmethod\tColumn\tSelect (IQueryColumnExpressionConvertible expression)\r\nnoise\n")
    lines, types = api.format_members(output)
    assert types == 1 and lines == ["Terrasoft.Core.DB.Select  (Terrasoft.Core.dll; base Terrasoft.Core.DB.Query)",
                                    "  ctor     Select(UserConnection userConnection)",
                                    "  method   Column  Select (IQueryColumnExpressionConvertible expression)",
                                    "  method   Column  Select (String sourceColumnAlias)",
                                    "  property Columns  QueryColumnExpressionCollection"], lines
    seen = {}

    def runner(bin_dir, type_name, member):
        seen.update(bin=bin_dir, type=type_name, member=member)
        return output if type_name == "Select" else ""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        assert api.main(["Select", "Col", "--bin", str(HERE)], runner=runner) == 0
        assert api.main(["Nope", "--bin", str(HERE)], runner=runner) == 1
        assert api.main(["Select", "--bin", str(HERE / "missing")], runner=runner) == 2
    assert seen == {"bin": str(HERE), "type": "Nope", "member": ""} and "no public type 'Nope'" in out.getvalue()


def test_sqlstate_errors_odata_faults_and_spaces_in_paths():
    # some clio builds print the SQLSTATE and the message, then Done, exit 0 - no [ERR]: still an error, never "no rows"
    bad = FakeClio(output='42703: column "NoSuch" does not exist\nDone')
    raises(lambda: Environment("https://s", "u", "p", clio_name="dev", clio_run=bad).sql('select "NoSuch" from "SysSchema"'), RuntimeError, '42703: column "NoSuch" does not exist')
    raises(lambda: Environment("https://s", "u", "p", clio_name="dev", clio_run=bad).sql_exec("update x set a = 1"), RuntimeError, "42703")
    assert Environment("https://s", "u", "p", clio_name="dev", clio_run=FakeClio(rows=[[{"n": 1}]], output="Done\n")).sql("select 1") == [{"n": 1}]
    assert Environment("https://s", "u", "p", clio_name="dev", clio_run=FakeClio(rows=[5], output="Done")).sql("update x set a = 1") == []  # an update: clio writes the row count
    # an OData fault: the message chain, decoded (no \u escape cut in the middle)
    odata = json.dumps({"error": {"code": "", "message": "An error has occurred.", "innererror": {
        "message": "Column лон is not found", "type": "X", "internalexception": {"message": "deeper", "type": "Y"}}}})
    assert reduce_fault(odata) == "An error has occurred. <- Column лон is not found <- deeper"
    assert not reduce_fault("x" * 496 + "\\u04").endswith("\\u04")
    # a path with spaces, typed by hand, reaches the site percent-encoded; what is encoded already stays
    e, opener = env({("GET", "/0/odata/Contact"): (200, json.dumps({"value": []}))})
    assert e.request("GET", "odata/Contact?$filter=Name eq 'A b'&$top=1").ok
    assert opener.requests[-1]["query"] == "$filter=Name%20eq%20'A%20b'&$top=1", opener.requests[-1]["query"]
    assert e.request("GET", "odata/Contact?$filter=Name%20eq%20'A'").ok and opener.requests[-1]["query"] == "$filter=Name%20eq%20'A'"


def test_process_log_and_proc_run_exit_codes():
    pid = "aaaaaaaa-0000-0000-0000-000000000001"
    route = {("POST", "/ServiceModel/ProcessEngineService.svc/RunProcess"): (200, json.dumps({"success": True, "processId": pid}))}
    row = {"Id": pid, "Name": "Order", "Status": "Error", "ErrorDescription": "Expression expected" + chr(10) + "   at Terrasoft.Core.X()",
           "StartDate": "2026-11-11T08:00:00Z", "CompleteDate": None, "Process": "UsrOrder_Process"}
    clio = FakeClio(rows=[[row]])
    e = Environment("https://s", "u", "p", clio_name="dev", clio_run=clio)
    assert e.process_log(pid, "+03:00") == {"id": pid, "process": "UsrOrder_Process", "status": "Error", "state": "failed", "error": "Expression expected",
                                            "start": "2026-11-11 08:00:00 UTC (11:00 +03:00)", "end": "", "owner": None}
    assert f"where l.\"Id\" = '{pid}'" in clio.scripts[0] and 'left join "SysProcessStatus" st on st."Id" = l."StatusId"' in clio.scripts[0]
    assert Environment("https://s", "u", "p", clio_name="dev", clio_run=FakeClio(rows=[[]])).process_log(pid) is None
    raises(lambda: e.process_log("p'; drop table x"), ValueError, "not an Id")
    with tempfile.TemporaryDirectory() as tmp:
        s = settings_file(Path(tmp))
        code, out = run_cli("proc-run", ["-e", "dev", "UsrOrder_Process"], settings=s, opener=FakeOpener(route), clio_run=FakeClio(rows=[[row]]))
        assert code == 1 and "UsrOrder_Process: ok" in out and "log: Error (failed)" in out and "error: Expression expected" in out, out
        running = dict(row, Status="Running", ErrorDescription=None)
        code, out = run_cli("proc-run", ["-e", "dev", "UsrOrder_Process"], settings=s, opener=FakeOpener(route), clio_run=FakeClio(rows=[[running]]))
        assert code == 1 and "log: Running (running)" in out, out  # not completed: a process waiting on a signal is not done
        code, out = run_cli("proc-run", ["-e", "dev", "UsrOrder_Process"], settings=s, opener=FakeOpener(route), clio_run=FakeClio(rows=[[]]))
        assert code == 0 and f"log: no SysProcessLog row for {pid}" in out, out
        code, out = run_cli("proc-run", ["-e", "dev", "UsrOrder_Process"], settings=s, opener=FakeOpener(route), clio_run=FakeClio(output="[ERR] - denied"))
        assert code == 0 and "log: not read - sql: [ERR] - denied" in out, out
        clio = FakeClio(rows=[[row]])
        code, out = run_cli("proc-run", ["-e", "dev", "UsrOrder_Process", "--no-log"], settings=s, opener=FakeOpener(route), clio_run=clio)
        assert code == 0 and "log:" not in out and clio.calls == []


def test_unit_runner_warns_when_the_test_dll_is_older_than_the_package():
    unit = load("unit")
    stale = FakeClio(rows=[[{"changed": "2026-11-11T09:00:00", "compiled": "2026-11-11T08:00:00"}]])
    e = Environment("https://s", "u", "p", clio_name="dev", clio_run=stale)
    assert unit.stale_dll(e, "UsrTests") == "warning: the test package's dll is older than its last push (UsrTests changed 2026-11-11T09:00:00, compiled 2026-11-11T08:00:00)"
    assert "from \"SysPackage\" p where p.\"Name\" = 'UsrTests'" in stale.scripts[0] and "\"ProjectName\" like '%UsrTests%'" in stale.scripts[0]
    fresh = Environment("https://s", "u", "p", clio_name="dev", clio_run=FakeClio(rows=[[{"changed": "2026-11-11T08:00:00", "compiled": "2026-11-11T08:05:00"}]]))
    assert unit.stale_dll(fresh, "UsrTests") is None
    never = Environment("https://s", "u", "p", clio_name="dev", clio_run=FakeClio(rows=[[{"changed": "2026-11-11T08:00:00", "compiled": None}]]))
    assert "no successful compilation of UsrTests" in unit.stale_dll(never, "UsrTests")
    assert unit.stale_dll(Environment("https://s", "u", "p", clio_name="dev", clio_run=FakeClio(rows=[[]])), "UsrTests") == "warning: no package UsrTests on the site"
    # MS SQL has no boolean literal: the bit form is tried after the first statement fails
    class Bits(FakeClio):
        def __call__(self, args):
            text = Path(args[args.index("-f") + 1]).read_text(encoding="utf-8")
            if '"Result" = true' in text:
                return 0, "[ERR] - Invalid column name 'true'"
            return super().__call__(args)
    bits = Bits(rows=[[{"changed": "2026-11-11T08:00:00", "compiled": "2026-11-11T08:05:00"}]])
    assert unit.stale_dll(Environment("https://s", "u", "p", clio_name="dev", clio_run=bits), "UsrTests") is None and '"Result" = 1' in bits.scripts[-1]
    raises(lambda: unit.stale_dll(e, "Usr'Tests"), ValueError, "not a table or column name")
    with tempfile.TemporaryDirectory() as tmp:
        s = settings_file(Path(tmp))
        opener = FakeOpener({("POST", "/rest/UsrTests/Run"): (200, json.dumps([{"Name": "S1", "Success": True}]))})
        clio = FakeClio(rows=[[{"changed": "2026-11-11T09:00:00", "compiled": "2026-11-11T08:00:00"}]])
        code, out = run_cli("unit", ["run", "-e", "dev", "--runner", "rest/UsrTests/Run", "--class", "UsrOrderTest", "--package", "UsrTests"],
                            settings=s, opener=opener, clio_run=clio)
        assert code == 0 and out.splitlines() == ["ok    S1", "1 passed, 0 failed", "warning: the test package's dll is older than its last push "
                                                  "(UsrTests changed 2026-11-11T09:00:00, compiled 2026-11-11T08:00:00)"], out
        code, out = run_cli("unit", ["run", "-e", "dev", "--runner", "rest/UsrTests/Run", "--class", "X", "--package", "UsrTests"],
                            settings=s, opener=opener, clio_run=FakeClio(output="[ERR] - denied"))
        assert code == 0 and "warning: the dll age was not checked - sql: [ERR] - denied" in out, out

def test_references_to_the_layers_a_merge_removes():
    from creatio_schemas.describe.merge import references
    ids = [{"id": "11111111-0000-4000-8000-000000000001", "package": "UsrB"}, {"id": "11111111-0000-4000-8000-000000000002", "package": "UsrC"}]
    fks = [{"table": "SysEditPage", "column": "SysEntitySchemaId"}, {"table": "SysGridPage", "column": "SysEntitySchemaId"}]
    hits = [{"ref": "SysEditPage.SysEntitySchemaId", "id": ids[1]["id"], "n": "2"}, {"ref": "SysGridPage.SysEntitySchemaId", "id": ids[0]["id"], "n": "0"}]
    clio = FakeClio(rows=[ids, fks, hits])
    e = Environment("https://s", "u", "p", clio_name="dev", clio_run=clio)
    assert references(e, "Contact", ["UsrB", "UsrC"]) == ["references: SysEditPage.SysEntitySchemaId 2 rows point at UsrC's Contact"]
    assert "s.\"Name\" = 'Contact'" in clio.scripts[0] and "p.\"Name\" in ('UsrB', 'UsrC')" in clio.scripts[0]
    assert "rc.delete_rule = 'NO ACTION'" in clio.scripts[1] and "ccu.table_name = 'SysSchema'" in clio.scripts[1]
    assert clio.scripts[2].count("union all") == 1 and f"\"SysEntitySchemaId\" in ('{ids[0]['id']}', '{ids[1]['id']}')" in clio.scripts[2]
    clean = FakeClio(rows=[ids, fks, []])
    assert references(Environment("https://s", "u", "p", clio_name="dev", clio_run=clean), "Contact", ["UsrB", "UsrC"]) == []
    assert references(Environment("https://s", "u", "p", clio_name="dev", clio_run=FakeClio(rows=[[]])), "Contact", ["UsrB"]) == []  # no layer on the site


if __name__ == "__main__":
    for fn in [v for k, v in list(globals().items()) if k.startswith("test_")]:
        fn()
        print("ok", fn.__name__)
