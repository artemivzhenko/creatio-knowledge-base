---
command: check-auth-code-flow
block: clio-security
source: clio 8.1.0.145, clio/docs/commands/check-auth-code-flow.md (MIT)
---
# check-auth-code-flow - check whether the environment can use the OAuth authorization code flow

## Name

check-auth-code-flow - check whether the environment can use the OAuth authorization code flow


## Aliases

auth-code-flow


## Description

The check-auth-code-flow command reads the Creatio endpoint
`identityServiceInfo/canUseAuthorizationCodeFlow` and reports whether the environment is
configured to use the OAuth authorization code flow with the Identity Service. Useful as a quick
diagnostic when setting up the AI chat identity flow.


## Synopsis

```bash
check-auth-code-flow [options]
```


## Options

```bash
--format                            Output format: text (true/false, default) or json (canUseAuthorizationCodeFlow object)
Default: text

--timeout                           Request timeout in milliseconds
Default: 100000

--uri                   -u          Application uri

--Password              -p          User password

--Login                 -l          User login (administrator permission required)

--Environment           -e          Environment name

--Maintainer            -m          Maintainer name

--clientId                          OAuth client id

--clientSecret                      OAuth client secret

--authAppUri                        OAuth app URI
```


## Examples

```bash
clio check-auth-code-flow -e development
Print true or false for the development environment

clio auth-code-flow -e development --format json
Print a JSON object with the canUseAuthorizationCodeFlow flag
```


## Output

    0       Flag retrieved successfully
    1       Flag could not be retrieved or an error occurred


## Prerequisites

- Valid Creatio environment with accessible web services
