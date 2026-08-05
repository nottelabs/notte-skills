# Changelog

All notable changes to the `notte` plugin are documented here. The plugin was
named `notte-cli` before 2026-08-05; the pre-reset entries below describe it
under that name.

**Versioning restarts at `0.0.x`.** The plugin was never published, so the
`1.x` numbers that appear further down were reconstructed from `git log` rather
than shipped to anyone. Nothing depended on them, so they are retired here
rather than carried forward. Under `0.x`, breaking changes are expected and do
not need a major bump - see <https://semver.org/#spec-item-4>. Tag releases as
`notte-v<version>` from the first real release so consumers can pin instead of
tracking the default branch.

## 0.0.2 (2026-08-06)

First versioned state of the plugin, and the first entry after the version
reset. Combines everything on this branch: a full re-verification of every
documented command against `notte` CLI **v0.0.29** (reading the CLI source, and
deploying real Functions, where `--help` did not settle the behaviour), and the
`notte-functions-build` rename. These were drafted as two versions before the
reset and are one release now.

### Renames

Called out rather than filed under "breaking": nothing was published under the
old name, so there is nothing downstream to break. Anyone who tried the plugin
from the default branch will need the new invocation.

* **`notte-functions-forge` is renamed to `notte-functions-build`.** Invocations
  change accordingly: `/notte-functions-build` in Claude Code,
  `$notte:notte-functions-build` in Codex. "Forge" was a metaphor nobody types —
  the skill description had to enumerate "forge, build, generate, or bake" to be
  discoverable, which is a tell that the name was not carrying itself. "Build"
  also matches the vocabulary of the `anything-api` MCP server, whose `build`
  tool does the same job from natural language, so the two now read as one
  concept. `notte-functions-doctor` keeps its name: the metaphor is apt,
  unambiguous, and less prone to over-triggering than "repair" or "fix" would be.
  Prose, filenames (`built_function.py`), and cross-references were updated with it

### Features

* document `notte search`, `notte profiles`, `notte functions secrets`, and the
  `files` / `usage` / `health` / `clear` / `sessions offset` commands, none of
  which appeared in any skill. `notte-functions-build` now uses `notte search`
  to research a target instead of opening a browser session for it
* document the two bundled MCP servers and when to prefer them over the CLI.
  `anything-api` is a marketplace of ready-made Notte Functions — the build skill now
  checks it (`search`) **before** paying the exploration cost of building a new one
* document the phone-number gate: `notte personas create --create-phone-number`
  fails on a standard account because provisioning is unlocked per-account by
  the Notte team. Both `notte-browser` and the account-management reference now
  say so, tell the agent not to retry or work around it, and point at
  https://cal.com/pintoa/15mins to request access. `notte personas sms` was
  documented with no way to obtain a number
* document the new `sessions start` flags: `--aspect-ratio`, `--screenshot-type`,
  `--chrome-args`, `--extra-http-headers`, `--web-bot-auth`, and the external /
  Tailscale proxy flags, which are relevant to the bot-detection guidance

### Bug Fixes

* **the marketplace check ran before there was anything to search for.** It sat
  in `notte-functions-build` Phase 0, ahead of the phase that works out the
  target site and fields. Moved to Phase 1c, after intent is parsed and before
  the plan gate
* `notte-functions-doctor` Phase 1 called a bare `notte functions list`, which
  pages at 10 — on any busy account the Function being repaired simply would not
  appear. It now widens the page size and prints id + name
* move the "it may have been deleted rather than broken" check into
  `notte-functions-doctor` Phase 1, where the Function fails to turn up, instead
  of Phase 2, where it was too late to be useful
* `[doctor-verify]` throwaway Functions leaked. Cleanup only ran in Phase 6,
  after the contract passed *and* the user approved, so an abandoned or rejected
  repair left copies behind. Phase 5 now reuses an existing throwaway rather than
  stacking new ones, and states that the name-guarded delete runs however the
  repair ends
* `notte-functions-doctor` Phase 6 re-runs the live Function to confirm health,
  which writes again if the Function writes. It now says to let the user decide
  for a Function with side effects, rather than invoking it reflexively
* correct `notte-functions-build` Phase 3, which said to *add* a `run(...)` entry
  point when the export already defines one — an agent could reasonably end up
  with two
* Delivery promised to show "three ways" to invoke a Function and listed two
* the `--var` example used a parameter absent from the worked example
* **`notte functions run` blocks.** `function-management.md` described it as
  fire-and-forget and demonstrated a `sleep 10` + `run-metadata` poll, while
  `self-test.md` and both Function skills built their entire pass/fail protocol
  on the inline `result`. The CLI issues one synchronous POST with no
  client-side polling, so the blocking description is the correct one; the poll
  loop is gone
