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
from creatio_schemas.describe.index import INDEX_FORMAT, located  # noqa: E402
from describe import main  # noqa: E402

PAGES = TOOLS / "pages" / "tests" / "fixtures" / "UsrPkg"
RULES = TOOLS / "rules" / "tests" / "fixtures" / "UsrPkg"
PROCS = TOOLS / "process" / "tests" / "fixtures" / "UsrPkg"
SQL = TOOLS / "sqlscripts" / "tests" / "fixtures" / "UsrPkg"


def test_parse_query():
    assert parse_query("elements type=crt.Input parent=X") == ("elements", None, {"type": "crt.Input", "parent": "X"})
    assert parse_query("element UsrName") == ("element", "UsrName", {})
    assert parse_query('find "Order bed"') == ("find", "Order bed", {})
    assert parse_query("") == ("topics", None, {})


def test_compare_exits_one_on_a_difference():
    import tempfile
    folder = Path(tempfile.mkdtemp())
    a, b = folder / "a.txt", folder / "b.txt"
    a.write_text("rows 6\nchecksum UsrNote aaa\n", encoding="utf-8")
    b.write_text("rows 6\nchecksum UsrNote aaa\n", encoding="utf-8")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert main(["compare", str(a), str(b)]) == 0
    assert out.getvalue().strip() == "same"
    b.write_text("rows 5\nchecksum UsrNote aaa\n", encoding="utf-8")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert main(["compare", str(a), str(b)]) == 1
    assert out.getvalue().strip() == "~ rows  6 -> 5"


def test_package_level_lists_every_kind():
    out = describe_package(PAGES)
    lines = out.splitlines()
    assert lines[0].startswith("UsrPkg") and "5 items" in lines[0]
    assert any(l.startswith("  object ") and "UsrOrder " in l and "columns" in l for l in lines)
    assert any(l.startswith("  page ") and "UsrTests_FormPage" in l and "page of UsrPkg" in l for l in lines)
    only = describe_package(PAGES, "object").splitlines()
    assert len(only) == 4 and all(l.startswith("  object") for l in only[1:])
    assert "sql " in describe_package(SQL, "sql")
    assert "rules " in describe_package(RULES, "rules")
    assert "process " in describe_package(PROCS, "process")


def test_schema_summaries_are_the_inspect_output():
    assert describe_schema(PAGES, "UsrOrder").startswith("UsrOrder:")
    assert "rule(s)" in describe_schema(RULES, "UsrPkgBusinessRule")
    assert "elements:" in describe_schema(PROCS, "UsrProcess_0d4c445")


def test_a_kind_is_one_registry_entry():
    from creatio_schemas.describe import registry
    from creatio_schemas.entity import EntitySchema
    demo = registry.Kind("demo", EntitySchema, lambda p, n, d: n == "UsrOrderStatus", EntitySchema, lambda e: "a demo lookup",
                         {"hello": lambda item, name, f: f"world from {item.name}"})
    registry.register(demo)
    try:
        # the index caches kind and summary, but carries a fingerprint of the registry: a new kind rebuilds it by itself
        assert "  demo      UsrOrderStatus" in describe_package(PAGES) and "a demo lookup" in describe_package(PAGES, "demo")
        assert describe_item(PAGES, "UsrOrderStatus", "hello") == "world from UsrOrderStatus"
        assert "columns" not in describe_item(PAGES, "UsrOrderStatus", "topics") and "files" in describe_item(PAGES, "UsrOrderStatus", "topics")
        assert "  object    UsrOrder " in describe_package(PAGES)  # other objects keep their kind
    finally:
        registry.unregister("demo")
        PackageIndex(PAGES).refresh(rebuild=True)
    assert "  object    UsrOrderStatus" in describe_package(PAGES) and "columns" in describe_item(PAGES, "UsrOrderStatus", "topics")


def test_output_contract_cuts_long_answers():
    from creatio_schemas.describe import DEFAULT_LIMIT, TAIL, cut
    assert DEFAULT_LIMIT == 40 and TAIL.format(more=3) == "  ... 3 more; add limit=0 for all"
    assert cut(["a", "b", "c"], 2) == ["a", "b", "  ... 1 more; add limit=0 for all"] and cut(["a", "b"], 2) == ["a", "b"] and cut(["a"] * 99, 0) == ["a"] * 99
    DCM = TOOLS / "dcm" / "tests" / "fixtures" / "UsrPkg"
    full = describe_schema(DCM, "UsrRequestCases", limit=0)
    short = describe_schema(DCM, "UsrRequestCases", limit=10)
    assert len(full.splitlines()) > 10 and len(short.splitlines()) == 11
    assert short.splitlines()[-1].startswith(f"  ... {len(full.splitlines()) - 10} more; add limit=0 for all; this is the summary - ask describe_item for one part (topics: ")
    assert "stages" in short.splitlines()[-1] and describe_schema(DCM, "UsrRequestCases") == full  # 28 lines: under the default


def test_list_limits_and_unlimited():
    full = describe_item(PAGES, "UsrTests_FormPage", "elements limit=0").splitlines()
    short = describe_item(PAGES, "UsrTests_FormPage", "elements limit=2").splitlines()
    assert len(full) > 2 and short == full[:2] + [f"  ... {len(full) - 2} more; add limit=0 for all"]
    package_full = describe_package(PAGES, limit=0).splitlines()
    package_short = describe_package(PAGES, limit=2).splitlines()
    assert package_short == package_full[:3] + [f"  ... {len(package_full) - 3} more; add limit=0 for all"]
    for query in ("elements limit=-1", "elements limit=bad"):
        try:
            describe_item(PAGES, "UsrTests_FormPage", query)
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

        def dependents(self, name):
            return []

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
    lookups = describe_item(PAGES, "UsrOrder", "columns type=Lookup")
    assert "UsrStatus" in lookups and "UsrName" not in lookups
    assert "base" in describe_item(PAGES, "UsrOrder", "columns own=false")
    one = describe_item(PAGES, "UsrOrder", "column UsrQuantity")
    assert one.startswith("UsrQuantity") and '"A2": "UsrQuantity"' in one
    assert "flags:" in describe_item(PAGES, "UsrOrder", "flags")
    assert "columns" in describe_item(PAGES, "UsrOrder", "topics")


def test_page_queries_return_only_the_part_asked():
    sections = describe_item(PAGES, "UsrTests_FormPage", "sections")
    assert "view-config-diff" in sections and "handlers" in sections
    elements = describe_item(PAGES, "UsrTests_FormPage", "elements type=crt.DateTimePicker")
    assert elements.count("\n") == 2 and "UsrDate" in elements and "UsrName" not in elements
    assert '"name": "UsrName"' in describe_item(PAGES, "UsrTests_FormPage", "element UsrName")
    assert "PDS.UsrName" in describe_item(PAGES, "UsrTests_FormPage", "attributes bound=true")
    assert "UsrPkg" in describe_item(PAGES, "UsrTests_FormPage", "data-sources")
    assert "SideAreaProfileContainer:" in describe_item(PAGES, "UsrTests_FormPage", "containers")
    assert "view_config_diff" in describe_item(PAGES, "UsrTests_FormPage", "find UsrIsActive").lower().replace("-", "_")
    assert describe_item(PAGES, "UsrTests_FormPage", "handlers") == "(no handlers)"
    assert describe_item(PAGES, "UsrOrder_FormPage", "elements") == "(no matching element)"  # the template form has no fields yet
    try:
        describe_item(PAGES, "UsrTests_FormPage", "attribute Nope")
    except QueryError as e:
        assert "no attribute Nope" in str(e)
    else:
        raise AssertionError("an unknown attribute must be refused")


def test_handlers_are_split_by_brace_matching():
    from creatio_schemas.page import PageSchema
    page = PageSchema(PAGES, "UsrTests_FormPage")
    page.body = page.body.replace("handlers: /**SCHEMA_HANDLERS*/[]/**SCHEMA_HANDLERS*/",
                                  'handlers: /**SCHEMA_HANDLERS*/[\n{ request: "crt.SaveRecordRequest", handler: async (request, next) => { const s = "}"; return await next?.handle(request); } },\n'
                                  "{ request: 'crt.HandleViewModelInitRequest', handler: async (request, next) => { return next?.handle(request); } }\n]/**SCHEMA_HANDLERS*/")
    hs = page.handlers()
    assert [r for r, _ in hs] == ["crt.SaveRecordRequest", "crt.HandleViewModelInitRequest"]
    assert 'const s = "}"' in hs[0][1] and hs[0][1].endswith("}")


def test_process_rules_sql_queries():
    assert "FormulaTask" in describe_item(PROCS, "UsrProcess_0d4c445", "elements") or "elements" in describe_item(PROCS, "UsrProcess_0d4c445", "topics")
    assert "->" in describe_item(PROCS, "UsrProcess_0d4c445", "flows")
    assert "In" in describe_item(PROCS, "UsrProcess_0d4c445", "params") or "(no parameters)" in describe_item(PROCS, "UsrProcess_0d4c445", "params")
    rules = describe_item(RULES, "UsrPkgBusinessRule", "rules")
    assert rules.count("\n") + 1 == len(describe_item(RULES, "UsrPkgBusinessRule", "rules").splitlines())
    first = rules.splitlines()[0].split()[0]
    assert "when" in describe_item(RULES, "UsrPkgBusinessRule", f"rule {first}")
    scripts = describe_package(SQL, "sql").splitlines()[1:]
    name = scripts[0].split()[1]
    assert len(describe_item(SQL, name, "body")) > 10
    assert "cultures:" in describe_item(PAGES, "UsrOrder", "resources")


