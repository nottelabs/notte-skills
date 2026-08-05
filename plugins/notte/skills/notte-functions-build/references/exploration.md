---
name: exploration
description: How to explore a site once and find a stable, reproducible data path - API-first, DOM fallback
---

# Exploration Reference

The exploration phase is the expensive, non-deterministic part of building a Function. Do it **once**, find the most stable path to the target data, record exactly how to reproduce it, then stop. Everything downstream (the generated Function, every future run) inherits the stability of what you find here.

## Stability ranking - prefer paths in this order

| Priority | Path | Stability | Notes |
|----------|------|-----------|-------|
| 1 | **Internal data API** (the site's own XHR/fetch endpoints) | Highest | Survives visual redesigns; breaks only on backend contract changes |
| 2 | **Structured `scrape`** with a typed instruction | Medium | Robust to small layout shifts; depends on the model reading the page |
| 3 | **DOM selectors** (`data-testid` > `id` > `name` > `aria-label`) | Low | Breaks on redesign; last resort |

A Function built on an internal API keeps working far longer than one built on CSS selectors. Always probe for the API first.

## API-first discovery

The data you see on the page almost always arrives via a background request. Find it:

```bash
notte sessions start --headless
notte page goto "{url}"
# Trigger the data load: search, scroll, paginate, or click into a detail page
notte page observe
notte page wait 1500
# Capture what the page fetched. `notte sessions network` DOWNLOADS the network
# logs (HAR) to a folder and prints the path - read those files to inspect the
# requests. `notte sessions network --urls-only` instead prints just the URLs inline.
notte sessions network
```

In the downloaded logs (or the `--urls-only` list), look for the request that returns the target data as JSON (not HTML, not analytics, not ads). When you find it, record:

- The **full URL** and method.
- Which **query/body parameters** map to your business variables (the search keyword, page number, category id, sort order).
- The **response shape** - which JSON fields become your output fields.

Confirm the endpoint reproduces the data directly. You can replay a discovered fetch from the page context to verify it returns what you expect:

```bash
notte page eval-js '
async () => {
  const r = await fetch("/api/search?q=laptop&page=1", { headers: { "accept": "application/json" } });
  const j = await r.json();
  return JSON.stringify({ keys: Object.keys(j), count: (j.results || j.items || []).length });
}
'
```

If the endpoint returns the data reliably, that is your path. Note it and move to generation.

### Network capture tips

- **Network data is page-scoped.** After navigating to a new page, re-`observe`, `wait`, then re-read `notte sessions network`. Earlier requests may not carry over.
- **Wait for stability** before reading the network log - trigger the interaction, give it ~1-1.5s, then read.
- **Filter mentally for JSON.** Ignore static assets, fonts, images, telemetry. You want the call whose response contains your fields.
- **Authenticated endpoints are fine** when the session is logged in (via a profile or vault) - the Function will run under the same authenticated session. Do not bypass authentication or access controls; only read data the logged-in user can already see.

## DOM fallback

When there is no usable API (data is server-rendered into HTML, or the API is signed/obfuscated past reach), fall back to extraction. Prefer the structured `scrape` command over hand-written selectors - it is more resilient and produces typed output directly:

```bash
notte page scrape --instructions "Extract each product as JSON with: title (string), price (number), url (string)" -o json
```

With `-o json`, the shape depends on whether you passed `--instructions`:

- **With `--instructions`** the extracted object is returned **at the top level** - the fields you asked for are the JSON keys, so `... -o json | jq '.title'` works directly. There is no wrapper to unpack.
- **Without `--instructions`** you get `{"markdown": "..."}` - the raw page text and nothing else.

```bash
notte page scrape --instructions "Extract heading and subheading as JSON" -o json
# -> {"heading": "...", "subheading": "..."}
```

Inside a deployed Function the equivalent is `session.scrape(..., response_format=Model)`, which returns the typed model directly.

Only drop to raw selectors when `scrape` cannot reliably target the data. If you must, follow this selector priority and validate on the real page (never write selectors speculatively from assumed structure):

```
data-testid  >  id  >  name  >  aria-label  >  stable structural path
```

Avoid pure positional selectors (`:nth-child`, `[3]`) unless the structure is genuinely stable. Test a candidate selector with `notte page eval-js` and confirm it hits the expected count before committing to it.

## When a means fails

A deterministic failure (explicit error, structural mismatch, 4xx that is not auth) means the *means* is wrong - do not retry it with tweaked parameters. Instead:

1. Return to the goal (the data you need).
2. Enumerate the other ways to reach it (different endpoint, different trigger, DOM fallback).
3. Pick the next means and try that.

A transient failure (timeout, dropped connection) warrants exactly one retry, not a loop.

## Pagination and scale

If the user will run this at scale or across pages, verify the pagination mechanism during exploration:

- For API paths: confirm the page/offset/cursor parameter and that incrementing it returns new data.
- For DOM paths: confirm the next-page control and that the new page's data is addressable the same way.

Bake the pagination mechanism into a parameter (`max_pages`, `cursor`) so one Function covers the whole range.

## Exploration budget

Cap exploration at roughly 100 tool steps. If you still cannot find a stable path - heavy bot protection, signed endpoints, a login wall you lack credentials for - stop and report the specific obstacle to the user with options (provide credentials, enable `--proxy`/`--solve-captchas`, accept a DOM-only path, pick a different source). Do not burn an unbounded number of steps.

## Success criteria

Before leaving exploration you must have:

- A single, reproducible command (API fetch or `scrape`) that returns the target data.
- A clear mapping from business variables -> request parameters.
- A clear mapping from response fields -> output schema fields.
- The pagination mechanism, if scale is required.

With those recorded, the session export in Phase 3 will capture a faithful, stable Function.
