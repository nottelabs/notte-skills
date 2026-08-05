---
name: python-sdk-interop
description: Minimal Python SDK guidance for exported workflows and Notte Functions
---

# Python SDK Interop

Use this only when editing `notte sessions workflow-code` exports or writing a Notte Function file by hand. Keep ordinary browser tasks in the CLI skill.

## Function Shape

Notte Functions are Python files with a `run()` entry point. Parameters on `run()` become invocation inputs for the CLI, SDK, and HTTP endpoint; returned dicts/lists are available from `notte functions run-metadata`.

```python
from notte_sdk import NotteClient


client = NotteClient()


def run(url: str, query: str):
    with client.Session(solve_captchas=True, proxies=True) as session:
        session.execute(type="goto", url=url)
        session.execute(type="fill", selector="input[name='q']", value=query)
        session.execute(type="press_key", key="Enter")
        return session.scrape(instructions="Extract results as JSON")
```

Deploy with:

```bash
notte functions create --file workflow.py --name "Search Workflow"
notte functions run
notte functions run-metadata --run-id <run-id>
```

Invoke the deployed Function as an API endpoint:

```bash
curl -L -X POST "https://api.notte.cc/functions/{function_id}/runs/start" \
  -H "Authorization: Bearer $NOTTE_API_KEY" \
  -H "X-Notte-Api-Key: $NOTTE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "function_id": "{function_id}",
    "variables": {
      "url": "https://example.com",
      "query": "laptop"
    }
  }'
```

## Practical Rules

- Use `from notte_sdk import NotteClient` for hosted workflows. Do not mix it with local `import notte` examples in the same file.
- Use `client.Session(...)` as a context manager.
- Put `solve_captchas=True` and `proxies=True` on `Session`, not on `Agent`.
- Use `session.execute(...)` for known URLs/selectors and `client.Agent(session=session).run(...)` only for ambiguous steps.
- If using observe IDs in Python, call `session.observe()` first. Pass the plain ID, such as `B3` or `I1`.
- If an agent reports that it ran out of steps, raise `max_steps`; retrying the same config usually repeats the failure.
- Do not put credentials in task strings. Use vaults or environment-backed setup.

## Structured Extraction

For CLI scraping, prefer narrow instructions:

```bash
notte page scrape --instructions "Extract title, price, and URL as JSON"
```

For Python SDK scraping, use `client.scrape(...)` for one-shot extraction or `session.scrape(...)` after navigation/authentication. Keep the instructions narrow and skip an agent unless the task requires judgment or interaction.

```python
from notte_sdk import NotteClient


client = NotteClient()
products = client.scrape(
    "https://example.com/products",
    instructions="Extract visible products with name, price, and URL as JSON",
)
print(products)
```
