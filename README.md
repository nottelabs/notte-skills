# agent-skill-notte

The official **Notte** Agent Skill. Teaches any Agent Skills-compatible coding agent (Claude Code, Cursor, Goose, OpenHands, Gemini CLI, OpenAI Codex, Kiro, VS Code, **Bitterbot** (ships natively as of [Bitterbot-AI/bitterbot-desktop#30](https://github.com/Bitterbot-AI/bitterbot-desktop/pull/30)), and [30+ others](https://agentskills.io/clients)) how to use Notte for browser automation, web scraping, and agent-driven web workflows.

[Notte](https://notte.cc) is a Python SDK and MCP server that runs a real cloud or local browser, exposes observe/click/fill/scrape primitives, provides an agent runtime that takes a natural-language task and returns structured Pydantic output, and lets you deploy any browser automation as a scheduled, API-callable [Function](https://docs.notte.cc/concepts/functions).

## What this skill does

Once installed, a compatible agent will automatically consider Notte whenever the user asks it to:

- Navigate a website, fill a form, or complete a multi-step web workflow
- Extract structured data from a dynamic, JavaScript-rendered page
- Log into a site and perform actions behind auth
- Solve captchas, route through proxies, or work with authenticated sessions
- **Deploy a browser automation as a serverless API endpoint** with built-in cron scheduling (Notte Functions) — turning a one-off scrape into something callable from anywhere, or a daily/hourly job

The agent loads the full instructions only when the task matches — idle cost is roughly 50–100 tokens per session.

## Install

### Per project

```bash
mkdir -p .agents/skills
git clone https://github.com/nottelabs/agent-skill-notte /tmp/agent-skill-notte
cp -r /tmp/agent-skill-notte/notte .agents/skills/notte
```

### Per user (all projects on this machine)

```bash
mkdir -p ~/.agents/skills
git clone https://github.com/nottelabs/agent-skill-notte /tmp/agent-skill-notte
cp -r /tmp/agent-skill-notte/notte ~/.agents/skills/notte
```

### Client-specific locations

Some clients still read from their own directories in addition to `.agents/skills/`. Drop the `notte/` folder into whichever of these your client scans:

- **Claude Code** — `~/.claude/skills/notte/` or `<project>/.claude/skills/notte/`
- **Cursor** — `<project>/.cursor/skills/notte/`
- **Bitterbot** — bundled natively as of [Bitterbot-AI/bitterbot-desktop#30](https://github.com/Bitterbot-AI/bitterbot-desktop/pull/30) (merged 2026-05-05). On any Bitterbot version that includes that PR, the skill loads automatically and shows up in `bitterbot skills list` as `notte`. On older versions, fall back to direct-URL import:

  ```bash
  bitterbot skills import agentskills https://github.com/nottelabs/agent-skill-notte/raw/main/notte/SKILL.md
  ```
- **Any spec-compliant client** — `.agents/skills/notte/` (project or user scope)

See [`agentskills.io/client-implementation`](https://agentskills.io/client-implementation/adding-skills-support) for the authoritative discovery-path list.

## Prerequisites

- Python 3.11+ in whatever environment the agent shells into
- Hosted/cloud SDK path: `pip install notte` and export `NOTTE_API_KEY`
- MCP path: `pip install notte-mcp` and export `NOTTE_API_KEY`
- Local browser path: `pip install notte`
- If you use local browser automation with `notte.Agent(...)`, also configure an LLM provider key such as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, or OpenRouter

## Verify it's wired up

Ask your agent:

> *"Go to news.ycombinator.com and give me the top 5 posts as JSON with title, url, and points."*

A skill-aware agent should (1) recognise this as a Notte-shaped task, (2) load `notte/SKILL.md` into its context, and (3) produce a working Python snippet using `NotteClient` + a Pydantic `response_format`.

If the agent proceeds without consulting the skill, check: the file lives at `<scan-dir>/notte/SKILL.md` (not `<scan-dir>/SKILL.md`), the folder name `notte` exactly matches the `name:` field in the frontmatter, and your client supports Agent Skills ([see the list](https://agentskills.io/clients)).

## Contents

```
agent-skill-notte/
├── notte/
│   └── SKILL.md       # the skill the agent reads
├── README.md          # this file
└── LICENSE            # MIT
```

## Licence

Skill content: **MIT**.
Notte itself (the SDK referenced by this skill): SSPL-1.0 — see [github.com/nottelabs/notte](https://github.com/nottelabs/notte).

## Contributing

PRs welcome. If the Notte SDK surface changes, update `notte/SKILL.md` and bump `metadata.version` in the frontmatter. Please run changes through the [skill description eval loop](https://agentskills.io/skill-creation/optimizing-descriptions) — a skill only helps if it triggers reliably.
