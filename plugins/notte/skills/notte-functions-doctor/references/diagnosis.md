---
name: diagnosis
description: Classify why a Notte Function failed from its run metadata, and decide what is code-fixable
---

# Diagnosis Reference

The goal of diagnosis is to name the failure class correctly *before* touching code. The wrong class wastes runs and can make a healthy Function worse. The fastest way to read the failure is to **reproduce it** - re-run the Function and read the inline `result`, which carries the clean error text:

```bash
notte functions run --function-id "{function_id}" -o json | jq '{status, result}'
```

**Read `result`, not `status` alone.** A failed run may report `status: "failed"`, but an error inside `run()` can also return `status: "closed"` with the error in `result` - so `"closed"` does not guarantee success. The dependable read is **`result`**:

- a **JSON object** matching the schema -> the run produced data (if it is empty or violates a bound, that is drift; see class 1).
- a **string** beginning `Script execution failed ...` with a `Traceback` -> the run raised; the exception or `AssertionError` message is in that string (classes 1, 2, 3, or 4 depending on what it says).

(You can also pull the last failed run from history with `notte functions runs --function-id "{function_id}" --only-active=false -o json`. **Include `--only-active=false`**: for runs "active" means *still executing*, so on older CLIs completed runs are filtered out and the list looks empty. That form works on every CLI version. Note `run-metadata`'s `result` is a Python `repr` rather than clean JSON. Re-running still gives the cleanest read.)

## Failure taxonomy

### 1. Selector / endpoint drift  -  CODE-FIXABLE

**Signals:** `result` is a JSON object that is empty (`[]`, `null`, zero rows) or missing fields, violating the contract's non-emptiness/shape bounds; **or** `result` is an error string whose only error is `AssertionError: health contract ...` (the run's own contract caught the emptiness). No deeper `Traceback` into scrape/parse code.

**Meaning:** the path still ran, but produced no data. Usually the site moved the data (renamed a CSS class, changed an internal endpoint, restructured the response). It can equally be a **pure code defect** in the Function (a bad filter, a wrong field name, an over-narrow query) that drops the data even though the page is fine. Re-exploration tells you which: if the live page still has the data, the bug is in the Function's code and the fix is the code, not the path.

**Action:** re-explore the live site (forge exploration). If the data moved, find the new path; if the page is fine, fix the code that drops it. Then patch, verify, promote.

### 2. Hard exception  -  CODE-FIXABLE

**Signals:** `result` is an error string with a **`Traceback`** into the scrape/parse code (not just an `AssertionError`) - a selector resolved to nothing and a later line dereferenced it, a navigation 404'd, a parse blew up.

**Meaning:** the path broke hard rather than silently. Often the same root cause as drift, just caught by an exception instead of an empty result.

**Action:** identify the failing step from the traceback, re-explore that step, patch, verify, promote.

### 3. Expired credentials / auth wall  -  NOT a code fix

**Signals:** `result` (the returned object, or the error string) shows a login page, a redirect to `/login` or an SSO host, a 401/403, or scraped content that is a sign-in form instead of the target data. Confirm with a `notte page screenshot` during re-exploration.

**Meaning:** the session is no longer authenticated - the vault credential expired, the persona/profile lost its cookies, or MFA is now required.

**Action:** report this. The fix is in configuration, not scrape logic. Check, in order: (a) `notte functions secrets list` for a missing/rotated secret the Function reads from `os.environ` (inspect one with `notte functions secrets get NAME`, re-set with `notte functions secrets set NAME <value>`, remove a stale one with `notte functions secrets delete NAME`); (b) that the Function's `run()` session is opened with the intended `vault_id`/`profile_id`; (c) the vault credential itself (`notte vaults credentials add` upserts it for a URL) or the profile's saved login. Editing the scrape logic will not help and may mask the real problem. Once the user confirms the credential/secret is refreshed, you can re-verify, but do not patch scrape code for this class.

### 4. Anti-bot block / captcha  -  NOT a code fix (config, not code)

**Signals:** `result` shows a captcha challenge, a "verify you are human" interstitial, a Cloudflare/DataDome block page, or sudden empty results that coincide with a block page in a `notte page screenshot` taken during re-exploration.

**Meaning:** the site started challenging the session. The data path may be unchanged.

**Action:** advise the session-level mitigations rather than touching extraction logic - `--proxy` / `--proxy-country`, `--solve-captchas`, or a profile with established trust. These are Function/session configuration. Do not loop retries blindly; that escalates the block.

### 5. Site gone or restructured  -  REPORT, then maybe rebuild

**Signals:** the target URL 404s, the page is a completely different layout, the product/section no longer exists, or the whole information architecture changed.

**404 tie-breaker (class 2 vs class 5).** A 404 alone is ambiguous - it appears under both the hard-exception class (a step's URL drifted) and here (the target is gone). Decide by re-exploring: if the same data exists at a **new path**, it is class 2/drift - re-point the Function and fix it. If the path is simply gone with **no replacement** (and the site root still works), it is class 5 - report. A quick check during re-exploration: confirm the site root returns 200 while the target path returns 404, and look for any new path serving the same data before concluding the target is gone.

**Meaning:** this is past "drift" - the Function's assumptions about the site are void.

**Action:** report to the user and confirm the new target or intent. A restructure this deep is closer to re-forging than repairing - consider handing back to [notte-functions-forge](../../notte-functions-forge/SKILL.md) with the user's confirmation of the new target.

## Disambiguating empty results

An empty `result` is the ambiguous case. Distinguish three things before assuming drift:

1. **Genuinely no data** (a search that legitimately returns nothing) - the contract's `notes` should say whether empty is ever legitimate. Re-run with inputs that *must* return data (a known-populated query) to rule this out.
2. **Blocked/auth** - check `result` (and a screenshot during re-exploration) for a challenge or login page (classes 3-4), not a structural break.
3. **Drift** - inputs that should return data return nothing, and there is no block or login page. Now it is class 1.

Always run the disambiguating check (a known-good input) before concluding drift. It costs one run and prevents repairing a Function that was never broken.

## Reproduce before you repair

Confirm the failure is current and deterministic, not a one-off transient (a timeout, a momentary outage):

```bash
notte functions run --function-id "{function_id}" -o json | jq '{status, result}'
```

If a fresh run's `result` is a valid object that satisfies the contract, the original failure was transient - report that and stop. Do not repair a Function that is currently healthy.

## Output of diagnosis

Before leaving this phase you should be able to state, in one sentence: **the failure class, the evidence, and whether it is code-fixable.** For example: *"Class 1 drift - run finished but returned 0 listings and the `len >= 1` bound failed, no block/login page; code-fixable, proceed to re-explore."*
