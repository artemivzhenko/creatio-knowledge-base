# Project environment synchronization

`python no-code/tools/project.py sync <project.json> [--framework <folder>]`
copies `environment.url`, `login`, and `password` from the project into the test
framework's `Configuration/creatio.env.config.json`. The framework defaults to
`paths.testFramework`, relative to `project.json` when not absolute.

Existing unrelated configuration and case folders are retained; new files use
`./Cases`. The command prints changed field names, never credentials. The project
file is the source of truth; do not copy credentials back from the framework.
When an existing file changes it is rewritten as JSON; its comments and formatting
are not retained.
