# Migration skill tests

## Offline regression suite

From the repository root, with Python 3.12+ and Node 24+:

```sh
python3 scripts/migration-tests/test-examples.py
node --test scripts/migration-tests/test-examples.mjs
```

These execute the Python, TypeScript Playwright, and TypeScript Puppeteer code
blocks extracted from the shipped skill reference. Fault-injecting clients test
observable results, primary-error preservation, independent cleanup, missing
pages/contexts, Python interruption, and absence of raw transport-error logging.
They do not call providers or need credentials. CI runs both suites.

The doubles intentionally do not establish the SDK's own startup rollback,
network retry, or server behavior. Type checks against real packages and live
probes are separate evidence below. A future new example must get an executable
case, not just a prose assertion that its path is supported.

## Independent skill evaluations

`eval-cases.json` contains reproducible requests and source fixtures. Materialize
one case in a fresh temporary repository, give an independent evaluator only the
request, fixture, and skill, and inspect the resulting changes and report. Do not
give it the conclusions in this document as part of its task. These are snapshot
agent evaluations, not deterministic CI tests or a claim of model-wide success.

Run date: 2026-09-21. Initial skill revision: d3be162. Evaluations exposed the
SDK callback logging issue; examples were then corrected and regression-tested.

| Case | Observed result |
|---|---|
| No-credentials Browserbase assessment | Produced inventory and compatibility report; source hashes unchanged; no login or sessions. |
| Browserbase + Stagehand v4 | Checked current extension restriction; reported blocked; did not downgrade or rewrite framework. This is a documentation-based gate, not a live reproduction. |
| Invoice-only comparison | Calculated 2,000 sessions and 50 raw hours; separated stated $50 browser/$20 proxy/$30 plan charges; withheld unsupported savings. Source unchanged. |
| Python Browserbase job | Migrated synchronous read_title contract, mapped 120-second lifetime, resolved dependencies, and passed 12 mocked lifecycle/error tests. |
| Kernel CDP and remote execution | Migrated CDP function with public contract preserved; retained remote VM function as an explicit partial migration. Real-package TypeScript check and six mocked lifecycle tests passed. |
| Hyperbrowser reusable async worker | Produced explicit session owner, profile mapping, reconnect and cancellation handling. Six mocked Python tests passed, including cancellation during threaded start. |
| Steel Puppeteer plus Browserbase worker | Migrated selected worker; second worker byte-identical. Eight mocked tests and real-package TypeScript checks passed. Rejected unsupported fractional-minute timeout pending a decision and validated exact-origin state schema. |

The migrated fixture tests were rerun by the primary agent. Generated implementations
are evaluation artifacts, not shipped adapters or evidence of source-provider parity.

## Example regression evidence

The original TypeScript examples failed four combined-failure cases: workflow
errors were replaced by client cleanup errors. Explicit lifecycle ownership and
primary-error preservation fixed these. SDK 1.9.1 `.use()` also logs callback
exceptions, so the examples now avoid that wrapper and leave sanitized reporting
to the application. The 19 Python and 30 TypeScript example tests pass.

The updated TypeScript examples compile against `notte-sdk` 1.9.1,
`playwright-core` 1.63.0, `puppeteer-core` 25.11.0, and TypeScript 7.0.2.
The Python example ran with `notte-sdk` 1.9.1 and Playwright 1.63.0 on Python 3.12.

## Live coverage and remaining inputs

Live probes use temporary sessions, synthetic state, and a public read-only
target. Initial Notte-only feature checks are in `live-results.json`; subsequent
credentialed checks against all four source providers are in
`source-live-results.json`. No real authenticated account was used. Temporary
Notte profiles were deleted.

| Path | Result |
|---|---|
| Notte create/CDP/Playwright navigation | Passed; expected example.com title. |
| Puppeteer reconnect to same Notte session | Passed; same page/title after Playwright disconnect. |
| Explicit stop and closed status | Passed. |
| Exact documented Python example | Passed against live Notte. |
| New Notte profile; cookie/localStorage write then separate reader session | Passed with synthetic state; not proof of real login portability. |
| Buffer upload through Playwright | Passed; browser-side file text matched fixture. |
| Playwright data-URL and blob downloads | Failed byte integrity: both yielded zero-byte local files via save_as. The same files returned the correct 25 bytes through the session-file API after stop; test files were deleted. |
| Playwright set_content with default load wait | Timed out twice on the live public page. Installing the controlled DOM fixture through evaluate worked; cause not established. |
| Explicit France proxy and 1200x800 viewport | Passed; diagnostic endpoint reported FR and viewport matched. One configuration only. |
| Replay retrieval after stop | Passed; replay URL returned nonempty bytes. Playback and cross-user permissions not tested. |
| Kernel, Browserbase, Hyperbrowser, Steel to Notte | Passed live create/CDP/navigation, synthetic cookie and exact-origin localStorage export/import, and Puppeteer reconnect on both sides. Browserbase and Hyperbrowser required their source keep-alive options for reconnect. All stop/release calls acknowledged; source terminal status was not polled. |
| Real login/MFA, tenant isolation, other proxy configurations, CAPTCHA, extensions, replay/embed permissions | Unverified; require representative targets/accounts and feature configuration. |
| Kernel VM execution, managed agents/jobs, self-hosted/private-network workflows | Contract assessment only; application/runtime fixtures and access needed. |
| Cost/performance parity | Unverified; needs workload telemetry/invoices and equivalent source-provider runs. |

The source probes first connected with Playwright, navigated to example.com,
set a synthetic cookie and localStorage value, and exported `storageState()`.
They imported cookies with `addCookies()` into Notte's default context and
installed an origin-scoped `addInitScript()` for localStorage before navigation.
The target title, cookie value, and storage value matched. Both sides were also
reconnected using Puppeteer after Playwright disconnected. State stayed in memory.