def test_index_follows_the_disk():
    import shutil
    import tempfile
    tmp = Path(tempfile.mkdtemp()) / "packages"
    shutil.copytree(PAGES, tmp / "UsrPkg")
    try:
        first = index_workspace(tmp)
        assert "UsrPkg: 5 schemas" in first and "+5 added" in first
        assert (tmp.parent / ".creatio-index" / "UsrPkg.json").is_file()
        assert "up to date" in index_workspace(tmp)
        # a pulled schema appears: the next call indexes it, nothing else is re-read
        shutil.copytree(RULES / "Schemas" / "UsrPkgBusinessRule", tmp / "UsrPkg" / "Schemas" / "UsrPkgBusinessRule")
        again = index_workspace(tmp)
        assert "+1 added" in again and "UsrPkgBusinessRule" in again
        # a changed file is noticed by size/mtime
        meta = tmp / "UsrPkg" / "Schemas" / "UsrOrder" / "metadata.json"
        meta.write_text(meta.read_text(encoding="utf-8") + " ", encoding="utf-8")
        assert "~1 changed" in index_workspace(tmp)
        where = find_schema(tmp, "UsrPkg")
        assert "object in UsrPkg" in where and "Schemas/UsrPkg/metadata.json" in where
        assert "UsrTests_FormPage (page)" in where and "UsrPkgBusinessRule (rules)" in where
        assert "cultures" in where  # resource files folded into one line
        idx = PackageIndex(tmp / "UsrPkg")
        assert "UsrOrderStatus" in idx.schemas["UsrOrder"]["refs"]  # a lookup column refers by UId
        assert "no schema named Nope" in find_schema(tmp, "Nope")
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)


CS = HERE / "fixtures" / "UsrPkg"


DATA = TOOLS / "data" / "tests" / "fixtures" / "UsrPkg"
OBJECTS = TOOLS / "objects" / "tests" / "fixtures" / "UsrPkg"


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
        assert rebuilt.data["format"] == INDEX_FORMAT and rebuilt.data["data"]["UsrStatus"]["rows"] == 2
        assert json.loads(idx.path.read_text(encoding="utf-8"))["format"] == INDEX_FORMAT


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


def test_keys_topic_names_the_metadata_keys():
    full = describe_item(CS, "UsrOrderService", "keys")  # a source code schema made as full JSON
    assert "A2           Name" in full and "B6           PackageUId" in full and "B8           CreatedInVersion" in full
    diff = describe_item(PAGES, "UsrOrder", "keys")  # an object made in the designer: a diff against its parent
    assert diff.startswith("diff form against the parent's metadata") and "= A5                     CreatedInPackageId" in diff and "+ D2 " in diff
    assert describe_item(TOOLS / "sqlscripts" / "tests" / "fixtures" / "UsrPkg", describe_package(TOOLS / "sqlscripts" / "tests" / "fixtures" / "UsrPkg", "sql").splitlines()[1].split()[1], "keys") == "(no metadata.json)"


def test_lookups_follow_the_parent_chain():
    from creatio_schemas.describe import lookups
    out = lookups(PAGES)
    assert out.splitlines()[0].startswith("1 lookups in UsrPkg")
    assert "  UsrOrderStatus" in out and "parent BaseLookup" in out and "0 own columns" in out and "bindings: none" in out and "used by 1" in out
    assert "not decided" not in out
    cli = io.StringIO()
    with contextlib.redirect_stdout(cli):
        assert main(["lookups", str(PAGES)]) == 0
    assert "UsrOrderStatus" in cli.getvalue()


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


def test_broken_items_cost_one_line_each():
    import shutil
    import tempfile
    from creatio_schemas.csharp import CSharpSource
    from creatio_schemas.data import DataBinding
    from creatio_schemas.describe import lookups

    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp) / "packages" / "UsrPkg"
        shutil.copytree(DATA, pkg)
        shutil.copytree(CS / "Files", pkg / "Files", dirs_exist_ok=True)
        (pkg / "Data" / "UsrEmpty").mkdir()
        shutil.copy(pkg / "Data" / "UsrStatus" / "descriptor.json", pkg / "Data" / "UsrEmpty" / "descriptor.json")
        (pkg / "Data" / "UsrEmpty" / "data.json").write_bytes(b"")  # an empty data.json
        (pkg / "Data" / "UsrNoDescriptor").mkdir()  # a Data folder without its descriptor
        (pkg / "Data" / "UsrNoDescriptor" / "data.json").write_text("{}", encoding="utf-8")
        cs = pkg / "Files" / "cs"
        (cs / "UsrLegacy.cs").write_bytes("namespace Terrasoft.Configuration\r\n{\r\n\t// Комментарий в кодировке Windows\r\n"
                                          "\tpublic class UsrLegacy\r\n\t{\r\n\t\tpublic string Hello() {\r\n\t\t\treturn \"Привет\";\r\n\t\t}\r\n\t}\r\n}\r\n".encode("cp1251"))
        (cs / "UsrBroken.cs").write_bytes(b"public class UsrBroken { \x98\xff }")  # 0x98 is undefined in cp1251 too
        (cs / "UsrTuple.cs").write_text("public class UsrTuple\r\n{\r\n\tprivate (string url, Guid id) GetPair() {\r\n\t\treturn (\"\", Guid.Empty);\r\n\t}\r\n"
                                        "\tpublic UsrTuple(int a) : base(a) {\r\n\t}\r\n}\r\npublic enum UsrState { New, Done = 2 }\r\n", encoding="utf-8")

        legacy = CSharpSource(pkg, cs / "UsrLegacy.cs")
        assert legacy.error is None and "Привет" in legacy.text and [m["name"] for m in legacy.members()] == ["Hello"]
        broken = CSharpSource(pkg, cs / "UsrBroken.cs")
        assert broken.summary().startswith("unreadable: UnicodeDecodeError") and broken.types == []
        tup = CSharpSource(pkg, cs / "UsrTuple.cs")  # the IndexError of a tuple return type, the KeyError of an enum value's source
        assert [(m["kind"], m["name"]) for m in tup.members("UsrTuple")] == [("method", "GetPair"), ("constructor", "UsrTuple")]
        assert tup.member("Done") == "Done = 2" and tup.member("New") == "New"
        for name, text in (("UsrEmpty", "empty file"), ("UsrNoDescriptor", "descriptor.json: missing")):
            try:
                DataBinding(pkg, name)
            except ValueError as e:
                assert text in str(e) and name in str(e), e
            else:
                raise AssertionError(name)

        listing = describe_package(pkg)
        assert "Files/cs/UsrLegacy.cs" in listing and "(cp1251)" in listing.split("Files/cs/UsrLegacy.cs")[1].splitlines()[0], listing
        assert "cannot read: UnicodeDecodeError" in listing and "Data/UsrEmpty" in listing and "Data/UsrNoDescriptor" in listing
        errors = describe_package(pkg, "error")
        assert len(errors.splitlines()) == 4 and "Files/cs/UsrBroken.cs" in errors and "empty file" in errors, errors
        where = find_schema(pkg, "UsrOrderStatus")
        assert "bindings: Data/UsrStatus (3 rows" in where and where.endswith(f"3 items unreadable (describe.py package {pkg} --kind error lists them)"), where
        assert find_schema(pkg, "UsrBroken.cs").startswith("Files/cs/UsrBroken.cs  cannot read, in UsrPkg: UnicodeDecodeError")
        lk = lookups(pkg)
        assert "UsrOrderStatus" in lk and "bindings: Data/UsrStatus (3 rows)" in lk and lk.endswith("3 items unreadable (describe.py package "
                                                                                                    f"{pkg} --kind error lists them)"), lk
        assert describe_item(pkg, "UsrOrderStatus", "columns")  # the rest of the package still answers
        (pkg / "Data" / "UsrEmpty" / "data.json").write_text('{"PackageData": []}', encoding="utf-8")
        assert find_schema(pkg, "UsrOrderStatus").endswith("2 items unreadable (describe.py package " f"{pkg} --kind error lists them)")


LAYER_RULE = "0b7c2c9e-4c1d-4b8e-9f3a-1d2e3f4a5b6c"


def _layer_body(props: str) -> str:
    rule = f'"{LAYER_RULE}": {{"uId": "{LAYER_RULE}"{props}}}' if props is not None else ""
    return ('define("UsrMyEntity1Page", [], function() {\n\treturn {\n\t\tbusinessRules: /**SCHEMA_BUSINESS_RULES*/{\n'
            f'\t\t\t"Owner": {{{rule}}}\n\t\t}}/**SCHEMA_BUSINESS_RULES*/,\n\t\tdiff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/\n\t}};\n}});\n')


class FakeLayersEnv:
    clio_name, url = "dev", "https://dev.example/"

    def __init__(self, rows):
        self.rows, self.sql_text = rows, []

    def sql(self, text):
        self.sql_text.append(text)
        return self.rows


def _row(pkg, sl, pl, body="", ext="true"):
    return {"package": pkg, "extendParent": ext, "modifiedOn": "2026-11-10 09:15:00.123", "modifiedBy": "Supervisor", "isChanged": "false",
            "manager": "ClientUnitSchemaManager", "size": str(len(body)), "md5": "0123456789abcdef0123456789abcdef", "body": body, "sl": sl, "pl": pl}


