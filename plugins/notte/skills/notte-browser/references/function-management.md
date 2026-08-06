---
name: function-management
description: Guide to creating, managing, and scheduling workflow functions
---

# Function Management Reference

Complete guide to creating, managing, and scheduling workflow functions with the notte CLI.

## Overview

Functions are reusable Python workflows that can be:
- Invoked as HTTP API endpoints
- Run on-demand from the CLI or SDK (serverless)
- Scheduled with cron expressions
- Shared publicly and forked by others
- Tracked with run history and metadata

Think of a Function as the endpoint version of a browser task. A tested `notte page ...` session proves the task works; `notte sessions workflow-code` turns that task into code; `notte functions create` deploys that code behind a stable Function ID that can be triggered repeatedly.

## Development Workflow

### Choosing an implementation path

Decide how the Function will actually fetch its data before writing it. Prefer, in this order:

1. **A documented or observed JSON/HTTP endpoint** that returns the needed fields - check the page's own XHR calls with `notte sessions network`. Fastest, cheapest, and deterministic.
2. **A deterministic parse of rigidly structured HTML**, when the markup is stable and the fields map to fixed elements. Still deterministic, still no model in the hot path.
3. **`session.scrape(...)`**, the right tool for dynamic, irregular, or JS-rendered pages. It costs an LLM call on every invocation, is output-bound (roughly seconds proportional to the number of fields extracted), and returns results that vary from run to run.

Rank by the page, not by habit: a site with a public API or a fixed table should not pay for an extraction model on each run.

### Building from a tested session

Building a function should start from a tested CLI session. The easiest and most reliable path is:

1. Try the browser task directly with `notte sessions start` and `notte page ...` commands until it works.
2. Export the successful session with `notte sessions workflow-code`. If the current-session pointer is gone, or the session has already been stopped, pass the captured session ID explicitly with `notte sessions workflow-code --session-id <session-id>`.
3. Use the exported script as the implementation base for the Function.

For interactive, stateful, or authenticated flows - logins, multi-step forms, anything where the working sequence and session state are painful to reconstruct by hand - export `workflow-code` before hand-writing the Function. The exported script captures the exact `goto`, `wait`, scrape settings, selectors, and session options that worked in the browser, which is precisely what is hard to guess back. For a stateless Function built on an endpoint or HTML structure you already confirmed, writing that request directly is fine.

### Step-by-Step Process

1. **Build interactively** - Use `notte sessions start` and `notte page` commands to develop your automation step-by-step in the terminal
2. **Export code** - Run `notte sessions workflow-code` to generate a working Python script from your session. If the session is no longer current, use `notte sessions workflow-code --session-id <session-id>`.
3. **Parameterize the export** - Edit the generated script only as needed: add a `run(...)` entry point, replace hardcoded user inputs with function parameters, define response models, and add small cleanup logic
4. **Create function** - Upload the edited export with `notte functions create --file my_function.py` (becomes current function)
5. **Test in cloud** - Run `notte functions run`, which blocks until the run finishes and returns `status` and `result` inline
6. **Inspect logs if needed** - `notte functions run-metadata --run-id <run-id>` exposes the `logs` field for deeper debugging
7. **Iterate** - Update your code based on results, then use `notte functions update --file my_function.py`
8. **Schedule** - When stable, add a cron schedule: `notte functions schedule --cron "0 9 * * *"`

### Complete Example

This example uses `scrape` to demonstrate the end-to-end CLI flow, not because it is the best implementation for this particular site: the Hacker News front page has both a public JSON API (`hn.algolia.com/api/v1/search_by_date?tags=front_page`) and rigidly structured HTML, so a real Function for it should follow path 1 or 2 above. Read the flow, not the extraction choice.

**Step 1-3 — build interactively, then export:**

```bash
# Build your automation interactively and keep the session ID
SESSION_ID=$(notte sessions start --headless -o json | jq -r '.session_id')
notte page goto "https://news.ycombinator.com"
notte page observe
notte page scrape --instructions "Extract top 5 story titles and URLs"

# Stop the session when the interactive test is done
notte sessions stop --session-id "$SESSION_ID"

# Export the session as Python code.
# This still works after stop because the session ID is explicit.
notte sessions workflow-code --session-id "$SESSION_ID" > hn_scraper.py
```

