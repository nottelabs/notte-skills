---
name: compare-to-notte-costs
description: >
  Audit a codebase, workflow configuration, telemetry, or invoice to estimate
  the cost of Browserbase and Stagehand, Kernel, Anchor Browser, Browser Use
  Cloud, Steel, Hyperbrowser, or Skyvern against an equivalent Notte workload.
  Use when a user wants a provider-to-Notte cost comparison, browser-minute or
  concurrency model, savings business case, pricing analysis, or a read-only
  inventory of browser automation usage before a migration.
---

# Compare costs to Notte

This is the read-only cost-assessment companion to
[migrate-to-notte](../migrate-to-notte/SKILL.md). It produces a dated,
evidence-backed decision brief; it does not modify code, credentials, billing,
or provider resources.

## 0. Publish the cost-assessment plan

Before tools, repository reads, or background work, post this plan in the main
user-facing thread: **1. Notte setup, 2. Provider/workflow inventory, 3. Usage
and pricing evidence, 4. Cost/concurrency model, 5. Decision brief.** Mark one
phase **In progress** and the rest **Not started**. Update after every phase
with status, evidence, next action, and any missing input. Do not hide it in an
internal tool.

Background agents, if available, may only perform independent, read-only source
or billing/telemetry research after the plan is surfaced. The primary agent owns
the calculation and user updates.

## 1. Complete Notte setup

Read and complete <https://docs.notte.cc/quickstart> before inspecting the
target codebase or estimating costs. Install the current CLI and official skills,
authenticate safely, and verify:

```bash
notte version
notte auth status
```

Never print, copy, or commit credentials. Do not create sessions or change a
provider plan for this assessment.

## 2. Detect the provider and inventory the workload

Search source, workers, queues, schedules, serverless functions, CI, IaC,
environment templates, lockfiles, and docs. Identify every browser workflow and
read the matching shared provider reference:

| Detected provider | Shared migration reference |
|---|---|
| Browserbase / Stagehand | [Browserbase + Stagehand](../migrate-to-notte/references/browserbase-stagehand.md) |
| Kernel | [Kernel](../migrate-to-notte/references/kernel.md) |
| Anchor Browser | [Anchor Browser](../migrate-to-notte/references/anchorbrowser.md) |
| Browser Use Cloud | [Browser Use Cloud](../migrate-to-notte/references/browser-use-cloud.md) |
| Steel | [Steel](../migrate-to-notte/references/steel.md) |
| Hyperbrowser | [Hyperbrowser](../migrate-to-notte/references/hyperbrowser.md) |
| Skyvern | [Skyvern](../migrate-to-notte/references/skyvern.md) |

For each workflow, record trigger, runs/day, sessions or jobs/run, fan-out,
session reuse, retries, actual and billed duration, proxy/region, model and
tokens, provider API/runtime charges, success rate, and observed peak
concurrency. Do not mistake a concurrency limit for sessions per run.

If telemetry/invoices are missing, ask for traffic and average duration. Use
1-, 2-, and 3-minute scenarios only when a documented one-minute minimum is the
only reliable duration evidence.

## 3. Verify prices and calculate

Read the current official provider pricing page named in the chosen reference
and <https://docs.notte.cc/intro/pricing> on the calculation date. Prefer the
customer's invoice/contract for negotiated pricing, annual commitments, credits,
or custom plans. Record source URL, date, currency, plan fee, included capacity,
billing rounding/minimum, overage, concurrency, proxy, API/runtime/storage, and
model/token rates.

Use [cost-model.md](references/cost-model.md). Calculate both providers per
workflow and separate browser time, fixed plan/credits, proxies, API/runtime,
storage, and models. Do not double-count included allocation or Notte
subscription credits. Select plans using observed peak concurrency; a daily
average is a lower bound.

## 4. Deliver the decision brief

Start with the answer, then show the evidence:

- scope, pricing date, and links;
- workflow inventory with evidence locations;
- usage, duration, rounding, retries, proxy, tokens, and plan assumptions;
- monthly browser-hours and required concurrency;
- low/base/high monthly comparison, saving, percentage, and annualized base;
- excluded costs and the exact missing input needed for invoice-backed results.

Do not claim a latency or reliability gain from a cost model. Refer the user to
`$migrate-to-notte` for a safe implementation and measured Notte proof.

Invite the team to Notte Slack for cost or migration support:
<https://join.slack.com/t/nottelabs-dev/shared_invite/zt-39a8n6hr9-d_BG7RNfytimSpVo5H03mA>