def test_layers_order_rule_states_and_the_custom_layer():
    from creatio_schemas.describe.layers import layers_sql, render, rule_state, schema_layers, to_json
    import creatio_schemas.environment as environment
    import json

    sql = layers_sql("UsrO'Page", "Custom")
    assert "where s.\"Name\" = 'UsrO''Page'" in sql and "\"SysSchemaContent\"" in sql and "md5(" in sql and "(select \"Id\" from \"SysPackage\" where \"Name\" = 'Custom')" in sql
    assert rule_state("", LAYER_RULE) == "no body" and rule_state(_layer_body(None), LAYER_RULE) == "absent"
    assert rule_state(_layer_body(""), LAYER_RULE) == "enabled" and rule_state(_layer_body(', "enabled": false'), LAYER_RULE) == "disabled"
    assert rule_state(_layer_body(', "enabled": true, "removed": true'), LAYER_RULE) == "removed"
    assert rule_state("not a module at all", LAYER_RULE) == "absent"
    rows = [_row("Custom", "0", "0", _layer_body(', "removed": true')), _row("CrtBase", "1", "5", _layer_body(""), ext="false"),
            _row("UsrPkg", "0", "2", _layer_body(', "enabled": false')), _row("UsrOrphan", "-1", "-1")]
    env = FakeLayersEnv(rows)
    result = schema_layers(env, "UsrMyEntity1Page", LAYER_RULE)
    assert len(env.sql_text) == 1 and "UsrMyEntity1Page" in env.sql_text[0]
    # outside the hierarchy first, then farthest first: the base (schema level 1), package level descending; Custom last
    assert [x["package"] for x in result["layers"]] == ["UsrOrphan", "CrtBase", "UsrPkg", "Custom"]
    assert [x["rule"] for x in result["layers"]] == ["no body", "enabled", "disabled", "removed"] and result["custom"] == ["Custom"]
    assert result["layers"][1]["level"] == 5 and result["layers"][0]["level"] is None and "body" not in result["layers"][0]
    text = render(result, "dev")
    assert text.splitlines()[0] == "UsrMyEntity1Page on dev: 4 copies, applied first to last (the last one wins)"
    assert "replacing" in text.splitlines()[1] and "01234567 " in text and "2026-11-10 09:15:00 " in text and text.endswith("Custom layer present: Custom")
    assert json.loads(to_json(result))["custom"] == ["Custom"]
    assert render(schema_layers(FakeLayersEnv([]), "UsrNope"), "dev") == "UsrNope on dev: no SysSchema copy of that name"
    plain = schema_layers(FakeLayersEnv(rows[1:3]), "UsrMyEntity1Page")
    assert plain["custom"] == [] and "rule" not in plain["layers"][0] and "Custom layer" not in render(plain)
    # the customisation package named by project.json, not by the default
    assert schema_layers(FakeLayersEnv(rows), "UsrMyEntity1Page", custom_layer="UsrPkg")["custom"] == ["UsrPkg"]

    original = environment.open_environment
    try:
        seen = {}

        def fake_open(env_name=None, project=None, **kw):
            seen.update(env=env_name, project=project)
            if not env_name and not project:
                raise ValueError("name the environment")
            return FakeLayersEnv(rows)
        environment.open_environment = fake_open
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            assert main(["layers", "UsrMyEntity1Page", "-e", "dev", "--rule", LAYER_RULE]) == 1  # Custom has a copy
            assert main(["layers", "UsrMyEntity1Page", "-e", "dev", "--custom-layer", "UsrNoSuchPkg"]) == 0
            assert main(["layers", "UsrMyEntity1Page"]) == 2
        text = out.getvalue()
        assert "rule " + LAYER_RULE + ": removed in the layer applied last (Custom)" in text and "Custom layer present: Custom" in text
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project.json"
            project.write_text(json.dumps({"environment": {"clioName": "dev", "customLayer": "UsrPkg"}}), encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                assert main(["layers", "UsrMyEntity1Page", "--project", str(project), "--json"]) == 1
            assert json.loads(out.getvalue())["custom"] == ["UsrPkg"] and seen["project"] == str(project)
    finally:
        environment.open_environment = original


def test_typed_dependencies_resolve_by_uid_and_context():
    from creatio_schemas.describe.deps import Edge, dependencies
    # an object: parent and lookups by UId (the stock asset names Contact and BaseEntity), merged per target
    out = dependencies(PAGES, "UsrOrder")
    assert "  object BaseEntity  parent" in out and "  object Contact  lookup: CreatedBy, ModifiedBy, UsrContact, UsrManager" in out
    assert "  object UsrOrderStatus  lookup: UsrStatus" in out and "  page UsrOrder_FormPage  data-source: PDS  [name]" in out
    # a page: every data source by name, its attribute columns proved on that object's effective columns
    out = dependencies(PAGES, "UsrTests_FormPage", "out")
    assert "  object UsrPkg  data-source: PDS, UsrName, UsrComment" in out and "UsrName?" not in out and "  page PageWithTabsFreedomTemplate  parent" in out
    assert "  object SysFile  data-source: AttachmentListDS, Name  [name]" in out and "dependents" not in out  # a stock object: its columns from the stock catalogue
    assert "  object UsrOrder  data-source: UsrOrderListDS, UsrName, UsrQuantity  [name]" in out  # the data source's own attributes are columns too
    from creatio_schemas.describe.deps import Resolver
    from creatio_schemas.workspace import Workspace
    r = Resolver(Workspace(PAGES))
    assert r.column_names("UsrOrder", ["UsrStatusId", "UsrStatus.Name", "Nope", "null", "ModifiedById"]) == ["UsrStatusId", "UsrStatus.Name", "Nope?", "ModifiedById"]
    # filters, direction and the topic form
    assert dependencies(PAGES, "UsrOrderStatus", "in", kind="object").splitlines() == ["UsrOrderStatus  object in UsrPkg", "dependents:", "  object UsrOrder  lookup: UsrStatus"]
    assert "dependents: nothing typed in the workspace of kind process" in dependencies(PAGES, "UsrOrderStatus", "in", kind="process")
    assert describe_item(PAGES, "UsrOrder_FormPage", "uses via=data-source").endswith("  object UsrOrder  data-source: PDS  [name]")
    assert dependencies(PAGES, "Nope").startswith("no schema named Nope")
    # other kinds: a process data element, a Classic page's details and mixin, a data binding, a C# listener
    assert "  object 368340c2-dddc-46fe-ac7f-d3485b497f95  delete-data: DeleteDataUserTask1" in dependencies(PROCS, "UsrDeleteOldLogs_Process", "out")
    classic = dependencies(TOOLS / "classicui" / "tests" / "fixtures" / "UsrPkg", "UsrOrderPage", "out")
    assert "  page UsrOrderProductDetailV2  detail: UsrOrderProductDetail  [name]" in classic and "  page UsrPrintMixin  mixin: UsrPrintMixin  [name]" in classic
    assert "  object UsrOrder  entity  [name]" in classic and "  page BasePageV2  parent  [name]" in classic
    assert "  object UsrOrderStatus  binds: Id, Name, Description  [name]" in dependencies(TOOLS / "data" / "tests" / "fixtures" / "UsrPkg", "Data/UsrStatus", "out")
    assert "  object UsrOrder  listener: UsrOrderEventListener, UsrStatusId?, UsrAmount?  [name]" in dependencies(CS, "Files/cs/UsrOrderEventListener.cs", "out")
    # the edges live in the index and find_schema shows both directions
    idx = PackageIndex(PAGES)
    idx.refresh()
    assert idx.data["format"] == INDEX_FORMAT and {d["via"] for d in idx.schemas["UsrOrder"]["deps"]} == {"parent", "lookup"}
    assert idx.dependents("UsrOrder")[0][:2] == ("page", "UsrOrder_FormPage")
    assert Edge.from_dict(idx.schemas["UsrOrder"]["deps"][1]).line().startswith("object ")
    found = find_schema(PAGES, "UsrOrder")
    assert "  depends on: object BaseEntity  parent; object Contact  lookup" in found and "  dependents: page UsrOrder_FormPage (data-source); page UsrTests_FormPage (data-source)" in found


TEXT_CS = """namespace Terrasoft.Configuration
{
	[EntityEventListener(SchemaName = "UsrOrder")]
	public class UsrOrderListener : BaseEntityEventListener
	{
		public override void OnSaving(object sender, EntityBeforeEventArgs e) {
			var order = (Entity)sender;
			Guid status = order.GetTypedColumnValue<Guid>("UsrStatusId");
			order.SetColumnValue("UsrNope", 1);
		}
	}

	public class UsrQueries
	{
		public void Run(UserConnection uc) {
			var esq = new EntitySchemaQuery(uc.EntitySchemaManager, "UsrPkg");
			esq.AddColumn("UsrName");
			esq.AddColumn("UsrContactLookup.Name");
			var update = new Update(uc, "UsrOrderStatus").Set("Name", Column.Parameter("x")).Set("UsrMissing", Column.Parameter(1));
			var joined = new Select(uc).Column("Id").From("UsrOrder").InnerJoin("UsrPkg").On("UsrPkg", "Id").IsEqual("UsrOrder", "Id");
			var process = uc.ProcessSchemaManager.GetInstanceByName("UsrTest_Process");
			string again = "UsrOrderStatus";
			// "UsrOrder" in a comment is no word of the code
		}
	}
}
"""


def test_text_extractors_add_words_of_code_sql_and_rules():
    import shutil
    import tempfile
    from creatio_schemas.describe.deps import Edge, Resolver, _merge, _sql_tables
    from creatio_schemas.process import ProcessSchema
    from creatio_schemas.workspace import Workspace

    assert [e.ref for e in _merge([Edge("object", "A", None, "x", "text"), Edge("object", "a", "u1", "x", "name"), Edge("object", "A", None, "x", "text")])] == ["name"]
    assert _merge([Edge("object", "A", None, "x", "text"), Edge("object", "A", "u1", "x", "uid")])[0].to_uid == "u1"
    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp) / "packages" / "UsrPkg"
        shutil.copytree(PAGES, pkg)
        (pkg / "Files" / "cs").mkdir(parents=True)
        (pkg / "Files" / "cs" / "UsrText.cs").write_text(TEXT_CS, encoding="utf-8")
        out = dependencies_out(pkg, "Files/cs/UsrText.cs")
        assert "  object UsrOrder  listener: UsrOrderListener, UsrStatus, UsrNope?  [name]" in out, out  # UsrStatusId is the lookup UsrStatus
        assert "  object UsrPkg  esq: UsrName, UsrContactLookup.Name  [name]" in out  # a path: its first part is checked
        assert "  object UsrOrderStatus  query: Name, UsrMissing?  [name]" in out
        assert "  object UsrOrder  query  [name]" in out and "  object UsrPkg  query  [name]" in out  # a join: two tables, no columns
        assert "UsrTest_Process" not in out and "string" not in out  # another manager's schema; a word already reached
        (pkg / "Files" / "cs" / "UsrText.cs").write_text(TEXT_CS.replace('"UsrOrderStatus";', '"UsrTests_FormPage"; string w = "UsrOrderStatus" + "x";')
                                                       .replace('new Update(uc, "UsrOrderStatus")', 'new Update(uc, "UsrOther")'), encoding="utf-8")
        out = dependencies_out(pkg, "Files/cs/UsrText.cs")
        assert "  object UsrOrderStatus  string  [text]" in out and "UsrTests_FormPage" not in out, out  # a page name is no object
        # SQL: tables of every statement form, quoted or not; a comment, a string and a CTE are not tables
        r = Resolver(Workspace(pkg))
        sql = ('-- update "UsrPkg"\nwith cte as (select 1)\ninsert into "UsrOrder" ("Name") select "Name" from cte join usrorderstatus s on true;\n'
               "update [dbo].[UsrPkg] set x = 'from \"Contact\"';\ndelete from public.\"Contact\";\nalter table if exists \"UsrNoSuch\" add y int;\n")
        assert [e.line() for e in _sql_tables(sql, r)] == ["object UsrOrder  table  [text]", "object UsrOrderStatus  table  [text]",
                                                           "object UsrPkg  table  [text]", "object Contact  table  [text]"]
        # Freedom page: a workspace client schema in SCHEMA_DEPS is a module; a package of the devkit is not
        page = pkg / "Schemas" / "UsrTests_FormPage" / "UsrTests_FormPage.js"
        page.write_text(page.read_text(encoding="utf-8").replace("/**SCHEMA_DEPS*/[]", '/**SCHEMA_DEPS*/["@creatio-devkit/common", "UsrOrder_FormPage"]', 1), encoding="utf-8")
        assert "  page UsrOrder_FormPage  module  [name]" in dependencies_out(pkg, "UsrTests_FormPage")
    # a process script task: the same words, the element first
    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp) / "packages" / "UsrPkg"
        shutil.copytree(PROCS, pkg)
        proc = ProcessSchema(pkg, "UsrProcess_0d4c445")
        proc.add_element("script", "ScriptTask1")
        proc.set_script("ScriptTask1", 'var esq = new EntitySchemaQuery(UserConnection.EntitySchemaManager, "Contact");\nesq.AddColumn("Name");\nesq.AddColumn("UsrNope");\nreturn true;')
        proc.save()
        contact = next(l for l in dependencies_out(pkg, "UsrProcess_0d4c445").splitlines() if l.startswith("  object Contact  esq:"))
        assert contact == "  object Contact  esq: ScriptTask1, Name, UsrNope?  [name]", contact  # a stock object: the stock catalogue's columns (S20-T04)
    # rules: an object's rule names its columns; a page rule's attributes reach the data source's object
    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp) / "packages" / "UsrPkg"
        shutil.copytree(RULES, pkg)
        assert "  object UsrPkg  column: UsrNumber, UsrIsActive, UsrName, UsrComment, UsrContactLookup, UsrAccount, UsrContactLookup.Account, UsrAmount  [name]" in dependencies_out(pkg, "UsrPkgBusinessRule")
        out = dependencies_out(pkg, "UsrTests_FormPageBusinessRule")
        assert "  page UsrTests_FormPage  target" in out and "  object UsrPkg  column: UsrIsActive, UsrNumber  [name]" in out
    # Classic: the columns rules bind, a lookup attribute's object; messages give nothing
    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp) / "packages" / "UsrPkg"
        shutil.copytree(CLASSIC, pkg)
        js = pkg / "Schemas" / "UsrOrderPage" / "UsrOrderPage.js"
        js.write_text(js.read_text(encoding="utf-8").replace('"UsrStatus": {\n\t\t\t\t\tlookupListConfig', '"UsrStatus": {\n\t\t\t\t\treferenceSchemaName: "UsrOrderStatus",\n\t\t\t\t\tlookupListConfig', 1)
                      .replace("businessRules: /**SCHEMA_BUSINESS_RULES*/{}", 'businessRules: /**SCHEMA_BUSINESS_RULES*/{"UsrTotal": {"Bind": {"conditions": '
                               '[{"leftExpression": {"attribute": "UsrAmount"}}]}}}', 1), encoding="utf-8")
        out = dependencies_out(pkg, "UsrOrderPage")
        assert "  object UsrOrderStatus  lookup: UsrStatus  [name]" in out, out
        assert "  object UsrOrder  rule: UsrTotal?, UsrAmount?, UsrStatus?, UsrNumber?  [name]" in out  # UsrOrder is not in this workspace: every column ends with ?
        assert "UsrOrderTotalChanged" not in out