**Step 4 — edit the export to add a `run()` entry point and parameters.**
`hn_scraper.py` should end up looking like this:

```python
from notte_sdk import NotteClient
from pydantic import BaseModel


class Story(BaseModel):
    title: str | None = None
    url: str | None = None


class Result(BaseModel):
    stories: list[Story] | None = None


client = NotteClient()


def run(max_stories: int = 5):
    max_stories = int(max_stories)  # run variables arrive as strings

    with client.Session() as session:
        session.execute(type="goto", url="https://news.ycombinator.com")
        session.execute(type="wait", time_ms=1000)

        data = session.scrape(
            instructions=f"Extract top {max_stories} story titles and URLs",
            response_format=Result,
        )

        # With response_format, `data` is a typed Result - count the list, not
        # the container. Without it, scrape returns a dict, and len(dict) counts
        # keys, not rows.
        stories = data.stories or []
        return {"stories": [s.model_dump() for s in stories], "count": len(stories)}


run()
```

**Step 5-8 — create, test, iterate, schedule:**

```bash
# Create the function and capture its id (it also becomes the current function,
# but referencing it explicitly is safer once you have more than one)
FUNCTION_ID=$(notte functions create \
  --file hn_scraper.py \
  --name "HN Top Stories" \
  --description "Scrapes top stories from Hacker News" \
  -o json | jq -r '.function_id')

# Test it. This blocks until the run completes - no sleep/poll needed.
notte functions run --function-id "$FUNCTION_ID" -o json | jq '{status, result}'

# If you need execution logs, take the run id from the run you just did.
# (`notte functions runs` also lists it - the full history, newest first.)
RUN_ID=$(notte functions run --function-id "$FUNCTION_ID" -o json | jq -r '.function_run_id')
notte functions run-metadata --function-id "$FUNCTION_ID" --run-id "$RUN_ID" -o json | jq -r '.logs[]'

# If needed, update and iterate
notte functions update --function-id "$FUNCTION_ID" --file hn_scraper.py
notte functions run --function-id "$FUNCTION_ID" -o json | jq '{status, result}'

# Schedule when ready (every day at 9 AM)
notte functions schedule --function-id "$FUNCTION_ID" --cron "0 9 * * *"
```

### Tips for Iterative Development

- **Start simple**: Build a minimal version first, then add features
- **Test frequently**: Run `notte functions run` after each change to catch issues early
- **Monitor logs**: The `logs` field in run-metadata shows print statements and errors
- **Use variables**: Add function parameters for flexibility (e.g., `max_stories` in the example)
- **Return data**: Always return structured data from your `run()` function for easy access via run-metadata
- **Read `result`, not `status` alone**: `notte functions run -o json` blocks until the run finishes and returns `status` and `result` inline. A successful run reports `status: "closed"` - and so does a run that raised inside `run()`, with the error text in `result`. Treat a `result` that is a JSON payload as success and one that is an error string (`Script execution failed` / `Traceback`) as a failure. `result` is the return value of `run()` serialized to JSON, so a `dict` comes back as a real nested object.
- **Get logs from `run-metadata`, using the run id `functions run` returned**: `functions run` does not include logs, but its response carries `function_run_id`. Note `run-metadata`'s own `result` is a Python `repr` (single-quoted, not valid JSON), so read logs there and take the result from `functions run`.
- **Run history is the default**: `notte functions runs` lists every run, newest first; `--running` narrows to those still executing. The simplest path is still to keep the `function_run_id` from the `functions run` response and skip the listing entirely.
- **Mind the request timeout**: the run is synchronous, so it is bounded by the global `--timeout` (default 60 seconds). A Function slower than that fails the *command* while the run continues server-side. Set it generously on the first invocation: `notte functions run --timeout 600`.
- **Never re-run after a command timeout**: the client giving up does not cancel the run - it finishes normally server-side. Re-running invokes the Function a second time and repeats any write, submission, or purchase. Find the in-flight run with `notte functions runs --function-id <id> --running`, read its outcome from the full history once it leaves `active`, and only start a fresh run if nothing is pending.

## Creating Functions

**Note:** When you create a function, it automatically becomes the "current" function. All subsequent commands (run, update, schedule, etc.) use this function by default. Use `--function-id <function-id>` only when you need to manage multiple functions simultaneously or reference a specific function.

