# Hyperbrowser to Notte

Reviewed 2026-09-21. Hyperbrowser documents current Python 1.0+ and legacy Python
examples separately; match the application's installed release.

## Detect and map

Look for `@hyperbrowser/sdk`, Python `hyperbrowser`, `HYPERBROWSER_API_KEY`,
`wsEndpoint`, `ws_endpoint`, `HyperAgent`, and Hyperbrowser API hostnames. Search
for scrape/crawl/agent calls within identified wrappers, not as proof of a
provider by themselves.

| Source surface | Notte replacement or decision |
|---|---|
| `client.sessions.create(...)` | Notte Session; preserve the framework and sync/async execution model. |
| TS `session.id`, `wsEndpoint` / Python `id`, `ws_endpoint` | Notte ID/CDP URL from the [shared integration](notte-sessions.md). |
| `client.sessions.stop(id)` | Notte session stop, guaranteed independently of CDP cleanup. |
| `timeoutMinutes` / `timeout_minutes` | Maximum lifetime maps to `max_duration_minutes`, not inactivity timeout. |
| `screen.width/height` | `viewport_width` / `viewport_height`; verify actual viewport, device scale, and screenshots. |
| `profile: {id, persistChanges}` / Python `persist_changes` | New Notte profile ID and `profile: {id, persist}`; preserve read/write intent. |
| `useProxy`, country/stealth/CAPTCHA options | Map required routing and behavior with current schemas; do not assume flag parity. |

Hyperbrowser normally stops a session when its automation client disconnects.
Its `keepAlive=true` CDP query parameter changes this, but closing all pages still
stops the session. Do not append this provider-specific parameter to a Notte URL.
Make ownership, reconnect, explicit stop, and maximum lifetime clear in the new
adapter and validate those paths.

Profile saving can take time after stop. Do not interpret an immediate failed
reuse as proof that persistence is unsupported. Use provider readiness signals
where available and bounded retries, then verify Notte behavior separately with
[authentication state](authentication-state.md).

HyperAgent, Browser Use/computer-use tasks, Fetch/Scrape/Extract/Crawl/Search,
sandboxes, volumes, custom images, and x402 are not all session APIs. Preserve job
status/polling/cancellation, callback schemas, extraction schemas, model/cache
behavior, filesystem, and payment contracts before proposing replacements. Keep
an existing external agent framework when compatible with Notte CDP.

## Fetch only when needed

- [Lifecycle](https://www.hyperbrowser.ai/docs/sessions/lifecycle): connection ownership, keep-alive, timeout, and SDK versions.
- [Profiles](https://hyperbrowser.ai/docs/sessions/profiles): save timing and profile operations.
- [Parameters](https://hyperbrowser.ai/docs/sessions/parameters) and [proxies](https://hyperbrowser.ai/docs/sessions/proxy): map only options the application uses.
- [Docs index](https://hyperbrowser.ai/docs/llms.txt): find exact managed-agent, file, job, and sandbox APIs when used.
- [Pricing](https://hyperbrowser.ai/docs/pricing): fetch current rates and limits for requested cost comparisons.
