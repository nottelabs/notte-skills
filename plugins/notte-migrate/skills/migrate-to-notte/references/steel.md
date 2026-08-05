# Steel

Search: `steel-sdk|STEEL_API_KEY|steel\.dev|sessions\.(create|release)|connect\.steel|scrape\(|profiles|credentials|agent.?traces`.

| Surface | Candidate Notte design | Verify |
|---|---|---|
| Session/WebSocket | Session; generated workflow or CDP framework connection | cleanup, contexts/pages, events |
| Scrape/Browser Tools | typed scrape or deterministic workflow | rendered output, status/error, billing |
| Profile/Credentials | Profile/Vault/Persona | isolation, expiry, MFA, rotation |
| Files/extensions | File Storage/session extension | paths, MIME/size, retention |
| Proxy/region/mobile/CAPTCHA | capability after target test | identity, CAPTCHA type, access rate |
| Live/past session/Agent Traces | viewer/replay + application telemetry | embed, retention, compliance |
| Self-hosted cluster | separate architecture decision | locality, tenancy, operations |

Read: <https://docs.steel.dev/llms.txt>,
<https://docs.steel.dev/overview/pricinglimits>, <https://docs.notte.cc/quickstart>.
