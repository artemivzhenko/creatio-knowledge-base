"""
MCP server exposing the Creatio knowledge base.

All the indexing and ranking lives in kb_index.py; this file is only the MCP
transport plus the tool descriptions the model reads.

Run directly for stdio:  python server.py
"""

from __future__ import annotations

import os
from pathlib import Path

# The SDK renamed FastMCP to MCPServer in mcp 2.0. Both expose the same .tool()
# decorator and .run(), so one shim covers either version.
try:
    from mcp.server.mcpserver import MCPServer as _Server  # mcp >= 2.0
except ImportError:  # pragma: no cover - older SDK
    from mcp.server.fastmcp import FastMCP as _Server  # mcp 1.x

from kb_index import KnowledgeBase, default_root

mcp = _Server(
    "creatio-kb",
    instructions=(
        "Curated Creatio development recipes for this solution: Classic UI (7.x) "
        "pages, details and sections, Freedom UI (8.x) pages, and C# server code. "
        "Search this knowledge base BEFORE writing Creatio code - it carries the "
        "project's idioms, naming rules and known traps that general knowledge "
        "does not have. Start with search_recipes, then get_recipe for the full "
        "example."
    ),
)

_ROOT: Path = default_root()
_KB: KnowledgeBase | None = None
_FINGERPRINT: tuple[int, float] | None = None


def _fingerprint(root: Path) -> tuple[int, float]:
    """Cheap staleness check: file count plus the newest mtime."""
    count = 0
    newest = 0.0
    for sub in ("Frontend", "Backend"):
        base = root / sub
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix in (".js", ".cs", ".sql"):
                count += 1
                newest = max(newest, path.stat().st_mtime)
    return count, newest


def kb() -> KnowledgeBase:
    """Return the index, rebuilding it when the knowledge base changed on disk."""
    global _KB, _FINGERPRINT
    current = _fingerprint(_ROOT)
    if _KB is None or current != _FINGERPRINT:
        _KB = KnowledgeBase(_ROOT)
        _FINGERPRINT = current
    return _KB


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #


@mcp.tool()
def kb_overview() -> str:
    """
    Map of the Creatio knowledge base: areas, topics and how many recipes each holds.

    Call this first when you do not know what the knowledge base covers. For a
    concrete task, go straight to search_recipes instead.
    """
    base = kb()
    lines = [f"Creatio knowledge base at {base.root}", f"{len(base.recipes)} recipes.", ""]
    for area, topics in base.areas().items():
        lines.append(f"{area} ({sum(topics.values())})")
        for topic, count in topics.items():
            lines.append(f"   {count:>3}  {topic}")
        lines.append("")
    lines.append(
        "Areas: ClassicUI (Creatio 7.x pages, details, sections), "
        "FreedomUI (8.x Angular pages), Backend (C# server code), SQL."
    )
    return "\n".join(lines)


@mcp.tool()
def search_recipes(query: str, area: str = "", limit: int = 8) -> str:
    """
    Find knowledge base recipes for a Creatio task, by keyword or by symptom.

    ALWAYS call this before writing Creatio code - the recipes carry the exact
    idioms, the naming rules and the known traps for this codebase, which are not
    guessable from general knowledge.

    query: what you are trying to do, in plain words or as an API name.
           Examples: "filter a lookup field", "run a business process",
           "crt.OpenLookupPageRequest", "make a detail editable".
    area:  optional filter - "ClassicUI", "FreedomUI", "Backend" or "SQL".
           Leave empty to search everything; Classic UI and Freedom UI often have
           a recipe each for the same task, and seeing both tells you which UI
           generation the answer belongs to.
    limit: how many results (default 8).

    Returns a ranked list of ids with titles and summaries. Read a full recipe
    with get_recipe.
    """
    base = kb()
    results = base.search(query, area=area or None, limit=max(1, min(limit, 25)))
    if not results:
        return (
            f'No recipe matched "{query}"'
            + (f" in area {area}" if area else "")
            + ".\nTry fewer or more general words, or call kb_overview to see what exists."
        )

    lines = [f'{len(results)} recipe(s) for "{query}"' + (f" in {area}" if area else "") + ":", ""]
    for recipe, score in results:
        lines.append(f"[{recipe.area}] {recipe.id}   (score {score:.1f})")
        lines.append(f"    {recipe.title}")
        summary = recipe.summary(300)
        if summary:
            lines.append(f"    {summary}")
        lines.append("")
    lines.append("Use get_recipe(<id>) to read the full recipe with its code.")
    return "\n".join(lines)


