---
name: health-contract
description: The health contract a forged Function carries so it can be self-tested at build time and repaired later
---

# Health Contract Reference

A **health contract** is a small, explicit description of what a *correct* result from a Function looks like. Forge stamps it into every Function it generates. It pays off twice:

1. **At build time** - the self-test (Phase 4) has an unambiguous pass/fail target instead of "looks about right".
2. **At repair time** - [notte-functions-doctor](../../notte-functions-doctor/SKILL.md) reads the contract to know what to repair *toward*. Without it, repair is guessing whether `[]` means "no results today" or "the selector broke".

The contract is the single most valuable thing a forged Function carries beyond its code. The cost to add it at build time is near zero; the cost of not having it at repair time is high.

## What goes in a contract

Two parts: the **schema** (already implied by the response model) and the **sanity bounds** (the part you must add deliberately).

| Element | Source | Example |
|---------|--------|---------|
| Output schema | the Pydantic response model | `stories: list[Story]` |
| Non-emptiness | you decide per field | `len(result.stories) >= 1` |
| Count bounds | expected volume | `1 <= len(result.stories) <= 100` |
| Field shape | value-level sanity | `price > 0`, `url.startswith("http")` |
| Freshness/format | domain knowledge | dates parse, ids match a pattern |

The schema alone is not enough: a broken scrape usually still returns a schema-valid but **empty or garbage** payload. The sanity bounds are what catch that.

## How forge stamps it

Two complementary mechanisms - use both:

### 1. A machine-readable comment block

Put a clearly delimited block near the top of the Function file so doctor (and humans) can find it without running the code:

```python
# === HEALTH CONTRACT ===
# schema: { stories: [ { rank: int, title: str, url: str, points: int } ] }
# bounds:
#   - len(stories) >= 5            # HN front page always has many stories
#   - every story has title and url
#   - points >= 0
# notes: empty list means the page structure changed, NOT "no data today"
# === END HEALTH CONTRACT ===
```

### 2. Light runtime assertions in `run()`

Encode the cheap, high-signal bounds as assertions so a broken run fails loudly instead of silently returning junk. A failed assertion surfaces directly in the run `result` (a string containing `AssertionError: <your message>`), so the message is your diagnostic:

```python
def run(max_stories: int = 10):
    ...
    result = session.scrape(..., response_format=Model)

    # health contract - fail loud on a structurally broken result
    assert result.stories, "health contract violated: 0 stories (page structure likely changed)"
    assert all(s.title and s.url for s in result.stories), "health contract violated: missing title/url"

    return result
```

Keep assertions **cheap and structural**. They guard against "the path broke", not against legitimate business variation. Do not assert on values that can reasonably change between runs (exact counts, specific prices, today's first result).

## Calibrating bounds

Set bounds from what you actually observed during exploration, not from hope:

- If the front page showed ~30 results, `>= 5` is a safe floor that still catches "0".
- If a field was missing on ~30% of items during exploration, **do not** assert it is always present - record that in the `notes` and in the delivery report instead.
- Prefer floors (`>= 1`) over exact equality. The contract should flag breakage, not normal variance.

## Partial coverage is still valid

If some fields could not be reliably extracted, the Function can still ship. Put the reliable fields under contract, mark the unreliable ones as optional in the schema, and document the gap in both the contract `notes` and the delivery report. Never assert on a field you know is flaky - that turns normal variance into false breakage.
