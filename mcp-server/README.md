# Creatio KB MCP server

Exposes this knowledge base to an AI assistant over MCP, so the model can look up a
recipe for a concrete task instead of loading all 169 files into context.

## What it gives the model

| Tool | Purpose |
| --- | --- |
| `search_recipes(query, area?, limit?)` | Ranked search by task or symptom. `area` = `ClassicUI` / `FreedomUI` / `Backend` / `SQL`. |
| `get_recipe(recipe_id)` | Full text of one recipe: explanation header plus runnable code. |
| `find_api(symbol, limit?)` | Reverse lookup — which recipes use `crt.OpenLookupPageRequest`, `UseAdminRights`, `EntitySchemaQuery`… A bare name also matches the dotted one. |
| `list_recipes(area?, topic?)` | Browse ids and titles. |
| `kb_overview()` | Map of areas, topics and counts — the entry point when the model does not know what exists. |

Search is lexical BM25 with a title bonus, built in memory at startup. No API keys,
no network, no embedding service. The index rebuilds automatically when a file in
the knowledge base changes, so editing a recipe takes effect on the next call.

## Install

```bash
cd mcp-server
python -m venv .venv
.venv/Scripts/activate        # Windows;  source .venv/bin/activate on macOS/Linux
pip install -e .
```

`pip install -e .` pulls the only dependency, `mcp>=2.0`.

> The SDK renamed `FastMCP` to `MCPServer` in mcp 2.0. `server.py` imports either,
> so an existing `mcp<2` environment also works.

## Check it without a client

`kb_index.py` is pure standard library, so the index and the ranking can be
exercised on their own:

```bash
python kb_index.py                          # index report: areas, topics, warnings
python kb_index.py "filter a lookup field"  # try a query
```

A healthy report ends with no warnings — a warning means a recipe lost its header
block and only got a title derived from its file name.

## Wire it into a client

Replace `<KB>` with the absolute path to this knowledge base folder (the one
containing `Frontend/` and `Backend/`), and `<PY>` with the interpreter from the
virtual environment (`<KB>/mcp-server/.venv/Scripts/python.exe` on Windows,
`<KB>/mcp-server/.venv/bin/python` elsewhere).

### Claude Code

```bash
claude mcp add creatio-kb -- <PY> <KB>/mcp-server/server.py
```

Or in `.mcp.json` at the root of the project you develop Creatio in:

```json
{
  "mcpServers": {
    "creatio-kb": {
      "command": "<PY>",
      "args": ["<KB>/mcp-server/server.py"]
    }
  }
}
```

### Cursor — `.cursor/mcp.json`

```json
{
  "mcpServers": {
    "creatio-kb": {
      "command": "<PY>",
      "args": ["<KB>/mcp-server/server.py"]
    }
  }
}
```

### Claude Desktop — `claude_desktop_config.json`

```json
{
  "mcpServers": {
    "creatio-kb": {
      "command": "<PY>",
      "args": ["<KB>/mcp-server/server.py"]
    }
  }
}
```

### Knowledge base in another location

The server assumes the knowledge base is the parent folder of `mcp-server/`.
Point it elsewhere with an environment variable:

```json
{
  "mcpServers": {
    "creatio-kb": {
      "command": "<PY>",
      "args": ["<KB>/mcp-server/server.py"],
      "env": { "CREATIO_KB_ROOT": "D:/knowledge/creatio-knowledge-base" }
    }
  }
}
```

## Companion skill

`../skill/creatio-kb/SKILL.md` tells a Claude Code agent *when* to reach for these
tools. The MCP server supplies the data; the skill supplies the habit of consulting
it before writing Creatio code. Install it by copying the folder into
`.claude/skills/` of the project you work in.

## How indexing works

- Recipes are discovered under `Frontend/ClassicUI`, `Frontend/FreedomUI`,
  `Backend/C#` and `Backend/SQL`.
- The title and description come from the header block: `// --- Title ---` in `.js`
  files, `/// <summary>` in `.cs`, the leading `--` comment in `.sql`.
- A recipe id is its path without the extension, e.g.
  `Frontend/ClassicUI/Fields/HowToFilterLookupField`.
- Tokenisation splits dotted and camelCase identifiers, so `crt.OpenLookupPageRequest`
  is findable as `crt.OpenLookupPageRequest`, `OpenLookupPageRequest`, and
  `lookup page`.

## Adding recipes

Drop a new file into the right area folder and keep the header block format — it is
what supplies the title and summary. Nothing else needs updating; the index picks it
up on the next tool call.
