# Hyperbrowser

Search: `hyperbrowser|HYPERBROWSER_|hyperagent|browser.?use|computer.?use|scrape|crawl|extract|fetch|search|sandboxes?|x402`.

| Surface | Candidate Notte design | Verify |
|---|---|---|
| Session/CDP framework | Session; generated workflow then CDP when needed | cleanup, contexts, events, timeout |
| Fetch/Scrape/Extract/Crawl/Search jobs | typed scrape/search or deterministic workflow | async polling, pagination, schema, billing |
| HyperAgent/action cache | deterministic generated code; bounded Agent fallback | cache invalidation, tokens, steps, retry |
| Browser Use/computer-use task | preserve async task/callback contract | cancel/status/human handoff |
| Profile/proxy/stealth/CAPTCHA | Profile and capability after target test | IP/geo, access rate, policy |
| Files/extensions/recordings/live view | File Storage/viewer/replay | retention, embed, artifacts |
| Sandbox/volume/custom image/X402 | retain or separately redesign runtime/payment architecture | filesystem, processes, networks, payment/idempotency |

Read: <https://hyperbrowser.ai/docs/llms.txt>,
<https://hyperbrowser.ai/docs/pricing>, <https://docs.notte.cc/quickstart>.
