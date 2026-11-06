"""Byte-exact text I/O shared by every schema type.

The platform exports JSON with CRLF and 2-space indent, some files with a BOM and some
without; a git checkout may have turned CRLF into LF. Readers return the BOM flag and the
newline style so that writers can reproduce the file exactly.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path

BOM = "﻿"
CRLF = "\r\n"
EMPTY_GUID = "00000000-0000-0000-0000-000000000000"
GUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
DATA_VALUE_TYPES: dict[str, str] = json.loads((Path(__file__).resolve().parent / "assets" / "data_value_types.json").read_text(encoding="utf-8"))
DVT_OF: dict[str, str] = {v: k for k, v in DATA_VALUE_TYPES.items()}  # type name -> data value type UId
# Types the 8.3.2 designer knows beyond the 8.2.3 list (from its ClientApp bundle); Float0 and Money0/1/3 do not exist in 8.2.3.
DATA_VALUE_TYPES_83: dict[str, str] = json.loads((Path(__file__).resolve().parent / "assets" / "data_value_types_8.3.json").read_text(encoding="utf-8"))
ALL_DATA_VALUE_TYPES: dict[str, str] = {**DATA_VALUE_TYPES, **DATA_VALUE_TYPES_83}
ONLY_83 = {"Float0", "Money0", "Money1", "Money3"}


def new_uid() -> str:
    return str(uuid.uuid4())


def is_uid(value) -> bool:
    return isinstance(value, str) and bool(GUID_RE.fullmatch(value))


def read_text(path: Path) -> tuple[str, bool]:
    """(text with its newlines untouched, had a BOM)."""
    with open(path, encoding="utf-8", newline="") as fh:
        text = fh.read()
    return (text[1:], True) if text.startswith(BOM) else (text, False)


def write_text(path: Path, text: str, bom: bool) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text((BOM if bom else "") + text, encoding="utf-8", newline="")


def newline_of(text: str) -> str:
    return CRLF if CRLF in text or not text else "\n"


def dump_json(obj, nl: str = CRLF) -> str:
    """JSON the way the platform writes it: 2-space indent, non-ASCII kept."""
    return json.dumps(obj, indent=2, ensure_ascii=False).replace("\n", nl)


def wcf_now() -> str:
    """ModifiedOnUtc as the WCF literal the platform parses: \\/Date(ms)\\/ (whole seconds, as an export has them)."""
    return f"\\/Date({int(time.time()) * 1000})\\/"
