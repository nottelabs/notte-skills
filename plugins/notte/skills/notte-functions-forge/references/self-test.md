---
name: self-test
description: Validate a forged Function in the cloud against its health contract, and self-repair until it passes
---

# Self-Test Reference

A Function is not done when it is created - it is done when a real cloud run returns a result that satisfies the [health contract](health-contract.md). This reference covers the validate-and-repair loop that closes that gap. The same loop is reused by [notte-functions-doctor](../../notte-functions-doctor/SKILL.md) to verify a repair.

## `functions run` blocks and returns the result inline

`notte functions run -o json` runs the Function in the cloud, **waits for it to finish**, and returns both `status` and `result` in one payload. For the common case you do not need a separate poll:

```bash
notte functions run --function-id "$TARGET_ID" -o json | jq '{status, result}'
```

There is no client-side polling - the CLI issues one synchronous POST and waits. That means the call is bounded by the global `--timeout` (default **60 seconds**). A Function slower than that fails the *command* while the run continues server-side, which looks like a failure but is not one. Raise it for anything non-trivial: `--timeout 600`.

## Read the `result` (status alone is not enough)

The dependable pass/fail signal is `result`:

| `result` is... | meaning |
|----------------|---------|
| a JSON payload matching your schema (e.g. `{"quotes": [...]}`) | the run produced data - now check the contract bounds |
| a string starting `Script execution failed ...` / containing a `Traceback` | the run **FAILED** - the exception or health-contract `AssertionError` message is inside that string |

`result` is the return value of `run()` serialized to JSON, so a `dict` return arrives as a real nested object you can address with `jq` directly. (`run-metadata`'s `result` is different - a Python `repr` - which is why contract validation should read `functions run`.)

The run `status` is a weaker signal. A failed run may report `status: "failed"`, but a Python error inside `run()` (including a health-contract `AssertionError`) can also come back as `status: "closed"` with the error in `result`. So **never treat `status: "closed"` as proof of success** - always inspect `result`. Treat `status == "failed"` **or** a `result` that is an error string as a FAIL.

This is why the [health contract](health-contract.md) assertions matter: a broken run returns `result` as `"... AssertionError: health contract violated: 0 quotes ..."`, which tells you both that it broke and why, in the one field you already have.

## Always target an explicit Function id

Capture the Function id once and pass `--function-id "$TARGET_ID"` on every `run`, `run-metadata`, and `update` below. Do not rely on the implicit "current function" pointer: `notte functions create` and `delete` move it, so a bare command can run against - or overwrite - the wrong Function once more than one exists.

- **Forge** sets `TARGET_ID` to the Function it just created.
- **Doctor** sets `TARGET_ID` to the throwaway verify Function, never the live one.

```bash
TARGET_ID="<the function id you are testing>"
```

## Step 1 - run with representative inputs

Run the Function in the cloud (not locally) so you test the real deployment path:

```bash
notte functions run --function-id "$TARGET_ID" -o json | jq '{status, result}'
```

Pass non-default parameters with `--var key=value` (repeatable) or `--vars '{json}'`, and exercise a realistic case (a real keyword, a real page), not just the defaults:

```bash
notte functions run --function-id "$TARGET_ID" --var page=2 -o json | jq '{status, result}'
# or, when you need real numbers/booleans instead of strings:
notte functions run --function-id "$TARGET_ID" --vars '{"page": 2}' -o json | jq '{status, result}'
```

`--var` passes every value as a string (`page=2` arrives as `"2"`); use `--vars` JSON when the parameter must be a real number or boolean. Run variables are **not** coerced to your `run()` type hints, so the Function body must cast inputs it uses numerically (e.g. `page = int(page)`).

## Step 2 - check the result against the health contract

A run **passes** only if **all** of these hold:

1. `result` is a structured object (not an error string) and `status` is not `"failed"`.
2. it matches the response schema.
3. it satisfies every sanity bound (non-empty where required, counts in range, field shapes valid).

A run whose `result` is an error string, or an object that is empty / violates a bound, is a **FAIL** - even when `status` is `"closed"`. That silent case is the whole reason the contract exists.

## Step 3 - design minimal but covering test cases

Use the fewest runs that still exercise every path:

- One run with **default** parameters (the common case).
- One run per **meaningfully different** parameter value (a different category, a paginated case, an edge input that returns few results).
- If the task has multiple capabilities (list page + detail page), exercise each at least once.

Do not run hundreds of cases. Cover the functional paths, confirm the contract holds, stop.

## Step 4 - self-repair on failure

On a FAIL, diagnose from the `result` (and logs, below), fix the Function file, push the update, and re-run the **same** target:

```bash
# edit the function file to fix the issue, then:
notte functions update --function-id "$TARGET_ID" --file forged_function.py
notte functions run --function-id "$TARGET_ID" -o json | jq '{status, result}'
```

Common failure -> fix:

| What `result` shows | Likely cause | Fix |
|---------------------|--------------|-----|
| an error string with a `Traceback` | exception in `run()` | fix the failing line; re-export from a fresh session if the path drifted |
| a structured object that is empty | selector/endpoint returned nothing | re-check the path against the live site; the structure may differ from exploration |
| an error string with `AssertionError: health contract ...` | contract violated | either the path broke (fix it) or the bound was too strict (recalibrate per [health-contract.md](health-contract.md)) |
| an error string mentioning a timeout | slow page / missing wait | add a `wait`, or narrow what is scraped |
| the **command** times out with no `result` at all | the run outlived the 60s request timeout | re-run with `--timeout 600`; the run itself is probably fine |

Repeat until a run passes the contract. Never ship on a FAIL or on an unverified run.

## Optional - deeper logs and run history

The inline `result` is enough to validate the contract. If you need execution logs, take the `function_run_id` the run you just did returned and read that run's metadata:

```bash
RUN_ID=$(notte functions run --function-id "$TARGET_ID" -o json | jq -r '.function_run_id')
notte functions run-metadata --function-id "$TARGET_ID" --run-id "$RUN_ID" -o json | jq -r '.logs[]'
```

If you look the id up in history instead, pass `--only-active=false` - `notte functions runs` filters to *active* runs by default, so a Function whose runs have all finished lists as `[]`.

`run-metadata`'s `result` can come back as a Python `repr` rather than clean JSON, so prefer the `notte functions run` output (above) for contract validation, and use `run-metadata` only for logs and history.

## Optional - isolate the self-test in a sub-agent

If your runtime supports dispatching a sub-agent (for example, Claude Code's Task tool), you can hand the validation to an isolated agent: give it the Function id and the test cases, have it follow this loop, and report per-case pass/fail plus any contract violations. This keeps the noisy run/inspect output out of the main session. It is an optimization, not a requirement - running the loop inline is equally correct.
