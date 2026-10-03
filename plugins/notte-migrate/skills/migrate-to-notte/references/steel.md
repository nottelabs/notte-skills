# Steel to Notte

Reviewed 2026-09-21. Identify hosted versus self-hosted Steel and the installed
SDK before mapping its sessions.

## Detect and map

Look for `steel-sdk`, Python `steel`, `STEEL_API_KEY`, `steelAPIKey`,
`connect.steel.dev`, custom API/WebSocket base URLs, `sessionContext`,
`profileId`, and `sessions.release`.

| Source surface | Notte replacement or decision |
|---|---|
| `client.sessions.create(...)` | Create a Notte Session with mapped settings. |
| `wss://connect.steel.dev?apiKey=...&sessionId=...` | Use the Notte SDK's returned CDP URL unchanged. Never reuse Steel query parameters or log the URL. |
| `client.sessions.release(id)` | Stop the Notte session even after a failed connection or workflow. |
| `timeout` / `inactivityTimeout` in milliseconds | Map separately to `max_duration_minutes` / `idle_timeout_minutes`; resolve values not representable in whole minutes explicitly. |
| Python `api_timeout` | Session timeout; do not confuse it with the SDK's HTTP request `timeout`. Confirm the installed signature. |
| `profileId`, `persistProfile` | Create/map a Notte profile ID and attach with `profile: {id, persist}`. |
| `sessions.context(id)` and `sessionContext` | Export/import supported state explicitly using [authentication state](authentication-state.md); this is not a portable full profile. |
| `useProxy`, `proxyUrl`, `solveCaptcha` | Map proxy/challenge intent to Notte `proxies` and `solve_captchas`; verify exact schema and behavior. |

Steel's current docs recommend constructing the authenticated connection URL
rather than using `session.websocketUrl` directly. Detect both patterns in older
code, but generate neither for Notte. Disconnecting a client is distinct from
releasing its provider session; use the [shared lifecycle examples](notte-sessions.md).

Steel context export captures cookies and local storage from a live session.
Capture required state before release, and do not treat the resulting JSON as
Playwright storage state without checking its schema. The full Profiles API is a
separate feature. A profile ID, dedicated IP ID, extension ID, or stored credential
ID cannot be transferred simply by copying the identifier.

For routing, distinguish browser compute region from proxy egress geography.
Preserve intentional proxy overrides and browser/mobile fingerprint requirements.
Notte proxy defaults are not evidence of the same region or network identity.

Self-hosted Steel may rely on private networking, persistent disks, custom Chrome,
local process access, or unrestricted extensions. Assess those before proposing
cloud sessions. Browser Tools, credentials, files, and Agent Traces also need
separate output, access-control, and retention mappings; a Notte replay URL is not
a replacement for an application consuming Steel's trace schema.

## Fetch only when needed

- [Session configuration](https://docs.steel.dev/overview/sessions-api/configuration): units, profile flags, proxy precedence, and current region constraints.
- [Lifecycle](https://docs.steel.dev/overview/sessions-api/session-lifecycle) and [Playwright](https://docs.steel.dev/integrations/playwright): source connection and release contracts.
- [Auth context](https://docs.steel.dev/overview/sessions-api/reusing-auth-context) and [Profiles](https://docs.steel.dev/overview/profiles-api/overview): choose a state migration path.
- [Docs index](https://docs.steel.dev/llms.txt): exact file, trace, extension, or self-hosting APIs when detected.
- [Pricing and limits](https://docs.steel.dev/overview/pricinglimits): current costs/quotas when requested.
