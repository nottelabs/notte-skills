# Notte session integration

SDK shapes checked against Python and npm `notte-sdk` 1.9.1 on 2026-09-21. Session
creation, `cdp_url()`/`cdpUrl()`, stop, profiles and the defaults below were
exercised live with 1.10.15 on 2026-11-24.
Recheck the selected release's signatures/types before adapting these examples.
The examples illustrate the browser boundary; they do not establish live feature
parity. Keep the application's existing automation inside that boundary.

## Packages and authentication

| Language | Package/import | Session API |
|---|---|---|
| Python | `notte-sdk`; `from notte_sdk import NotteClient` | `with client.Session(...) as session`, `session.cdp_url()` |
| TypeScript | `notte-sdk`; `import { NotteClient } from "notte-sdk"` | `client.Session(...).use(callback)`, `await session.cdpUrl()` |

Both clients accept `NOTTE_API_KEY` from the environment. Use the application's
existing secret injection. Do not replace a package based on an unverified
marketing snippet: `@notte/sdk`, `client.sessions.start()` and a `cdpUrl` property
are not the API used by these examples.

Keep the installed Playwright/Puppeteer package and its compatible version. A
remote CDP connection does not require downloading another local Chromium. CDP
is a Chromium connection protocol, not a WebDriver endpoint or a guarantee of
all browser-engine features. Verify the selected browser type accordingly.

## Python: existing synchronous Playwright

```python
from notte_sdk import NotteClient
from playwright.sync_api import sync_playwright


def read_title(url: str) -> str:
    session = NotteClient().Session(max_duration_minutes=5, idle_timeout_minutes=2)
    session.start()
    playwright = None
    browser = None
    failed = False
    try:
        playwright = sync_playwright().start()
        browser = playwright.chromium.connect_over_cdp(session.cdp_url())
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()
        # Keep the existing workflow and assertions here.
        page.goto(url)
        return page.title()
    except BaseException:
        failed = True
        raise
    finally:
        cleanup_error = None
        cleanups = ([browser.close] if browser else []) + [session.stop]
        if playwright:
            cleanups.append(playwright.stop)
        for cleanup in cleanups:
            try:
                cleanup()
            except BaseException as error:
                if cleanup_error is None:
                    cleanup_error = error
        if cleanup_error is not None and not failed:
            raise cleanup_error
```

Explicit cleanup attempts browser disconnect, provider stop, and Playwright
shutdown independently, while preserving the original workflow exception.
For async Python, preserve the existing async Playwright client; use `async_playwright`, await its operations, and keep
synchronous Notte SDK calls out of latency-sensitive event loops where necessary.
Do not invent `async with client.Session()` or await synchronous SDK methods.
For threaded lifecycle calls, serialize access to the session and test
cancellation and cleanup explicitly.

## TypeScript: existing Playwright

```typescript
import { NotteClient } from "notte-sdk";
import { chromium, type Browser } from "playwright-core";

export async function readTitle(url: string): Promise<string> {
  const session = new NotteClient().Session({ max_duration_minutes: 5, idle_timeout_minutes: 2 });
  await session.start();
  let browser: Browser | undefined;
  let failed = false;
  try {
    browser = await chromium.connectOverCDP(await session.cdpUrl());
    const context = browser.contexts()[0];
    if (!context) throw new Error("Missing default browser context");
    const page = context.pages()[0] ?? await context.newPage();
    // Keep the existing workflow and assertions here.
    await page.goto(url);
    return await page.title();
  } catch (error) {
    failed = true;
    throw error;
  } finally {
    let cleanupFailed = false;
    let cleanupError: unknown;
    for (const cleanup of [() => browser?.close(), () => session.stop()]) {
      try { await cleanup(); } catch (error) {
        if (!cleanupFailed) { cleanupFailed = true; cleanupError = error; }
      }
    }
    if (!failed && cleanupFailed) throw cleanupError;
  }
}
```

## TypeScript: existing Puppeteer

```typescript
import { NotteClient } from "notte-sdk";
import puppeteer, { type Browser } from "puppeteer-core";

export async function readTitle(url: string): Promise<string> {
  const session = new NotteClient().Session({ max_duration_minutes: 5, idle_timeout_minutes: 2 });
  await session.start();
  let browser: Browser | undefined;
  let failed = false;
  try {
    browser = await puppeteer.connect({ browserWSEndpoint: await session.cdpUrl() });
    const context = browser.defaultBrowserContext();
    if (!context) throw new Error("Missing default browser context");
    const page = (await context.pages())[0] ?? await context.newPage();
    // Keep the existing workflow and assertions here.
    await page.goto(url);
    return await page.title();
  } catch (error) {
    failed = true;
    throw error;
  } finally {
    let cleanupFailed = false;
    let cleanupError: unknown;
    for (const cleanup of [() => browser?.disconnect(), () => session.stop()]) {
      try { await cleanup(); } catch (error) {
        if (!cleanupFailed) { cleanupFailed = true; cleanupError = error; }
      }
    }
    if (!failed && cleanupFailed) throw cleanupError;
  }
}
```