def test_export_writes_a_file_per_item_and_removes_the_gone_ones():
    import shutil
    import tempfile
    from creatio_schemas.describe.export import default_out, export

    assert default_out(PAGES) == PAGES.resolve().parent / ".creatio-export"  # a package folder outside `packages/`: next to it
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "export"
        (out / "UsrPkg").mkdir(parents=True)
        (out / "UsrPkg" / "UsrGone.md").write_text("an item that no longer exists", encoding="utf-8")
        (out / "UsrPkg" / "notes.txt").write_text("not ours", encoding="utf-8")
        (out / "OtherPkg").mkdir()
        (out / "OtherPkg" / "X.md").write_text("another package's file", encoding="utf-8")
        assert export(PAGES, out) == f"6 files written, 1 removed, 1 package(s) -> {out}"
        files = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
        assert files == ["OtherPkg/X.md", "UsrPkg/UsrOrder.md", "UsrPkg/UsrOrderStatus.md", "UsrPkg/UsrOrder_FormPage.md",
                         "UsrPkg/UsrPkg.md", "UsrPkg/UsrTests_FormPage.md", "UsrPkg/_package.md", "UsrPkg/notes.txt"], files
        text = (out / "UsrPkg" / "UsrOrder.md").read_bytes().decode("utf-8")
        assert "\r" not in text and text.startswith("# UsrOrder\n\n```text\nUsrOrder: 'Order'  own object")
        assert "\n## Depends on\n\n```text\nobject BaseEntity  parent\n" in text
        assert "\n## Dependents\n\n```text\npage UsrOrder_FormPage  data-source: PDS  [name]\n" in text
        assert f"\n## Files\n\n```text\n{PAGES.resolve() / 'Resources' / 'UsrOrder.Entity' / 'resource.en-US.xml'}  (" in text
        assert "  page      UsrTests_FormPage" in (out / "UsrPkg" / "_package.md").read_text(encoding="utf-8")
    # a data binding goes to Data/, an unreadable item is one line, the package file lists it; a gone binding's folder goes
    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp) / "packages" / "UsrPkg"
        shutil.copytree(DATA, pkg)
        (pkg / "Data" / "UsrEmpty").mkdir()
        shutil.copy(pkg / "Data" / "UsrStatus" / "descriptor.json", pkg / "Data" / "UsrEmpty" / "descriptor.json")
        (pkg / "Data" / "UsrEmpty" / "data.json").write_bytes(b"")
        out = Path(tmp) / "export"
        export(pkg, out)
        assert (out / "UsrPkg" / "Data" / "UsrEmpty.md").read_text(encoding="utf-8").startswith("Data/UsrEmpty: cannot read: ") and \
            len((out / "UsrPkg" / "Data" / "UsrEmpty.md").read_text(encoding="utf-8").splitlines()) == 1
        assert "## Cannot read" in (out / "UsrPkg" / "_package.md").read_text(encoding="utf-8")
        assert "binds UsrOrderStatus" in (out / "UsrPkg" / "Data" / "UsrStatus.md").read_text(encoding="utf-8")
        assert "data Data/UsrStatus  binds: Id, Name, Description  [name]" in (out / "UsrPkg" / "UsrOrderStatus.md").read_text(encoding="utf-8")
        for name in [p.name for p in (pkg / "Data").iterdir()]:
            shutil.rmtree(pkg / "Data" / name)
        assert export(pkg, out).split(", ")[1] == "4 removed" and not (out / "UsrPkg" / "Data").exists()
        assert default_out(pkg) == Path(tmp).resolve() / ".creatio-export"
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            assert main(["export", str(pkg), "--out", str(out)]) == 0
        assert stdout.getvalue().startswith("2 files written, 0 removed")


def dependencies_out(path, name):
    from creatio_schemas.describe.deps import dependencies
    return dependencies(path, name, "out", limit=0)


def test_impact_lists_dependents_and_the_locks_of_other_active_tasks():
    import json
    import tempfile
    from creatio_schemas.describe.deps import impact
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        for folder, data, done in (("013-other", {"schemas": ["UsrOrder_FormPage"], "affects": ["UsrOrderStatus"]}, False),
                                   ("011-done", {"schemas": ["UsrOrder"]}, True), ("012-this", {"schemas": ["UsrOrder"]}, False)):
            (t / folder).mkdir()
            (t / folder / "schemas.json").write_text(json.dumps(data), encoding="utf-8")
            if done:
                (t / folder / "success-report.md").write_text("ok", encoding="utf-8")
        text, conflicts = impact(PAGES, ["UsrOrder", "UsrOrderStatus"], t, "012-this")
        assert conflicts == 1 and "    page UsrOrder_FormPage (data-source) - task 013-other changes it" in text
        assert "UsrOrderStatus  object in UsrPkg  [task 013-other depends on it]" in text and "    object UsrOrder (lookup)" in text
        assert "affects: UsrOrder_FormPage, UsrTests_FormPage" in text and "011-done" not in text  # a finished task locks nothing; what the task changes is not what it affects
        assert text.endswith("2 dependents of 2 schema(s); 1 conflict(s) with other active tasks")
        md, _ = impact(PAGES, ["UsrOrder"], t, "012-this", md=True)
        assert md.splitlines()[:4] == ["## Impact", "", "| Schema | Dependents | Other active tasks |", "|---|---|---|"]
        assert "| `UsrOrder` | page UsrOrder_FormPage (data-source), page UsrTests_FormPage (data-source) | task 013-other changes it (page UsrOrder_FormPage) |" in md
        # the current task's own lock is not a conflict; a schema another task changes is
        assert impact(PAGES, ["UsrOrder"], t, "012-this")[1] == 1 and impact(PAGES, ["UsrOrder_FormPage"], t, "012-this")[1] == 1
        assert impact(PAGES, ["UsrOrder_FormPage"], t, "013-other")[1] == 0
    text, conflicts = impact(PAGES, ["Nope"])
    assert text.startswith("Nope  (not in the workspace)") and conflicts == 0 and "locks not checked" in text
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert main(["impact", str(PAGES), "UsrOrderStatus", "--md"]) == 0
    assert out.getvalue().startswith("## Impact")


