# Skyvern

Search: `skyvern|SKYVERN_|launch_cloud_browser|page\.(act|extract|validate|prompt)|run_task|data_extraction_schema|run_with.*code|webhook`.

| Surface | Candidate Notte design | Verify |
|---|---|---|
| Cloud browser/Playwright page | Session; generated workflow then CDP only as needed | page/tab, timeout, cleanup |
| `act`/prompt action | observed deterministic workflow | action, fallback, retry, model cost |
| typed extract/validation | typed scrape and contract test | required/nullable/partial output |
| agent task/UI workflow | deterministic workflow first; bounded Agent if needed | steps, terminal status, scheduling, run history |
| code cache | versioned generated code plus tested fallback | invalidation, first-run cost, branch coverage |
| session/profile/vault/2FA | Profile, Vault/Persona, or human flow | no cookie export, MFA, audit, IP binding |
| proxy/CAPTCHA/files/artifacts | target-tested capability and app telemetry | geo/IP, retention, artifact/trace needs |
| async task/webhook/self-hosted | preserve caller/runtime architecture | run ID, HMAC, retry/dedupe, private network |

Read: <https://www.skyvern.com/docs/llms.txt>,
<https://www.skyvern.com/docs/developers/getting-started/quickstart>,
<https://docs.notte.cc/quickstart>. Price action/credits, browser minutes,
code-cache fallback, proxy, and model usage separately.
