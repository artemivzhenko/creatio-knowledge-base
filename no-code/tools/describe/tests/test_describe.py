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


def test_a_kind_is_one_registry_entry():
    from creatio_schemas.describe import registry
    from creatio_schemas.entity import EntitySchema
    demo = registry.Kind("demo", EntitySchema, lambda p, n, d: n == "iaOrderStatus", EntitySchema, lambda e: "a demo lookup",
                         {"hello": lambda item, name, f: f"world from {item.name}"})
    registry.register(demo)
    try:
        # the index caches kind and summary, but carries a fingerprint of the registry: a new kind rebuilds it by itself
        assert "  demo      iaOrderStatus" in describe_package(PAGES) and "a demo lookup" in describe_package(PAGES, "demo")
        assert describe_item(PAGES, "iaOrderStatus", "hello") == "world from iaOrderStatus"
        assert "columns" not in describe_item(PAGES, "iaOrderStatus", "topics") and "files" in describe_item(PAGES, "iaOrderStatus", "topics")
        assert "  object    iaOrder " in describe_package(PAGES)  # other objects keep their kind
    finally:
        registry.unregister("demo")
        PackageIndex(PAGES).refresh(rebuild=True)
    assert "  object    iaOrderStatus" in describe_package(PAGES) and "columns" in describe_item(PAGES, "iaOrderStatus", "topics")


def test_output_contract_cuts_long_answers():
    from creatio_schemas.describe import DEFAULT_LIMIT, TAIL, cut
    assert DEFAULT_LIMIT == 40 and TAIL.format(more=3) == "  ... 3 more; add limit=0 for all"
    assert cut(["a", "b", "c"], 2) == ["a", "b", "  ... 1 more; add limit=0 for all"] and cut(["a", "b"], 2) == ["a", "b"] and cut(["a"] * 99, 0) == ["a"] * 99
    DCM = TOOLS / "dcm" / "tests" / "fixtures" / "iaTest"
    full = describe_schema(DCM, "iaRequestCases", limit=0)
    short = describe_schema(DCM, "iaRequestCases", limit=10)
    assert len(full.splitlines()) > 10 and len(short.splitlines()) == 11
    assert short.splitlines()[-1].startswith(f"  ... {len(full.splitlines()) - 10} more; add limit=0 for all; this is the summary - ask describe_item for one part (topics: ")
    assert "stages" in short.splitlines()[-1] and describe_schema(DCM, "iaRequestCases") == full  # 28 lines: under the default


def test_list_limits_and_unlimited():
    full = describe_item(PAGES, "iaTests_FormPage", "elements limit=0").splitlines()
    short = describe_item(PAGES, "iaTests_FormPage", "elements limit=2").splitlines()
    assert len(full) > 2 and short == full[:2] + [f"  ... {len(full) - 2} more; add limit=0 for all"]
    package_full = describe_package(PAGES, limit=0).splitlines()
    package_short = describe_package(PAGES, limit=2).splitlines()
    assert package_short == package_full[:3] + [f"  ... {len(package_full) - 3} more; add limit=0 for all"]
    for query in ("elements limit=-1", "elements limit=bad"):
        try:
            describe_item(PAGES, "iaTests_FormPage", query)
            assert False, query
        except QueryError as e:
            assert "non-negative integer" in str(e)


def test_find_and_lookup_limits():
    from unittest.mock import patch
    from creatio_schemas.describe import lookups
    from creatio_schemas.describe import index

    class FakeIndex:
        def __init__(self, path):
            self.package = Path(path)
            self.data = {"package": "UsrPkg", "data": {}}
            self.schemas = {
                f"UsrLookup{i}": {"kind": "object", "parent": "BaseLookup", "caption": "", "summary": "",
                                  "files": {}, "refs": ["UsrA", "UsrB", "UsrC"]}
                for i in range(3)
            }
            self.schemas.update({
                f"UsrUnknown{i}": {"kind": "object", "parent": "UsrExternal", "caption": "", "summary": "",
                                   "files": {}, "refs": []}
                for i in range(3)
            })

        def refresh(self):
            pass

        def referrers(self, name):
            return [("object", f"UsrUser{i}") for i in range(3)]

    with patch.object(index, "packages_of", return_value=[Path("UsrPkg")]), patch.object(index, "PackageIndex", FakeIndex):
        limited = find_schema("unused", "UsrLookup0", 1)
        assert limited.count("  ... 2 more; add limit=0 for all") == 2
        assert "UsrB" not in limited and "UsrUser1" not in limited
        full = find_schema("unused", "UsrLookup0", 0)
        assert "UsrC" in full and "UsrUser2" in full and "... " not in full
        limited = lookups("unused", 1)
        assert limited.count("  ... 2 more; add limit=0 for all") == 2
        full = lookups("unused", 0)
        assert "UsrLookup2" in full and "UsrUnknown2" in full and "... " not in full


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


DATA = TOOLS / "data" / "tests" / "fixtures" / "UsrPkg"


