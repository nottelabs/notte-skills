# Anchor Browser

Search: `anchorbrowser|ANCHOR(?:BROWSER)?_|agentTask|perform-web-task|/v[12]/tasks|cdp_url|live_view_url|workflow.*json|cleanupSessions`.

| Surface | Candidate Notte design | Verify |
|---|---|---|
| Session/CDP/live view | Session and generated workflow; CDP only when needed | lifecycle, viewer permissions, tabs |
| `agentTask` / task workflow | deterministic workflow first; bounded Agent if needed | step/model cost, schema, retry, human handoff |
| Automation/Code Tasks | Function or application runtime | graph/branching, async polling, schedules, rollback |
| Profile/identity/MFA | Profile + Vault/Persona or human flow | secret boundary, expiry, audit |
| Batch/events | bounded application orchestration | cancellation, partial failure, queue visibility |
| Proxy/CAPTCHA/files/extensions | Notte capability only after target testing | IP continuity, MIME/retention, support |

Read: <https://docs.anchorbrowser.io/llms.txt>,
<https://docs.anchorbrowser.io/pricing>, <https://docs.notte.cc/quickstart>.
Price creation, minute rounding, proxy/egress, AI/BYOK, and task charges apart.