The examples own session stop; Puppeteer disconnect alone does not release it.
When the application deliberately reuses a session across jobs, retain its
longer-lived start/stop owner. Keep the session ID in memory for cleanup/status;
do not log the CDP URL.

SDK 1.9.1 `.use()` logs callback exceptions, which can include signed connection
URLs. These examples use explicit lifecycle management to avoid that logging and
preserve a primary error when cleanup also fails. Report secondary cleanup
failures through sanitized application telemetry if needed. Never log a raw
transport exception. The SDK owns rollback when `start()` itself fails; verify
that behavior separately against the selected version.

## Configuration and lifecycle invariants

- Distinguish `max_duration_minutes` from `idle_timeout_minutes`, HTTP request
  timeout, CDP connect timeout, and per-action timeout. Convert seconds or
  milliseconds explicitly; resolve fractional-minute requirements with the user
  or a tested application-side deadline rather than silently changing behavior.
- Set an explicit `idle_timeout_minutes` compatible with the maximum lifetime,
  especially for short sessions. In live SDK 1.9.1 migration tests, a two-minute
  maximum with the default idle timeout was rejected with HTTP 422; explicitly
  setting idle to one or two minutes succeeded. Preserve required idle behavior
  and keep it no greater than the maximum; do not increase the maximum merely
  to bypass validation.
- Access the provider's default context when using its persisted state. An
  additional context is isolated; its cookies/settings are not automatically
  inherited. Preserve multi-context behavior only after testing its requirements.
- Retrieve connection URLs through the SDK. Do not synthesize hosts or copy old
  provider query parameters. Passing an old-provider CDP URL into a Notte Session
  keeps the old host in use and does not complete this migration.
- Cleanup must attempt provider stop even when connection or client cleanup
  fails. Preserve the original application error and record cleanup failures
  separately if necessary. Do not log raw credential-bearing transport errors.
  Test the selected SDK's exception behavior; these small examples do not define
  the application's production error policy.
- `proxies=True` is documented as best-effort US routing and can use nearby
  countries. Use explicit supported routing and verify observed egress when the
  source requires a particular country. Compute region and egress are distinct.
- Map persistence with [authentication state](authentication-state.md).
  CAPTCHA flags, viewport, and stealth settings require tests of the
  actual behavior; none is an automatic guarantee of target-site access.
- An open CDP connection with no traffic does not count as activity, and neither
  does polling session status. A client that holds the connection open and
  waits is closed at the idle timeout (default 3 min). A CDP command such as
  `Runtime.evaluate` resets it. Source code that relied on an open connection to
  keep a browser alive (Kernel) needs an explicit idle timeout or a keepalive.

## Defaults that differ

These defaults change behavior without raising an error. Set each one explicitly
when the source provider behaved differently, and list them in the mapping:

| Option | Notte default | Typical source behavior to check |
|---|---|---|
| `proxies` | `True` (residential, billed per GB) | Direct egress by default on Browserbase and Kernel |
| `block_ads` | `True` | Browserbase `blockAds` defaults to false |
| `dialog_policy` | `"auto"`: dismisses alert, confirm and prompt | Client code that accepts or answers dialogs needs `"client"` |
| `max_duration_minutes` | 15; plan caps 15/120/300 min (Free/Developer/Startup) | Longer source timeouts |
| `idle_timeout_minutes` | 3, max 30 | Long inactivity timeouts, keep-alive |
| `record_session` | `True` | Recording off by default on Kernel and Browser Use |
| `profile.persist` | `False` | Browser Use writes profiles back by default |

## Not available on Notte

Classify as **Blocked** when the application requires them: region selection,
Chrome extensions, a remote WebDriver URL (Selenium/BiDi), browser pools.

The 30-minute cap applies to inactivity, not to session length. A session that
keeps sending CDP commands stays up until `max_duration_minutes`. Classify long
waits by what the application needs:

- More than 30 minutes with no CDP traffic: **Adapt** with a CDP keepalive if the
  user accepts the extra traffic. Pause/resume is an option only if the client
  can reconnect and the workspace and lifetime checks below pass, even if the
  wait starts with an open connection. Otherwise **Blocked**.
