"""
Indexing and search core for the Creatio knowledge base.

Pure standard library on purpose: this module carries all the logic, so it can be
imported, run and checked without the MCP SDK installed. server.py is only a thin
transport wrapper around it.

    python kb_index.py                 # index report
    python kb_index.py "lookup filter" # try a search
"""

from __future__ import annotations

import math
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------- #
# Layout
# --------------------------------------------------------------------------- #

# area -> (relative root, file suffixes)
AREAS = {
    "ClassicUI": ("Frontend/ClassicUI", (".js",)),
    "FreedomUI": ("Frontend/FreedomUI", (".js",)),
    "Backend": ("Backend/C#", (".cs",)),
    "SQL": ("Backend/SQL", (".sql",)),
}

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from", "how",
    "in", "into", "is", "it", "its", "not", "of", "on", "or", "so", "that", "the",
    "then", "there", "these", "this", "to", "use", "used", "using", "when", "which",
    "with", "you", "your", "we", "do", "does", "can", "will", "would", "should",
    "make", "want", "need", "way", "via",
}

# Ranking weights. BM25 runs over the code body; a query term appearing in the
# title or in the header comment earns a flat bonus on top. Folding all three
# fields into one term-frequency pool ranked badly: BM25 saturates quickly, so a
# passing mention in a long file could outrank an exact title match.
W_TITLE_HIT = 4.5
W_DESC_HIT = 0.9
# In a recipe collection the title states the topic and the body is only
# supporting evidence, so the body score is scaled down rather than left to
# dominate through sheer repetition of common words like "event" or "listener".
W_BODY_SCALE = 0.5
# Documents matching only one term of a multi-word query are damped by coverage.
COVERAGE_FLOOR = 0.35

_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")
_CAMEL_RE = re.compile(r"[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[a-z0-9]+")


def _split_camel(word: str) -> list[str]:
    return [p.lower() for p in _CAMEL_RE.findall(word) if p]


def tokenize(text: str) -> list[str]:
    """
    Lexical tokens tuned for API names.

    "crt.OpenLookupPageRequest" yields the whole dotted name, each dotted part,
    and the camelCase pieces, so both "OpenLookupPageRequest" and "lookup page"
    find it.
    """
    out: list[str] = []
    for raw in _TOKEN_RE.findall(text):
        low = raw.lower()
        out.append(low)
        parts = raw.split(".")
        if len(parts) > 1:
            for p in parts:
                out.append(p.lower())
        for p in parts:
            sub = _split_camel(p)
            if len(sub) > 1:
                out.extend(sub)
    return [t for t in out if len(t) > 1 and t not in STOPWORDS]


def extract_symbols(text: str) -> Counter:
    """
    API-looking identifiers, original case preserved, for the reverse lookup:
    dotted names (crt.X, sdk.X, Terrasoft.X) and multi-word CamelCase names.
    """
    found: Counter = Counter()
    for raw in _TOKEN_RE.findall(text):
        if "." in raw:
            found[raw] += 1
            continue
        if len(raw) > 3 and len(_split_camel(raw)) > 1 and raw[0].isupper():
            found[raw] += 1
    return found


# --------------------------------------------------------------------------- #
# Header parsing
# --------------------------------------------------------------------------- #

# // --- How to filter a lookup field --------------------------------------
_JS_TITLE_RE = re.compile(r"^[ \t]*//[ \t]*-{2,}[ \t]*(.+?)[ \t]*-{2,}[ \t]*$", re.M)
_JS_COMMENT_RE = re.compile(r"^[ \t]*//[ \t]?(.*)$")

_CS_SUMMARY_RE = re.compile(r"///\s*<summary>(.*?)///\s*</summary>", re.S)
_SQL_COMMENT_RE = re.compile(r"^[ \t]*--[ \t]?(.*)$")


def _humanize(stem: str) -> str:
    """HowToRunBackgroundTask -> 'How to run background task'."""
    words = _split_camel(stem)
    if not words:
        return stem
    text = " ".join(words)
    return text[0].upper() + text[1:]


def _js_header(src: str) -> tuple[str, str]:
    m = _JS_TITLE_RE.search(src)
    if not m:
        return "", ""
    title = m.group(1).strip()
    lines = src[: m.start()].count("\n") + 1
    body: list[str] = []
    for line in src.split("\n")[lines:]:
        cm = _JS_COMMENT_RE.match(line)
        if cm is None:
            if line.strip() == "":
                # A blank line inside the header block ends it.
                break
            break
        body.append(cm.group(1).rstrip())
    return title, "\n".join(body).strip()