def test_index_binding_resources_and_format_rebuild():
    import json
    import shutil
    import tempfile
    from unittest.mock import patch
    from creatio_schemas.describe import lookups
    from creatio_schemas.resources import Resources

    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp) / "UsrPkg"
        shutil.copytree(DATA, pkg)
        original = PackageIndex(pkg)
        original.refresh()
        assert original.data["data"]["UsrStatus"]["keys"] == ["New", "In progress", "Done"]
        binding = pkg / "Data" / "UsrStatus"
        desc = {"Descriptor": {"Schema": {"Name": "UsrOrderStatus"}, "Columns": [
            {"ColumnName": "Code", "ColumnUId": "usr-code"},
            {"ColumnName": "Name", "ColumnUId": "usr-name"},
        ]}}
        (binding / "descriptor.json").write_text(json.dumps(desc), encoding="utf-8")
        rows = {"PackageData": [
            {"Row": [{"SchemaColumnUId": "usr-code", "Value": "UsrFirst"}]},
            {"Row": [{"SchemaColumnUId": "usr-code", "Value": "UsrSecond"}]},
        ]}
        (binding / "data.json").write_text(json.dumps(rows), encoding="utf-8")
        localization = binding / "Localization"
        (localization / "data.json").write_text(json.dumps(rows), encoding="utf-8")
        idx = PackageIndex(pkg)
        idx.refresh()
        entry = idx.data["data"]["UsrStatus"]
        assert entry["rows"] == 2 and entry["columns"] == ["Code", "Name"]
        assert entry["keys"] == ["UsrFirst", "UsrSecond"]
        res = Resources(pkg / "Resources" / "UsrOrderStatus.Entity")
        resources = idx.schemas["UsrOrderStatus"]["resources"]
        assert resources == {"cultures": sorted(res.cultures), "keys": len(res.cultures.get("en-US", {})),
                             "missing": {c: len(keys) for c, keys in res.missing().items()}}
        assert "resources:" in find_schema(pkg, "UsrOrderStatus")
        assert "Data/UsrStatus (2 rows, UsrPkg)" in find_schema(pkg, "UsrOrderStatus")
        with patch("creatio_schemas.describe.index.read_text", side_effect=AssertionError("unexpected file read")):
            assert "Data/UsrStatus (2 rows)" in lookups(pkg)
        old = json.loads(idx.path.read_text(encoding="utf-8"))
        old["format"] = 1
        old["data"]["UsrStatus"]["rows"] = 99
        idx.path.write_text(json.dumps(old), encoding="utf-8")
        rebuilt = PackageIndex(pkg)
        rebuilt.refresh()
        assert rebuilt.data["format"] == 2 and rebuilt.data["data"]["UsrStatus"]["rows"] == 2
        assert json.loads(idx.path.read_text(encoding="utf-8"))["format"] == 2


def test_data_bindings_answer_columns_and_rows():
    assert describe_schema(DATA, "UsrStatus").startswith("UsrStatus: binds UsrOrderStatus, 3 rows, columns Id Name(loc) Description(loc)")
    listed = describe_package(DATA, "data")
    assert "  data      UsrStatus" in listed and "SysSettings_UsrMaxRows" in listed and len(listed.splitlines()) == 4
    cols = describe_item(DATA, "UsrStatus", "columns")
    assert cols.splitlines()[0].startswith("Id ") and "key" in cols.splitlines()[0] and "(loc)" in cols
    rows = describe_item(DATA, "UsrStatus", "rows limit=1 culture=en-US")
    assert len(rows.splitlines()) == 2 and rows.endswith("... 2 more; add limit=0 for all") and 'Name="New"' in rows
    key = rows.splitlines()[0].split()[0]
    assert "Name = " in describe_item(DATA, "UsrStatus", f"row {key}")
    try:
        describe_item(DATA, "UsrStatus", "row nope")
        raise AssertionError("expected QueryError")
    except QueryError:
        pass


CLASSIC = TOOLS / "classicui" / "tests" / "fixtures" / "UsrPkg"


def test_classic_ui_schemas_answer_diff_and_methods():
    listed = describe_package(CLASSIC)
    assert "  classic   UsrOrderPage" in listed and "diff operations" in listed and "  classic   UsrOrderSection" in listed
    assert describe_schema(CLASSIC, "UsrOrderPage").startswith("UsrOrderPage:")
    diff = describe_item(CLASSIC, "UsrOrderPage", "diff op=insert")
    assert diff.splitlines() and all(line.startswith("insert ") for line in diff.splitlines())
    first = diff.splitlines()[0].split()[1]
    assert first in describe_item(CLASSIC, "UsrOrderPage", f"element {first}") and "values" in describe_item(CLASSIC, "UsrOrderPage", f"element {first}")
    methods = describe_item(CLASSIC, "UsrOrderPage", "methods")
    name = methods.splitlines()[0].split()[0]
    assert describe_item(CLASSIC, "UsrOrderPage", f"method {name}").startswith(name)
    assert "diff" in describe_item(CLASSIC, "UsrOrderPage", "topics") and "details" in describe_item(CLASSIC, "UsrOrderPage", "topics")
    try:
        describe_item(CLASSIC, "UsrOrderPage", "element Nope")
        raise AssertionError("expected QueryError")
    except QueryError:
        pass


def test_lookups_follow_the_parent_chain():
    from creatio_schemas.describe import lookups
    out = lookups(PAGES)
    assert out.splitlines()[0].startswith("1 lookups in iaTest")
    assert "  iaOrderStatus" in out and "parent BaseLookup" in out and "0 own columns" in out and "bindings: none" in out and "used by 1" in out
    assert "not decided" not in out
    cli = io.StringIO()
    with contextlib.redirect_stdout(cli):
        assert main(["lookups", str(PAGES)]) == 0
    assert "iaOrderStatus" in cli.getvalue()


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