- Disconnected gaps of more than 30 minutes (the source used `keepAlive` or
  standby): pause/resume can hold the session, but it returns 409 on production
  workspaces without a feature flag. Per the backend code (expiry not tested
  live), a session lives at most 24 hours from start, paused time included, and
  a workspace can hold at most 10 paused sessions. **Adapt** only when the
  required gap fits that window and a test on the target workspace shows pause,
  resume after a representative gap, and CDP reconnection all working; otherwise
  **Blocked**. The CDP connection drops on pause, so the client must reconnect
  after resume.

## One-URL connect

`wss://api.notte.cc/sessions/connect?token=<NOTTE_API_KEY>&<start fields>`
creates a session when a client connects and stops it within about 3 s of the
disconnect, including when the client process dies. It returns the session ID in
the `X-Session-Id` handshake header. Live-checked with Playwright
`connect_over_cdp` and Puppeteer `connect` on 2026-11-24.

- Use it when the source hard-codes a provider WebSocket URL (for example
  `wss://connect.browserbase.com?apiKey=`) or a third-party tool takes only a URL,
  and each connection can start with a fresh browser. Every connection creates
  a new session, so a tool that disconnects between jobs and expects the same
  browser back loses its tabs and login. In that case, start the session with
  the SDK and pass its CDP URL to the tool.
- Accepted query fields include `proxies`, `max_duration_minutes`,
  `idle_timeout_minutes`, `viewport_width`, `viewport_height`, `solve_captchas`,
  `block_ads`, `dialog_policy` and `user_agent`. Unknown fields are ignored.
- `profile`, proxy lists, headers, `record_session=false` and
  `log_session=false` are refused. Use the SDK for those.
- Every failure, including a bad key or a refused field, is a 403 with an empty
  body. Start from a minimal URL when debugging.
- The URL carries the API key. Never log or commit it.

## Remote downloads

A download event is not evidence that file bytes reached the caller. In a live
check on 2026-09-21 with Python SDK 1.9.1 and Playwright 1.63.0, both data-URL and
blob downloads produced zero-byte files through `download.save_as()`. Retrieving
the same files through Notte's session-file API after stop returned the expected
bytes. Treat direct CDP download behavior as something to verify for the actual
workflow, not a portable provider assumption.

When a download needs adaptation, keep the owning session ID before stopping.
List that session's files with source `session_download`, wait with a bounded
deadline for the expected artifact, and identify the file by the application's
expected metadata rather than selecting the first unrelated download. Python
uses `client.files.list(session_id, source="session_download")` and
`client.files.download(session_id, file_id, local_dir=...)`. TypeScript exposes
`client.Files(sessionId).list({source: "session_download"})` and `.download(fileId)`.
Validate the content, length, or checksum and preserve the caller's filename/path
contract. Test access after stop if the application requires it. Do not delete
application artifacts as part of a production migration test; remove only test
files created by the proof.

## Documentation routing

Fetch only pages relevant to detected usage. Prefer exact feature/API links over
loading the full docs corpus. Keep prices, limits, region lists, retention, and
full option schemas in their maintained source rather than copying them here.
If sources disagree, inspect installed package types/source and mark unresolved
server behavior unverified. A failed docs fetch is not proof a feature is absent.

| Need | Source |
|---|---|
| SDK version/source | [Python package](https://pypi.org/project/notte-sdk/), [npm package](https://www.npmjs.com/package/notte-sdk), [SDK repository](https://github.com/nottelabs/notte) |
| Lifecycle and settings | [Lifecycle](https://docs.notte.cc/features/sessions/lifecycle), [configuration](https://docs.notte.cc/features/sessions/configuration) |
| Framework connection | [Playwright](https://docs.notte.cc/features/sessions/playwright), [Puppeteer](https://docs.notte.cc/features/sessions/puppeteer), [Stagehand compatibility](https://docs.notte.cc/integrations/stagehand) |
| Authentication | [Profiles](https://docs.notte.cc/features/sessions/browser-profiles), [cookies](https://docs.notte.cc/features/sessions/cookies) |
| Network/challenges | [Proxies](https://docs.notte.cc/features/sessions/proxies), [CAPTCHA](https://docs.notte.cc/features/sessions/captcha-solving). There is no region page: region selection is not available |
| Remote files | [Files](https://docs.notte.cc/concepts/file-storage); verify session ownership, upload paths, download availability after stop, and retention |
| Debugging artifacts | [Live view](https://docs.notte.cc/features/sessions/live-view), [recordings](https://docs.notte.cc/features/sessions/recordings); verify access and artifact readiness |
| Optional capabilities | [Functions](https://docs.notte.cc/concepts/functions), [Browser Use](https://docs.notte.cc/integrations/browser-use). Extensions are not available |
| Cost/limits | [Pricing](https://docs.notte.cc/intro/pricing), [rate limits](https://docs.notte.cc/api-reference/rate-limits) |
| Find an API not linked above | [Docs index](https://docs.notte.cc/llms.txt) |