### From a Python File

```bash
notte functions create --file function.py
```

### With Metadata

```bash
notte functions create \
  --file workflow.py \
  --name "Product Price Monitor" \
  --description "Monitors competitor prices daily" \
  --shared  # Make publicly available
```

### Function File Format

Function files define browser automation steps with the following requirements:

**Required:**
- Must contain a `def run()` function - this is the entry point
- Must create a session using `NotteClient().Session()`
A trailing module-level `run()` call is **optional**. `notte sessions
workflow-code` emits one and the examples below keep it for consistency with the
export, but the runtime invokes `run()` itself - leaving the call in or taking it
out makes no difference to a deployed Function. Do not write logic that depends
on either behaviour.

**Do not include `from __future__ import annotations`.** Under PEP 563 the
Pydantic field annotations become unresolved forward references, and a deployed
Function fails at `response_format=Model` with
`PydanticUserError: Model is not fully defined`. The `X | None` syntax works
without it. `notte sessions workflow-code` may emit that import - remove it
before deploying.

**Function Variables (Parameters):**
- Parameters in the `run()` function become POST body parameters when triggering the function
- Use type hints to document expected types (e.g., `str`, `int`, `bool`, `list`, `dict`)
- Default values make parameters optional when triggering

**Return Values:**
- Data returned from `run()` is stored and accessible via `notte functions run-metadata`
- Return structured data (dict, list) for easy parsing
- The return value appears in the `result` field of run-metadata

**Basic Example:**

```python
# function.py
from notte_sdk import NotteClient

client = NotteClient()


def run(url: str):
    """Simple function with one required parameter."""
    with client.Session() as session:
        session.execute(type="goto", url=url)
        data = session.scrape()
        return data


run()
```

**Advanced Example with Variables:**

```python
# price_monitor.py
from notte_sdk import NotteClient
from pydantic import BaseModel

client = NotteClient()


class Product(BaseModel):
    name: str | None = None
    price: float | None = None
    url: str | None = None


class Products(BaseModel):
    products: list[Product] | None = None


def run(
    url: str,
    max_items: int = 10,
    only_discounted: bool = False,
    categories: list[str] | None = None
):
    """
    Function parameters become POST body parameters.

    Args:
        url: Required parameter (no default)
        max_items: Optional with default value
        only_discounted: Optional boolean
        categories: Optional list
    """
    max_items = int(max_items)

    with client.Session() as session:
        session.execute(type="goto", url=url)

        # Build extraction instructions dynamically
        instructions = f"Extract up to {max_items} products"
        if only_discounted:
            instructions += " that are on sale"
        if categories:
            instructions += f" in categories: {', '.join(categories)}"

        data = session.scrape(instructions=instructions, response_format=Products)

        # Count the list of rows, not the response container. Without
        # response_format, scrape returns a dict and len(dict) counts keys.
        products = data.products or []

        return {
            "success": True,
            "url": url,
            "products": [p.model_dump() for p in products],
            "count": len(products),
            "filters": {
                "max_items": max_items,
                "only_discounted": only_discounted,
                "categories": categories
            }
        }


run()
```

**Triggering with Parameters:**

When running the function, pass parameters as Function variables. The CLI is convenient for local iteration; the HTTP POST endpoint is what another service can call to reproduce the same browser task.

```bash
# Run with default parameters
notte functions run

# Invoke the same Function over HTTP
curl -L -X POST "https://api.notte.cc/functions/{function_id}/runs/start" \
  -H "Authorization: Bearer $NOTTE_API_KEY" \
  -H "X-Notte-Api-Key: $NOTTE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "function_id": "{function_id}",
    "variables": {
      "url": "https://example.com/products",
      "max_items": 5,
      "only_discounted": true,
      "categories": ["electronics"]
    }
  }'
```

The HTTP response returns a run identifier. Use `notte functions run-metadata --run-id <run-id>` to fetch logs and the value returned by `run(...)`.

**Accessing Return Values:**

```bash
# Get the result from run-metadata
notte functions run-metadata --run-id <run-id> -o json | jq '.result'

# Output:
# {
#   "success": true,
#   "url": "https://example.com/products",
#   "products": [...],
#   "count": 5,
#   "filters": {
#     "max_items": 5,
#     "only_discounted": true,
#     "categories": ["electronics"]
#   }
# }
```

