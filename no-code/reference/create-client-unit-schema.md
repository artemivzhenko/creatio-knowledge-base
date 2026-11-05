---
command: create-client-unit-schema
block: clio-schemas
source: clio 8.1.0.145, clio/docs/commands/create-client-unit-schema.md (MIT)
---
# create-client-unit-schema - Create a new JavaScript (ClientUnit) schema on a remote Creatio environment

## Name

create-client-unit-schema - Create a new JavaScript (ClientUnit) schema on a remote Creatio environment

**Aliases:** `client-unit-schema-create`


## Description

The create-client-unit-schema command creates a new JavaScript (ClientUnit) schema on a
remote Creatio environment via ClientUnitSchemaDesignerService. The schema is saved
directly to the server; no local workspace files are created.

The schema-name must start with a letter and contain only letters, digits, or underscores.
The name must be unique within the environment.


## Synopsis

```bash
clio create-client-unit-schema [options]
```


## Options

```bash
--schema-name                      New schema name (required)

--package-name                     Target package name that will own the new schema (required)

--caption                          Optional display caption; defaults to schema-name

--description                      Optional schema description

--caption-culture                  Override the culture for the generated schema
                                   caption (e.g. en-US, uk-UA). Precedence:
                                   override > the connected user's profile
                                   culture (see get-user-culture) > en-US.

--uri                    -u       Application uri

--Password               -p       User password

--Login                  -l       User login (administrator permission required)

--Environment            -e       Environment name

--Maintainer             -m       Maintainer name
```


## Example

```bash
clio create-client-unit-schema --schema-name UsrHelperModule --package-name Custom -e dev

clio create-client-unit-schema --schema-name UsrHelperModule --package-name Custom --caption "Helper Module" -e dev
# Create with a display caption
```


## Notes

- The schema caption is stored under the resolved culture (`--caption-culture` override > the connected user's profile culture > `en-US`). A caption whose script does not match a Latin-script culture (for example Cyrillic under `en-US`) is rejected with an actionable error; pass `--caption-culture` to author the caption in a specific language.