* **document the 60-second timeout trap, and that retrying it double-executes.**
  Because the run is synchronous it is bounded by the global `--timeout`, so a
  slow Function fails the *command* while the run continues server-side — which
  reads as a broken Function. Verified what actually happens: a Function invoked
  with `--timeout 10` that needed ~45s returned `context deadline exceeded` to
  the caller, yet its run stayed `active` and completed normally with the right
  `result` ~35s later. So the client giving up does **not** cancel the run, and
  "re-run with a bigger timeout" invokes the Function a second time —
  duplicating any form submission, purchase or write. The skills now say to set
  a generous timeout on the *first* invocation and, on a timeout, to recover the
  in-flight run (`notte functions runs`, whose active-only default surfaces
  exactly those) rather than retry. `notte-functions-doctor` additionally warns
  to check the workflow file for side effects before re-running to reproduce a
  failure, since it operates on live and possibly scheduled Functions
* **credential guidance no longer contradicts itself.** The skill warned that
  `--password` leaks via `argv`, then prescribed `--password "$VAR"` as the fix
  — but the shell expands that before `exec`, so `ps` sees the plaintext either
  way. Now states precisely what the env-var form does (keeps secrets out of
  shell history and committed files) and does not (hide them from `ps`), and
  directs callers to add a credential once and rely on the vault thereafter
* **`templates/authenticated-session.sh` no longer extracts a plaintext
  password.** It called `notte vaults credentials get`, put the password in a
  shell variable, and passed it as an argv to `notte page fill` — the exact leak
  the skill warns about, and a defeat of the sentinel mechanism. Rewritten to
  attach the vault with `--vault-id` and fill sentinels, with a comment
  explaining why the old approach must not be reintroduced. Its login check no
  longer greps page text for "error" (false positives) and no longer returns
  success when it cannot tell
* **one name for file storage.** `use_file_storage=True` was written three ways
  across four files (`enable_file_storage=True`, `storage=...`). Standardised on
  the real keyword, which matches the `--use-file-storage` flag
* **settle the trailing `run()` question — verified by deploying and running
  real Functions.** Examples disagreed on whether a Function file should call
  `run()` at module level, with no note either way. It is optional: a Function
  with no trailing call returned its value normally (the runtime invokes `run()`
  itself), and one *with* a trailing call logged exactly one invocation, so
  there is no double execution either. Said so explicitly in the reference, the
  interop notes, the skeleton, the build skill's cleanup step, and the rules, so the
  next reader does not infer a rule from the inconsistency
* **document the two `result` shapes.** `notte functions run` returns the value
  of `run()` serialized to JSON, so a `dict` arrives as a real nested object
  addressable with `jq`. `run-metadata`'s `result` is a Python `repr`
  (single-quoted, not valid JSON) — which is why contract validation should read
  `functions run` and use `run-metadata` for logs