def test_cli():
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert main(["deps", str(PAGES), "UsrOrder", "--in", "--kind", "page"]) == 0
    assert out.getvalue().splitlines()[:3] == ["UsrOrder  object in UsrPkg", "dependents:", "  page UsrOrder_FormPage  data-source: PDS  [name]"]
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert main(["package", str(PAGES), "--kind", "page"]) == 0
        assert main(["find", str(PAGES), "UsrOrder"]) == 0
        assert main(["item", str(PAGES), "UsrOrder", "columns type=Lookup"]) == 0
    assert "UsrTests_FormPage" in out.getvalue() and "UsrStatus" in out.getvalue()
    with contextlib.redirect_stderr(io.StringIO()):
        assert main(["item", str(PAGES), "UsrOrder", "nonsense"]) == 2




def test_schema_diff_names_the_added_column_against_head_and_a_folder():
    import shutil
    import subprocess
    import tempfile

    from creatio_schemas.describe.diff import diff_lines, schema_diff
    from creatio_schemas.entity import EntitySchema

    assert diff_lines(["UsrA  Text 'A'", "UsrB  Text 'B'", "flows:"], ["UsrA  Text 'A2'", "UsrC  Int 'C'", "flows:"]) == [
        "~ UsrA  Text 'A' -> Text 'A2'", "- UsrB Text 'B'", "+ UsrC Int 'C'"]
    assert diff_lines(["x -> y", "x -> z"], ["x -> z", "x -> w"]) == ["- x -> y", "+ x -> w"]  # a repeated key: whole lines
    git = ["git", "-c", "user.email=t@t", "-c", "user.name=t"]
    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp) / "packages" / "UsrPkg"
        shutil.copytree(OBJECTS, pkg)
        subprocess.run(git + ["init", "-q"], cwd=tmp, check=True)
        subprocess.run(git + ["add", "."], cwd=tmp, check=True)
        subprocess.run(git + ["commit", "-q", "-m", "base"], cwd=tmp, check=True)
        assert schema_diff(pkg) == "UsrPkg: no differences against HEAD"
        entity = EntitySchema(pkg, "UsrOrder")
        entity.add_column("UsrWeight", "Float", "Weight")
        entity.save()
        shutil.rmtree(pkg / "Schemas" / "UsrOrderStatus")
        text = schema_diff(pkg)
        lines = text.splitlines()
        assert lines[0] == "UsrOrder  object" and lines[1] == "  columns" and "    + UsrWeight Float 'Weight'" in lines
        assert "- UsrOrderStatus  object (removed)" in lines and text.count("+ UsrWeight") == 1  # the summary does not repeat it
        assert any(l.startswith("    ~ UsrStatus  Lookup -> UsrOrderStatus") and "Lookup -> c59697c2" in l for l in lines)  # its lookup lost its name
        assert lines[-1] == "UsrPkg against HEAD: 1 changed, 0 new, 1 removed; lines +1 -0 ~1"
        only = schema_diff(pkg, ["UsrOrder"], str(OBJECTS.parent))  # a folder of packages instead of git
        assert only.splitlines()[0] == "UsrOrder  object" and "(removed)" not in only
        with contextlib.redirect_stdout(io.StringIO()) as out:
            assert main(["diff", str(pkg), "UsrOrder", "--against", str(OBJECTS)]) == 0
        assert "+ UsrWeight Float 'Weight'" in out.getvalue()
        shutil.move(pkg / "Schemas" / "UsrOrder", pkg / "Schemas" / "UsrOrder2")  # the same UId under a new name
        text = schema_diff(pkg)
        assert text.splitlines()[0] == "~ UsrOrder -> UsrOrder2  object (renamed)" and "+ UsrWeight Float" in text, text
        assert "- UsrOrder  object (removed)" not in text and "+ UsrOrder2  object (new)" not in text
        assert schema_diff(pkg, ["UsrOrder2"]).splitlines()[0].startswith("~ UsrOrder -> UsrOrder2")
        try:
            schema_diff(pkg, ["UsrNoSuch"])
            raise AssertionError("an unknown item must be refused")
        except FileNotFoundError as e:
            assert "UsrNoSuch" in str(e)
        try:
            schema_diff(pkg, against="no-such-rev")
            raise AssertionError("an unknown revision must be refused")
        except QueryError as e:
            assert "no-such-rev" in str(e)


def test_impact_filters_dependents_by_kind():
    from creatio_schemas.describe.deps import impact
    text, _ = impact(PAGES, ["UsrOrder"], kind="page")
    lines = [l.strip() for l in text.splitlines() if l.startswith("    ")]
    assert lines and all(l.startswith("page ") for l in lines), lines
    with contextlib.redirect_stdout(io.StringIO()) as out:
        assert main(["impact", str(PAGES), "UsrOrder", "--kind", "nope"]) == 0
    assert "dependents: none typed" in out.getvalue()


def test_uids_resolve_both_ways_and_name_a_text():
    from creatio_schemas.describe.uids import resolve
    from creatio_schemas.process import ProcessSchema
    from creatio_schemas.workspace import Workspace
    ws = Workspace(PAGES)
    order = ws.find("UsrOrder", "EntitySchemaManager")[0]["uid"]
    status = ws.column_uids("UsrOrder")["UsrStatus"]
    assert resolve(PAGES, order).startswith(f"{order}  schema UsrOrder (Entity) in UsrPkg"), resolve(PAGES, order)
    assert resolve(PAGES, status) == f"{status}  column UsrOrder.UsrStatus"
    assert resolve(PAGES, "UsrOrder.UsrStatus") == f"{status}  column UsrOrder.UsrStatus"
    assert resolve(PAGES, "UsrOrder").startswith(f"{order}  schema UsrOrder")
    p = ProcessSchema(PROCS, "UsrProcess_0d4c445")
    start = p.element("StartEvent1")["UId"].lower()
    assert resolve(PROCS, start) == f"{start}  process UsrProcess_0d4c445 element StartEvent1 (StartEvent)"
    assert resolve(PROCS, "UsrProcess_0d4c445.StartEvent1").startswith(start)
    text = resolve(PROCS, f"[#[IsOwnerSchema:false].[Element:{{{start}}}].[Parameter:{{00000000-0000-0000-0000-000000000001}}]#]")
    assert "not in the workspace" in text and text.splitlines()[-1] == "[#[IsOwnerSchema:false].[Element:{StartEvent1}].[Parameter:{00000000-0000-0000-0000-000000000001}]#]", text
    assert "not in the workspace" in resolve(PAGES, "UsrNoSuch.X")
    with contextlib.redirect_stdout(io.StringIO()) as out:
        assert main(["uid", str(PAGES), "UsrOrder.UsrStatus"]) == 0
    assert status in out.getvalue()


def test_diff_forms_of_the_platform_files_and_located_errors():
    import json
    import shutil
    import tempfile
    from creatio_schemas.workspace import parse_diff
    column = '{\r\n  "UId": "u1",\r\n  "A2": "UsrCode"\r\n}'
    # an operation line written before the value's last `}`, and a blank last line: both read as the platform means them
    text = '+ MetaData.Schema.D2 {\r\n  "UId": "u1",\r\n~ MetaData.Schema.D2 [order]\r\n  "A2": "UsrCode"\r\n}\r\n= MetaData.Schema.A2 "UsrX"\r\n\r\n'
    assert parse_diff(text) == [("+", "MetaData.Schema.D2", column), ("~", "MetaData.Schema.D2", "[order]"), ("=", "MetaData.Schema.A2", '"UsrX"')]
    assert parse_diff(text.replace("\r\n", "\n")) == parse_diff(text)  # an LF file reads the same
    assert json.loads(parse_diff(text)[0][2]) == {"UId": "u1", "A2": "UsrCode"}
    assert parse_diff('+ MetaData.Schema.D2 {"A2": "a{b"}\r\n- MetaData.Schema.D2 x') == [("+", "MetaData.Schema.D2", '{"A2": "a{b"}'), ("-", "MetaData.Schema.D2", "x")]  # braces in strings
    tmp = Path(tempfile.mkdtemp())
    try:
        (tmp / "Schemas" / "UsrX").mkdir(parents=True)
        (tmp / "Schemas" / "UsrX" / "metadata.json").write_bytes('﻿{"MetaData": {"Ж": 1,, }}'.encode("utf-8"))
        try:
            json.loads((tmp / "Schemas" / "UsrX" / "metadata.json").read_text(encoding="utf-8-sig"))
        except ValueError as e:
            assert located(tmp, ["Schemas/UsrX/descriptor.json", "Schemas/UsrX/metadata.json"], e).startswith("Schemas/UsrX/metadata.json:25: JSONDecodeError: ")
        (tmp / "Schemas" / "UsrX" / "body.js").write_bytes(b"var a = '\x98';")  # a byte neither UTF-8 nor cp1251 decodes
        try:
            (tmp / "Schemas" / "UsrX" / "body.js").read_bytes().decode("cp1251")
        except UnicodeDecodeError as e:
            assert located(tmp, ["Schemas/UsrX/body.js"], e).startswith("Schemas/UsrX/body.js:9: UnicodeDecodeError: ")
        try:
            {}["ManagerName"]
        except KeyError as e:
            assert located(tmp, [], e) == f"KeyError: 'ManagerName' (raised at {Path(__file__).name}:{e.__traceback__.tb_lineno})"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _repo(root: Path, package_src: Path) -> Path:
    """A throwaway git repository holding <root>/packages/UsrPkg, committed once (the test's own, never a workspace)."""
    import shutil
    import subprocess
    pkg = root / "packages" / "UsrPkg"
    shutil.copytree(package_src, pkg)
    git = ["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", "-c", "core.autocrlf=false"]
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "core.autocrlf", "false"], cwd=root, check=True)
    subprocess.run(git + ["add", "-A"], cwd=root, check=True)
    subprocess.run(git + ["commit", "-q", "-m", "fixture"], cwd=root, check=True)
    return pkg


