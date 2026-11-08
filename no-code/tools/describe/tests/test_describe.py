"""Checks for the describe layer:  python tests/test_describe.py  (uses the other toolkits' fixtures)."""

import contextlib
import io
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(HERE.parent))

from creatio_schemas.describe import PackageIndex, QueryError, describe_item, describe_package, describe_schema, find_schema, index_workspace, parse_query  # noqa: E402
from describe import main  # noqa: E402

PAGES = TOOLS / "pages" / "tests" / "fixtures" / "iaTest"
RULES = TOOLS / "rules" / "tests" / "fixtures" / "iaTest"
PROCS = TOOLS / "process" / "tests" / "fixtures" / "iaTest"
SQL = TOOLS / "sqlscripts" / "tests" / "fixtures" / "iaTest"


def test_parse_query():
    assert parse_query("elements type=crt.Input parent=X") == ("elements", None, {"type": "crt.Input", "parent": "X"})
    assert parse_query("element iaName") == ("element", "iaName", {})
    assert parse_query('find "Order bed"') == ("find", "Order bed", {})
    assert parse_query("") == ("topics", None, {})


def test_package_level_lists_every_kind():
    out = describe_package(PAGES)
    lines = out.splitlines()
    assert lines[0].startswith("iaTest") and "5 items" in lines[0]
    assert any(l.startswith("  object ") and "iaOrder " in l and "columns" in l for l in lines)
    assert any(l.startswith("  page ") and "iaTests_FormPage" in l and "page of iaTest" in l for l in lines)
    only = describe_package(PAGES, "object").splitlines()
    assert len(only) == 4 and all(l.startswith("  object") for l in only[1:])
    assert "sql " in describe_package(SQL, "sql")
    assert "rules " in describe_package(RULES, "rules")
    assert "process " in describe_package(PROCS, "process")


def test_schema_summaries_are_the_inspect_output():
    assert describe_schema(PAGES, "iaOrder").startswith("iaOrder:")
    assert "rule(s)" in describe_schema(RULES, "iaTestBusinessRule")
    assert "elements:" in describe_schema(PROCS, "iaProcess_0d4c445")


def test_object_queries():
    lookups = describe_item(PAGES, "iaOrder", "columns type=Lookup")
    assert "iaStatus" in lookups and "iaName" not in lookups
    assert "base" in describe_item(PAGES, "iaOrder", "columns own=false")
    one = describe_item(PAGES, "iaOrder", "column iaQuantity")
    assert one.startswith("iaQuantity") and '"A2": "iaQuantity"' in one
    assert "flags:" in describe_item(PAGES, "iaOrder", "flags")
    assert "columns" in describe_item(PAGES, "iaOrder", "topics")


def test_page_queries_return_only_the_part_asked():
    sections = describe_item(PAGES, "iaTests_FormPage", "sections")
    assert "view-config-diff" in sections and "handlers" in sections
    elements = describe_item(PAGES, "iaTests_FormPage", "elements type=crt.DateTimePicker")
    assert elements.count("\n") == 2 and "iaDate" in elements and "iaName" not in elements
    assert '"name": "iaName"' in describe_item(PAGES, "iaTests_FormPage", "element iaName")
    assert "PDS.iaName" in describe_item(PAGES, "iaTests_FormPage", "attributes bound=true")
    assert "iaTest" in describe_item(PAGES, "iaTests_FormPage", "data-sources")
    assert "SideAreaProfileContainer:" in describe_item(PAGES, "iaTests_FormPage", "containers")
    assert "view_config_diff" in describe_item(PAGES, "iaTests_FormPage", "find iaIsActive").lower().replace("-", "_")
    assert describe_item(PAGES, "iaTests_FormPage", "handlers") == "(no handlers)"
    assert describe_item(PAGES, "iaOrder_FormPage", "elements") == "(no matching element)"  # the template form has no fields yet
    try:
        describe_item(PAGES, "iaTests_FormPage", "attribute Nope")
    except QueryError as e:
        assert "no attribute Nope" in str(e)
    else:
        raise AssertionError("an unknown attribute must be refused")


