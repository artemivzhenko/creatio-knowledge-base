"""The site lines of an object snapshot, through a FakeClio that answers one result file per statement."""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
sys.path.insert(0, str(HERE))

from test_env_tools import FakeClio  # noqa: E402

from creatio_schemas.environment import Environment  # noqa: E402
from creatio_schemas.integrity import compare, site_lines  # noqa: E402

COLUMNS = [{"column": "Id", "type": "uuid", "length": None, "nullable": "NO"},
           {"column": "Name", "type": "character varying", "length": "250", "nullable": "NO"},
           {"column": "UsrNote", "type": "character varying", "length": "50", "nullable": "YES"}]
LAYERS = [{"package": "CrtCoreBase", "extendParent": "false", "modifiedOn": "", "modifiedBy": "", "isChanged": "false", "manager": "", "size": "1", "md5": "a",
           "sl": "1", "pl": "2"},
          {"package": "UsrLayer", "extendParent": "true", "modifiedOn": "", "modifiedBy": "", "isChanged": "false", "manager": "", "size": "1", "md5": "b",
           "sl": "1", "pl": "1"}]


def site(columns=COLUMNS, md5=("aaa", "bbb")):
    clio = FakeClio(rows=[columns, [{"n": 6}], LAYERS, [{f"c{i}": m for i, m in enumerate(md5)}]])
    return Environment("https://s", "u", "p", clio_name="dev", clio_run=clio), clio


def test_site_lines_are_one_statement_each():
    env, clio = site()
    lines = site_lines(env, "UsrObj")
    assert lines == ["table UsrObj column Id uuid", "table UsrObj column Name character varying(250)", "table UsrObj column UsrNote character varying(50) null",
                     "rows 6", "checksum Name aaa", "checksum UsrNote bbb", "copy CrtCoreBase extendParent=false", "copy UsrLayer extendParent=true"], lines
    assert "information_schema.columns" in clio.scripts[0] and "table_name = 'UsrObj'" in clio.scripts[0]
    assert 'count(*)' in clio.scripts[1]
    assert "md5(string_agg(coalesce(\"Name\"::text, ''), '|' order by \"Id\"))" in clio.scripts[3] and "\"UsrNote\"" in clio.scripts[3]
    assert "\"Id\"::text" not in clio.scripts[3]  # Id orders the rows, it is not checksummed


def test_named_columns_and_chunks_of_fifty():
    env, clio = site()
    clio.rows[1:] = [[{"n": 1}], LAYERS, [{"c0": "x"}]]  # count, layers, one checksum
    assert "checksum UsrNote x" in site_lines(env, "UsrObj", ["UsrNote"])
    many = [{"column": f"C{i}", "type": "integer", "length": None, "nullable": "NO"} for i in range(120)]
    clio = FakeClio(rows=[many, [{"n": 0}], LAYERS, [{f"c{i}": "m" for i in range(50)}], [{f"c{i}": "m" for i in range(50)}], [{f"c{i}": "m" for i in range(20)}]])
    env = Environment("https://s", "u", "p", clio_name="dev", clio_run=clio)
    lines = site_lines(env, "UsrBig")
    assert len([l for l in lines if l.startswith("checksum")]) == 120
    assert len(clio.scripts) == 6, len(clio.scripts)  # columns, count, layers, three chunks


def test_a_missing_table_or_column_is_named():
    env, _ = site(columns=[])
    try:
        site_lines(env, "UsrNope")
    except KeyError as e:
        assert "no table UsrNope" in str(e)
    else:
        raise AssertionError("expected KeyError")
    env, _ = site()
    try:
        site_lines(env, "UsrObj", ["UsrGone"])
    except KeyError as e:
        assert "UsrGone" in str(e)
    else:
        raise AssertionError("expected KeyError")


def test_a_planted_difference_is_a_bug_report():
    env, _ = site()
    before = site_lines(env, "UsrObj")
    assert compare(before, before) == []
    env, _ = site(columns=COLUMNS[:2], md5=("aaa",))  # the layer's column is gone from the table
    after = site_lines(env, "UsrObj")
    diff = compare(before, after)
    assert "- table UsrObj column UsrNote character varying(50) null" in diff and "- checksum UsrNote bbb" in diff, diff
    env, _ = site(md5=("aaa", "zzz"))  # the data changed
    assert compare(before, site_lines(env, "UsrObj")) == ["- checksum UsrNote bbb", "+ checksum UsrNote zzz"]
    rows = [COLUMNS, [{"n": 5}], LAYERS, [{"c0": "aaa", "c1": "bbb"}]]
    env = Environment("https://s", "u", "p", clio_name="dev", clio_run=FakeClio(rows=rows))
    assert compare(before, site_lines(env, "UsrObj")) == ["~ rows  6 -> 5"]


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
