"""Checks for the expression module (conditions grammar, meta paths, rendering), without a package."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from creatio_schemas import filters  # noqa: E402
from creatio_schemas.expressions import Column, Condition, Const, Group, Null, Param, Setting, Sys, decode, describe, encode, lookup, parse  # noqa: E402
from creatio_schemas.rules.builder import spec_op, when_conditions  # noqa: E402
from creatio_schemas.rules.model import OPS  # noqa: E402

SPELLINGS = {
    "eq": ["=", "==", "equal"], "ne": ["!=", "<>", "not-equal"], "lt": ["<", "less"], "le": ["<=", "less-or-equal"],
    "gt": [">", "greater"], "ge": [">=", "greater-or-equal"], "contains": ["contains", "contain"],
    "not-contains": ["not contains", "not-contains", "not-contain"], "starts": ["starts with"], "ends": ["ends with"],
}
UNARY = {"empty": ["is null", "empty"], "filled": ["is not null", "filled"]}


def test_every_spelling_of_every_operator():
    for canonical, spellings in SPELLINGS.items():
        for s in spellings:
            for text in (f"UsrA {s} 5", f"UsrA {s.upper()} 5") if s[-1].isalpha() else (f"UsrA {s} 5", f"UsrA{s}5"):
                assert parse(text) == [Condition("UsrA", canonical, Const("5"))], text
    for canonical, spellings in UNARY.items():
        for s in spellings:
            assert parse(f"UsrA {s}") == [Condition("UsrA", canonical, Null())], s


def test_the_five_operand_forms_and_quotes():
    right = lambda text: parse("UsrA = " + text)[0].right
    assert right("100") == Const("100") and right("'a b'") == Const("a b", quoted=True) and right('"x;y"') == Const("x;y", quoted=True)
    assert right("{Parameter:Counter}") == Param("Counter") and right("{Record:UsrB}") == Column("UsrB") and right("attr:UsrB") == Column("UsrB")
    assert right("sys:CurrentUser") == Sys("CurrentUser") and right("setting:UsrLimit") == Setting("UsrLimit")
    assert right("Not started") == Const("Not started")  # a literal keeps its inner spaces


def test_conditions_are_split_on_semicolons_and_dotted_columns_are_left_sides():
    assert parse("UsrA > 1; ; Order.Status is not null;") == [Condition("UsrA", "gt", Const("1")), Condition("Order.Status", "filled", Null())]
    assert parse("") == []


def test_refusals_name_the_text_and_the_operators():
    for text in ("> 5", "UsrA", "UsrA ~ 5", "UsrAempty", "UsrA between 1"):
        try:
            parse(text)
            assert False, text
        except ValueError as e:
            assert f"cannot read condition {text.strip()!r}" in str(e) and "starts with" in str(e), str(e)


def test_describe_prints_one_way_whatever_the_source():
    c = parse("UsrAmount >= 100; UsrStatus filled; UsrType not-contain x; UsrOwner = sys:CurrentUser; UsrNote = 'a;b'")
    assert describe(c) == 'UsrAmount >= 100 and UsrStatus is not null and UsrType not contains x and UsrOwner = sys:CurrentUser and UsrNote = "a;b"'
    nested = Group((c[0], Group((c[1], Condition("UsrB", "eq", Const("1"), enabled=False)), "or")))
    assert describe(nested) == "UsrAmount >= 100 and (UsrStatus is not null or UsrB = 1 (disabled))"
    assert describe(Condition("UsrB", "between", Const("1, 5"))) == "UsrB between 1, 5"  # a stored comparison with no canonical name
    assert describe(Group(())) == ""


class FakeNames:
    """A process with a parameter `Counter`, a step `Step1` whose parameter `Result` reads the object UsrOrder."""

    UIDS = {("Parameter", "Counter", None): "p-1", ("Element", "Step1", None): "e-1", ("Parameter", "Result", "Step1"): "ep-1"}

    def uid_of(self, kind, name, parent=None):
        if kind == "EntityColumn":
            return f"col:{name}:{parent}"
        try:
            return self.UIDS[(kind, name, parent)]
        except KeyError:
            raise KeyError(f"no {kind} {name!r}") from None

    def name_of(self, uid):
        return {"p-1": "Counter", "e-1": "Step1", "ep-1": "Result"}.get(uid)


def test_meta_paths_round_trip_through_names():
    names = FakeNames()
    prefix = "[#[IsOwnerSchema:false].[IsSchema:false]"
    assert encode("{Parameter:Counter} > 10", names) == f"{prefix}.[Parameter:{{p-1}}]#] > 10"
    path = encode("{Element:Step1.Parameter:Result}", names)
    assert path == f"{prefix}.[Element:{{e-1}}].[Parameter:{{ep-1}}]#]" and decode(path, names) == "{Element:Step1.Parameter:Result}"
    assert encode("{Element:Step1.Parameter:Result.EntityColumn:UsrName}", names).endswith(".[EntityColumn:{col:UsrName:Step1.Result}]#]")
    assert decode("[#[IsOwnerSchema:false].[IsSchema:false].[Parameter:{zzz}]#]", names) == "{Parameter:zzz}"  # an unknown id is kept
    assert decode(5, names) == 5 and encode("plain text", names) == "plain text"
    assert lookup("ref-uid", "rec") == "[#Lookup.ref-uid.rec#]" and lookup("ref-uid", "rec", "Status") == "[#Lookup.Status.rec.rec#]"


def test_encode_refuses_what_it_cannot_resolve():
    for text, message in (("{Parameter:Missing}", "no Parameter 'Missing'"), ("{Record:UsrB}", "cannot encode {Record:UsrB}")):
        try:
            encode(text, FakeNames())
            assert False, text
        except (KeyError, ValueError) as e:
            assert message in str(e), str(e)


def test_filters_read_the_shared_grammar():
    assert filters.parse_conditions("UsrAmount > 100; UsrStatus is not null; UsrType == 'Parcel x'; UsrA <> 2; UsrB not contains z") == [
        ("UsrAmount", ">", "100"), ("UsrStatus", "is not null", ""), ("UsrType", "=", "Parcel x"), ("UsrA", "!=", "2"), ("UsrB", "not contains", "z")]
    assert filters.parse_conditions("UsrA filled; UsrB empty") == [("UsrA", "is not null", ""), ("UsrB", "is null", "")]
    built = filters.build("UsrOrder", filters.parse_conditions("UsrA not contains z"), {"UsrA": ("ShortText", None)})
    summary = filters.summarize(filters.load(built), "UsrOrder")
    assert summary == "UsrOrder where UsrA not contains z"


def test_rules_read_the_shared_grammar():
    assert when_conditions("UsrAmount > 100; UsrOwner = sys:CurrentUserContact; UsrFlag = true; UsrB = {Record:UsrC}; UsrD filled; UsrN = '7'") == [
        {"left": "UsrAmount", "op": "greater", "value": 100}, {"left": "UsrOwner", "op": "equal", "sys": "CurrentUserContact"},
        {"left": "UsrFlag", "op": "equal", "value": True}, {"left": "UsrB", "op": "equal", "attr": "UsrC"},
        {"left": "UsrD", "op": "filled"}, {"left": "UsrN", "op": "equal", "value": "7"}]
    assert spec_op("equal") == OPS["equal"] and spec_op("<=") == OPS["less-or-equal"] and spec_op("is not null") == OPS["filled"] and spec_op(3) == 3
    for text in ("UsrA starts with x", "UsrA = {Parameter:P}"):
        try:
            when_conditions(text)
            assert False, text
        except ValueError:
            pass



def test_an_apostrophe_inside_a_word_does_not_open_a_quote():
    from creatio_schemas.filters import parse_conditions
    assert parse_conditions("Name = O'Brien; UsrAmount > 1") == [("Name", "=", "O'Brien"), ("UsrAmount", ">", "1")]
    assert parse_conditions("Name = 'a; b'; UsrAmount > 1") == [("Name", "=", "a; b"), ("UsrAmount", ">", "1")]
    # a quoted literal round-trips through the text form, quotes inside it included
    from creatio_schemas.expressions.conditions import Const, operand
    from creatio_schemas.expressions.render import operand_text
    for text in ('say "hi"', "a; b", "plain"):
        assert operand(operand_text(Const(text, quoted=True))) == Const(text, quoted=True), text

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