Initial reconnect attempts failed for Browserbase and Hyperbrowser with default
session settings. Repeating with Browserbase's session `keepAlive: true` and
Hyperbrowser's CDP URL `keepAlive=true` passed. These settings belong to the source
provider and must not be copied blindly onto Notte. See
[Browserbase keep-alive](https://docs.browserbase.com/guides/long-running-sessions#keep-alive-sessions)
and [Hyperbrowser lifecycle](https://www.hyperbrowser.ai/docs/sessions/lifecycle).
The evidence retains unsuccessful attempts as well as successful retries.

Provider credentials are available and have been validated. Remaining inputs
are representative source applications with locked dependencies, permitted test
accounts/URLs and expected authenticated assertions, the specific advanced
features to preserve, and workload telemetry/invoices for cost or performance
claims. Real account portability, source-imported profile persistence across a
second Notte session, and managed-agent/VM contracts remain unverified. Do not
put API keys or authentication state into fixtures, chat, or committed evidence.

## Blind live migration evaluations

On 2026-09-21, seven source scripts ran successfully against their original
providers before conversion. Each converter was a separate subagent with no
conversation history. Its inputs were one source repository, the skill at
revision `73da9e6`, the migration request, and bounded execution permissions.
Converters did not receive baseline results, proposed mappings, other converters'
outputs, or the parent's additional connection-failure checks.

| Source case | Blind conversion and independent verification |
|---|---|
| Kernel + Playwright | Passed form interaction, table extraction, in-memory upload, PNG signature, cookie/localStorage reconnect, and intentional workflow failure. Parent also verified connection failure and three closed Notte sessions. |
| Browserbase + Playwright | Same acceptance and additional cleanup checks passed with two-minute lifetime preserved. |
| Hyperbrowser + Playwright | Same acceptance and additional cleanup checks passed with reconnect retained. |
| Steel + Puppeteer | Passed form interaction, PNG signature, localStorage reconnect, intentional workflow failure, and additional connection-failure cleanup. |
| Stagehand 3.7.3 browser workflow | Passed unchanged navigation, locator interaction and calculated output on Notte; parent confirmed cleanup after success and connection failure. This fixture contains no AI calls. |
| Stagehand 4.1.0 | Source initialization/navigation/snapshot passed on Browserbase. Converter and parent separately reproduced Notte rejecting `Extensions.loadUnpacked` during `localBrowser.connect`. Both confirmed cleanup. Converter retained the source app and did not downgrade. |
| Stagehand 3.7.3 AI workflow | Source passed two real `act` calls and schema-based `extract`. Converter preserved them. Target created a Notte session but stopped on missing `OPENAI_API_KEY`; parent reproduced the blocker and confirmed closed status. AI acceptance is not passed. |

The parent reran all 44 additional mocked lifecycle tests supplied by the six
implemented migrations. These are separate from the earlier 49 shipped-example
regressions and 32 offline fixture tests. The controlled DOM fixtures are not
real login, MFA, tenant isolation, full profile migration, or framework-wide
compatibility tests. Source release calls succeeded; source terminal statuses
were not polled in these fixture runs.

Several converters initially received HTTP 422 after specifying a two-minute
maximum without overriding the longer default idle timeout. Explicit compatible
idle timeouts resolved their creation failures. The shared session guide now
calls this out. The Stagehand reference now distinguishes the verified v3 browser
path, model credentials for local AI execution, and the live v4 blocker.

### Reproduce or inspect

- `blind-live-cases.json`: source code, pinned direct dependencies, requests, and
  original lockfile hashes. Give an evaluator only its selected case and skill.
- `blind-live-migrations.json`: generated target code and lifecycle tests for
  review or reruns. These are evaluation snapshots, not supported adapters.
- `blind-live-results.json`: observed results and limitations, including discarded
  parent harness runs that instrumented CommonJS instead of the imported ESM SDK.
- `verify-live-migration.mjs`: parent verification for the four plain-driver
  migrations and deterministic Stagehand v3 case. It runs the unchanged acceptance,
  injects a connection failure, and checks provider-side closed status.

Materialize a selected case's `files` into an empty directory, then initialize a
Git repository before asking the evaluator to work in a separate worktree.
For a recorded target, overlay the matching migration's `files` onto its source
files. Run `npm install --ignore-scripts` in that directory. Direct versions are
pinned, but resolving dependencies afresh is not guaranteed to reproduce the
original transitive lockfile; record the generated lockfile and versions.

Offline checks for the generated migrations, using Node 26.8.1 in this run:

```sh
node --experimental-test-module-mocks --experimental-vm-modules --test lifecycle.test.mjs
```

The following live commands create billable sessions. Use authorized test
credentials through the environment and review the fixture first:

```sh
node scripts/migration-tests/verify-live-migration.mjs /path/to/migrated-fixture
# The deterministic Stagehand v3 fixture has one acceptance run, not two:
node scripts/migration-tests/verify-live-migration.mjs /path/to/stagehand3-fixture stagehand
```

Do not use that success verifier for either blocked Stagehand case. Stagehand v4
has a separate opt-in compatibility probe in its recorded migration. The AI
fixture needs a real model credential or configured gateway before its unchanged
acceptance can establish AI behavior. Source-provider credentials alone do not
resolve this dependency.

A further fresh-context Hyperbrowser evaluation used the revised skill. It passed
unchanged live acceptance with exactly two creation attempts, two created
sessions, and both confirmed closed. The earlier HTTP 422 issue did not recur.
The parent reran its eight mocked lifecycle checks; it did not repeat another
live run for this recheck.
