# Session payments

These commands require a CLI release with the `payment` command and an API
with payments enabled. Sandbox (`--mode test`) is the default; live spending
requires separate server-side enablement.

```bash
notte payment request --session-id "$SESSION_ID" --amount 100 --currency usd \
  --merchant-url https://example.com --merchant-name Example \
  --description "Buy one sandbox item for this browser session, with a maximum total of one US dollar including all applicable fees." \
  --idempotency-key "$REQUEST_KEY" -o json
notte payment status "$PAYMENT_ID" -o json
notte payment wait "$PAYMENT_ID" --wait-timeout 10m -o json
```

Use a unique `REQUEST_KEY` for each intended purchase. Reuse it with the same
inputs after an uncertain response. Without this option, the CLI generates a
key and prints it on stderr. The request response contains the payment `id`.
Amounts are integer minor units (100 minor units in USD = $1.00), from 1 to 50000. Descriptions
must contain 100 to 4000 characters. Merchant URLs must use HTTPS without URL
credentials.

No separate wallet-connect command is required. On first use, send the user the
`connection_url` and `connection_phrase`. Once connected, send the user the
`approval_url` from the updated status. The user controls wallet connection and
spending approval. Do not treat a browser redirect as proof of approval.

`wait` polls the backend and prints new connection/approval instructions on
stderr. In JSON mode, stdout contains one final payment object when ready.
A declined, expired, failed, or closed payment exits nonzero, as does a wait
timeout. Ending the CLI does not cancel provisioning. Resume waiting with the
same payment ID rather than creating another request.

Wait for `ready` before continuing checkout. It means temporary credentials are
installed in the session vault, not that a merchant was paid. Use the existing
card placeholders through the execution layer; do not request or print raw card
numbers, security codes, or wallet tokens. Existing login credentials remain in
the vault. An occupied card slot is rejected instead of overwritten. Verify the
merchant purchase separately.