def _cs_header(src: str, stem: str) -> tuple[str, str]:
    m = _CS_SUMMARY_RE.search(src)
    if not m:
        return "", ""
    raw = m.group(1)
    lines = [re.sub(r"^\s*///\s?", "", ln).rstrip() for ln in raw.split("\n")]
    text = "\n".join(ln for ln in lines).strip()
    if not text:
        return "", ""
    # First sentence becomes the title, the rest is the description.
    first = re.split(r"(?<=[.!?])\s", text, maxsplit=1)
    title = first[0].strip().rstrip(".")
    if len(title) > 110:
        title = _humanize(stem)
    return title, text


def _sql_header(src: str, stem: str) -> tuple[str, str]:
    body: list[str] = []
    for line in src.split("\n"):
        cm = _SQL_COMMENT_RE.match(line)
        if cm is None:
            if not body:
                continue
            break
        body.append(cm.group(1).rstrip())
    text = "\n".join(body).strip()
    title = text.split("\n")[0].strip() if text else _humanize(stem)
    return title, text


# --------------------------------------------------------------------------- #
# Model
# --------------------------------------------------------------------------- #


@dataclass
class Recipe:
    id: str
    title: str
    area: str
    topic: str
    path: str            # absolute
    rel_path: str        # relative to the kb root, POSIX
    description: str
    source: str = field(repr=False, default="")
    symbols: Counter = field(repr=False, default_factory=Counter)
    tf: Counter = field(repr=False, default_factory=Counter)      # body only
    title_terms: set = field(repr=False, default_factory=set)
    desc_terms: set = field(repr=False, default_factory=set)
    length: int = 0

    def summary(self, width: int = 240) -> str:
        text = " ".join(self.description.split())
        # Plain ASCII: some MCP clients and Windows consoles mangle "…".
        return text[: width - 3] + "..." if len(text) > width else text


