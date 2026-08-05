# Changelog

All notable changes to the `notte` plugin are documented here. The plugin was
named `notte-cli` before 2026-08-05; entries below 1.4.0 describe it under that
name.

Versions before 1.4.0 were never tagged; the entries below are reconstructed
from `git log` so that downstream consumers can tell which skill content
corresponds to which version. Tag releases as `notte-v<version>` from now
on so consumers can pin instead of tracking the default branch.

## [1.5.0](https://github.com/nottelabs/notte-skills/compare/notte-v1.4.0...notte-v1.5.0) (2026-08-05)

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

## [1.4.0](https://github.com/nottelabs/notte-skills/compare/notte-v1.3.0...notte-v1.4.0) (2026-08-05)

Packaging and distribution only — no skill content changed.

### Features

* wire the hosted Notte MCP servers into the plugin: `plugins/notte/.mcp.json` declares `notte-browser` (`https://api.notte.cc/mcp`) and `anything-api` (`https://anything.notte.cc/mcp`) as streamable HTTP servers, referenced from `plugin.json` via `"mcpServers": "./.mcp.json"`. Replaces the inert root `mcp.json`, which used the legacy SSE shape, pointed at `http://localhost:8001/sse`, and was referenced by nothing.

### Bug Fixes

* remove the `notte-sdks` marketplace entry and Cursor skills path, which pointed at a directory that does not exist in the repository
* declare skills explicitly in `plugin.json` (`"skills": "./skills/"`) instead of relying on directory convention
* add `scripts/validate-plugins.py` and run it in CI on every change under `plugins/**` and the manifests

## [1.3.0](https://github.com/nottelabs/notte-skills/compare/notte-v1.2.0...notte-v1.3.0) (2026-07-29)

### Features

* add provider migration and cost skills ([#20](https://github.com/nottelabs/notte-skills/pull/20)) ([3921ff8](https://github.com/nottelabs/notte-skills/commit/3921ff8)) — adds the `migrate-to-notte` and `compare-to-notte-costs` skills covering Browserbase/Stagehand, Kernel, Anchor Browser, Browser Use Cloud, Steel, Hyperbrowser, and Skyvern

## [1.2.0](https://github.com/nottelabs/notte-skills/compare/notte-v1.1.0...notte-v1.2.0) (2026-06-30)

### Features

* add `notte-functions-forge` and `notte-functions-doctor` skills ([#16](https://github.com/nottelabs/notte-skills/pull/16)) ([b051cff](https://github.com/nottelabs/notte-skills/commit/b051cff))

### Bug Fixes

* **notte-browser:** correct the run-output field ([#17](https://github.com/nottelabs/notte-skills/pull/17)) ([7334a3d](https://github.com/nottelabs/notte-skills/commit/7334a3d))

## [1.1.0](https://github.com/nottelabs/notte-skills/compare/notte-v1.0.0...notte-v1.1.0) (2026-06-05)

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

## 1.0.0 (2026-05-07)

### Features

* restructure the repository as a marketplace plugin ([#1](https://github.com/nottelabs/notte-skills/pull/1)) ([90308d2](https://github.com/nottelabs/notte-skills/commit/90308d2)) — initial release of the `notte-cli` plugin with the `notte-browser` skill