def test_handlers_are_split_by_brace_matching():
    from creatio_schemas.page import PageSchema
    page = PageSchema(PAGES, "iaTests_FormPage")
    page.body = page.body.replace("handlers: /**SCHEMA_HANDLERS*/[]/**SCHEMA_HANDLERS*/",
                                  'handlers: /**SCHEMA_HANDLERS*/[\n{ request: "crt.SaveRecordRequest", handler: async (request, next) => { const s = "}"; return await next?.handle(request); } },\n'
                                  "{ request: 'crt.HandleViewModelInitRequest', handler: async (request, next) => { return next?.handle(request); } }\n]/**SCHEMA_HANDLERS*/")
    hs = page.handlers()
    assert [r for r, _ in hs] == ["crt.SaveRecordRequest", "crt.HandleViewModelInitRequest"]
    assert 'const s = "}"' in hs[0][1] and hs[0][1].endswith("}")


def test_process_rules_sql_queries():
    assert "FormulaTask" in describe_item(PROCS, "iaProcess_0d4c445", "elements") or "elements" in describe_item(PROCS, "iaProcess_0d4c445", "topics")
    assert "->" in describe_item(PROCS, "iaProcess_0d4c445", "flows")
    assert "In" in describe_item(PROCS, "iaProcess_0d4c445", "params") or "(no parameters)" in describe_item(PROCS, "iaProcess_0d4c445", "params")
    rules = describe_item(RULES, "iaTestBusinessRule", "rules")
    assert rules.count("\n") + 1 == len(describe_item(RULES, "iaTestBusinessRule", "rules").splitlines())
    first = rules.splitlines()[0].split()[0]
    assert "when" in describe_item(RULES, "iaTestBusinessRule", f"rule {first}")
    scripts = describe_package(SQL, "sql").splitlines()[1:]
    name = scripts[0].split()[1]
    assert len(describe_item(SQL, name, "body")) > 10
    assert "cultures:" in describe_item(PAGES, "iaOrder", "resources")


def test_index_follows_the_disk():
    import shutil
    import tempfile
    tmp = Path(tempfile.mkdtemp()) / "packages"
    shutil.copytree(PAGES, tmp / "iaTest")
    try:
        first = index_workspace(tmp)
        assert "iaTest: 5 schemas" in first and "+5 added" in first
        assert (tmp.parent / ".creatio-index" / "iaTest.json").is_file()
        assert "up to date" in index_workspace(tmp)
        # a pulled schema appears: the next call indexes it, nothing else is re-read
        shutil.copytree(RULES / "Schemas" / "iaTestBusinessRule", tmp / "iaTest" / "Schemas" / "iaTestBusinessRule")
        again = index_workspace(tmp)
        assert "+1 added" in again and "iaTestBusinessRule" in again
        # a changed file is noticed by size/mtime
        meta = tmp / "iaTest" / "Schemas" / "iaOrder" / "metadata.json"
        meta.write_text(meta.read_text(encoding="utf-8") + " ", encoding="utf-8")
        assert "~1 changed" in index_workspace(tmp)
        where = find_schema(tmp, "iaTest")
        assert "object in iaTest" in where and "Schemas/iaTest/metadata.json" in where
        assert "iaTests_FormPage (page)" in where and "iaTestBusinessRule (rules)" in where
        assert "cultures" in where  # resource files folded into one line
        idx = PackageIndex(tmp / "iaTest")
        assert "iaOrderStatus" in idx.schemas["iaOrder"]["refs"]  # a lookup column refers by UId
        assert "no schema named Nope" in find_schema(tmp, "Nope")
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)


CS = HERE / "fixtures" / "UsrPkg"


