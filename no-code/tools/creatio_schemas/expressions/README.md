---
description: The condition grammar and the meta-path codec shared by filters, business rules, DCM steps and process expressions - one text form for "column op value" with every operator spelling, the Names protocol behind {Parameter:X} / {Element:E.Parameter:P}, and describe, which prints stored conditions back the same way.
---

# expressions

One grammar for a condition, one codec for the designer's meta paths, one way to read them back. Pure standard library.

```
expressions/
  conditions.py   parse(text) -> [Condition]; Condition(left, op, right); the operands Const, Param, Column, Sys, Setting, Null
  metapath.py     encode(text, names) / decode(text, names) over [#...#]; Names (uid_of, name_of); lookup(schema, record)
  render.py       describe(Condition | Group | list) -> "UsrAmount > 100 and UsrStatus is not null"
```

## The grammar

`<Column> <op> <value>`, ANDed with `;` (a `;` inside quotes stays). `Column` is a name or a dotted path.

| canonical | spellings |
| --- | --- |
| `eq` | `=` `==` `equal` |
| `ne` | `!=` `<>` `not-equal` |
| `lt` `le` `gt` `ge` | `<` `<=` `>` `>=`, or `less` `less-or-equal` `greater` `greater-or-equal` |
| `contains` / `not-contains` | `contains` `contain` / `not contains` `not-contains` `not-contain` |
| `starts` / `ends` | `starts with` / `ends with` |
| `empty` / `filled` | `is null` `empty` / `is not null` `filled` (no value) |

The value is one of: a literal (quotes dropped; `'a;b'` keeps the `;`), `{Parameter:X}`, `{Record:Col}` or `attr:X`,
`sys:CurrentUser`, `setting:Code`. A consumer takes what it can store and refuses the rest with a message: a filter
stores the text of any operand as a literal, a rule has no `{Parameter:X}` and no `starts with`, a DCM step result
takes `==`, `!=`, `<`, `<=`, `>`, `>=` and a literal.

## Where it is used

| Toolkit | Text in | Printed by |
| --- | --- | --- |
| filters (`filters.parse_conditions`: signals, data elements) | `UsrAmount > 100; UsrStatus is not null` | `filters.summarize` |
| rules | `"when": "UsrAmount > 100; UsrOwner = sys:CurrentUserContact"` in the spec, next to or instead of `conditions` | `inspect`'s `when` line |
| DCM steps | `NextStage = Stage4` in the `conditions` of `add_step` | `DcmSchema.conditions()` |

The `op` of a rule spec's `conditions` entries also takes any spelling (`">="`, `"is not null"`).

## Meta paths

`encode` turns `{Parameter:X}`, `{Element:E.Parameter:P}` and `{Element:E.Parameter:P.EntityColumn:<uid or Column>}`
into `[#[IsOwnerSchema:false].[IsSchema:false]...#]` and refuses any `{...}` it cannot resolve (the platform reads an
unencoded one as "Expression expected" at run time). The schema that owns the names implements `Names`:
`uid_of(kind, name, parent)` raises its own error for a name it does not have, `name_of(uid)` gives the name or None.
`process.ExpressionCodec` (a process) and DCM's `_Names` (a case, a step) are the two implementations; `decode` keeps
an unknown id as text. `lookup(schema, record)` is `[#Lookup.<schema uid>.<record id>#]`.

## Not here

Evaluating a formula, a filter editor for page requests, and translating between a FilterGroup and rule nodes (they
run in different places and stay separate).
