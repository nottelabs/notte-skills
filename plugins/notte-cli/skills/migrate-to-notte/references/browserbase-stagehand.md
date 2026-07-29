# Browserbase + Stagehand

Search: `browserbase|stagehand|BROWSERBASE_|STAGEHAND_|@browserbasehq|modelGateway|contextId`.

| Surface | Candidate Notte design | Verify |
|---|---|---|
| Browserbase session/CDP | Notte Session; generated workflow first, CDP only when needed | lifecycle, pages/tabs, disconnect, timeout |
| Stagehand `act`/`observe` | CLI-observed deterministic workflow | target, waits, fallback, cost |
| Stagehand `extract` | typed Notte scrape | schema, nullability, bad output |
| Stagehand agent | bounded Notte Agent/Fallback | steps, tokens, result, retry |
| Context/credentials | Notte Profile/Vault/Persona | persistence, MFA, ownership |
| Functions/Fetch/Search | Function or scrape/search only after output/billing comparison | caller contract, idempotency, rate/cost |

Read: <https://docs.browserbase.com/llms.txt>,
<https://docs.stagehand.dev>, <https://docs.notte.cc/llms.txt>,
<https://docs.notte.cc/quickstart>. Price browser, proxy, model, and API/runtime
charges independently; a Stagehand-over-Notte CDP bridge is temporary, not a
completed removal.