def test_review_sorts_a_pulled_package_and_restores_what_is_not_kept():
    import json
    import shutil
    import subprocess
    import tempfile
    from creatio_schemas.describe.diff import schema_diff
    from creatio_schemas.describe.review import render, review
    root = Path(tempfile.mkdtemp())
    try:
        pkg = _repo(root, OBJECTS)
        meta = pkg / "Schemas" / "UsrOrderStatus" / "metadata.json"
        raw = meta.read_bytes()
        meta.write_bytes(raw.replace(b"\r\n", b"\n") if b"\r\n" in raw else raw.replace(b"\n", b"\r\n"))  # line endings only
        desc = pkg / "descriptor.json"
        data = json.loads(desc.read_text(encoding="utf-8-sig"))
        dropped = data["Descriptor"]["DependsOn"].pop()["Name"]
        desc.write_text(json.dumps(data, indent=2), encoding="utf-8")  # a dependency dropped, the BOM gone
        order = pkg / "Schemas" / "UsrOrder" / "descriptor.json"
        order.write_text(order.read_text(encoding="utf-8-sig").replace('"Name": "UsrOrder"', '"Name": "UsrOrder", "Caption": "Changed"', 1), encoding="utf-8")
        (pkg / "Resources" / "UsrGone.Entity").mkdir()
        (pkg / "Resources" / "UsrGone.Entity" / "resource.en-US.xml").write_text("<x/>", encoding="utf-8")
        answer = review(pkg)
        assert answer["eol_only"] == ["Schemas/UsrOrderStatus/metadata.json"], answer["eol_only"]
        assert answer["dependencies"] == {"dropped": [dropped], "added": []} and answer["orphans"] == ["UsrGone.Entity"]
        assert answer["untracked"] == ["Resources/UsrGone.Entity/resource.en-US.xml"] and answer["content"] == schema_diff(pkg)
        text = render(answer)
        assert text.startswith("UsrPkg: 4 changed file(s) against HEAD\nline endings or BOM only (1) - nothing changed:") and f"dependencies: dropped {dropped}" in text, text
        assert "resource folders with no schema: Resources/UsrGone.Entity" in text and "would restore" not in text
        plan = review(pkg, keep=["UsrOrder"])
        assert sorted(plan["restore"]) == ["Schemas/UsrOrderStatus/metadata.json", "descriptor.json"] and not plan["applied"], plan["restore"]
        assert "would restore (run with --apply) from HEAD (2):\n  git checkout HEAD -- " in render(plan)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            assert main(["review", str(pkg), "--keep", "UsrOrder", "--apply"]) == 0
        assert "restored from HEAD (2):" in out.getvalue()
        status = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, check=True).stdout
        assert "UsrOrder/descriptor.json" in status and "descriptor.json\n" not in status.replace("UsrOrder/descriptor.json", "") and "UsrOrderStatus" not in status, status
        assert review(pkg)["dependencies"] == {"dropped": [], "added": []}  # the dependency is back
        with contextlib.redirect_stderr(io.StringIO()):
            assert main(["review", str(root)]) == 2  # not a package folder
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_precommit_refuses_archives_binaries_large_and_stray_files():
    import shutil
    import subprocess
    import tempfile
    from creatio_schemas.describe.review import precommit
    root = Path(tempfile.mkdtemp())
    try:
        pkg = _repo(root, OBJECTS)  # an assembly package (Type 1)
        (pkg / "Files" / "Bin").mkdir(parents=True)
        (pkg / "Files" / "Bin" / "UsrPkg.dll").write_bytes(b"MZ")
        (pkg / "Files" / "UsrPkg.pdb").write_bytes(b"x")
        (pkg / "Files" / "backup.zip").write_bytes(b"PK")
        (pkg / "Files" / "big.json").write_bytes(b"0" * (5 * 1024 * 1024 + 1))
        (root / "notes.txt").write_text("x", encoding="utf-8")
        (root / "README.md").write_text("x", encoding="utf-8")
        (root / "unstaged.rar").write_bytes(b"x")
        subprocess.run(["git", "add", "packages", "notes.txt", "README.md"], cwd=root, check=True)
        problems = precommit(root)
        assert problems == ["notes.txt: outside packages/ (known roots: .gitignore, .gitattributes, .editorconfig, README.md, project.json, .clio, .vscode, tasks, docs)",
                            "packages/UsrPkg/Files/UsrPkg.pdb: a binary outside Files/Bin of an assembly package",
                            "packages/UsrPkg/Files/backup.zip: an archive",
                            "packages/UsrPkg/Files/big.json: 5.0 MB (over 5 MB)"], problems
        with contextlib.redirect_stdout(io.StringIO()) as out:
            assert main(["precommit", str(root)]) == 1
        assert "backup.zip: an archive" in out.getvalue()
        subprocess.run(["git", "reset", "-q"], cwd=root, check=True)
        assert precommit(root) == []
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _layer_workspace(root: Path, packages: dict) -> Path:
    """packages: {name: (depends_on, {schema: replacing})} -> <root>/packages/<name>/ with the descriptors only."""
    import json
    for name, (deps, schemas) in packages.items():
        pkg = root / "packages" / name
        pkg.mkdir(parents=True)
        (pkg / "descriptor.json").write_text("﻿" + json.dumps({"Descriptor": {"UId": f"pkg-{name}", "Name": name,
                                                                                   "DependsOn": [{"UId": f"pkg-{d}", "Name": d} for d in deps]}}), encoding="utf-8")
        for schema, replacing in schemas.items():
            (pkg / "Schemas" / schema).mkdir(parents=True)
            (pkg / "Schemas" / schema / "descriptor.json").write_text(json.dumps({"Descriptor": {
                "UId": f"uid-{name}-{schema}", "Name": schema, "ExtendParent": replacing, "ManagerName": "EntitySchemaManager"}}), encoding="utf-8")
    return root


def test_layers_in_order_by_dependencies_and_by_the_site():
    import shutil
    import tempfile
    from creatio_schemas.describe.merge import layers_in_order

    root = Path(tempfile.mkdtemp())
    try:
        # UsrA <- UsrB, UsrA <- UsrC (siblings); UsrD (no layer) <- UsrB, UsrC; UsrE <- UsrD: E comes after both through D
        _layer_workspace(root, {
            "UsrE": (["UsrD"], {"Contact": True}),
            "UsrC": (["UsrA"], {"Contact": True}),
            "UsrB": (["UsrA", "CrtBase"], {"Contact": True, "UsrThing": True}),
            "UsrD": (["UsrB", "UsrC"], {}),
            "UsrA": (["CrtBase"], {"Contact": True, "UsrThing": False}),
        })
        layers = layers_in_order(root, "Contact")
        assert [x.package for x in layers] == ["UsrA", "UsrB", "UsrC", "UsrE"], layers
        assert [x.siblings for x in layers] == [(), ("UsrC",), ("UsrB",), ()]
        assert all(x.replacing and x.source == "workspace" for x in layers) and layers[0].uid == "uid-UsrA-Contact"
        assert layers[3].folder == root / "packages" / "UsrE" / "Schemas" / "Contact"
        own = layers_in_order(root / "packages", "UsrThing")
        assert [(x.package, x.replacing) for x in own] == [("UsrA", False), ("UsrB", True)]
        assert layers_in_order(root, "Contact", manager="ClientUnitSchemaManager") == [] and layers_in_order(root, "UsrNope") == []
        # the site's order wins; the vendor base has no folder; UsrE is not on the site yet: after the site's copies
        site = [_row("CrtBase", "1", "9", ext="false"), _row("UsrA", "0", "4"), _row("UsrC", "0", "3"), _row("UsrB", "0", "2")]
        for row in site:
            row["manager"] = "EntitySchemaManager"
        env = FakeLayersEnv(site)
        layers = layers_in_order(root, "Contact", env)
        assert [(x.package, x.source) for x in layers] == [("CrtBase", "site"), ("UsrA", "site"), ("UsrC", "site"), ("UsrB", "site"), ("UsrE", "workspace")]
        assert layers[0].folder is None and not layers[0].replacing and layers[0].uid == "" and layers[2].uid == "uid-UsrC-Contact"
        assert all(x.siblings == () for x in layers) and len(env.sql_text) == 2 and '"HierarchyLevel"' in env.sql_text[1]

        class LevelEnv(FakeLayersEnv):  # the runtime order: HierarchyLevel, then the name - UsrB before UsrC on one level
            def sql(self, text):
                self.sql_text.append(text)
                levels = {"UsrA": "4", "UsrB": "5", "UsrC": "5"}
                return [{"package": p, "level": v} for p, v in levels.items()] if "HierarchyLevel" in text else self.rows
        layers = layers_in_order(root, "Contact", LevelEnv(site))
        assert [x.package for x in layers] == ["CrtBase", "UsrA", "UsrB", "UsrC", "UsrE"]
        assert list(root.rglob(".creatio-index")) == []  # read-only: nothing written into the workspace
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _two_layer_workspace(root: Path) -> None:
    """The objects fixture (a replacing Account in UsrPkg, its fetched base) plus UsrPkg2, a second layer that adds UsrRating."""
    import json
    import shutil
    from creatio_schemas import EntitySchema

    fixtures = TOOLS / "objects" / "tests" / "fixtures"
    shutil.copytree(fixtures / "UsrPkg", root / "packages" / "UsrPkg")
    shutil.copytree(fixtures / ".creatio-bases", root / ".creatio-bases")
    shutil.copytree(fixtures / ".creatio-bases" / "UsrPkg", root / ".creatio-bases" / "UsrPkg2")
    second = root / "packages" / "UsrPkg2"
    shutil.copytree(fixtures / "UsrPkg", second)
    shutil.rmtree(second / "Schemas")
    shutil.rmtree(second / "Resources")
    d = json.loads((second / "descriptor.json").read_text("utf-8-sig"))
    d["Descriptor"].update({"Name": "UsrPkg2", "UId": "11111111-2222-4333-8444-555555555555", "DependsOn": [{"Name": "UsrPkg", "UId": "x"}]})
    (second / "descriptor.json").write_text(json.dumps(d), "utf-8")
    layer = EntitySchema.create_replacing(second, "Account")
    layer.add_column("UsrRating", "Integer", "Rating", default=3, required=True)
    layer.save()


