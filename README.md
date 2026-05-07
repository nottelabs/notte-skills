# Notte Skills

Official AI agent skills from [Notte](https://notte.cc) for using our CLI and Python SDK from any Agent Skills-compatible coding agent (Claude Code, Cursor, Goose, OpenHands, Gemini CLI, OpenAI Codex, Kiro, VS Code, **Bitterbot** (ships natively as of [Bitterbot-AI/bitterbot-desktop#30](https://github.com/Bitterbot-AI/bitterbot-desktop/pull/30)), and [30+ others](https://agentskills.io/clients)).

Notte runs a real cloud or local browser, exposes observe/click/fill/scrape primitives, provides an agent runtime that takes a natural-language task and returns structured Pydantic output, and lets you deploy any browser automation as a scheduled, API-callable [Function](https://docs.notte.cc/concepts/functions).

## Installation

### Claude Code

```bash
# Add the Notte skills marketplace
/plugin marketplace add nottelabs/notte-skills

# Install the CLI skill
/plugin install notte-cli

# Install the SDK skills
/plugin install notte-sdks
```

### Cursor

Install from the Cursor Marketplace:

1. Open Cursor Settings > Plugins
2. Search for "Notte"
3. Install the plugin

The Cursor plugin includes all skills, an MCP server for cloud browser management, and best-practice rules.

### Any agent

```bash
npx skills add nottelabs/notte-skills
```

### Manual installation

```bash
git clone https://github.com/nottelabs/notte-skills.git
cp -r notte-skills/plugins/notte-cli ~/.claude/skills/
cp -r notte-skills/plugins/notte-sdks ~/.claude/skills/
```

## Prerequisites

Before using these skills, ensure you have:

1. **Python 3.11+** in whatever environment the agent shells into.
2. **A Notte API key** for hosted mode (recommended):

   ```bash
   pip install notte
   export NOTTE_API_KEY=...   # from https://console.notte.cc
   ```

   Or **local mode** (no API key, runs Chromium on the user's machine):

   ```bash
   pip install notte
   patchright install --with-deps chromium
   ```

3. If you use `notte.Agent(...)` in local mode, an LLM provider key such as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, or an OpenRouter key.

Once installed, your coding agent will automatically know how to use Notte.

## Available skills

### notte-cli

CLI skills for using Notte CLI commands.

| Skill | Description |
|-------|-------------|
| **notte-browser** | Manage browser sessions, accounts, and deploy Notte Functions from the command line |

### notte-sdks

SDK skills for building browser automation and agent workflows with the Notte Python SDK.

| Skill | Description |
|-------|-------------|
| **notte** | Drive a real browser from Python: observe / click / fill / scrape, run agent tasks against natural-language goals, return Pydantic-typed output, and deploy automations as serverless Notte Functions |

## Verify it's wired up

Ask your agent:

> *"Go to news.ycombinator.com and give me the top 5 posts as JSON with title, url, and points."*

A skill-aware agent should (1) recognise this as a Notte-shaped task, (2) load the appropriate skill into its context, and (3) produce a working Python snippet using `NotteClient` + a Pydantic `response_format`.

If the agent proceeds without consulting the skill, check: the skill files live at the expected scan path, the folder names match the `name:` field in each `SKILL.md` frontmatter, and your client supports Agent Skills ([see the list](https://agentskills.io/clients)).

## Documentation

- [Notte documentation](https://docs.notte.cc)
- [Console / API keys](https://console.notte.cc)
- [Python SDK source](https://github.com/nottelabs/notte)
- [Agent Skills specification](https://agentskills.io/specification)

## Support

- [GitHub Issues](https://github.com/nottelabs/notte-skills/issues)

## License

Skill content: **MIT**.
Notte itself (the SDK referenced by these skills): SSPL-1.0 — see [github.com/nottelabs/notte](https://github.com/nottelabs/notte).
