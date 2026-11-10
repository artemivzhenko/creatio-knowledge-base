#!/usr/bin/env python3
"""The set an author task starts with, in one command, built by the toolkits (objects, data, pages).

    python scaffold.py entity <package> <Object> --caption "Shipment"
        [--column "UsrNumber:Integer:required" ..]                 Name:Type[:flag,..]; a lookup: Name:Lookup:<Object>[:flag,..]
        [--lookup "UsrStatus:UsrShipmentStatus:New,In progress,Done" ..]   column : lookup object : rows of its binding
        [--pages] [--cultures en-US,ru-RU] [--dry-run]
    python scaffold.py source <package> <Name> --caption "Order service" [--service] [--cultures ..]
    python scaffold.py module <package> <Name> [--caption ..] [--mixin] [--cultures ..]

Builds the object (BaseEntity), each lookup object it lacks (BaseLookup) with a data binding Data/<Lookup> of
the listed names (new Ids), the lookup columns, and with --pages the form page <Object>_FormPage (every column
as a field) and the list page <Object>_ListPage, each as its toolkit writes it and each validated. Captions are
the names without the prefix, split at capitals ("UsrShipDate" -> "Ship date"). An existing schema or binding
is refused, never overwritten. Everything is built in a scratch copy first: --dry-run prints the diff of every
file, otherwise the files are copied into the package.

`source` writes an empty source code schema (SourceCodeSchemaManager: full metadata, `.SourceCode` resources, a
CRLF `.cs` laid out by the code style; `--service` the [ServiceContract] skeleton of the KB recipe), `module` a client
module (ClassicSchema.create_module; `--mixin` the Ext.define mixin a Classic page lists in `mixins`).
"""

from __future__ import annotations

import difflib
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from creatio_schemas.classicui import ClassicSchema  # noqa: E402
from creatio_schemas.classicui.write import MODULE_BASE_UID  # noqa: E402
from creatio_schemas.cli import CommandLine  # noqa: E402
from creatio_schemas.data import DataBinding  # noqa: E402
from creatio_schemas.entity import EntitySchema  # noqa: E402
from creatio_schemas.files import CRLF, dump_json, new_uid, read_text, write_text  # noqa: E402
from creatio_schemas.resources import Resources  # noqa: E402
from creatio_schemas.schema import Descriptor  # noqa: E402
from creatio_schemas.workspace import Package  # noqa: E402
from creatio_schemas.page import PageSchema  # noqa: E402
from creatio_schemas.workspace import Workspace  # noqa: E402


def caption_of(name: str) -> str:
    """UsrShipDate -> Ship date."""
    bare = re.sub(r"^(Usr|[a-z][a-z0-9]*)(?=[A-Z])", "", name)  # the Usr prefix, or a lower-case one (ia, a1)
    words = re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z0-9]+", bare) or [bare]
    return " ".join([words[0]] + [w if w.isupper() else w.lower() for w in words[1:]])


def parse_column(spec: str) -> dict:
    """Name:Type[:Ref][:flag,flag] -> {name, type, ref, flags}."""
    parts = [p.strip() for p in spec.split(":")]
    if len(parts) < 2 or not all(parts[:2]):
        raise ValueError(f"--column expects Name:Type[:flags], got {spec!r}")
    name, type_name, rest = parts[0], parts[1], parts[2:]
    ref = None
    if type_name == "Lookup":
        if not rest or not rest[0]:
            raise ValueError(f"--column {spec!r}: a lookup needs its object, Name:Lookup:<Object>")
        ref, rest = rest[0], rest[1:]
    flags = [f.strip() for part in rest for f in part.split(",") if f.strip()]
    return {"name": name, "type": type_name, "ref": ref, "flags": flags}


def parse_lookup(spec: str) -> dict:
    """Column:LookupObject[:Row,Row] -> {column, object, rows}."""
    parts = spec.split(":", 2)
    if len(parts) < 2 or not parts[0].strip() or not parts[1].strip():
        raise ValueError(f"--lookup expects Column:LookupObject[:Row,Row], got {spec!r}")
    rows = [r.strip() for r in parts[2].split(",") if r.strip()] if len(parts) > 2 else []
    return {"column": parts[0].strip(), "object": parts[1].strip(), "rows": rows}


def plan(package: Path, obj: str, lookups: list[dict], pages: bool) -> list[str]:
    """What will be made; refuses anything that exists."""
    ws = Workspace(package)
    out = []
    if ws.find(obj, "EntitySchemaManager") or (package / "Schemas" / obj).exists():
        raise FileExistsError(f"object {obj} exists; scaffold builds new schemas only")
    out.append(f"object {obj}")
    for lk in lookups:
        if not ws.find(lk["object"], "EntitySchemaManager"):
            out.append(f"lookup object {lk['object']}")
        if lk["rows"]:
            if (package / "Data" / lk["object"]).exists():
                raise FileExistsError(f"data binding {lk['object']} exists in {package.name}")
            out.append(f"data binding {lk['object']} ({len(lk['rows'])} rows)")
    for page in ([f"{obj}_FormPage", f"{obj}_ListPage"] if pages else []):
        if ws.find(page, "ClientUnitSchemaManager") or (package / "Schemas" / page).exists():
            raise FileExistsError(f"page {page} exists")
        out.append(f"page {page}")
    return out


