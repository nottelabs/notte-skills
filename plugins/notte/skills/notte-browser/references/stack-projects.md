---
name: stack-projects
description: Guide to managing a git-versioned project of Notte functions with notte stack
---

# Stack Projects Reference

`notte functions` manages one deployed function at a time, by id. `notte stack`
manages a directory of them as a project: sources in git, shared code imported
normally, and a lockfile recording what each function became in each
environment.

Use `notte functions` for a one-off file. Use `notte stack` when you have more
than one function, or any code shared between them.

## Requirements

`notte stack` needs [uv](https://astral.sh/uv), which also supplies the Python
the runtime uses:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

The rest of the CLI needs nothing.

## Layout

```
notte.toml               project config, hand-written
notte.lock.json          per-environment function ids and hashes, machine-written
.notte/                  venv and build output, gitignored
functions/
  _shared/               underscore means library, never deployed
    http.py
  amazon_search/
    main.py              the entrypoint: exactly one run()
    parse.py             a helper, bundled into the artifact
    test_main.py         a test, never bundled
  quick_check.py         a single-file function
```

Anything under `functions/` whose name does not start with `_` is a unit: a
directory with `main.py`, or a top-level `<name>.py`.

Shared code is imported normally and flattened away at deploy time:

```python
from .parse import clean
from .._shared.http import fetch_json
```

## Commands

```bash
notte stack init [dir]              # scaffold notte.toml, functions/, editor config
notte stack new <name>              # scaffold one function
notte stack sync                    # build .notte/venv mirroring the runtime
notte stack check [target]          # bundle, validate and type check. Writes nothing remote
notte stack status                  # what changed since the last deploy
notte stack deploy [target]         # build, validate, upload, apply schedules
notte stack pull                    # adopt functions that already exist remotely
notte stack secrets diff            # required secrets that are not configured
notte stack secrets push [file]     # set missing secrets from .env.<env>
notte stack doctor                  # toolchain, environment and runtime report
```

`target` is a name, a glob, `all`, or a path, so `notte stack deploy
functions/amazon_search` works and tab-completes.

`notte stack install` is an alias for `sync`.

## Typical flow

```bash
notte stack init && cd .
notte stack sync            # editor now resolves notte_sdk and pydantic
notte stack new scraper
notte stack check           # catches contract, import and type errors locally
notte stack deploy
```

`deploy` uploads only what changed, tracked per environment in the lockfile, and
asks before writing unless `--yes` is passed.

## notte.toml

The minimal file is three lines; environments are opt-in and most projects never
add them.

```toml
[project]
name = "my-stack"

[functions.amazon_search]
name         = "Amazon product search"
description  = "Searches by keyword"
domain       = "amazon.com"
instructions = "Takes ~30s. `query` is the search term."
cron           = "cron(0 9 * * ? *)"      # six-field AWS EventBridge form
cron_variables = { query = "laptop" }     # arguments the scheduled run uses
secrets        = ["PARTNER_TAG"]          # beyond what the AST scan finds
```

Metadata is applied on every deploy, so editing `description` here reaches the
deployed function on the next `notte stack deploy`.

`self_healing` exists but only works for functions an agent built: it resumes
the thread that created them, and a CLI deploy has none.

## Environments

`--env` defaults to `prod` and most projects never pass it. A project with
several environments declares them, and the endpoint and its credential are
always resolved together:

```toml
[env.staging]
api_url = "https://us-staging.notte.cc"
api_key = "${env:NOTTE_API_KEY_STAGING}"
```

Naming an environment that resolves to a different endpoint is refused rather
than silently retargeted.

## Secrets

Secret names live in git; values do not.

```bash
notte stack secrets diff              # what the deployed functions require
notte stack secrets push              # sets missing ones from .env.<env>
```

Read them in a function through the SDK, since bare `import os` is rejected:

```python
from notte_sdk.types import os

def run() -> Response:
    token = os.environ["PARTNER_TAG"]
```

`deploy` warns when a function requires a secret that is not configured, and
refuses to schedule it — a cron that fails at 09:00 is a bad way to find out.

## What check enforces

`notte stack check` writes nothing remote, so it is safe as a CI gate. It runs
the runtime's own rules rather than a local copy of them, fetched from
`GET /functions/health`:

- exactly one top-level `run()`, returning a `BaseModel` declared in the file
- only imports the runtime actually ships, at the versions it ships
- a type check over both the sources and the flattened artifact

Diagnostics are mapped back from the artifact to the file and line they came
from.

## Things the bundler rejects, and the fix

| Rejected | Instead |
|---|---|
| `from . import parse` then `parse.clean()` | `from .parse import clean` |
| `from .parse import *` | import the names explicitly |
| two modules defining the same top-level name | rename one |
| an import sharing a line with anything else | put each import on its own line |
| a relative import inside a function body | move it to the top of the file |

Aliases survive: `from .parse import clean as scrub` still binds `scrub`.
