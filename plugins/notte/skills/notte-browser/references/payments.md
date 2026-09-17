# Session payments

To try a dev/test payment, use `--mode test`.

Connect the user's wallet first, using the same mode as the payment:

```bash
notte payment connect --mode test -o json
```

If `status=awaiting_connection`, send `connection_url` and `connection_phrase`
to the user and let them authorize. Notte detects completion in the background.
Run `connect` again to confirm `connected` or retrieve the pending link; it reuses
the connection. No session is needed and there is no separate connection-status
command. Only the authenticated wallet owner can use the connection.

Once connected, request spending:

```bash
notte payment request --session-id "$SESSION_ID" --mode test --amount 1.00 --currency usd \
  --merchant-url https://example.com --merchant-name Example \
  --description "Buy one sandbox item for this browser session, with a maximum total of one US dollar including all applicable fees." \
  --idempotency-key "$REQUEST_KEY" -o json
notte payment status "$PAYMENT_ID" -o json
notte payment wait "$PAYMENT_ID" --wait-timeout 10m -o json
```

Use a unique `REQUEST_KEY` for each intended purchase. Reuse it with the same
inputs after an uncertain response. Without this option, the CLI generates a
key and prints it on stderr. The request response contains the payment `id`.
Amounts are in currency units: `100.91` with `--currency usd` means USD 100.91.
The maximum is USD 500.00 for USD requests; other currencies have corresponding
limits of 50,000 minor units. Fractional amounts unsupported by the currency are
rejected without rounding. Descriptions
must contain 100 to 4000 characters. Merchant URLs must use HTTPS without URL
credentials.

`request` fails with `wallet_not_connected` if connection is incomplete. Run
`connect` and complete authorization before retrying; no payment was created by
that rejection. A successful request returns the payment ID and spending approval
URL (or briefly `creating`; use `status` to retrieve the URL when available).

Send `approval_url` to the user **before starting a blocking wait**. The user must
approve the spending request. Then use `payment wait` on the same payment ID.
Do not create another request to advance an existing payment. Never treat a browser
redirect as proof of approval.

`wait` prints approval/verification instructions on stderr. In JSON mode, stdout
contains one final payment object when ready. Agents whose command tools buffer
stderr until exit must use `payment status -o json` to obtain and relay any further
verification URL before continuing to wait.
A declined, expired, failed, or closed payment exits nonzero, as does a wait
timeout. Ending the CLI does not cancel provisioning. Resume waiting with the
same payment ID rather than creating another request.

Wait for `ready` before continuing checkout. It means temporary credentials are
installed in the session vault, not that a merchant was paid. Use the existing
card placeholders through the execution layer; do not request or print raw card
numbers, security codes, or wallet tokens. Existing login credentials remain in
the vault. An occupied card slot is rejected instead of overwritten. Verify the
merchant purchase separately.

## Switch wallet accounts

To connect a different account in the same mode, disconnect the current wallet first:

```bash
notte payment disconnect -o json
notte payment connect -o json
```

Disconnect revokes and forgets only the selected mode's connection; the other
mode is unaffected. Use `--mode test` for a test wallet. Omitting `--mode` uses
the API default (live). A successful disconnect returns `status=disconnected` and the
affected `mode`.

If the API returns `wallet_has_active_payments`, let active payments and card
cleanup finish before retrying. Do not disconnect as a way to advance a pending
payment. After reconnecting, relay the new connection URL and phrase to the user
and confirm `connected` before requesting spending.

## Example: complete a merchant checkout

As the agent, use `--vault-field` to fill card fields from the session vault.
The CLI sends Notte's placeholder for the selected field; Notte replaces it with
the stored card value at execution time, before filling the merchant's form.
Do not retrieve or pass the issued card values yourself.

| Checkout field | `--vault-field` value |
| --- | --- |
| Card number | `card_number` |
| Cardholder name | `card_holder_name` |
| Expiration (month/year) | `card_expiration` |
| CVV/CVC | `card_cvv` |

These fields work with an approved payment in either mode. Do not supply a literal
value alongside `--vault-field`.

For example, after the user asks you to buy an item, use the existing session
containing their cart. Inspect checkout to establish the merchant and final total,
including shipping and taxes. This example assumes an authorized USD 35.00 order.
Set `CHECKOUT_URL` to the merchant's actual checkout URL and `MERCHANT_NAME` to its
name. The selectors below illustrate a form with standard autocomplete attributes
and a combined expiration field; use the actual fields and submit button from
`observe`, including the relevant iframe when the payment form is embedded.

```bash
# Inspect the checkout in the same session that holds the cart.
notte page goto --session-id "$SESSION_ID" "$CHECKOUT_URL"
notte page observe --session-id "$SESSION_ID"

# Connect first. Relay the URL/phrase, then re-run to confirm connected.
notte payment connect -o json

# Only after connected, request the spending approval for this order.
PAYMENT_ID=$(notte payment request --session-id "$SESSION_ID" \
  --amount 35.00 --currency usd \
  --merchant-url "$CHECKOUT_URL" --merchant-name "$MERCHANT_NAME" \
  --description "Purchase the item in the user's current shopping cart, with an authorized total of USD 35.00 including shipping and taxes, after explicit wallet approval." \
  --idempotency-key "$REQUEST_KEY" -o json | jq -er '.id')

# Relay approval_url to the user before waiting. They approve the spending.
notte payment status "$PAYMENT_ID" -o json
notte payment wait "$PAYMENT_ID" --wait-timeout 10m -o json
```

Continue only after `wait` succeeds with `status=ready`. If waiting times out,
resume waiting on this payment ID. If wallet verification is required, relay
`next_action` to the user: `auto_resume` continues on the same request; other
resolutions require completing the action and explicitly requesting payment again
with a new idempotency key. Do not fill or submit checkout while approval or
verification is pending.

```bash
# Refresh the page observation, then fill with placeholders, not secrets.
notte page observe --session-id "$SESSION_ID"
notte page fill --session-id "$SESSION_ID" 'input[autocomplete="cc-number"]' --vault-field card_number
notte page fill --session-id "$SESSION_ID" 'input[autocomplete="cc-name"]' --vault-field card_holder_name
notte page fill --session-id "$SESSION_ID" 'input[autocomplete="cc-exp"]' --vault-field card_expiration
notte page fill --session-id "$SESSION_ID" 'input[autocomplete="cc-csc"]' --vault-field card_cvv

# Recheck the merchant and total before submitting the authorized order.
notte page observe --session-id "$SESSION_ID"
notte page click --session-id "$SESSION_ID" 'button:has-text("Pay")'

# Verify the merchant's order confirmation, amount, and order reference.
notte page observe --session-id "$SESSION_ID"
```

Complete any merchant authentication requested by the user flow. Report the
purchase as successful only when the merchant confirms it; `payment ready`
proves only that the card was provisioned. If the outcome is uncertain, inspect
the order state before retrying submission to avoid a duplicate purchase.
