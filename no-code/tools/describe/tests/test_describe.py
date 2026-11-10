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
        assert rebuilt.data["format"] == 4 and rebuilt.data["data"]["UsrStatus"]["rows"] == 2
        assert json.loads(idx.path.read_text(encoding="utf-8"))["format"] == 4


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
    diff = describe_item(PAGES, "iaOrder", "keys")  # an object made in the designer: a diff against its parent
    assert diff.startswith("diff form against the parent's metadata") and "= A5                     CreatedInPackageId" in diff and "+ D2 " in diff
    assert describe_item(TOOLS / "sqlscripts" / "tests" / "fixtures" / "iaTest", describe_package(TOOLS / "sqlscripts" / "tests" / "fixtures" / "iaTest", "sql").splitlines()[1].split()[1], "keys") == "(no metadata.json)"


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
    out = dependencies(PAGES, "iaOrder")
    assert "  object BaseEntity  parent" in out and "  object Contact  lookup: CreatedBy, ModifiedBy, iaContact, iaManager" in out
    assert "  object iaOrderStatus  lookup: iaStatus" in out and "  page iaOrder_FormPage  data-source: PDS  [name]" in out
    # a page: every data source by name, its attribute columns proved on that object's effective columns
    out = dependencies(PAGES, "iaTests_FormPage", "out")
    assert "  object iaTest  data-source: PDS, iaName, iaComment" in out and "iaName?" not in out and "  page PageWithTabsFreedomTemplate  parent" in out
    assert "  object SysFile  data-source: AttachmentListDS, Name  [name]" in out and "dependents" not in out  # a stock object: its columns from the stock catalogue
    assert "  object iaOrder  data-source: iaOrderListDS, iaName, iaQuantity  [name]" in out  # the data source's own attributes are columns too
    from creatio_schemas.describe.deps import Resolver
    from creatio_schemas.workspace import Workspace
    r = Resolver(Workspace(PAGES))
    assert r.column_names("iaOrder", ["iaStatusId", "iaStatus.Name", "Nope", "null", "ModifiedById"]) == ["iaStatusId", "iaStatus.Name", "Nope?", "ModifiedById"]
    # filters, direction and the topic form
    assert dependencies(PAGES, "iaOrderStatus", "in", kind="object").splitlines() == ["iaOrderStatus  object in iaTest", "dependents:", "  object iaOrder  lookup: iaStatus"]
    assert "dependents: nothing typed in the workspace of kind process" in dependencies(PAGES, "iaOrderStatus", "in", kind="process")
    assert describe_item(PAGES, "iaOrder_FormPage", "uses via=data-source").endswith("  object iaOrder  data-source: PDS  [name]")
    assert dependencies(PAGES, "Nope").startswith("no schema named Nope")
    # other kinds: a process data element, a Classic page's details and mixin, a data binding, a C# listener
    assert "  object 368340c2-dddc-46fe-ac7f-d3485b497f95  delete-data: DeleteDataUserTask1" in dependencies(PROCS, "iaDeleteOldLogs_Process", "out")
    classic = dependencies(TOOLS / "classicui" / "tests" / "fixtures" / "UsrPkg", "UsrOrderPage", "out")
    assert "  page UsrOrderProductDetailV2  detail: UsrOrderProductDetail  [name]" in classic and "  page UsrPrintMixin  mixin: UsrPrintMixin  [name]" in classic
    assert "  object UsrOrder  entity  [name]" in classic and "  page BasePageV2  parent  [name]" in classic
    assert "  object UsrOrderStatus  binds: Id, Name, Description  [name]" in dependencies(TOOLS / "data" / "tests" / "fixtures" / "UsrPkg", "Data/UsrStatus", "out")
    assert "  object UsrOrder  listener: UsrOrderEventListener, UsrStatusId?, UsrAmount?  [name]" in dependencies(CS, "Files/cs/UsrOrderEventListener.cs", "out")
    # the edges live in the index and find_schema shows both directions
    idx = PackageIndex(PAGES)
    idx.refresh()
    assert idx.data["format"] == 4 and {d["via"] for d in idx.schemas["iaOrder"]["deps"]} == {"parent", "lookup"}
    assert idx.dependents("iaOrder")[0][:2] == ("page", "iaOrder_FormPage")
    assert Edge.from_dict(idx.schemas["iaOrder"]["deps"][1]).line().startswith("object ")
    found = find_schema(PAGES, "iaOrder")
    assert "  depends on: object BaseEntity  parent; object Contact  lookup" in found and "  dependents: page iaOrder_FormPage (data-source); page iaTests_FormPage (data-source)" in found