def scratch_copy(package: Path) -> Path:
    """The package and, of its neighbours, what the workspace scan reads (descriptors and metadata), in a temp folder."""
    root = Path(tempfile.mkdtemp()) / package.parent.name
    shutil.copytree(package, root / package.name)
    for other in package.parent.iterdir():
        if other == package or not (other / "descriptor.json").is_file():
            continue
        (root / other.name).mkdir(parents=True)
        shutil.copy2(other / "descriptor.json", root / other.name / "descriptor.json")
        for f in other.glob("Schemas/*/*"):
            if f.name in ("descriptor.json", "metadata.json"):
                (root / other.name / f.parent.relative_to(other)).mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, root / other.name / f.relative_to(other))
    return root / package.name


def build(package: Path, obj: str, caption: str, columns: list[dict], lookups: list[dict], pages: bool, cultures: list[str] | None) -> list:
    """Every item, made in `package` by its toolkit; returns them (for validation and the round trip)."""
    items = []
    ws = Workspace(package)
    for lk in lookups:
        if not ws.find(lk["object"], "EntitySchemaManager") and not (package / "Schemas" / lk["object"]).exists():
            items.append(EntitySchema.create(package, lk["object"], caption_of(lk["object"]), parent="BaseLookup", cultures=cultures))
    ent = EntitySchema.create(package, obj, caption, parent="BaseEntity", cultures=cultures)
    for col in columns:
        ent.add_column(col["name"], col["type"], caption_of(col["name"]), col["ref"], **{f: True for f in col["flags"]})
    for lk in lookups:
        ent.add_column(lk["column"], "Lookup", caption_of(lk["column"]), lk["object"])
    ent.save()
    items.append(ent)
    for lk in lookups:
        if lk["rows"]:
            items.append(DataBinding.create(package, lk["object"], lk["object"], ["Id"], [{"Name": r} for r in lk["rows"]], cultures))
    if pages:
        form = PageSchema.create(package, f"{obj}_FormPage", obj, "form", f"{caption} form page", cultures)
        for name in [c["name"] for c in columns] + [lk["column"] for lk in lookups]:
            form.add_field(name)
        form.save()
        items += [form, PageSchema.create(package, f"{obj}_ListPage", obj, "list", caption, cultures)]
    return items


def changed_files(scratch: Path, package: Path) -> dict[Path, Path]:
    """relative path -> scratch file, for every file that is new or differs from the package."""
    out = {}
    for f in sorted(p for p in scratch.rglob("*") if p.is_file()):
        rel = f.relative_to(scratch)
        target = package / rel
        if not target.is_file() or target.read_bytes() != f.read_bytes():
            out[rel] = f
    return out


