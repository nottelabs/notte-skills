---
name: python-sdk-interop
description: Minimal Python SDK guidance for exported workflows and Notte Functions
---

# Python SDK Interop

Use this only when editing `notte sessions workflow-code`, `notte agents workflow-code`, or writing a Notte Function file by hand. Keep ordinary browser tasks in the CLI skill.

## Function Shape

Notte Functions are Python files with a `run()` entry point. Parameters on `run()` become invocation inputs; returned dicts/lists are available from `notte functions run-metadata`.

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

## Practical Rules

- Use `from notte_sdk import NotteClient` for hosted workflows. Do not mix it with local `import notte` examples in the same file.
- Use `client.Session(...)` as a context manager.
- Put `solve_captchas=True` and `proxies=True` on `Session`, not on `Agent`.
- Use `session.execute(...)` for known URLs/selectors and `client.Agent(session=session).run(...)` only for ambiguous steps.
- If using observe IDs in Python, call `session.observe()` first. CLI IDs look like `@B3`; SDK IDs are usually passed without `@`.
- If an agent reports that it ran out of steps, raise `max_steps`; retrying the same config usually repeats the failure.
- Do not put credentials in task strings. Use vaults or environment-backed setup.

## Structured Extraction

For CLI scraping, prefer narrow instructions such as `Extract title, price, and URL as JSON`. For Python agent runs that require validation, use a Pydantic model as `response_format` and validate `response.answer`.

```python
from pydantic import BaseModel


class Product(BaseModel):
    name: str
    price: str
    url: str


class Products(BaseModel):
    products: list[Product]


result = client.Agent(session=session, max_steps=15).run(
    task="Extract the visible products",
    response_format=Products,
)
products = Products.model_validate_json(result.answer)
```
