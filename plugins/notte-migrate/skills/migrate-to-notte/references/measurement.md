# Measurement model

Use one window and currency. Model each workflow separately:

```text
baseline = plan/credits + browser + proxy + API/runtime/storage + model
notte    = plan/credits + browser + proxy + runtime/storage + model
saving   = baseline - notte
saving % = saving / baseline
```

Collect invoice rate/plan, included allocation, minimum/rounding, sessions/jobs,
billed minutes, retries, proxy GB, API/function calls, tokens, and peak
concurrency. Do not double-count included capacity or subscription credits.
When actual duration is unknown, round each session under provider rules and
show 1-, 2-, and 3-minute scenarios. Use observed peak concurrency for plan
selection; daily-average concurrency is a lower bound.

Compare latency only with identical workflow, target, auth state, proxy mode,
region, model, and output schema. Report raw samples for small `n`; calculate
p50/p95 only with a meaningful sample. Include source URLs and calculation date.
