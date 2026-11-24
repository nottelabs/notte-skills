# Kernel to Notte

Reviewed 2026-09-21; timeout and profile rows rechecked live on 2026-11-24 with
`notte-sdk` 1.10.15. These are migration mappings, not a complete API reference.
Check installed versions and the linked docs before editing.

## Detect

Look for `@onkernel/sdk`, Python `kernel`, `KERNEL_API_KEY`, `browsers.create`,
`cdp_ws_url`, `webdriver_ws_url`, and custom Kernel API base URLs. Inspect wrappers
and Kernel app entrypoints as well as direct SDK calls.

## Map the browser boundary

| Kernel surface | Notte replacement or decision |
|---|---|
| TypeScript `kernel.browsers.create()` / Python `kernel.browsers.create()` | Create a Notte Session; keep the existing automation client. |
| `session_id` and `cdp_ws_url` | Notte session ID and SDK-provided CDP URL; see [shared examples](notte-sessions.md). |
| TS `browsers.deleteByID(id)` / Python `browsers.delete_by_id(id)` | Stop the Notte session independently of disconnecting the automation client. |
| `profile: {name/id, save_changes}` | Create/map a Notte profile ID and preserve write intent with `profile: {id, persist}`. Source IDs and names are not portable. A Kernel profile archive (full user-data dir) cannot be imported; move cookies and web storage with [authentication state](authentication-state.md). |
| `timeout_seconds` (inactivity, up to 72 h) | `idle_timeout_minutes`, max 30. On Kernel an open CDP connection counts as activity; on Notte it does not: a quiet connection was closed at the 3-minute default idle timeout in a live check, while a CDP `Runtime.evaluate` every 60 s kept the session alive. Set the idle timeout explicitly, or add a keepalive only if the user accepts the extra traffic. Required idle periods above 30 min are **Blocked**. |
| Standby (no billing while idle) | No equivalent. Pause/resume is not available on production workspaces without a feature flag (409). **Blocked** when required. |
| `region` | No region selection on Notte. **Blocked** when required. |
| `extensions` | No Chrome extensions on Notte. **Blocked** when the workflow depends on one. |
| GPU, `headless`, `kiosk_mode` | No equivalent session options. Record them as gaps rather than dropping them silently. |
| `webdriver_ws_url` / WebDriver BiDi | Separate compatibility check. A CDP URL is not a WebDriver/BiDi endpoint. |
| Browser pool acquire/release | Notte has no browser pools. Verify lease, queue wait, warm capacity, and release semantics, then choose an application-side queue or record the gap. |

Kernel has distinct control modes: CDP, remote Playwright execution, OS-level
computer controls, and WebDriver BiDi. Only the CDP path is a browser-connection
swap. Remote execution runs code in the browser VM; moving it into the application
changes locality, dependencies, filesystem access, serialization, and latency.
Preserve return/error contracts and measure when those properties matter.

Kernel profile saves replace a snapshot rather than merge concurrent updates.
Record which worker owns writes. Loading a profile into an already running Kernel
browser restarts Chromium; do not assume Notte has the same hot-load API. Prefer
attaching the mapped profile on creation and validate the second session with
[authentication state](authentication-state.md).

Treat Managed Auth, computer controls, apps/invocations, SSH/processes, private
networking, and VM files as separate capabilities. A Notte Profile is not an
automatic substitute for a managed login service, nor is a browser Function a
replacement for arbitrary VM compute.

## Fetch only when needed

- [Control modes](https://kernel.sh/docs/introduction/control): determine whether the source uses CDP or a different execution model.
- [Profile save/reuse](https://kernel.sh/docs/browsers/profiles/save-and-reuse) and [concurrency](https://kernel.sh/docs/browsers/profiles/concurrency): map persistence and writers.
- [Playwright execution](https://kernel.sh/docs/browsers/playwright-execution): inspect runtime and return contracts when used.
- [File I/O](https://kernel.sh/docs/browsers/file-io): map remote paths and downloads when used.
- [Docs index](https://www.kernel.sh/docs/llms.txt): locate exact APIs for other detected features.
- [Pricing](https://www.kernel.sh/docs/info/pricing): fetch only for a requested cost comparison; distinguish browsers, pools, runtime, auth, and storage.