def test_snapshot_disk_lines_are_the_effective_object_over_the_layers():
    import shutil
    import tempfile
    from creatio_schemas.integrity import compare, snapshot

    root = Path(tempfile.mkdtemp())
    try:
        _two_layer_workspace(root)
        lines = snapshot(root, "Account")
        assert lines[0] == "layers: UsrPkg > UsrPkg2", lines[0]
        columns = {l.split()[1]: l for l in lines if l.startswith("column ")}
        assert "Name" in columns and "GPSE" in columns, "the columns of the base and of the first layer"
        assert columns["UsrRating"].endswith("Integer required default 3") and columns["Owner"].split()[3:5] == ["Lookup", "lookup"]
        assert any(l.startswith("index ") for l in lines)
        assert compare(lines, snapshot(root, "Account")) == []  # equal snapshots compare empty
        # a copy of the workspace with the second layer's column removed shows as `- column UsrRating ...`
        other = Path(tempfile.mkdtemp())
        try:
            shutil.rmtree(other)
            shutil.copytree(root, other)
            from creatio_schemas import EntitySchema
            layer = EntitySchema(other / "packages" / "UsrPkg2", "Account")
            layer.remove_column("UsrRating")
            layer.save()
            diff = compare(lines, snapshot(other, "Account"))
            assert len(diff) == 1 and diff[0].startswith("- column UsrRating "), diff
        finally:
            shutil.rmtree(other, ignore_errors=True)
        try:
            snapshot(root, "UsrNope")
        except KeyError as e:
            assert "UsrNope" in str(e)
        else:
            raise AssertionError("expected KeyError")
        # the base of a replacing layer that is neither on disk nor fetched stops the snapshot
        shutil.rmtree(root / ".creatio-bases")
        try:
            snapshot(root, "Account")
        except RuntimeError as e:
            assert "objects.py base" in str(e)
        else:
            raise AssertionError("expected RuntimeError")
    finally:
        shutil.rmtree(root, ignore_errors=True)


SHORT_TEXT, LOOKUP = "325a73b8-0f47-44a0-8412-7606f78003ac", "b295071f-7ea9-4e62-8d1a-919bf3732ff2"
PAGE_BODY = """define("UsrOrderPage", [], function() {{
	return {{
		entitySchemaName: "UsrOrder",
		methods: {{{methods}
		}},
		diff: /**SCHEMA_DIFF*/[{diff}]/**SCHEMA_DIFF*/
	}};
}});
"""


def _object_layer(pkg: Path, name: str, columns: list, replacing: bool = True) -> None:
    """A replacing object (`+ MetaData.Schema.D2 {column}` lines) or an own one; columns: (name, uid, type[, ref uid])."""
    import json
    folder = pkg / "Schemas" / name
    folder.mkdir(parents=True)
    uid = f"00000000-0000-4000-8000-{abs(hash((pkg.name, name))) % 10 ** 12:012d}"
    (folder / "descriptor.json").write_text(json.dumps({"Descriptor": {"UId": uid, "Name": name, "Parent": {"UId": "16be3651-8fe2-4159-8dd0-a803d4683dd3", "Name": name},
                                                                        "ExtendParent": replacing, "ManagerName": "EntitySchemaManager"}}), encoding="utf-8")
    lines = [f'= MetaData.Schema.UId "{uid}"']
    for col in columns:
        c = {"UId": col[1], "A2": col[0], "A3": uid, "A4": uid, "A5": f"pkg-{pkg.name}", "S2": col[2]}  # created / modified in this layer
        if len(col) > 3:
            c["S4"] = col[3]
        lines.append("+ MetaData.Schema.D2 " + json.dumps(c, indent=2).replace("\n", "\r\n"))
    (folder / "metadata.json").write_bytes(("\r\n".join(lines) + "\r\n").encode("utf-8"))


def _page_layer(pkg: Path, methods: dict, diff: list) -> None:
    import json
    folder = pkg / "Schemas" / "UsrOrderPage"
    folder.mkdir(parents=True)
    (folder / "descriptor.json").write_text(json.dumps({"Descriptor": {"UId": f"page-{pkg.name}", "Name": "UsrOrderPage", "ExtendParent": True,
                                                                        "Parent": {"UId": "base-page", "Name": "UsrOrderPage"}, "ManagerName": "ClientUnitSchemaManager"}}), encoding="utf-8")
    (folder / "metadata.json").write_text("{}", encoding="utf-8")
    body = PAGE_BODY.format(methods=",".join(f"\n\t\t\t{k}: function() {{\n\t\t\t\t{v}\n\t\t\t}}" for k, v in methods.items()),
                            diff=", ".join(json.dumps({"operation": op, "name": n}) for n, op in diff))
    (folder / "UsrOrderPage.js").write_text(body, encoding="utf-8")


