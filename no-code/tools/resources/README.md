---
description: Creatio captions of a whole package (Resources/<Schema>.<Kind>/resource.<culture>.xml of every schema kind) - which cultures the package ships and which schemas carry which, the keys missing per culture and schema, filling a culture from another, setting, renaming and removing a key in every culture; only changed files are written, byte for byte otherwise.
---

# Resource tools

Package-level work on the **captions** every schema keeps per culture, for a localisation task:
what the package ships, what is missing where, and the edits that touch many files. Each kind's
own toolkit still edits its captions through the same `Resources` class. Pure Python standard
library.

| File | What it does |
| --- | --- |
| `resources.py` | CLI: cultures, missing, fill, set, rename-key, remove-key |
| `../creatio_schemas/resources.py` | `Resources` (one folder) and `package_resources(package)` (every folder, `.kind` the suffix) |
| `tests/test_resources_tools.py` | checks on copies of the process and user-task fixtures |

```bash
python resources.py cultures UsrPkg
python resources.py missing  UsrPkg --culture ru-RU --keys
python resources.py fill     UsrPkg --to ru-RU --dry-run      # the diff of every file that would change
python resources.py fill     UsrPkg --to ru-RU
python resources.py set      UsrPkg UsrOrder Caption en-US="Order" ru-RU="Заказ"
python resources.py rename-key UsrPkg UsrOrder_FormPage LocalizableStrings.OldText LocalizableStrings.NewText
```

## How it is stored

`Resources/<Schema>.<Kind>/resource.<culture>.xml`, one file per culture, BOM, CRLF:
`<Resources Culture="..."><Group Type="String"><Items><Item Name="Key" Value="..." /></Items></Group></Resources>`;
image items carry `Type`, `ContentType`, `FileExtension` before `Value`. Kind suffixes in the
local packages (1394 folders): ClientUnit 343, Entity 335, Process 262, Addon 250, SourceCode 165,
Dcm 32, ProcessUserTask 4, Service 3. A schema has a file per culture it was saved in: the
designer writes element captions in en-US only, so most culture files hold fewer keys than en-US
(4083 such files), and 590 folders lack a culture their package ships at all. A missing key shows
the en-US text in the interface.

The package's cultures are the union over its schemas (local packages: 28 in 17 of 23, 1 in 2).
`descriptor.json` of a schema repeats its en-US `Caption`.

## What the tools write

- `missing` compares every schema with `--from` (en-US) in each culture of the package, a culture
  the schema has no file for counting as all of its keys; `--kind` takes `object`, `page`,
  `process`, `dcm`, `user-task`, `source`, `addon` or a folder suffix.
- `fill` copies the values of those keys from `--from` into `--to`, image items with their
  attributes; a schema without a `--to` file gets one.
- `set` sets a key in the cultures given (and the en-US `Caption` in `descriptor.json` too);
  `rename-key` / `remove-key` act on the key and every key under it (`Key.`) in every culture.
- Only files whose text changes are written; `--dry-run` prints their unified diff. A file is
  rendered by `Resources`, which reproduces all 9426 local resource files byte for byte.

## Verified

Files only: every resource file of the local package folders renders to its own bytes; `cultures`
and `missing` on a 24-schema package with 28 cultures answer in under a second. Not pushed: a filled
culture is plain resource text the platform already reads.

## Checks

```bash
python tests/test_resources_tools.py
```