TEXT_CS = """namespace Terrasoft.Configuration
{
	[EntityEventListener(SchemaName = "iaOrder")]
	public class UsrOrderListener : BaseEntityEventListener
	{
		public override void OnSaving(object sender, EntityBeforeEventArgs e) {
			var order = (Entity)sender;
			Guid status = order.GetTypedColumnValue<Guid>("iaStatusId");
			order.SetColumnValue("iaNope", 1);
		}
	}

	public class UsrQueries
	{
		public void Run(UserConnection uc) {
			var esq = new EntitySchemaQuery(uc.EntitySchemaManager, "iaTest");
			esq.AddColumn("iaName");
			esq.AddColumn("iaContactLookup.Name");
			var update = new Update(uc, "iaOrderStatus").Set("Name", Column.Parameter("x")).Set("iaMissing", Column.Parameter(1));
			var joined = new Select(uc).Column("Id").From("iaOrder").InnerJoin("iaTest").On("iaTest", "Id").IsEqual("iaOrder", "Id");
			var process = uc.ProcessSchemaManager.GetInstanceByName("iaTest_Process");
			string again = "iaOrderStatus";
			// "iaOrder" in a comment is no word of the code
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
        pkg = Path(tmp) / "packages" / "iaTest"
        shutil.copytree(PAGES, pkg)
        (pkg / "Files" / "cs").mkdir(parents=True)
        (pkg / "Files" / "cs" / "UsrText.cs").write_text(TEXT_CS, encoding="utf-8")
        out = dependencies_out(pkg, "Files/cs/UsrText.cs")
        assert "  object iaOrder  listener: UsrOrderListener, iaStatus, iaNope?  [name]" in out, out  # iaStatusId is the lookup iaStatus
        assert "  object iaTest  esq: iaName, iaContactLookup.Name  [name]" in out  # a path: its first part is checked
        assert "  object iaOrderStatus  query: Name, iaMissing?  [name]" in out
        assert "  object iaOrder  query  [name]" in out and "  object iaTest  query  [name]" in out  # a join: two tables, no columns
        assert "iaTest_Process" not in out and "string" not in out  # another manager's schema; a word already reached
        (pkg / "Files" / "cs" / "UsrText.cs").write_text(TEXT_CS.replace('"iaOrderStatus";', '"iaTests_FormPage"; string w = "iaOrderStatus" + "x";')
                                                       .replace('new Update(uc, "iaOrderStatus")', 'new Update(uc, "iaOther")'), encoding="utf-8")
        out = dependencies_out(pkg, "Files/cs/UsrText.cs")
        assert "  object iaOrderStatus  string  [text]" in out and "iaTests_FormPage" not in out, out  # a page name is no object
        # SQL: tables of every statement form, quoted or not; a comment, a string and a CTE are not tables
        r = Resolver(Workspace(pkg))
        sql = ('-- update "iaTest"\nwith cte as (select 1)\ninsert into "iaOrder" ("Name") select "Name" from cte join iaorderstatus s on true;\n'
               "update [dbo].[iaTest] set x = 'from \"Contact\"';\ndelete from public.\"Contact\";\nalter table if exists \"iaNoSuch\" add y int;\n")
        assert [e.line() for e in _sql_tables(sql, r)] == ["object iaOrder  table  [text]", "object iaOrderStatus  table  [text]",
                                                           "object iaTest  table  [text]", "object Contact  table  [text]"]
        # Freedom page: a workspace client schema in SCHEMA_DEPS is a module; a package of the devkit is not
        page = pkg / "Schemas" / "iaTests_FormPage" / "iaTests_FormPage.js"
        page.write_text(page.read_text(encoding="utf-8").replace("/**SCHEMA_DEPS*/[]", '/**SCHEMA_DEPS*/["@creatio-devkit/common", "iaOrder_FormPage"]', 1), encoding="utf-8")
        assert "  page iaOrder_FormPage  module  [name]" in dependencies_out(pkg, "iaTests_FormPage")
    # a process script task: the same words, the element first
    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp) / "packages" / "iaTest"
        shutil.copytree(PROCS, pkg)
        proc = ProcessSchema(pkg, "iaProcess_0d4c445")
        proc.add_element("script", "ScriptTask1")
        proc.set_script("ScriptTask1", 'var esq = new EntitySchemaQuery(UserConnection.EntitySchemaManager, "Contact");\nesq.AddColumn("Name");\nesq.AddColumn("UsrNope");\nreturn true;')
        proc.save()
        contact = next(l for l in dependencies_out(pkg, "iaProcess_0d4c445").splitlines() if l.startswith("  object Contact  esq:"))
        assert contact == "  object Contact  esq: ScriptTask1, Name, UsrNope?  [name]", contact  # a stock object: the stock catalogue's columns (S20-T04)
    # rules: an object's rule names its columns; a page rule's attributes reach the data source's object
    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp) / "packages" / "iaTest"
        shutil.copytree(RULES, pkg)
        assert "  object iaTest  column: iaNumber, iaIsActive, iaName, iaComment, iaContactLookup, iaAccount, iaContactLookup.Account, iaAmount  [name]" in dependencies_out(pkg, "iaTestBusinessRule")
        out = dependencies_out(pkg, "iaTests_FormPageBusinessRule")
        assert "  page iaTests_FormPage  target" in out and "  object iaTest  column: iaIsActive, iaNumber  [name]" in out
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
        (out / "iaTest").mkdir(parents=True)
        (out / "iaTest" / "iaGone.md").write_text("an item that no longer exists", encoding="utf-8")
        (out / "iaTest" / "notes.txt").write_text("not ours", encoding="utf-8")
        (out / "OtherPkg").mkdir()
        (out / "OtherPkg" / "X.md").write_text("another package's file", encoding="utf-8")
        assert export(PAGES, out) == f"6 files written, 1 removed, 1 package(s) -> {out}"
        files = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
        assert files == ["OtherPkg/X.md", "iaTest/_package.md", "iaTest/iaOrder.md", "iaTest/iaOrderStatus.md", "iaTest/iaOrder_FormPage.md",
                         "iaTest/iaTest.md", "iaTest/iaTests_FormPage.md", "iaTest/notes.txt"], files
        text = (out / "iaTest" / "iaOrder.md").read_bytes().decode("utf-8")
        assert "\r" not in text and text.startswith("# iaOrder\n\n```text\niaOrder: 'Order'  own object")
        assert "\n## Depends on\n\n```text\nobject BaseEntity  parent\n" in text
        assert "\n## Dependents\n\n```text\npage iaOrder_FormPage  data-source: PDS  [name]\n" in text
        assert f"\n## Files\n\n```text\n{PAGES.resolve() / 'Resources' / 'iaOrder.Entity' / 'resource.en-US.xml'}  (" in text
        assert "  page      iaTests_FormPage" in (out / "iaTest" / "_package.md").read_text(encoding="utf-8")
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
        for folder, data, done in (("013-other", {"schemas": ["iaOrder_FormPage"], "affects": ["iaOrderStatus"]}, False),
                                   ("011-done", {"schemas": ["iaOrder"]}, True), ("012-this", {"schemas": ["iaOrder"]}, False)):
            (t / folder).mkdir()
            (t / folder / "schemas.json").write_text(json.dumps(data), encoding="utf-8")
            if done:
                (t / folder / "success-report.md").write_text("ok", encoding="utf-8")
        text, conflicts = impact(PAGES, ["iaOrder", "iaOrderStatus"], t, "012-this")
        assert conflicts == 1 and "    page iaOrder_FormPage (data-source) - task 013-other changes it" in text
        assert "iaOrderStatus  object in iaTest  [task 013-other depends on it]" in text and "    object iaOrder (lookup)" in text
        assert "affects: iaOrder_FormPage, iaTests_FormPage" in text and "011-done" not in text  # a finished task locks nothing; what the task changes is not what it affects
        assert text.endswith("2 dependents of 2 schema(s); 1 conflict(s) with other active tasks")
        md, _ = impact(PAGES, ["iaOrder"], t, "012-this", md=True)
        assert md.splitlines()[:4] == ["## Impact", "", "| Schema | Dependents | Other active tasks |", "|---|---|---|"]
        assert "| `iaOrder` | page iaOrder_FormPage (data-source), page iaTests_FormPage (data-source) | task 013-other changes it (page iaOrder_FormPage) |" in md
        # the current task's own lock is not a conflict; a schema another task changes is
        assert impact(PAGES, ["iaOrder"], t, "012-this")[1] == 1 and impact(PAGES, ["iaOrder_FormPage"], t, "012-this")[1] == 1
        assert impact(PAGES, ["iaOrder_FormPage"], t, "013-other")[1] == 0
    text, conflicts = impact(PAGES, ["Nope"])
    assert text.startswith("Nope  (not in the workspace)") and conflicts == 0 and "locks not checked" in text
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert main(["impact", str(PAGES), "iaOrderStatus", "--md"]) == 0
    assert out.getvalue().startswith("## Impact")


def test_cli():
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert main(["deps", str(PAGES), "iaOrder", "--in", "--kind", "page"]) == 0
    assert out.getvalue().splitlines()[:3] == ["iaOrder  object in iaTest", "dependents:", "  page iaOrder_FormPage  data-source: PDS  [name]"]
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