def test_csharp_by_signatures():
    out = describe_package(CS)
    assert "  source    UsrOrderService" in out and "DTO, web service; 3 methods" in out
    assert "  csharp    Files/cs/UsrOrderEventListener.cs" in out and "entity event listener of UsrOrder; 3 methods" in out
    assert len(describe_package(CS, "csharp").splitlines()) == 3
    text = describe_schema(CS, "UsrOrderService")
    assert "[ServiceContract] [AspNetCompatibilityRequirements] public class UsrOrderService : BaseService  - web service, 3 members" in text
    assert "[OperationContract] [WebInvoke] public OrderLabelResponse GetLabel(string orderId)  (42)" in text
    assert "operations: ESQ read, Update (raw SQL)" in text
    # a plain file by path, by file name or by stem; nested types, enums, expression-bodied members, comments with braces
    for name in ("Files/cs/UsrOrderLabel.cs", "UsrOrderLabel.cs", "UsrOrderLabel"):
        label = describe_schema(CS, name)
        assert "public static class UsrOrderLabel  - static helper, 6 members, lines 22-46" in label
        assert "    private class Cache  - class, 2 members" in label and "values: Short, Padded" in label
        assert "method      public static bool IsLabel(string text)  (34)" in label
    assert describe_item(CS, "UsrOrderLabel", "member UsrOrderLabel.Build").startswith("public static string Build(string type, int seq) {")
    assert describe_item(CS, "UsrOrderLabel", "member UsrOrderLabel.Build").rstrip().endswith("}")
    assert describe_item(CS, "UsrOrderLabel", "member Build").count("Build(") == 2  # the interface's and the class's
    members = describe_item(CS, "UsrOrderService", "members UsrOrderService kind=method visibility=public")
    assert "GetLabel" in members and "RebuildAll" in members and "ReadOrder" not in members
    assert describe_item(CS, "UsrOrderService", "operations").splitlines()[1].strip().startswith("59  Update (raw SQL)")
    assert "entity event listener of UsrOrder" in describe_item(CS, "UsrOrderEventListener", "classes")
    assert describe_item(CS, "UsrOrderLabel", "regions") == "(no regions)" and len(describe_item(CS, "UsrOrderService", "regions").splitlines()) == 4
    assert "   25  private static readonly string Separator" in describe_item(CS, "UsrOrderLabel", "find Separator")
    assert "Terrasoft.Core.Entities.Events" in describe_item(CS, "UsrOrderEventListener", "usings")
    try:
        describe_item(CS, "UsrOrderLabel", "member Nope")
        raise AssertionError("expected QueryError")
    except QueryError as exc:
        assert "no member Nope" in str(exc) and "UsrOrderLabel.Build" in str(exc)
    idx = PackageIndex(CS)
    idx.refresh()
    assert idx.schemas["UsrOrderService"]["kind"] == "source" and "web service" in idx.schemas["UsrOrderService"]["summary"]
    # Files/cs files are index items of their own: one file, no descriptor, no resources; referred to by their types
    label = idx.schemas["Files/cs/UsrOrderLabel.cs"]
    assert label["kind"] == "csharp" and list(label["files"]) == ["Files/cs/UsrOrderLabel.cs"] and label["caption"] == "" and label["manager"] is None
    assert "Files/cs/UsrOrderLabel.cs" in idx.schemas["UsrOrderService"]["refs"]  # the service calls UsrOrderLabel.Build
    found = find_schema(CS, "UsrOrderLabel")
    assert found.startswith("Files/cs/UsrOrderLabel.cs  csharp in UsrPkg") and "used by: UsrOrderService (source)" in found
    assert find_schema(CS, "UsrOrderLabel.cs").splitlines()[0] == found.splitlines()[0]
    assert "refers to: Files/cs/UsrOrderLabel.cs" in find_schema(CS, "UsrOrderService")


def test_cli():
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert main(["package", str(PAGES), "--kind", "page"]) == 0
        assert main(["find", str(PAGES), "iaOrder"]) == 0
        assert main(["item", str(PAGES), "iaOrder", "columns type=Lookup"]) == 0
    assert "iaTests_FormPage" in out.getvalue() and "iaStatus" in out.getvalue()
    with contextlib.redirect_stderr(io.StringIO()):
        assert main(["item", str(PAGES), "iaOrder", "nonsense"]) == 2


if __name__ == "__main__":
    for fn in [v for k, v in list(globals().items()) if k.startswith("test_")]:
        fn()
        print("ok", fn.__name__)
