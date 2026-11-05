---
command: idp-unbind
block: clio-security
source: clio 8.1.0.145, clio/docs/commands/idp-unbind.md (MIT)
---
# idp-unbind - Unbind an identity provider from an external service or feature code

Unbind an identity provider from an external service or feature code.


## Usage

```bash
clio idp-unbind --service-code <VALUE> [options]
```


## Options

```bash
--service-code <VALUE>   External service or feature code. Required.
--timeout <NUMBER>       Request timeout in milliseconds. Default: 100000.
-e, --Environment        Environment name.
```


## Examples

```bash
clio idp-unbind --service-code GlobalSearch -e dev
```
