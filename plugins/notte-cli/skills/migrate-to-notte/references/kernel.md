# Kernel

Search: `kernel|@onkernel|browsers\.create|cdp_ws_url|webdriver_ws_url|Computer Controls|Managed Auth|browser pool`.

| Surface | Candidate Notte design | Verify |
|---|---|---|
| Browser/CDP/WebDriver session | Notte Session; CDP or Selenium only when required | tabs, waits, disconnect, capabilities |
| Remote Playwright VM | generated workflow or app-side CDP code | locality, dependencies, return/error contract |
| Computer Controls | observed deterministic controls; bounded agent for ambiguity | viewport/DPR, coordinates, idempotency |
| Profiles/Managed Auth | Profile, Vault, Persona, or human login | MFA, rotation, consent, audit |
| Pool acquire/release | Browser Pool or application queue | warm capacity, lease, queue wait |
| Apps/invocations/files/processes | Function or application service | sync/async contract, timeout, artifacts/logs |

Read: <https://www.kernel.sh/docs/llms.txt>,
<https://www.kernel.sh/docs/info/pricing>,
<https://docs.notte.cc/quickstart>. Price headless/headful/GPU, pools, runtime,
auth, storage, and model usage separately; do not equate remote VM execution to
a browser session.
