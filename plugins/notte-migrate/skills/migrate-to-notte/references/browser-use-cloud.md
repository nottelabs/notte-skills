# Browser Use Cloud

Search: `browser-use|browser_use|runs\.create|sessionId|cdpUrl|browserSettings|proxyCountryCode|workspace|live.?url`.

| Surface | Candidate Notte design | Verify |
|---|---|---|
| Hosted run | Agent only for agentic work; generated workflow for stable paths | result/error, cancel, timeout, idempotency |
| Cloud browser/CDP | Session; explicit stop | CDP disconnect, page state, cleanup |
| Text result | typed scrape/Agent with contract test | JSON/schema, null/error handling |
| Follow-up session/profile | live Session or Profile plus app-owned conversation state | which state persists, concurrency, expiry |
| Workspace/files/live view | File Storage and viewer/replay | paths, retention, signed URL, embed |
| Proxy | region/proxy configuration after like-for-like test | default proxy, country, GB/cost |

Read: <https://docs.browser-use.com/llms.txt>,
<https://browser-use.com/pricing>, <https://docs.notte.cc/quickstart>. Cloud API
versions differ; verify the installed version and explicit stop behaviour.
