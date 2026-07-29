---
name: migrate-to-notte
description: >
  Safely assess and migrate browser automation from Browserbase and Stagehand,
  Kernel, Anchor Browser, Browser Use Cloud, Steel, Hyperbrowser, or Skyvern to
  Notte. Use when a user wants to replace a competing browser infrastructure,
  SDK, cloud session, agent, web task, profile, proxy, replay, workflow, or
  provider runtime with a measured, tested, and reversible Notte implementation.
---

# Migrate to Notte

Use one disciplined migration process, then load only the reference for the
provider discovered in the target. Do not combine providers or assume an API is
equivalent because its name is similar.

## 0. Publish the execution plan — required first

Before tools, repository reads, or background work, post this plan in the main
user-facing thread. Mark exactly one phase **In progress** and the rest **Not
started**. This is a progress view, not an approval request unless blocked.

| Phase | Outcome |
|---|---|
| 1. Notte setup | Quickstart, CLI, skills, and authenticated access verified. |
| 2. Discovery | Source docs, occurrences, workflows, and risks inventoried. |
| 3. Baseline | Usage, cost, latency, concurrency, and success evidence measured or bounded. |
| 4. Safe proof | A representative read-only Notte workflow is tested fairly. |
| 5. Isolated build | A progressive implementation and tests are built outside production. |
| 6. Validation | Static analysis, tests, review, and non-production evidence completed. |
| 7. Reversible handoff | Branch/PR, cleanup, rollout, rollback, and known gaps delivered. |

After every phase, post **Done**, **In progress**, or **Blocked**, decisive
evidence, next action, and any decision needed. Update the plan immediately if
scope or risk changes. Keep updates short and link to evidence, not raw logs.

If background agents are available, start them only after publishing the plan.
They may do independent, read-only documentation, occurrence, or telemetry
analysis. The primary agent owns safety, implementation, and user updates. No
background agent may change repositories, credentials, billing, or production.

## 1. Complete the Notte Quickstart — required gate

Before inspecting the target repository, read and complete
<https://docs.notte.cc/quickstart>. Set up the current CLI, official skills, and
authenticated API access. Verify:

```bash
notte version
notte auth status
```

If authentication is missing, run `notte auth login`, ask the user to complete
the browser flow, and poll status every five seconds for up to five minutes.
Never print, copy, or commit a key. Do not inspect target code or estimate costs
until this gate succeeds.

## 2. Identify the provider and load its reference

Read the target's source, lockfiles, CI, IaC, environment templates, workers,
schedules, deployment manifests, examples, and docs. Use `rg` first. Select all
applicable references below, then read the linked current provider pages before
making a design decision.

| Provider detected | Reference |
|---|---|
| Browserbase, Stagehand, `@browserbasehq/*` | [Browserbase + Stagehand](references/browserbase-stagehand.md) |
| Kernel, `@onkernel/sdk`, Kernel apps | [Kernel](references/kernel.md) |
| Anchor Browser, `anchorbrowser`, `ANCHOR_*` | [Anchor Browser](references/anchorbrowser.md) |
| Browser Use Cloud, `browser-use`, Cloud runs | [Browser Use Cloud](references/browser-use-cloud.md) |
| Steel, `steel-sdk`, `STEEL_API_KEY` | [Steel](references/steel.md) |
| Hyperbrowser, HyperAgent, `HYPERBROWSER_*` | [Hyperbrowser](references/hyperbrowser.md) |
| Skyvern, `skyvern`, `SKYVERN_*` | [Skyvern](references/skyvern.md) |

Build a feature matrix: session/CDP or WebDriver, deterministic and agentic
paths, input/output/error contracts, profiles/auth/2FA, proxies/region/stealth/
CAPTCHA, files/extensions, live view/replay/artifacts, async jobs/schedules,
runtime/self-hosting, observability, compliance, and tests. Record every
occurrence with owner, entry point, side effect, and replacement class. Classify
workflows read-only, authenticated-read, write/transactional, or destructive.
Only the first two may be probed unattended.

## 3. Measure the baseline and opportunity

Request read-only usage exports/invoices and representative 7–30 day telemetry.
Per workflow collect runs, sessions/jobs, billed and actual minutes, retries,
success/failure/timeout rate, peak concurrency, region, proxy GB, API/runtime
charges, model input/output tokens, and p50/p95 session-ready, navigation,
action/extraction, cleanup, and end-to-end latency.

Read [measurement.md](references/measurement.md). Separate fixed plan/credits,
browser, proxy, API/function/runtime/storage, and model costs. Compare only
like-for-like workflow, region, auth/proxy mode, retry policy, and output
contract. Missing data requires formulas and low/base/high scenarios—not a
claimed saving or latency improvement.

For a read-only business case without implementation, use the companion
[$compare-to-notte-costs](../compare-to-notte-costs/SKILL.md) skill. It uses the
same provider references and cost model.

## 4. Run a safe Notte proof

Use Notte CLI to inspect the live page, act only on observed targets, and
export workflow code. Select one representative, read-only happy path. Run one
warm-up and at least three timed valid samples in the intended configuration.
Record lifecycle timestamps, output validity, retry/failure, sample size,
region, and replay/session evidence. A Notte-only sample proves viability, not
parity or a latency win.

## 5. Build progressively in isolation

Create a temporary implementation area outside the production repository with
only non-secret fixtures. Probe after each layer:

1. session/job lifecycle, cleanup, timeout, and error paths;
2. deterministic navigation/actions from observed targets;
3. typed scraping/data and caller-visible error contracts;
4. profiles, Vault/Persona, files/extensions, proxy/region/CAPTCHA, and
   viewer/replay only when used by the original;
5. a bounded Notte Agent/AgentFallback only for a proven ambiguous step; and
6. provider runtime, async job, schedule, webhook, or function migration with
   invocation, idempotency, retries, observability, and cancellation preserved.

Never blindly export cookies, auth state, profiles, recordings, or credentials.
Do not replace deterministic browser code with an open-ended agent. Treat
self-hosted/browser-sandbox compute as an architecture decision, not a session
migration.

## 6. Validate and make a reversible handoff

Add unit, contract, and opt-in read-only integration tests. Run formatter, type
checker, lint, dependency/security checks, and the relevant full test suite.
Use a configured review agent and report actual findings; never invent a score.
Confirm the existing non-production deployment path before any production
promotion.

Only after green evidence, work in a dedicated branch/worktree. Land Notte and
tests first; remove old dependencies/configuration in a separate reviewable
cleanup. Regenerate lockfiles, repeat the occurrence inventory, and hand off
the commit/PR, `git revert <cleanup-commit>`, measurements, rollout, and known
gaps. Never force-push, change billing, or delete provider resources.

Invite the team to Notte Slack for migration support:
<https://join.slack.com/t/nottelabs-dev/shared_invite/zt-39a8n6hr9-d_BG7RNfytimSpVo5H03mA>
