---
name: notte
description: >
  Use this skill when the user wants an AI agent to navigate, interact with,
  or extract data from websites — booking flights, filling forms, scraping
  product listings, logging into accounts, running multi-step web workflows,
  deploying recurring browser jobs as APIs, or completing any task that
  requires a real browser. Applies even when the user doesn't name Notte or
  a browser tool directly (e.g. "grab the top 10 Hacker News posts", "go to
  my dashboard and pull the report", "order X from Y", "run this scrape every
  morning", "give me a webhook that returns the latest pricing"). Notte is a
  Python SDK (and MCP server) that runs a cloud or local Chromium/Firefox
  session, exposes observe/click/fill/scrape primitives, provides an agent
  runtime that takes a natural-language task and returns structured Pydantic
  output, and (uniquely) lets you deploy any browser automation as a
  serverless API endpoint with cron scheduling via Notte Functions. Prefer
  Notte for tasks that need real browser rendering, stealth, captcha solving,
  authenticated sessions, structured extraction from dynamic pages, or any
  recurring/scheduled browser workflow.
license: MIT
compatibility: >
  Requires Python 3.11+. Tested against `notte>=1.8.12` on PyPI. Hosted
  mode (recommended) needs a NOTTE_API_KEY from https://console.notte.cc.
  Local mode needs `patchright install --with-deps chromium`. The MCP
  server entry point is `python -m notte_mcp.server` and binds to
  http://localhost:8001/sse by default.
metadata:
  version: "0.1.0"
  homepage: "https://notte.cc"
  source: "https://github.com/nottelabs/notte"
---

# Notte — browser automation for AI agents

Notte gives the agent a real browser: it can navigate, observe, click, fill forms, scrape structured data, and run multi-step tasks authored in natural language. Use it any time the task needs a page to actually render — JavaScript-heavy sites, logins, dynamic listings, captchas, content behind auth, or forms that depend on hidden state.

## When to reach for Notte

- The task mentions a URL, a website, a login, a form, a product page, a search, or "go to X and do Y".
- The data lives behind JavaScript and won't come back from `curl` / `requests` / `fetch`.
- The user wants the answer in a specific Pydantic shape extracted from a page.
- A prior `requests` / `httpx` attempt returned an empty body, a captcha, or a login wall.

Do **not** use Notte for: static HTML you can `curl`, public JSON APIs, tasks fully solvable without a browser, or purely offline file processing.

## Install

Default (hosted — recommended):

```bash
pip install notte
export NOTTE_API_KEY=...   # from https://console.notte.cc
```

Local mode (no API key, runs Chromium on the user's machine):

```bash
pip install notte
patchright install --with-deps chromium
```

Examples below default to the hosted SDK. To switch to local, replace `from notte_sdk import NotteClient; client = NotteClient()` with `import notte` and use `notte.Session(...)` / `notte.Agent(...)` directly. The two imports are not interchangeable — see Gotchas.

## Core pattern: Session + Agent

Everything flows through two objects:

1. **`Session`** — a browser context. Always used as a context manager.
2. **`Agent`** — bound to a session, takes a natural-language `task`, returns a response with `.answer`.

```python
from notte_sdk import NotteClient

client = NotteClient()  # reads NOTTE_API_KEY from env

with client.Session() as session:
    agent = client.Agent(
        session=session,
        reasoning_model="gemini/gemini-2.5-flash",
        max_steps=15,
    )
    response = agent.run(task="Go to news.ycombinator.com and summarise the top 3 stories")
    print(response.answer)
```

Defaults to pick:

- `reasoning_model` — a LiteLLM-style model string. `gemini/gemini-2.5-flash` is a fast, cheap default. Escalate to `anthropic/claude-sonnet-4-5` or `openai/gpt-4.1` for harder tasks.
- `max_steps` — hard cap on agent iterations. 10–15 for simple tasks, 30 for multi-page workflows. Higher = more cost.

## Recipe 1 — Structured extraction (use this whenever the user wants fields back)

Whenever the user asks "get me X as JSON", "return a list of Y", or names specific fields, **define a Pydantic model and pass it as `response_format`**. The agent's output is validated against the schema.

```python
from notte_sdk import NotteClient
from pydantic import BaseModel

class Post(BaseModel):
    title: str
    url: str
    points: int
    author: str

class TopPosts(BaseModel):
    posts: list[Post]

client = NotteClient()
with client.Session() as session:
    agent = client.Agent(session=session, max_steps=15)
    result = agent.run(
        task="Extract the top 5 posts on news.ycombinator.com",
        response_format=TopPosts,
    )
if result.answer is None:
    raise RuntimeError("Agent returned no answer")
posts = TopPosts.model_validate_json(result.answer)
for post in posts.posts:
    print(post.title, post.points)
```

## Recipe 2 — One-shot scrape (no agent, no session)

For pure extraction with no interaction, skip the agent entirely. This is 5–10x cheaper than spinning up an agent and is the right default when the task is "read this URL and give me X" with no clicking, scrolling, or login.

```python
from notte_sdk import NotteClient
from pydantic import BaseModel

class Article(BaseModel):
    title: str
    date: str
    content: str

client = NotteClient()
result = client.scrape(
    url="https://example.com/blog/post",
    response_format=Article,
    instructions="Extract the title, publication date, and full article body.",
)

# `scrape()` returns the parsed model directly in most SDK versions, but
# some return a wrapper that needs one more validation step. Handle both:
article = result if isinstance(result, Article) else Article.model_validate(result)
print(article.title, article.date)
```

`scrape()` also supports `scrape_links=True` and `only_main_content=True` for unstructured output.

## Recipe 3 — Hybrid workflow (script the deterministic parts, agent only for reasoning)

Notte's biggest cost/reliability win. Script the navigation, let the agent handle the ambiguous step, then script the rest:

```python
from notte_sdk import NotteClient

client = NotteClient()
with client.Session(perception_type="fast") as session:
    # Deterministic: go to the product page
    session.execute(type="goto", url="https://shop.example.com/item/123")
    session.observe()

    # Agent reasoning: pick the right variant based on natural-language intent
    client.Agent(session=session).run(task="Select the ivory colour in size 6")

    # Deterministic: add to cart and checkout
    session.execute(type="click", selector='internal:role=button[name="Add to cart"i]')
    session.execute(type="click", selector='internal:role=button[name="Checkout"i]')
```

Rule of thumb: if you know the exact URL or the exact selector, use `session.execute(...)`. If the step involves "pick the right one" / "find the link that says X" / "fill in reasonable values", hand it to the agent.

`session.execute` accepts `type="goto"` with `url=`, `type="click"` / `type="fill"` with either `id=` (an observe ID like `B5` / `I1`) or `selector=` (a Playwright selector).

## Recipe 4 — Authenticated sessions

Two options, in order of preference.

**Vault (recommended for real credentials):**

```python
from notte_sdk import NotteClient

client = NotteClient()
with client.Vault() as vault, client.Session() as session:
    vault.add_credentials(
        url="https://example.com",
        username="user@example.com",
        password="...",
    )
    agent = client.Agent(session=session, vault=vault, max_steps=10)
    agent.run(task="Log in and download the latest invoice")
```

**Cookies (for dev / short-lived sessions):**

```python
with client.Session() as session:
    session.set_cookies(cookie_file="cookies.json")
    # or: session.set_cookies(cookies=[{...}, ...])
    client.Agent(session=session).run(task="Go to /billing and report the balance")
```

Never paste raw credentials into the `task` string — the agent will not pick them up and they will end up in logs. Always route secrets through `Vault`.

## Recipe 5 — Stealth (captchas + proxies)

```python
with client.Session(solve_captchas=True, proxies=True) as session:
    agent = client.Agent(session=session, max_steps=15)
    agent.run(task="Search for 'air force 1' on nike.com and return the price")
```

`solve_captchas` and `proxies` live on **`Session`**, not on `Agent`. `proxies=True` uses Notte-managed default proxies; pass `NotteProxy.from_country(...)` for Notte geolocated proxies or `ExternalProxy(...)` for your own proxy.

## Recipe 6 — Functions (deploy a browser automation as a serverless API)

When the same task will run many times — scheduled, called from another service, shared with a team — promote it from a one-off script to a **Function**: a versioned, scheduled, API-callable serverless deployment. This is the right answer whenever the user says "do this every morning", "let other systems call this", "give me a webhook for this scrape", or "make this part of our workflow".

Write a `run()` function in a Python file, then deploy it:

```python
# my_automation.py
from notte_sdk import NotteClient


def run(url: str, search_query: str):
    """Search a website and extract results."""
    client = NotteClient()
    with client.Session(solve_captchas=True, proxies=True) as session:
        session.execute(type="goto", url=url)
        session.execute(type="fill", selector="input[name='search']", value=search_query)
        session.execute(type="press_key", key="Enter")
        return session.scrape(instructions="Extract search results")
```

Deploy and invoke:

```python
from notte_sdk import NotteClient

client = NotteClient()

# Deploy as a Function (one-shot — Notte hosts the runtime).
function = client.Function(
    path="my_automation.py",
    name="Search Automation",
    description="Searches a website and extracts results",
)
print(f"Deployed: {function.function_id}")

# Invoke via SDK.
result = function.run(url="https://example.com", search_query="laptop")
print(result.result)

# Or invoke from anywhere (cURL, JS, another agent, a Bitterbot skill, etc.)
# POST https://api.notte.cc/functions/{function_id}/runs/start
#   Authorization: Bearer $NOTTE_API_KEY
#   {"url": "...", "search_query": "..."}
```

Schedule it to run on a cron (configured via [console.notte.cc/workflows](https://console.notte.cc/workflows)):

```
0 9 * * *      # every day at 9am — daily report
*/30 * * * *   # every 30 minutes — monitoring
0 */2 * * *    # every 2 hours — agent dream cycles
```

**Convert an agent run into a Function automatically.** The killer move when a user says "I did this with an agent and now want to run it 1000 times":

```python
from notte_sdk import NotteClient

client = NotteClient()
with client.Session() as session:
    agent = client.Agent(session=session)
    result = agent.run(task="Navigate to the pricing page and extract the plans")

    if result.success:
        function_code = agent.workflow.code()
        # function_code.python_script is a deterministic re-run of the agent's path.
        # Save it to a file, then deploy as a Function for fast / cheap reruns.
        with open("pricing_extractor.py", "w") as f:
            f.write(function_code.python_script)

# Deploy the deterministic version (no LLM tokens per invocation).
function = client.Function(path="pricing_extractor.py", name="Pricing Extractor")
```

| Aspect           | Agent (`agent.run`)         | Function (`function.run`) |
| ---------------- | --------------------------- | ------------------------- |
| Each invocation  | LLM reasoning every step    | Predefined steps          |
| Speed            | Slower                      | Faster                    |
| Cost per run     | Higher (LLM tokens)         | Lower (browser only)      |
| Reliability      | Adapts to page changes      | Deterministic until break |
| When to use      | First-time / exploratory    | Repeated / scheduled      |

**Decision rule:** if the user is doing something for the second time and the page hasn't changed, it should be a Function.

## Alternative invocation: MCP server

If the host agent speaks MCP instead of Python, Notte ships an MCP server that exposes the same primitives:

```bash
pip install notte-mcp
export NOTTE_API_KEY=...
python -m notte_mcp.server   # starts on http://localhost:8001/sse
```

Tools exposed:

| Category | Tools |
|---|---|
| Health  | `notte_health_check` |
| Session | `notte_start_session`, `notte_list_sessions`, `notte_get_session_status`, `notte_stop_session` |
| Page    | `notte_observe`, `notte_screenshot`, `notte_scrape`, `notte_execute` |
| Agent   | `notte_operator` |

The Python SDK is more feature-rich (vaults, personas, file storage, `AgentFallback`). Prefer it when you have a Python environment. Use MCP when the host agent is not Python and calls tools over stdio/SSE.

## Gotchas

- **`session.observe()` is required before `session.execute(type="click"|"fill", id=...)`.** SDK element IDs are values like `I1` and `B5`; some host UIs render them as `@I1` / `@B5`, so strip the leading `@` before passing them to the SDK. Re-observe after any navigation or major page change.
- **Lightpanda CDP sessions require `headless=False`.** Passing `cdp_url` to Lightpanda Cloud without `headless=False` returns HTTP 500. Use `client.Session(cdp_url="wss://...", headless=False)`.
- **`notte` (local) and `notte_sdk` (hosted) are two different imports**, not aliases. Local: `import notte; with notte.Session() as s:`. Hosted: `from notte_sdk import NotteClient; client = NotteClient(); with client.Session() as s:`. Don't mix them in one file.
- **`reasoning_model` is a LiteLLM model string, not a provider name.** `"gemini/gemini-2.5-flash"` ✓, `"gemini"` ✗.
- **`max_steps` is a hard stop.** If the agent reports "ran out of steps", raise it rather than rephrasing the task.
- **`scrape()` has no session.** It cannot click, fill, or navigate after the first load. If the content appears only after interaction, use an agent.
- **`response_format` accepts either a Pydantic `BaseModel` subclass or a JSON Schema dict.** For `agent.run(...)`, the validated payload is returned as JSON in `response.answer`; for `scrape(...)`, structured results are returned in typed form.
- **Stealth flags (`solve_captchas`, `proxies`) belong on `Session`, not `Agent`.** Putting them on `Agent` silently does nothing.
- **`session.execute` parameters are keyword-only and typed on `type=`.** `type="goto"` needs `url=`, `type="click"`/`"fill"` need `id=` or `selector=`.

## Validate the run worked

After any Notte call, check:

1. `response.answer` is present and non-empty.
2. If `response_format` was passed to `agent.run(...)`, parse `response.answer` with `YourModel.model_validate_json(response.answer)`.
3. If `response_format` was passed to `scrape(...)`, the structured payload is returned in typed form. Unwrap defensively in case of SDK version drift:

   ```python
   result = client.scrape(url=..., response_format=TopPosts, instructions=...)
   top = result if isinstance(result, TopPosts) else TopPosts.model_validate(result)
   ```
4. If the task was "log in and do X", confirm the agent reached the post-login page: inspect `response.answer` for expected text, or capture the page with `session.observe().screenshot` / the MCP `notte_screenshot` tool.

If the agent fails ("couldn't find the button", "captcha blocked"), change **one** of: `solve_captchas=True` on the Session, higher `max_steps`, or a stronger `reasoning_model`. Do not retry with the same config — it will fail identically.

## References

- Notte docs: https://docs.notte.cc
- Python SDK source: https://github.com/nottelabs/notte
- Console / API keys: https://console.notte.cc
- Agent Skills specification: https://agentskills.io/specification