## Managing Functions

### List Functions

```bash
# List all functions
notte functions list

# With pagination and filters
notte functions list --page 1 --page-size 20   # deleted functions are already hidden
```

Output includes function ID, name, description, and creation date.

### View Function Details

```bash
notte functions show
```

Returns function metadata plus a **download URL** for the workflow file (the
`url` field) - it does not inline the source. To read the current code:

```bash
URL=$(notte functions show --function-id "$FUNCTION_ID" -o json | jq -r '.url')
curl -L "$URL" -o current_function.py
```

`show` does not return the cron schedule. The CLI can set (`schedule`) and clear
(`unschedule`) one but cannot read it back, so record a Function's cron
elsewhere if you need to restore it after an update.

### Function Environment Secrets

Values a Function reads from `os.environ` are stored per-Function, outside the
workflow file:

```bash
notte functions secrets set API_TOKEN <value>
notte functions secrets list
notte functions secrets get API_TOKEN
notte functions secrets delete API_TOKEN
```

Read them inside `run()` with `os.environ["API_TOKEN"]`. Never hardcode a secret
in the workflow file or pass one as a run variable - run variables are recorded
with the run.

### Update Function Code

```bash
notte functions update --file workflow_v2.py
```

Updates the workflow code while preserving function ID and schedule.

### Delete Function

```bash
notte functions delete
```

Prompts for confirmation. Use `--yes` to skip.

## Running Functions

### Run On-Demand

```bash
notte functions run
```

Runs the Function in the cloud and **blocks until it finishes**, returning
`status` and `result` in one payload. There is no client-side polling, so the
call is bounded by the global `--timeout` (default 60 seconds).

This is the CLI equivalent of hitting the Function's HTTP invocation endpoint. Use the HTTP example in "Triggering with Parameters" when the user asks for an "endpoint" for a browser task; do not create a separate local web server unless they explicitly ask for one.

### Check Run Status

```bash
# List all runs for current function
notte functions runs

# With pagination and filters
notte functions runs --page 1 --page-size 10   # full history; --running narrows to in-flight
```

Output includes:
- Run ID
- Status (running, completed, failed)
- Start time
- End time (if finished)

### Stop a Running Function

```bash
notte functions run-stop --run-id <run-id>
```

## Run Metadata

Store and retrieve custom data for function runs:

### Get Metadata

```bash
notte functions run-metadata --run-id <run-id>
```

### Metadata Use Cases

- Track progress during long-running jobs
- Store results summary
- Record error details
- Pass data between scheduled runs

## Scheduling Functions

### Set a Cron Schedule

```bash
notte functions schedule --cron "0 9 * * *"
```

### Cron Expression Format

```
┌───────────── minute (0-59)
│ ┌───────────── hour (0-23)
│ │ ┌───────────── day of month (1-31)
│ │ │ ┌───────────── month (1-12)
│ │ │ │ ┌───────────── day of week (0-6, Sunday=0)
│ │ │ │ │
* * * * *
```

### Common Cron Examples

```bash
# Every hour
notte functions schedule --cron "0 * * * *"

# Every day at 9 AM
notte functions schedule --cron "0 9 * * *"

# Every Monday at 6 PM
notte functions schedule --cron "0 18 * * 1"

# Every 15 minutes
notte functions schedule --cron "*/15 * * * *"

# First day of each month at midnight
notte functions schedule --cron "0 0 1 * *"

# Weekdays at 8 AM
notte functions schedule --cron "0 8 * * 1-5"
```

### Remove Schedule

```bash
notte functions unschedule
```

Function remains but will no longer run automatically.

## Sharing Functions

### Make Public

```bash
# When creating
notte functions create --file workflow.py --shared

# Public functions can be discovered and forked by others
```

### Fork a Shared Function

Copy a shared function to your account:

```bash
notte functions fork --function-id <shared-function-id>
```

Creates a new function with the same code under your account.

## Example Workflows

### Daily Price Monitor

