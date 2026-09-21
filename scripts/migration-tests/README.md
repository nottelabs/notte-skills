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

Live probes use only temporary Notte sessions, synthetic state, and a public
read-only target. No source-provider credentials or real authenticated account
were used. Session cleanup was checked; temporary profiles were deleted.

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
| Source-provider-to-Notte state transfer | Unverified: source credentials and representative application needed. |
| Real login/MFA, tenant isolation, other proxy configurations, CAPTCHA, extensions, replay/embed permissions | Unverified; require representative targets/accounts and feature configuration. |
| Kernel VM execution, managed agents/jobs, self-hosted/private-network workflows | Contract assessment only; application/runtime fixtures and access needed. |
| Cost/performance parity | Unverified; needs workload telemetry/invoices and equivalent source-provider runs. |

To finish live provider comparisons, supply configured secret paths/account
references for Notte, Kernel, Browserbase (including project ID), Hyperbrowser,
and Steel. Use test projects and representative source repositories, locked SDK
versions, permitted target URLs/test accounts, enabled features, and a bounded
session/proxy budget. Do not put API keys or authentication state into fixtures,
chat, or committed evidence.