def entity(_, a) -> int:
    package = Path(a.package).resolve()
    columns = [parse_column(s) for s in a.column]
    lookups = [parse_lookup(s) for s in a.lookup]
    cultures = a.cultures.split(",") if a.cultures else None
    made = plan(package, a.object, lookups, a.pages)
    scratch = scratch_copy(package)
    try:
        items = build(scratch, a.object, a.caption, columns, lookups, a.pages, cultures)
        problems = [f"{item.name}: {p}" for item in items for p in item.errors()]
        if problems:
            raise ValueError("the toolkits refuse the result:\n  " + "\n  ".join(problems))
        files = changed_files(scratch, package)
        for rel, f in files.items():
            if a.dry_run:
                old = read_text(package / rel)[0] if (package / rel).is_file() else ""
                sys.stdout.write("".join(difflib.unified_diff(old.splitlines(True), read_text(f)[0].splitlines(True), f"a/{rel.as_posix()}",
                                                              f"b/{rel.as_posix()}")) + "\n")
            else:
                (package / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(f, package / rel)
    finally:
        shutil.rmtree(scratch.parent.parent, ignore_errors=True)
    print("\n".join(f"  {m}" for m in made))
    print(f"{len(files)} file(s) " + ("would be written (dry run: nothing written)" if a.dry_run else f"written to {package.name}"))
    return 0


CLASS_CS = """namespace Terrasoft.Configuration.@NAME@Namespace
{
	using System;
	using Terrasoft.Common;
	using Terrasoft.Core;

	#region Class: @NAME@

	/// <summary>
	/// @CAPTION@.
	/// </summary>
	public class @NAME@
	{

		#region Fields: Private

		private readonly UserConnection _userConnection;

		#endregion

		#region Constructors: Public

		public @NAME@(UserConnection userConnection) {
			userConnection.CheckArgumentNull(nameof(userConnection));
			_userConnection = userConnection;
		}

		#endregion

	}

	#endregion

}
"""

SERVICE_CS = """namespace Terrasoft.Configuration.@NAME@Namespace
{
	using System;
	using System.ServiceModel;
	using System.ServiceModel.Activation;
	using System.ServiceModel.Web;
	using Terrasoft.Web.Common;

	#region Class: @NAME@

	/// <summary>
	/// @CAPTION@: a thin API over the Files/cs classes; called as POST 0/rest/@NAME@/Ping.
	/// </summary>
	[ServiceContract]
	[DefaultServiceRoute]
	[AspNetCompatibilityRequirements(RequirementsMode = AspNetCompatibilityRequirementsMode.Required)]
	public class @NAME@ : BaseService
	{

		#region Methods: Public

		[OperationContract]
		[WebInvoke(Method = "POST", RequestFormat = WebMessageFormat.Json, BodyStyle = WebMessageBodyStyle.Wrapped,
			ResponseFormat = WebMessageFormat.Json)]
		public string Ping(string value) {
			return value;
		}

		#endregion

	}

	#endregion

}
"""


def create_source(package: Path, name: str, caption: str, service: bool = False, cultures: list[str] | None = None,
                  version: str = "8.2.3.1351") -> list[Path]:
    """An empty source code schema in the shape of real ones (102 surveyed): BOM + CRLF JSON files without a final newline,
    HD1 the common base, a CRLF .cs without BOM, the caption in Resources/<Name>.SourceCode."""
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name):
        raise ValueError(f"{name!r} is not a valid schema name")
    sdir = package / "Schemas" / name
    if sdir.exists() or Workspace(package).find(name, "SourceCodeSchemaManager"):
        raise FileExistsError(f"source code schema {name} exists in the workspace")
    pkg, uid = Package(package), new_uid()
    schema = {"ManagerName": "SourceCodeSchemaManager", "UId": uid, "A2": name, "A5": pkg.created_in_uid(), "B1": [], "B2": [], "B3": [],
              "B6": pkg.uid, "B8": version, "HD1": MODULE_BASE_UID}
    write_text(sdir / "metadata.json", dump_json({"MetaData": {"Schema": schema}}), True)
    desc = Descriptor.new(sdir / "descriptor.json", {"UId": uid, "Name": name, "ModifiedOnUtc": "", "ManagerName": "SourceCodeSchemaManager",
                                                     "Caption": caption, "DependsOn": []})
    write_text(desc.path, desc.text, True)
    write_text(sdir / "properties.json", dump_json({"Properties": {"CreatedInVersion": version}}), True)
    code = (SERVICE_CS if service else CLASS_CS).replace("@NAME@", name).replace("@CAPTION@", caption.rstrip("."))
    write_text(sdir / f"{name}.cs", code.replace("\n", CRLF), False)
    known = sorted({p.name[len("resource."):-len(".xml")] for p in package.glob("Resources/*/resource.*.xml")})
    res = Resources.empty(package / "Resources" / f"{name}.SourceCode", cultures or known or ["en-US"])
    res.set("Caption", caption)
    for path, (text, bom) in res.files().items():
        write_text(path, text, bom)
    return sorted([*sdir.iterdir(), *res.folder.iterdir()])


def source(_, a) -> int:
    package = Path(a.package).resolve()
    for f in create_source(package, a.name, a.caption, a.service, a.cultures.split(",") if a.cultures else None):
        print(f"  {f.relative_to(package).as_posix()}")
    return 0


def module(_, a) -> int:
    package = Path(a.package).resolve()
    s = ClassicSchema.create_module(package, a.name, a.caption, a.mixin, a.cultures.split(",") if a.cultures else None)
    for f in sorted(s.files()):
        print(f"  {f.relative_to(package).as_posix()}")
    print(f"  {(s.dir / (s.name + '.less')).relative_to(package).as_posix()}")
    return 0


def build_cli() -> CommandLine:
    c = CommandLine(__doc__, "object")
    p = c.command("entity", entity, "an object with its columns, lookups with seed rows, form and list pages", target=False)
    p.add_argument("package")
    p.add_argument("object")
    p.add_argument("--caption", required=True)
    p.add_argument("--column", action="append", default=[], metavar="Name:Type[:flags]")
    p.add_argument("--lookup", action="append", default=[], metavar="Column:LookupObject[:Row,Row]")
    p.add_argument("--pages", action="store_true", help="also <Object>_FormPage and <Object>_ListPage")
    p.add_argument("--cultures", help="comma-separated; default: the cultures the package's resources have")
    p.add_argument("--dry-run", action="store_true", help="print the diff of every file, write nothing")
    p = c.command("source", source, "an empty source code schema (a class, or --service the web service skeleton)", target=False)
    p.add_argument("package")
    p.add_argument("name")
    p.add_argument("--caption", required=True)
    p.add_argument("--service", action="store_true", help="the [ServiceContract] skeleton of the KB recipe")
    p.add_argument("--cultures", help="comma-separated; default the package's")
    p = c.command("module", module, "an empty client module (--mixin: the Ext.define mixin a Classic page lists)", target=False)
    p.add_argument("package")
    p.add_argument("name")
    p.add_argument("--caption")
    p.add_argument("--mixin", action="store_true")
    p.add_argument("--cultures", help="comma-separated; default the package's")
    return c


def main(argv=None) -> int:
    return build_cli().run(sys.argv[1:] if argv is None else argv, lambda a: None)


if __name__ == "__main__":
    sys.exit(main())
