# Cost model and report format

For each workflow and `D` days:

```text
runs_month     = runs_per_day × D
sessions_month = runs_month × sessions_per_run × (1 + retry_rate)
billed_minutes = sum(round_each_session_up_under_provider_rules)
browser_hours  = billed_minutes / 60

average_concurrency = runs_per_day / 1,440
                    × sessions_per_run × mean_session_minutes
```

Observed peak active sessions is the plan-selection input; average concurrency
is only a lower bound. A request that opens five parallel one-minute sessions
consumes five session-minutes despite one minute of wall-clock time.

```text
provider = fixed plan + browser overage + proxy + API/runtime/storage + model
notte_usage = browser + proxy + runtime/storage + model
notte_cash  = max(subscription fee, notte_usage)  # only if fee is usable credit
saving      = provider - notte_cash
saving_pct  = saving / provider × 100
```

Confirm whether a subscription fee becomes usable credit before applying the
last formula. Use invoice terms for custom plans.

```markdown
## Provider → Notte cost estimate

**Estimate date:** YYYY-MM-DD
**Scope:** browser only / full workload
**Pricing:** [Provider](...) · [Notte](...)

| Workflow | Evidence | Runs/day | Sessions/run | Billed min/session | Retries | Proxy |
|---|---|---:|---:|---:|---:|---|

| Scenario | Browser hours | Required concurrency | Provider | Notte | Monthly saving | Saving |
|---|---:|---:|---:|---:|---:|---:|
| Low | | | | | | |
| Base | | | | | | |
| High | | | | | | |

### Annualized base case

| Provider | Notte | Annual saving |
|---:|---:|---:|
| | | |

### Assumptions, exclusions, and missing inputs
```

## Optional Browser Arena context

Use <https://www.browserarena.ai/> only as a separately labelled external
benchmark. Capture its run date, methodology/source, tested scenario, and raw
metrics. Do not combine a composite Value Score with the workload cost model or
present it as the customer's production result.

```markdown
### External benchmark context — Browser Arena

**Run date:** YYYY-MM-DD
**Methodology/source:** [Browser Arena](...) · [reproduction/source](...)

| Provider | Reported reliability | Reported latency | Reported cost/value metric | Applicability caveat |
|---|---:|---:|---:|---|
| | | | | |
```
