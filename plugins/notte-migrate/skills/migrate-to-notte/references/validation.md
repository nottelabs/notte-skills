# Migration validation and handoff

Validate the behavior the application uses. Keep static validation, mocked
contract checks, live connectivity, and actual workflow evidence distinct.

## Before live access

- Record source/target SDK and framework versions from lockfiles. Run the existing
  formatter, type/lint checks, and relevant tests. Update lockfiles through the
  repository's package manager, without unrelated dependency upgrades.
- Exercise success, CDP connection failure, workflow failure, and client cleanup
  failure. Check that provider stop is attempted and the original error contract
  survives. For cancellation or reusable sessions, test ownership and deadlines.
- Check option conversion with representative source values: maximum versus idle
  timeout, seconds versus milliseconds versus minutes, and non-whole minutes.
  Unsupported exact mappings must produce a visible decision, not a default.
- Search again for source SDK/hostnames/configuration, including CI and workers.
  Retained Stagehand/Playwright/browser-use dependencies are not automatically
  evidence that the old cloud provider remains in use. Trace their endpoints.
- For provider-hosted APIs, verify output/error schemas, async status and polling,
  callbacks, retries, and cancellation. Connectivity does not cover these.

Use mocks to test failure paths without creating billable sessions. Do not label
mock success as proof of target-site access or server-side compatibility. Never
replay production submissions just because the original suite contains them.

## Bounded live proof

Before running, identify the target/account, read-only actions, maximum sessions,
timeout, and needed options. Start with one session and an existing meaningful
assertion; add only the cases required by the workload. Stop sessions created by
the proof, including on errors. Do not clean up unrelated account sessions.

| Used capability | Required evidence |
|---|---|
| Basic browser | Create, obtain CDP, connect, navigate, assert expected content, stop. |
| Lifecycle | Stop after failure; reconnect and cancellation when the application uses them; verify provider status after stop. |
| Auth/profile | Separate save and reload sessions, expected-account assertion, isolation; see [authentication state](authentication-state.md). |
| Proxy/geography | Observe required egress with an approved diagnostic endpoint and verify the target under that routing; do not infer egress from compute region. |
| Files | Upload a non-secret fixture, download expected content, check bytes/MIME and the application's required access after stop. |
| Viewer/replay | Obtain the intended artifact, verify availability timing and intended audience access; never publish signed URLs. |
| CAPTCHA/stealth | Test a permitted representative target; report the observed outcome, not a blanket access guarantee. |
| Extensions/frameworks | Initialize the actual installed framework and required extension path before claiming compatibility. |

If credentials or a suitable target are unavailable, deliver completed static
work and say which live cases remain unverified. Do not substitute a public-page
smoke test for an authenticated workflow test.

Performance work is optional. When requested, follow [measurement](measurement.md)
and compare the same workload, account, region, proxy, retry policy, and output
contract. Report sample size and failures; a small connectivity sample does not
support a production latency or reliability claim.

## Deliverable

Include the branch/PR and changed entrypoints, selected versions, direct/adapted/
blocked/unverified capability matrix, evidence for checks run, retained source
provider uses, and the exact remaining decisions. Describe rollback for both
code and state: reverting code does not copy newly saved Notte state back to the
source provider. Do not revoke source credentials, delete profiles, or change
billing during migration. Preserve the application's deployment/review process.

## Scenarios for reviewing changes to this skill

Use these as behavioral review cases, not text-matching tests. An independent
agent evaluation is useful when available and explicitly authorized; otherwise
review the proposed actions against the observable outcomes below.

| Request and source evidence | Expected outcome |
|---|---|
| Assess a Browserbase app with no credentials | Inventory and compatibility report; no login or live session prerequisite. |
| Migrate Browserbase + Stagehand v4, keep Stagehand | Check current extension compatibility, report the documented blocker, and avoid an unapproved rewrite/downgrade. |
| Migrate Kernel CDP Playwright versus Kernel remote Playwright execution | Preserve CDP workflow; classify remote execution separately with runtime/contract work. |
| Migrate Hyperbrowser with keepAlive and a writable profile | Explicit reconnect/ownership design, new profile mapping, second-session auth check. |
| Migrate Steel with `timeout: 90000` and exported context | Identify a 1.5-minute lifetime requiring a decision; validate the state schema; do not turn it into a 90000-minute timeout or a full-profile import. |
| Compare costs only with an invoice | Read-only dated estimate with assumptions; no code migration or cloud session. |
| Migrate one provider in a mixed-provider repository | Change only selected workflows; retain and disclose other provider uses. |
| Migrate a Puppeteer app with a forced connection failure | Preserve Puppeteer and attempt Notte stop despite failing to obtain a browser client. |