class KnowledgeBase:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.recipes: dict[str, Recipe] = {}
        self._df: Counter = Counter()
        self._symbol_index: dict[str, dict[str, int]] = defaultdict(dict)
        self._avg_len = 1.0
        self.skipped: list[str] = []
        self._load()

    # -- building ----------------------------------------------------------- #

    def _load(self) -> None:
        for area, (rel_root, suffixes) in AREAS.items():
            base = self.root / rel_root
            if not base.is_dir():
                continue
            for path in sorted(base.rglob("*")):
                if not path.is_file() or path.suffix not in suffixes:
                    continue
                self._add(area, base, path)
        self._finalize()

    def _add(self, area: str, base: Path, path: Path) -> None:
        try:
            src = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            self.skipped.append(f"{path}: {exc}")
            return

        stem = path.stem
        if path.suffix == ".js":
            title, desc = _js_header(src)
        elif path.suffix == ".cs":
            title, desc = _cs_header(src, stem)
        else:
            title, desc = _sql_header(src, stem)

        if not title:
            title = _humanize(stem)
            self.skipped.append(f"{path}: no header block, title derived from filename")

        rel = path.relative_to(self.root).as_posix()
        topic = path.parent.relative_to(base).as_posix()
        topic = "" if topic == "." else topic

        # The file name carries real intent here - every recipe is named
        # HowToDoTheThing - and the words in it are not always repeated in the
        # header sentence, so fold them into the title terms.
        title_terms = set(tokenize(title)) | set(tokenize(_humanize(stem)))
        desc_terms = set(tokenize(desc))
        tf = Counter(tokenize(src))

        recipe = Recipe(
            id=rel.rsplit(".", 1)[0],
            title=title,
            area=area,
            topic=topic,
            path=str(path),
            rel_path=rel,
            description=desc,
            source=src,
            symbols=extract_symbols(src),
            tf=tf,
            title_terms=title_terms,
            desc_terms=desc_terms,
            length=sum(tf.values()),
        )
        self.recipes[recipe.id] = recipe

    def _finalize(self) -> None:
        for r in self.recipes.values():
            for tok in r.tf:
                self._df[tok] += 1
            for sym, count in r.symbols.items():
                self._symbol_index[sym.lower()][r.id] = count
        total = sum(r.length for r in self.recipes.values())
        self._avg_len = (total / len(self.recipes)) if self.recipes else 1.0

    # -- querying ----------------------------------------------------------- #

    def search(self, query: str, area: str | None = None, limit: int = 8) -> list[tuple[Recipe, float]]:
        """BM25 over the weighted fields."""
        terms = tokenize(query)
        if not terms:
            return []
        unique = list(dict.fromkeys(terms))
        n = len(self.recipes) or 1
        k1, b = 1.2, 0.75

        scored: list[tuple[Recipe, float]] = []
        for r in self.recipes.values():
            if area and r.area.lower() != area.lower():
                continue

            body = 0.0
            matched = 0
            for term in unique:
                f = r.tf.get(term, 0)
                if not f:
                    continue
                matched += 1
                df = self._df.get(term, 0)
                idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
                denom = f + k1 * (1 - b + b * (r.length / self._avg_len))
                body += idf * (f * (k1 + 1)) / denom

            if not matched:
                continue

            title_hits = sum(1 for t in unique if t in r.title_terms)
            desc_hits = sum(1 for t in unique if t in r.desc_terms)

            # A document matching one term out of four is rarely the answer.
            coverage = matched / len(unique)
            damp = COVERAGE_FLOOR + (1 - COVERAGE_FLOOR) * coverage

            score = (
                W_BODY_SCALE * body
                + W_TITLE_HIT * title_hits
                + W_DESC_HIT * desc_hits
            ) * damp
            scored.append((r, score))

        scored.sort(key=lambda pair: (-pair[1], pair[0].id))
        return scored[:limit]

    def find_api(self, symbol: str, limit: int = 12) -> list[tuple[Recipe, int]]:
        """Which recipes mention this API symbol, most-mentions first."""
        key = symbol.strip().lower()
        hits = dict(self._symbol_index.get(key, {}))

        if not hits:
            # Fall back to a suffix / substring match: "OpenLookupPageRequest"
            # should still find "crt.OpenLookupPageRequest".
            for indexed, refs in self._symbol_index.items():
                if key and (indexed.endswith("." + key) or key in indexed):
                    for rid, count in refs.items():
                        hits[rid] = hits.get(rid, 0) + count

        out = [(self.recipes[rid], c) for rid, c in hits.items() if rid in self.recipes]
        out.sort(key=lambda pair: (-pair[1], pair[0].id))
        return out[:limit]

    def get(self, recipe_id: str) -> Recipe | None:
        rid = recipe_id.strip().strip("/")
        if rid in self.recipes:
            return self.recipes[rid]
        # Tolerate an extension, a leading slash, or just the file name.
        rid_noext = rid.rsplit(".", 1)[0]
        if rid_noext in self.recipes:
            return self.recipes[rid_noext]
        matches = [r for r in self.recipes.values() if r.id.endswith("/" + rid_noext)]
        if len(matches) == 1:
            return matches[0]
        return None

    def list(self, area: str | None = None, topic: str | None = None) -> list[Recipe]:
        out = [
            r
            for r in self.recipes.values()
            if (not area or r.area.lower() == area.lower())
            and (not topic or r.topic.lower() == topic.lower())
        ]
        out.sort(key=lambda r: r.id)
        return out

    def areas(self) -> dict[str, dict[str, int]]:
        """area -> topic -> recipe count."""
        tree: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for r in self.recipes.values():
            tree[r.area][r.topic or "(root)"] += 1
        return {a: dict(sorted(t.items())) for a, t in sorted(tree.items())}


# --------------------------------------------------------------------------- #
# Root resolution
# --------------------------------------------------------------------------- #


def default_root() -> Path:
    env = os.environ.get("CREATIO_KB_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    # mcp-server/kb_index.py -> the knowledge base root is the parent folder.
    return Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- #
# CLI - lets the index be checked without the MCP SDK
# --------------------------------------------------------------------------- #


def _main(argv: list[str]) -> int:
    root = default_root()
    kb = KnowledgeBase(root)

    if not kb.recipes:
        print(f"No recipes found under {root}", file=sys.stderr)
        return 1

    if len(argv) > 1:
        query = " ".join(argv[1:])
        results = kb.search(query, limit=10)
        print(f'search "{query}" -> {len(results)} hit(s)\n')
        for r, score in results:
            print(f"  {score:6.2f}  [{r.area}] {r.id}")
            print(f"          {r.title}")
        return 0

    print(f"knowledge base: {root}")
    print(f"recipes indexed: {len(kb.recipes)}")
    print(f"distinct terms:  {len(kb._df)}")
    print(f"api symbols:     {len(kb._symbol_index)}\n")
    for area, topics in kb.areas().items():
        total = sum(topics.values())
        print(f"  {area} ({total})")
        for topic, count in topics.items():
            print(f"      {count:>3}  {topic}")
    if kb.skipped:
        print(f"\nwarnings ({len(kb.skipped)}):")
        for w in kb.skipped:
            print(f"  - {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
