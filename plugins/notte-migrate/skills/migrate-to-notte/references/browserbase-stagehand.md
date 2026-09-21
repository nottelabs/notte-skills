# Browserbase and Stagehand to Notte

Reviewed 2026-09-21. Read the installed SDK/framework versions before choosing a
migration path. Browserbase infrastructure and the Stagehand framework are
separate dependencies.

## Detect and map

Look for `@browserbasehq/sdk`, Python `browserbase`, `BROWSERBASE_API_KEY`,
`BROWSERBASE_PROJECT_ID`, `connectUrl`, `connect_url`, `REQUEST_RELEASE`,
`@browserbasehq/stagehand`, Python `stagehand`, and Browserbase hostnames.

| Source surface | Notte replacement or decision |
|---|---|
| `sessions.create({projectId, ...})` / Python keyword equivalent | Notte Session with mapped options and `NOTTE_API_KEY`. Do not copy the Browserbase project ID into Notte. |
| TS `connectUrl` / Python `connect_url` | SDK-provided Notte CDP URL; keep Playwright/Puppeteer logic. |
| `sessions.update(id, {status: "REQUEST_RELEASE", ...})` | Stop Notte explicitly, including when CDP connection fails. |
| `timeout` in seconds | Map maximum lifetime to `max_duration_minutes`; validate non-whole minutes rather than silently rounding. Python SDKs may call the session field `api_timeout`. |
| `keepAlive` | Map intended disconnect/reconnect behavior; there is no assumed identical Notte flag. Test both disconnect and explicit stop. |
| `browserSettings.context: {id, persist}` | Create/map a Notte profile and use `profile: {id, persist}`. Distinguish a persistent Browserbase Context from a Playwright BrowserContext. |
| Proxy/region/CAPTCHA settings | Map actual routing and challenge requirements; option names and plan defaults are insufficient evidence. |

For saved login state, use [authentication state](authentication-state.md). A new
Playwright context does not automatically inherit a provider's persisted profile.

## Stagehand compatibility gate

Check [Notte's Stagehand integration](https://docs.notte.cc/integrations/stagehand)
and the installed Stagehand release before editing the application.

As documented on 2026-09-21, Stagehand v4 initialization requires
`Extensions.loadUnpacked`, which Notte Cloud rejects. The integration page reports
this for Python and TypeScript, with no client-side skip flag. Treat required v4
support as blocked unless current documentation and a representative test show
that this restriction has been resolved. Do not downgrade, remove Stagehand, or
rewrite `act`/`extract`/agent logic without the user's decision.

Older tutorials use `env: "LOCAL"` and `localBrowserLaunchOptions`; these are not
universal APIs across versions or Python packages. A supported Stagehand version
using Notte as its actual browser host can complete a Browserbase infrastructure
migration while retaining Stagehand. Verify any remaining Browserbase API/model
or hosted-service usage and disclose it separately.

If the user chooses a framework rewrite, map structured extraction schemas,
nullability, model settings, action cache, step limits, retries, and human handoff
explicitly. That is additional work, not a silent part of changing the CDP URL.

## Fetch only when needed

- [Create session](https://docs.browserbase.com/reference/api/create-a-session) and [release session](https://docs.browserbase.com/reference/api/update-a-session): exact lifecycle/options for the installed SDK.
- [Contexts](https://docs.browserbase.com/platform/browser/core-features/contexts): persistence timing, state, and context reuse.
- [Stagehand docs](https://docs.stagehand.dev): version-specific connection and framework contracts.
- [Browserbase docs index](https://docs.browserbase.com/llms.txt): locate file, proxy, replay, Functions, Fetch, or Search APIs only if detected.
- [Pricing](https://www.browserbase.com/pricing): current costs/quotas when requested; keep browser, model, proxy, and hosted API charges separate.