@mcp.tool()
def get_recipe(recipe_id: str) -> str:
    """
    Return the full text of one recipe: the explanation header and the runnable code.

    recipe_id: the id from search_recipes, for example
               "Frontend/ClassicUI/Fields/HowToFilterLookupField".
               A bare file name is accepted when it is unambiguous.

    The code is a template, not a drop-in: schema names, column names and the
    generated attribute suffixes (PDS_Name_a1b2c3d) must be replaced with the
    real ones from the project.
    """
    recipe = kb().get(recipe_id)
    if recipe is None:
        return (
            f'No recipe with id "{recipe_id}". '
            "Use search_recipes to find the right id."
        )
    header = (
        f"# {recipe.title}\n"
        f"area: {recipe.area}"
        + (f" / {recipe.topic}" if recipe.topic else "")
        + f"\nfile: {recipe.rel_path}\n"
        + "-" * 70
        + "\n"
    )
    return header + recipe.source


@mcp.tool()
def find_api(symbol: str, limit: int = 10) -> str:
    """
    Reverse lookup: which recipes use a given Creatio API symbol.

    Use this when you already have a symbol in hand and want to see it used
    correctly - from a code review, an error message, or existing project code.

    symbol: an API name such as "crt.OpenLookupPageRequest", "EntitySchemaQuery",
            "UseAdminRights", "LookupMultiAddMixin", "ProcessModuleUtilities".
            A bare name also matches a dotted one ("OpenLookupPageRequest" finds
            "crt.OpenLookupPageRequest").

    Returns the recipes that mention it, the most frequent user first.
    """
    base = kb()
    hits = base.find_api(symbol, limit=max(1, min(limit, 25)))
    if not hits:
        return (
            f'No recipe mentions "{symbol}". '
            "It may be spelled differently - try search_recipes with a description instead."
        )
    lines = [f'Recipes using "{symbol}":', ""]
    for recipe, count in hits:
        lines.append(f"[{recipe.area}] {recipe.id}   ({count} mention(s))")
        lines.append(f"    {recipe.title}")
    lines.append("")
    lines.append("Use get_recipe(<id>) to read one.")
    return "\n".join(lines)


@mcp.tool()
def list_recipes(area: str = "", topic: str = "") -> str:
    """
    Browse recipe ids and titles, optionally narrowed to an area and a topic.

    area:  "ClassicUI", "FreedomUI", "Backend" or "SQL".
    topic: a folder inside the area, e.g. "Details", "BaseMethods", "ESQ".
           Call kb_overview to see the available topics.

    Prefer search_recipes when you have a task in mind; this tool is for
    surveying what exists.
    """
    base = kb()
    items = base.list(area=area or None, topic=topic or None)
    if not items:
        return (
            "Nothing matched"
            + (f" area={area}" if area else "")
            + (f" topic={topic}" if topic else "")
            + ". Call kb_overview to see the available areas and topics."
        )
    lines = [f"{len(items)} recipe(s):", ""]
    for recipe in items:
        lines.append(f"[{recipe.area}] {recipe.id}")
        lines.append(f"    {recipe.title}")
    return "\n".join(lines)


def main() -> None:
    """Console entry point: serve over stdio."""
    global _ROOT
    _ROOT = default_root()
    if not (_ROOT / "Frontend").is_dir() and not (_ROOT / "Backend").is_dir():
        raise SystemExit(
            f"No knowledge base found at {_ROOT}. "
            "Set CREATIO_KB_ROOT to the folder that contains Frontend/ and Backend/."
        )
    mcp.run()


if __name__ == "__main__":
    main()
