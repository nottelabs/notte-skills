# Notte Skills - Official AI agent skills for browser automation

<div align="center">
  <p>
    Official AI agent skills from <strong>Notte</strong> — teach any Agent Skills-compatible coding agent (Claude Code, Cursor, Goose, OpenHands, Gemini CLI, OpenAI Codex, Kiro, VS Code, <strong>Bitterbot</strong>, and <a href="https://agentskills.io/clients" target="_blank" rel="noopener noreferrer">30+ others</a>) how to drive a real browser <br/>
    → Read more at: <a href="https://notte.cc?ref=github" target="_blank" rel="noopener noreferrer">Landing</a> • <a href="https://console.notte.cc/?ref=github" target="_blank" rel="noopener noreferrer">Console</a> • <a href="https://docs.notte.cc?ref=github" target="_blank" rel="noopener noreferrer">Docs</a> • <a href="https://x.com/nottecore?ref=github" target="_blank" rel="noopener noreferrer">X</a> • <a href="https://www.linkedin.com/company/nottelabsinc/?ref=github" target="_blank" rel="noopener noreferrer">LinkedIn</a>
  </p>
</div>

[![GitHub stars](https://img.shields.io/github/stars/nottelabs/notte-skills?style=social)](https://github.com/nottelabs/notte-skills/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Agent Skills](https://img.shields.io/badge/agent--skills-compatible-blue.svg)](https://agentskills.io/clients)
[![Bitterbot native](https://img.shields.io/badge/Bitterbot-native-blue.svg)](https://github.com/Bitterbot-AI/bitterbot-desktop/pull/30)

---

# What is Notte Skills?

This repository ships the official AI agent skill for [notte.cc](https://notte.cc?ref=github), letting your coding agent drive a real cloud or local browser. The bundled skill exposes observe/click/fill/scrape primitives, AI browser agents, and the ability to deploy browser automation as a scheduled, API-callable [Function](https://docs.notte.cc/concepts/functions).

## Installation

### Claude Code

```bash
# Add the Notte skills marketplace
/plugin marketplace add nottelabs/notte-skills

# Install the CLI skill
/plugin install notte-cli
```

### Cursor

Install from the Cursor Marketplace:

1. Open Cursor Settings > Plugins
2. Search for "Notte"
3. Install the plugin

The Cursor plugin includes the Notte browser skill, an MCP server for cloud browser management, and best-practice rules.

### Any agent

```bash
npx skills add nottelabs/notte-skills
```

### Manual installation

```bash
git clone https://github.com/nottelabs/notte-skills.git
cp -r notte-skills/plugins/notte-cli ~/.claude/skills/
```

## Prerequisites

Before using this skill, ensure you have:

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

Once installed, your coding agent will automatically know how to use Notte.

## Available skills

### notte-cli

CLI skills for using Notte CLI commands.

| Skill | Description |
|-------|-------------|
| **notte-browser** | Manage browser sessions, accounts, and deploy Notte Functions from the command line |

## Verify it's wired up

Ask your agent:

> *"/notte-browser Go to news.ycombinator.com and give me the top 5 posts as JSON with title, url, and points."*

A skill-aware agent should (1) load `notte-browser/SKILL.md` into its context, and (2) produce a working `notte` CLI invocation that scrapes the page and returns the result in the requested shape.

If the agent proceeds without consulting the skill, check: the skill files live at the expected scan path, the folder names match the `name:` field in each `SKILL.md` frontmatter, and your client supports Agent Skills ([see the list](https://agentskills.io/clients)).

## Documentation

- [Notte documentation](https://docs.notte.cc)
- [Console / API keys](https://console.notte.cc)
- [Python SDK source](https://github.com/nottelabs/notte)
- [Agent Skills specification](https://agentskills.io/specification)

## Support

- [GitHub Issues](https://github.com/nottelabs/notte-skills/issues)

## License

Skill content is licensed under the **MIT License**.
Notte itself (the SDK referenced by these skills) is licensed under SSPL-1.0 — see [github.com/nottelabs/notte](https://github.com/nottelabs/notte).

## Links

- [Landing](https://notte.cc?ref=github)
- [Console](https://console.notte.cc/?ref=github)
- [Documentation](https://docs.notte.cc?ref=github)
- [Main repository (nottelabs/notte)](https://github.com/nottelabs/notte)
- [Agent Skills specification](https://agentskills.io/specification)

Copyright © 2026 Notte Labs, Inc.