def test_merge_plan_targets_conflicts_and_dependencies():
    import shutil
    import tempfile
    from creatio_schemas.describe.merge import _call_parent, merge_plan

    assert _call_parent("save: function() { Ext.bind(function() { this.callParent(arguments); }, this)(); }") == (True, False)
    assert _call_parent("save: function() { var x = this.callParent(arguments); return x; }") == (False, True)
    assert _call_parent("save: function() { if (a == this.callParent(arguments)) {} return this.callParent(arguments); }") == (False, False)
    root = Path(tempfile.mkdtemp())
    try:
        # UsrA <- UsrB, UsrA <- UsrC (siblings); UsrB also depends on UsrExtra, which the target gains
        _layer_workspace(root, {"UsrA": (["CrtBase"], {}), "UsrB": (["UsrA", "UsrExtra"], {}), "UsrC": (["UsrA"], {}), "UsrExtra": (["CrtBase"], {})})
        pk = root / "packages"
        status = "11111111-0000-4000-8000-000000000001"
        _object_layer(pk / "UsrA", "Contact", [("UsrA1", "a1000000-0000-4000-8000-000000000001", SHORT_TEXT)])
        _object_layer(pk / "UsrB", "Contact", [("UsrB1", "b1000000-0000-4000-8000-000000000001", SHORT_TEXT),
                                               ("UsrDup", "d1000000-0000-4000-8000-000000000001", SHORT_TEXT),
                                               ("UsrStatus", "b2000000-0000-4000-8000-000000000001", LOOKUP, status)])
        _object_layer(pk / "UsrC", "Contact", [("UsrDup", "d2000000-0000-4000-8000-000000000002", SHORT_TEXT)])
        _object_layer(pk / "UsrB", "UsrBStatus", [], replacing=False)
        (pk / "UsrB" / "Schemas" / "UsrBStatus" / "descriptor.json").write_text(
            '{"Descriptor": {"UId": "%s", "Name": "UsrBStatus", "ManagerName": "EntitySchemaManager"}}' % status, encoding="utf-8")
        _object_layer(pk / "UsrB", "UsrThing", [])  # in two siblings only: no package below both
        _object_layer(pk / "UsrC", "UsrThing", [])
        _page_layer(pk / "UsrA", {"onEntityInitialized": "this.callParent(arguments);"}, [("UsrName", "insert")])
        _page_layer(pk / "UsrB", {"onEntityInitialized": "var r = this.callParent(arguments); return r;"}, [("UsrName", "merge"), ("Tab1", "merge")])
        text, conflicts = merge_plan(root, limit=0)
        lines = text.splitlines()
        assert lines[0] == "Contact object: 3 layers, target UsrA", lines
        assert lines[1:4] == ["  layer UsrA: +1 column", "  layer UsrB: +3 columns", "  layer UsrC: +1 column"], lines
        assert "  siblings: UsrB, UsrC (order guessed)" in lines
        assert "  conflict lookup UsrStatus -> UsrBStatus (its package UsrB depends on the target): UsrB" in lines
        assert "  conflict column UsrDup (two UIds): UsrB and UsrC" in lines and "  depends: UsrA gains UsrExtra" in lines
        page = lines.index("UsrOrderPage classic: 2 layers, target UsrA")
        assert lines[page + 1:page + 3] == ["  layer UsrA: +1 element, +1 method", "  layer UsrB: +2 elements, +1 method"], lines
        assert "  conflict method onEntityInitialized: UsrA and UsrB" in lines and "  conflict callParent return value used, method onEntityInitialized: UsrB" in lines
        assert not any("conflict element" in l for l in lines)  # an insert below and a merge above is the usual form
        assert "UsrThing object: 2 layers, no common lowest package: UsrB, UsrC" in lines
        assert lines[-1] == "3 schemas, 3 layers to remove, 4 conflicts, 1 without a common lowest package" and conflicts == 4
        one, _ = merge_plan(root, ["contact", "UsrNope"])
        assert one.splitlines()[0] == "UsrNope: no copy in the workspace" and one.endswith("1 schemas, 2 layers to remove, 2 conflicts")
        assert merge_plan(root, ["UsrBStatus"])[0].splitlines()[0] == "UsrBStatus: 0 replacing layers in the workspace, nothing to merge"
        assert merge_plan(root, limit=2)[0].splitlines()[2].startswith("  ... ")
        assert list(root.rglob(".creatio-index")) == []
        with contextlib.redirect_stdout(io.StringIO()) as out:
            assert main(["merge-plan", str(root), "Contact"]) == 1
        assert "target UsrA" in out.getvalue()
        with contextlib.redirect_stdout(io.StringIO()):
            assert main(["merge-plan", str(root), "UsrBStatus"]) == 0
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_merge_writes_one_layer_and_stops_on_what_it_cannot_prove():
    import json
    import shutil
    import tempfile
    from creatio_schemas.describe.merge import merge_object, merged_diff, layers_in_order, platform_drops
    from creatio_schemas.diff import SchemaDiff
    from creatio_schemas.resources import Resources
    from creatio_schemas.workspace import parse_diff

    assert platform_drops("+", "MetaData.Schema.EG1.BK4.[\"x\"].C2") and platform_drops("-", "MetaData.Schema.D20.FA4")
    assert not platform_drops("-", "MetaData.Schema.EG1.C2") and not platform_drops("+", "MetaData.Schema.D20.FA4")
    root = Path(tempfile.mkdtemp())
    try:
        # UsrBase <- UsrA (target) <- UsrB <- UsrC; UsrB also depends on UsrExtra
        _layer_workspace(root, {"UsrBase": (["CrtBase"], {}), "UsrA": (["UsrBase"], {}), "UsrB": (["UsrA", "UsrExtra"], {}),
                                "UsrC": (["UsrB"], {}), "UsrExtra": (["CrtBase"], {})})
        pk = root / "packages"
        cols = {"UsrA": ["UsrA1"], "UsrB": ["UsrB1", "UsrB2"], "UsrC": ["UsrC1"]}
        for i, (name, names) in enumerate(cols.items()):
            _object_layer(pk / name, "Contact", [(c, f"c{i}{j}000000-0000-4000-8000-000000000000", SHORT_TEXT) for j, c in enumerate(names)])
            meta = pk / name / "Schemas" / "Contact" / "metadata.json"
            text = meta.read_bytes().decode("utf-8")
            meta.write_bytes(text.replace("\r\n", f'\r\n= MetaData.Schema.B6 "pkg-{name}"\r\n- MetaData.Schema.D20.FA4\r\n', 1).encode("utf-8"))
            (meta.parent / "properties.json").write_text(json.dumps({"Properties": {"IsVirtual": "False", "From": name}}), encoding="utf-8")
        for name, items in (("UsrA", {"Columns.UsrA1.Caption": "A one"}), ("UsrC", {"Columns.UsrA1.Caption": "A one, by C", "Columns.UsrC1.Caption": "C one"})):
            res = Resources.empty(pk / name / "Resources" / "Contact.Entity", ["en-US"])
            for k, v in items.items():
                res.set(k, v)
            for p, (t, b) in res.files().items():
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(("﻿" if b else "") + t, encoding="utf-8")
        snapshot = sorted(str(p) for p in root.rglob("*"))
        text, code = merge_object(root, "Contact")
        assert code == 0 and text.splitlines()[0] == "Contact object: 3 layers, target UsrA", text
        assert "write packages/UsrA/Schemas/Contact/metadata.json" in text and "delete packages/UsrB/Schemas/Contact" in text
        assert "delete packages/UsrC/Resources/Contact.Entity" in text and text.endswith("3 layers -> 1 (dry run; --apply writes)")
        assert sorted(str(p) for p in root.rglob("*")) == snapshot  # a dry run writes nothing
        layers = [x for x in layers_in_order(root, "Contact") if x.replacing]
        merged = merged_diff(layers, layers[0], "pkg-UsrA")
        ops = parse_diff(merged)
        assert [json.loads(v)["A2"] for op, p, v in ops if p == "MetaData.Schema.D2" and op == "+"] == ["UsrA1", "UsrB1", "UsrB2", "UsrC1"]
        assert [v for op, p, v in ops if p == "MetaData.Schema.UId"] == ['"uid-UsrA-Contact"'.replace("uid-UsrA-Contact", layers[0].uid)]
        assert [v for op, p, v in ops if p == "MetaData.Schema.B6"] == ['"pkg-UsrA"']
        assert [p for op, p, v in ops if "D20.FA4" in p] == ["MetaData.Schema.D20.FA4"]  # the top layer's only
        # the merged diff folds to the same columns as the layers one after another
        base = {"D2": [], "D20": {"FA4": True}}
        one_by_one = base
        for x in layers:
            one_by_one = SchemaDiff((x.folder / "metadata.json").read_text(encoding="utf-8")).apply(one_by_one)
        assert SchemaDiff(merged).apply(base)["D2"] == one_by_one["D2"]
        text, code = merge_object(root, "Contact", apply=True)
        assert code == 0 and text.endswith("merged Contact into UsrA: 3 layers -> 1"), text
        assert not (pk / "UsrB" / "Schemas" / "Contact").exists() and not (pk / "UsrC" / "Resources" / "Contact.Entity").exists()
        a = pk / "UsrA" / "Schemas" / "Contact"
        assert json.loads((a / "descriptor.json").read_text(encoding="utf-8"))["Descriptor"]["UId"] == layers[0].uid
        written = (a / "metadata.json").read_bytes().decode("utf-8")
        columns = [json.loads(v) for op, p, v in parse_diff(written) if p == "MetaData.Schema.D2"]
        assert {(c["A3"], c["A4"], c["A5"]) for c in columns} == {(layers[0].uid, layers[0].uid, "pkg-UsrA")}  # the merged layer owns them
        assert all(x.uid not in written for x in layers[1:]) and "pkg-UsrB" not in written and "\r\r" not in written
        assert json.loads((a / "properties.json").read_text(encoding="utf-8"))["Properties"]["From"] == "UsrC"  # the top layer's flags
        assert [d["Name"] for d in json.loads((pk / "UsrA" / "descriptor.json").read_text(encoding="utf-8-sig"))["Descriptor"]["DependsOn"]] == ["UsrBase", "UsrExtra"]
        merged_res = Resources(pk / "UsrA" / "Resources" / "Contact.Entity")
        assert merged_res.get("Columns.UsrA1.Caption") == "A one, by C" and merged_res.get("Columns.UsrC1.Caption") == "C one"
        assert merge_object(root, "Contact")[0].splitlines()[0] == "Contact: 1 replacing layer in the workspace, nothing to merge"

        # the UId rule the other way: a target without a layer takes the top layer's UId, every layer goes
        shutil.rmtree(root)
        _layer_workspace(root, {"UsrBase": (["CrtBase"], {}), "UsrA": (["UsrBase"], {}), "UsrB": (["UsrA"], {})})
        for name in ("UsrA", "UsrB"):
            _object_layer(pk / name, "Contact", [(f"{name}1", f"{name.lower()}-col", SHORT_TEXT)])
        top_uid = json.loads((pk / "UsrB" / "Schemas" / "Contact" / "descriptor.json").read_text(encoding="utf-8"))["Descriptor"]["UId"]
        assert merge_object(root, "Contact", target="UsrB")[1] == 1  # not below UsrA
        text, code = merge_object(root, "Contact", target="UsrBase", apply=True)
        assert code == 0 and "delete packages/UsrA/Schemas/Contact" in text and "delete packages/UsrB/Schemas/Contact" in text, text
        assert json.loads((pk / "UsrBase" / "Schemas" / "Contact" / "descriptor.json").read_text(encoding="utf-8"))["Descriptor"]["UId"] == top_uid
        assert '= MetaData.Schema.B6 "pkg-UsrBase"' in (pk / "UsrBase" / "Schemas" / "Contact" / "metadata.json").read_text(encoding="utf-8")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    root = Path(tempfile.mkdtemp())
    try:  # siblings without the site, and a planted conflict: both stop and write nothing
        _layer_workspace(root, {"UsrA": (["CrtBase"], {}), "UsrB": (["UsrA"], {}), "UsrC": (["UsrA"], {})})
        pk = root / "packages"
        _object_layer(pk / "UsrA", "Contact", [("UsrA1", "a1", SHORT_TEXT)])
        _object_layer(pk / "UsrB", "Contact", [("UsrB1", "b1", SHORT_TEXT)])
        _object_layer(pk / "UsrC", "Contact", [("UsrC1", "c1", SHORT_TEXT)])
        snapshot = sorted(str(p) for p in root.rglob("*"))
        text, code = merge_object(root, "Contact", apply=True)
        assert code == 1 and text.endswith("stopped: siblings: their order is a guess without the site; run with -e - nothing written"), text
        _object_layer(pk / "UsrB", "Contact2", [("UsrDup", "d1", SHORT_TEXT)])
        _object_layer(pk / "UsrA", "Contact2", [("UsrDup", "d2", SHORT_TEXT)])
        snapshot = sorted(str(p) for p in root.rglob("*"))
        text, code = merge_object(root, "Contact2", apply=True)
        assert code == 1 and "conflict column UsrDup (two UIds): UsrA and UsrB" in text and "stopped: 1 conflicts" in text, text
        assert sorted(str(p) for p in root.rglob("*")) == snapshot
        with contextlib.redirect_stdout(io.StringIO()) as out:
            assert main(["merge", str(root), "Contact2"]) == 1
        assert "nothing written" in out.getvalue()

        # with the site: the siblings' order is known, the references check runs; a site-only layer among them stops
        class SiteEnv(FakeLayersEnv):
            def sql(self, text):
                self.sql_text.append(text)
                if "HierarchyLevel" in text:
                    return [{"package": p, "level": str(n)} for n, p in enumerate(("UsrA", "CrtSales", "UsrB", "UsrC"))]
                if "information_schema" in text:
                    return []  # no NO ACTION foreign key to SysSchema.Id
                if 'and p."Name" in (' in text:
                    return [{"id": f"id-{p}", "package": p} for p in ("UsrB", "UsrC")]
                return self.rows

        class RefEnv(SiteEnv):
            def sql(self, text):
                if "information_schema" in text:
                    return [{"table": "SysProcessLog", "column": "SysSchemaId"}]
                if "count(*)" in text:
                    return [{"ref": "SysProcessLog.SysSchemaId", "id": "id-UsrC", "n": "3"}]
                return super().sql(text)

        site = [_row("CrtBase", "1", "9", ext="false"), _row("UsrA", "0", "4"), _row("UsrB", "0", "2"), _row("UsrC", "0", "1")]
        vendor = _row("CrtSales", "0", "3")
        for row in site + [vendor]:
            row["manager"] = "EntitySchemaManager"
        text, code = merge_object(root, "Contact", env=SiteEnv(site))
        assert code == 0 and "  references: none to the 2 layers removed" in text and text.endswith("(dry run; --apply writes)"), text
        text, code = merge_object(root, "Contact", env=RefEnv(site))
        assert code == 1 and "  references: SysProcessLog.SysSchemaId 3 rows point at UsrC's Contact" in text and "stopped: 1 references" in text, text
        text, code = merge_object(root, "Contact", env=SiteEnv(site + [vendor]), apply=True)
        assert code == 1 and "  layer CrtSales: on the site only, not merged" in text, text
        assert "stopped: a layer on the site only folds after the target: CrtSales; the merge would put the removed layers' lines before it" in text, text
        assert sorted(str(p) for p in root.rglob("*")) == snapshot
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    for fn in [v for k, v in list(globals().items()) if k.startswith("test_")]:
        fn()
        print("ok", fn.__name__)
