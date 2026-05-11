---
name: browser-patterns
description: Routing and workflow patterns for Notte browser tasks
---

# Browser Patterns

Use Notte when the task benefits from a real browser session: JavaScript rendering, clicking, forms, auth, dynamic listings, captchas, proxies, screenshots, downloads, or a workflow that should later become a scheduled Function.

Prefer simpler tools for static HTML, public JSON APIs, offline files, or pages where browser state is irrelevant.

## Core Pattern

Use deterministic CLI commands when the next step is known:

```bash
notte page goto "https://example.com"
notte page observe
notte page click "B3"
notte page fill "input[name='email']" "user@example.com"
notte page scrape --instructions "Extract title, price, and URL as JSON"
```

Use `notte agents start` only when the browser needs judgment, such as finding the right link, choosing among similar options, or completing a loosely specified multi-step task.

For repeated work, build the flow interactively, export it with `notte sessions workflow-code` or `notte agents workflow-code`, then deploy it with `notte functions create`.