* **document what "active" means on each list command — it differs per
  resource.** Verified against the API by creating, deleting and stopping real
  records: for `functions`, `vaults` and `personas` it means *not deleted*; for
  `sessions` and `agents` it means *still running*; for `functions runs` it
  means *still executing*. A new "Filters on list commands" section spells this
  out, because a reader who learns the flag on `sessions list` will guess wrong
  on `functions list`. Two rules follow: never widen an artifact listing by
  reflex (that surfaces soft-deleted records, and acting on a deleted id fails
  confusingly), and do widen run listings, since `notte functions runs` lists
  `[]` once every run has finished. This mattered most in
  `notte-functions-doctor`, whose Phase 2 recovers the last good run to learn
  what correct output looks like — empty history would have read as "this
  Function never worked" and pushed it to the wrong failure class. Doctor also
  now checks `--include-deleted` before treating a missing Function as broken,
  since a deleted Function is not a repair job. Guidance is written to work on
  every CLI version: `--only-active=false` is valid everywhere, while newer
  CLIs use `--include-deleted`, `-a`/`--all` and `--running`
  (nottelabs/notte-cli#58)
* document that `functions run` returns no logs — they come from `run-metadata`
* **fix `len()` on a scrape result.** Four examples called `len()` on
  `session.scrape(...)` output to produce a `count`, which counts dict *keys*
  rather than rows. Rewritten to use `response_format` and count the typed list
* **reconcile vault credential filling.** `account-management.md` said
  credentials "auto-fill" on navigation; the skill said you must fill exact
  sentinel strings. The sentinel mechanism is correct — the reference now
  documents it, and its worked example attaches the vault it declares instead of
  setting `VAULT_ID` and never using it
* **correct the documented `scrape -o json` shape.** `exploration.md` said the
  parsed extraction lived under `.structured.data` with a `{markdown,
  structured}` wrapper. Checked against a live scrape: with `--instructions` the
  extracted object comes back **at the top level** (the requested fields are the
  JSON keys), and without them you get `{"markdown": "..."}` and nothing else.
  There is no wrapper. `templates/data-extraction.sh` unwrapped the phantom
  `.structured.data` and only worked by falling through its own `//` fallback;
  both merge steps now use the object directly
* remove `notte page observe https://example.com` — `observe` takes no arguments
* remove `--browser-type firefox`, which v0.0.29 no longer supports (only
  `chromium` and `chrome`; `chrome-nightly` / `chrome-turbo` are legacy aliases)
* correct the global `--timeout` default from 30 to 60 seconds
* correct `page captcha-solve "recaptcha"` to a real challenge type
  (`recaptcha_v2`), and clarify that `page click --timeout` is milliseconds
  against the element, distinct from the global seconds-based API timeout
* document `--vault-id` on `sessions start`, `notte sessions viewer`, the
  `--path` / positional output on `page screenshot`, the download-and-print
  behaviour of `sessions network`, and the difference between `sessions code`
  and `sessions workflow-code`
* fix `agents start`: add `--url`, `--use-vision`, `--response-format-json`, and
  `--session-offset`; drop the invented "(default: 30)" on `--max-steps`; list
  the reasoning models the CLI actually accepts
* fix the observe example, which returned `B1`/`B2` for *input* fields and then
  filled them, contradicting the `I*` = input convention used everywhere else
* `notte functions show` returns a download URL, not inline source, and cannot
  read a cron back — both now documented where the commands are introduced
* unbreak the mangled examples: a `bash` fence containing Python with steps
  numbered 1,2,3,4,5,5,6,7,8; the `eval-js` section with markdown bullets inside
  a bash fence; and the "Scheduled Data Collection" snippet that scheduled a
  `<function-id>` it never captured, from a workflow file whose body was `# ...`
* fix `data-extraction.sh`, which merged scrape output as a bare JSON array when
  `-o json` actually returns `{markdown, structured}`, silently producing garbage
* widen `allowed-tools` on all three skills. They were restricted to
  `Bash(notte:*)` while instructing the agent to run `curl`, `jq`, and `diff` —
  doctor could not perform its own Phase 1 source download or Phase 6 diff

## 0.0.1 - prior unreleased history

Everything that existed before the reset, collapsed into one entry because
none of it was ever released. The original headings are kept below for
provenance; their version numbers no longer mean anything.

### [1.5.0](https://github.com/nottelabs/notte-skills/compare/notte-v1.4.0...notte-v1.5.0) (2026-08-05)

Packaging and distribution only — no skill content changed.

### Features

* add a native OpenAI Codex surface. Codex already installed this repository through its compatibility fallbacks for `.claude-plugin/marketplace.json` and `.claude-plugin/plugin.json`, but with no Codex-specific metadata. This adds `.agents/plugins/marketplace.json` (Codex's own marketplace path, with the `policy` and `category` fields it expects) and `plugins/*/.codex-plugin/plugin.json` (preferred over the Claude manifest by Codex), carrying the `interface` block that Codex and ChatGPT install surfaces render: display name, descriptions, category, capabilities, legal links, starter prompts, and a logo
* add `agents/openai.yaml` to `notte-browser`, `notte-functions-forge`, and `notte-functions-doctor`, so all four skills — not just `migrate-to-notte` — carry a display name, short description, and default prompt on Codex and ChatGPT

### Bug Fixes

* wire the hosted MCP servers into the Cursor plugin. `.cursor-plugin/plugin.json` declared `skills` and `rules` but no `mcpServers`, so Cursor installed skills that referenced a browser it could not reach. The validator now fails if that field goes missing again
* document Codex installation in the README (`codex plugin marketplace add nottelabs/notte-skills`), the `$plugin:skill` invocation form Codex uses, and the `--agent codex` flag for `npx skills add`. The README advertised Codex compatibility but documented no way to install on it
* correct the manual-installation snippet, which copied the *plugin* directory into a *skills* directory and so left every `SKILL.md` two levels deep, where no client scans

### Miscellaneous

* extend `scripts/validate-plugins.py` to cover the Codex surface: both marketplaces must list the same plugins at the same paths, each plugin's Claude and Codex manifests must agree on name/version/description/component paths, manifest `interface` asset paths must resolve, and every skill must ship an `agents/openai.yaml`. That file is parsed rather than scanned, so unknown keys are caught at both levels — including the snake_case/camelCase slip between `openai.yaml` and `plugin.json` — along with a missing `interface` field, a `short_description` outside Codex's documented 25–64 characters, a `default_prompt` that does not invoke `$skill-name`, a malformed `policy` or `dependencies.tools` entry, and any YAML construct the parser cannot represent
* add `scripts/test-validate-plugins.py`, which exercises those checks against malformed and incomplete fixtures, and run it in CI alongside the validator

### [1.4.0](https://github.com/nottelabs/notte-skills/compare/notte-v1.3.0...notte-v1.4.0) (2026-08-05)

Packaging and distribution only — no skill content changed.

### Features

* wire the hosted Notte MCP servers into the plugin: `plugins/notte/.mcp.json` declares `notte-browser` (`https://api.notte.cc/mcp`) and `anything-api` (`https://anything.notte.cc/mcp`) as streamable HTTP servers, referenced from `plugin.json` via `"mcpServers": "./.mcp.json"`. Replaces the inert root `mcp.json`, which used the legacy SSE shape, pointed at `http://localhost:8001/sse`, and was referenced by nothing.

### Bug Fixes

* remove the `notte-sdks` marketplace entry and Cursor skills path, which pointed at a directory that does not exist in the repository
* declare skills explicitly in `plugin.json` (`"skills": "./skills/"`) instead of relying on directory convention
* add `scripts/validate-plugins.py` and run it in CI on every change under `plugins/**` and the manifests

### [1.3.0](https://github.com/nottelabs/notte-skills/compare/notte-v1.2.0...notte-v1.3.0) (2026-07-29)

### Features

* add provider migration and cost skills ([#20](https://github.com/nottelabs/notte-skills/pull/20)) ([3921ff8](https://github.com/nottelabs/notte-skills/commit/3921ff8)) — adds the `migrate-to-notte` and `compare-to-notte-costs` skills covering Browserbase/Stagehand, Kernel, Anchor Browser, Browser Use Cloud, Steel, Hyperbrowser, and Skyvern

### [1.2.0](https://github.com/nottelabs/notte-skills/compare/notte-v1.1.0...notte-v1.2.0) (2026-06-30)

### Features

* add `notte-functions-forge` and `notte-functions-doctor` skills ([#16](https://github.com/nottelabs/notte-skills/pull/16)) ([b051cff](https://github.com/nottelabs/notte-skills/commit/b051cff))

### Bug Fixes

* **notte-browser:** correct the run-output field ([#17](https://github.com/nottelabs/notte-skills/pull/17)) ([7334a3d](https://github.com/nottelabs/notte-skills/commit/7334a3d))

### [1.1.0](https://github.com/nottelabs/notte-skills/compare/notte-v1.0.0...notte-v1.1.0) (2026-06-05)

Documentation and guidance changes to `notte-browser` that shipped silently
under the `1.0.0` version pin.

### Features

* consolidate the Notte browser skill ([#4](https://github.com/nottelabs/notte-skills/pull/4)) ([e103e2b](https://github.com/nottelabs/notte-skills/commit/e103e2b))
* add a Notte docs index pointer ([#5](https://github.com/nottelabs/notte-skills/pull/5)) ([d973fb1](https://github.com/nottelabs/notte-skills/commit/d973fb1))
* document browser profiles ([#14](https://github.com/nottelabs/notte-skills/pull/14)) ([cd85130](https://github.com/nottelabs/notte-skills/commit/cd85130))
* add a session `workflow-code` example ([#15](https://github.com/nottelabs/notte-skills/pull/15)) ([3cb9f9e](https://github.com/nottelabs/notte-skills/commit/3cb9f9e))

### Bug Fixes

* emphasize session workflow export for Functions ([#6](https://github.com/nottelabs/notte-skills/pull/6)) ([1eb7542](https://github.com/nottelabs/notte-skills/commit/1eb7542))
* clarify that Notte Functions are API endpoints ([#7](https://github.com/nottelabs/notte-skills/pull/7)) ([3ee85e1](https://github.com/nottelabs/notte-skills/commit/3ee85e1))
* document the `only-main-content` scrape tradeoff ([#8](https://github.com/nottelabs/notte-skills/pull/8)) ([04d2a74](https://github.com/nottelabs/notte-skills/commit/04d2a74))
* document `workflow-code` session id export ([#9](https://github.com/nottelabs/notte-skills/pull/9)) ([3c8b8b8](https://github.com/nottelabs/notte-skills/commit/3c8b8b8))
* clarify Notte Function endpoint intents ([#11](https://github.com/nottelabs/notte-skills/pull/11)) ([519a0f5](https://github.com/nottelabs/notte-skills/commit/519a0f5))
* clarify Notte auth login handling ([#12](https://github.com/nottelabs/notte-skills/pull/12)) ([c29bb20](https://github.com/nottelabs/notte-skills/commit/c29bb20))

### 1.0.0 (2026-05-07)

### Features

* restructure the repository as a marketplace plugin ([#1](https://github.com/nottelabs/notte-skills/pull/1)) ([90308d2](https://github.com/nottelabs/notte-skills/commit/90308d2)) — initial release of the `notte-cli` plugin with the `notte-browser` skill