```python
# price_monitor.py
from notte_sdk import NotteClient
from pydantic import BaseModel

client = NotteClient()


class Price(BaseModel):
    product: str | None = None
    price: float | None = None


class Prices(BaseModel):
    prices: list[Price] | None = None


def run(competitor_url: str = "https://competitor.com/products"):
    with client.Session() as session:
        session.execute(type="goto", url=competitor_url)
        data = session.scrape(
            instructions="Extract all product prices as JSON",
            response_format=Prices,
        )
        rows = data.prices or []
        return {"prices": [p.model_dump() for p in rows], "count": len(rows)}


run()
```

```bash
# Create and schedule
FUNCTION_ID=$(notte functions create --file price_monitor.py --name "Price Monitor" -o json | jq -r '.function_id')
notte functions schedule --function-id "$FUNCTION_ID" --cron "0 9 * * *"
```

### Weekly Report Generator

```python
# weekly_report.py
from notte_sdk import NotteClient

client = NotteClient()

vault = client.Vault("my-vault-id")


def run(dashboard_url: str = "https://dashboard.example.com"):
    # `use_file_storage=True` attaches FileStorage - the same thing the
    # `--use-file-storage` CLI flag does. Needed here for the PDF download.
    with client.Session(use_file_storage=True, vault=vault) as session:
        session.execute(type="goto", url=f"{dashboard_url}/login")

        # The vault resolves sentinel placeholders into real credentials.
        # The secret never appears in this file.
        agent = client.Agent(session, vault=vault, max_steps=5)
        agent.run(task="Login to dashboard")

        session.execute(type="goto", url=f"{dashboard_url}/reports/weekly")

        report = session.scrape(instructions="Extract the weekly summary statistics")

        # Download PDF report
        session.execute(type="click", selector="#download-pdf-button")

        return report


run()
```

```bash
# Create and schedule for Monday mornings
FUNCTION_ID=$(notte functions create --file weekly_report.py --name "Weekly Report" -o json | jq -r '.function_id')
notte functions schedule --function-id "$FUNCTION_ID" --cron "0 8 * * 1"
```

### Error Monitoring with Retries

```python
# monitor_with_retry.py
import time

from notte_sdk import NotteClient
from pydantic import BaseModel

client = NotteClient()

class Status(BaseModel):
    healthy: bool | None = None
    message: str | None = None


def run(status_url: str = "https://app.example.com/status", max_retries: int = 3):
    max_retries = int(max_retries)

    for attempt in range(max_retries):
        try:
            with client.Session() as session:
                session.execute(type="goto", url=status_url)
                status = session.scrape(
                    instructions="Extract system status as JSON",
                    response_format=Status,
                )

                if status.healthy:
                    return {"success": True, "message": "All systems operational"}
                return {"success": False, "alert": True, "status": status.model_dump()}

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(30)
            else:
                return {"success": False, "error": f"Failed after {max_retries} attempts: {e}"}


run()
```

## Best Practices

### 1. Use Descriptive Names

```bash
notte functions create \
  --file workflow.py \
  --name "Daily Competitor Price Check" \
  --description "Monitors prices on competitor.com every morning at 9 AM"
```

### 2. Return Important Data from Functions

```bash
# Functions return data that can be retrieved via run metadata
notte functions run-metadata --run-id <run-id> -o json
```

### 3. Monitor Run History

```bash
# Check for failed runs. A script error may report status "failed", but an error
# inside run() can also come back as status "closed" with the error string in
# `result`, so match both.
notte functions runs -o json | jq '.[] | select(.status == "failed" or ((.result|type) == "string" and (.result|test("Script execution failed|Traceback"))))'
```

Note this list can return `[]` even for a Function with completed runs, so an
empty result here is not evidence that the Function never ran.

### 4. Test Before Scheduling

```bash
# Run manually first
notte functions run

# Check it completed successfully
notte functions runs

# Then schedule
notte functions schedule --cron "0 9 * * *"
```

### 5. Use Appropriate Schedules

- Don't schedule more frequently than needed
- Consider time zones
- Avoid peak hours if possible
- Account for function runtime when scheduling

### 6. Clean Up Unused Functions

```bash
# List functions and review
notte functions list

# Confirm you have the right target by reading its name back
notte functions show --function-id <old-func-id> -o json | jq -r '.name'

# Delete that specific id - never rely on the implicit "current function"
# pointer for a destructive command
notte functions delete --function-id <old-func-id> --yes
```
