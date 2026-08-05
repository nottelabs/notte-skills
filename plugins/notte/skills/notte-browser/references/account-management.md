---
name: account-management
description: Guide to managing personas and vaults for authentication
---

# Account Management Reference

Complete guide to managing personas and vaults for authentication and identity management.

## Overview

Notte provides two complementary systems for managing identities and credentials:

| Feature | Personas | Vaults |
|---------|----------|--------|
| Purpose | Auto-generated test identities | Store your own credentials |
| Email | Platform-generated inbox | Your email addresses |
| Credentials | Auto-managed | User-provided |
| Use case | Testing, signups | Login to existing accounts |

## Notte Personas

Personas are auto-generated identities with real email addresses. Perfect for:
- Testing signup flows
- Creating test accounts
- Receiving verification codes
- End-to-end testing

### Creating Personas

```bash
# Basic persona (email only)
notte personas create

# With associated vault for credentials
notte personas create --create-vault

# With a phone number - GATED, see below
notte personas create --create-phone-number
```

> **`--create-phone-number` is gated and will fail on a standard account.**
> Phone-number provisioning is unlocked per-account by the Notte team. Treat a
> failure here as an account entitlement, not a transient error - do not retry
> or attempt a workaround. To request access, book a 15-minute call at
> <https://cal.com/pintoa/15mins>. Until it is unlocked, personas have an email
> inbox only, and `notte personas sms` has nothing to return.

### Managing Personas

```bash
# List all personas
notte personas list

# With pagination and filters
notte personas list --page 1 --page-size 20 --only-active

# View persona details
notte personas show --persona-id <persona-id>

# Delete persona
notte personas delete --persona-id <persona-id>
```

### Receiving Emails

Personas have real email inboxes that receive messages:

```bash
# List emails received by persona
notte personas emails --persona-id <persona-id>
```

Example response:
```json
{
  "emails": [
    {
      "id": "email_123",
      "from": "noreply@example.com",
      "subject": "Verify your email",
      "received_at": "2024-01-15T10:30:00Z",
      "body": "Your verification code is: 123456"
    }
  ]
}
```

### Receiving SMS (gated feature)

Requires a persona created with `--create-phone-number`, which is unlocked
per-account by the Notte team. Book a call at <https://cal.com/pintoa/15mins> to
request access. If it is not unlocked, tell the user plainly and fall back to an
email-based verification flow where the target site supports one.

```bash
# List SMS messages
notte personas sms --persona-id <persona-id>
```

Example response:
```json
{
  "messages": [
    {
      "id": "sms_456",
      "from": "+1234567890",
      "body": "Your verification code is 789012",
      "received_at": "2024-01-15T10:31:00Z"
    }
  ]
}
```

### Persona Workflow Example

```bash
# Create persona for testing
PERSONA=$(notte personas create --create-vault -o json)
PERSONA_ID=$(echo "$PERSONA" | jq -r '.id')
EMAIL=$(echo "$PERSONA" | jq -r '.email')

# Start browser session
notte sessions start

# Fill signup form
notte page goto "https://example.com/signup"
notte page observe
notte page fill "I1" "$EMAIL"
notte page click "B1"

# Wait for verification email
sleep 10

# Get verification code from email
CODE=$(notte personas emails --persona-id "$PERSONA_ID" -o json | \
  jq -r '.emails[0].body' | \
  grep -oE '[0-9]{6}')

# Enter verification code
notte page observe
notte page fill "I1" "$CODE"
notte page click "B1"

# Cleanup
notte sessions stop
```

## User-Provided Vaults

Vaults store your own credentials for automated login to existing accounts.

### Creating Vaults

```bash
# Create vault
notte vaults create --name "Work Accounts"
```

### Managing Vaults

```bash
# List vaults
notte vaults list

# With pagination and filters
notte vaults list --page 1 --page-size 20 --only-active

# Update vault name
notte vaults update --vault-id <vault-id> --name "Personal Accounts"

# Delete vault
notte vaults delete --vault-id <vault-id>
```

## Credential Management

### Adding Credentials

Store credentials for specific URLs:

```bash

# Add credentials email
notte vaults credentials add \
  --vault-id <vault-id> \
  --url "https://example.com" \
  --email "user@example.com" \
  --password "$MYSITE_PASSWORD"

# With username (for sites that use username instead of email)
notte vaults credentials add \
  --vault-id <vault-id> \
  --url "https://example.com" \
  --username "myusername" \
  --password "$MYSITE_PASSWORD"

# With MFA secret for TOTP
notte vaults credentials add \
  --vault-id <vault-id> \
  --url "https://example.com" \
  --email "user@example.com" \
  --password "$MYSITE_PASSWORD" \
  --mfa-secret "EXAMPLEMFASECRET"   # placeholder — replace with your real base32 TOTP seed
```

> **Security note:** `--password` and `--mfa-secret` have no stdin or file-based
> alternative, so whatever you pass lands in `argv`, where `ps` can read it.
> Expanding from an environment variable (as shown above) keeps the literal
> secret out of your **shell history** and out of committed files, but the shell
> expands it before `exec`, so it does **not** hide the value from `ps`. Add each
> credential to the vault **once**, from a machine and shell you control, then
> rely on the vault and sentinel placeholders so the secret never crosses `argv`
> again. Avoid running these commands on shared or multi-tenant hosts.

### Listing Credentials

```bash
notte vaults credentials list --vault-id <vault-id>
```

Note: Passwords are not returned in list output for security.

### Getting Credentials for a URL

```bash
notte vaults credentials get --vault-id <vault-id> --url "https://example.com"
```

Returns credentials matching the URL.

### Deleting Credentials

```bash
notte vaults credentials delete --vault-id <vault-id> --url "https://example.com"
```

## MFA/TOTP Support

When you add an `--mfa-secret`, Notte can automatically generate TOTP codes:

```bash
# Add credentials with MFA secret
notte vaults credentials add \
  --vault-id <vault-id> \
  --url "https://secure.example.com" \
  --email "user@example.com" \
  --password "$SECURE_EXAMPLE_PASSWORD" \
  --mfa-secret "EXAMPLEMFASECRET"   # placeholder — replace with your real base32 TOTP seed

# During automation, TOTP codes are generated automatically
# when the site requests 2FA
```

The MFA secret is the base32-encoded key shown when setting up authenticator apps (usually displayed as a QR code or "manual entry" key).

## Sentinel Placeholders

Credentials do **not** auto-fill on navigation. Attaching a vault to a session
(`notte sessions start --vault-id <vault-id>`) enables *substitution*: you fill
these exact sentinel strings, and Notte swaps in the matching real credential
before the keystrokes reach the page.

| Field    | Sentinel             |
|----------|----------------------|
| email    | `user@example.org`   |
| username | `cooljohnny1567`     |
| password | `mycoolpassword`     |
| MFA code | `999779`             |

The match must be exact - any other string is filled literally. The same
sentinels work in agent fill actions when the agent is started with
`--vault-id`. This is what keeps the real secret out of your scripts, logs, and
shell history.

## Authentication Patterns

### When to Use Personas

Use personas when you need:
- **New accounts**: Testing signup flows
- **Disposable identities**: One-time verifications
- **Email/SMS verification**: Need to receive codes
- **Testing**: Creating accounts for test scenarios

```bash
# Signup flow testing
notte personas create --create-vault
# → Use generated email/sms for signup
# → Check personas emails/sms for verification codes
```

### When to Use Vaults

Use vaults when you need:
- **Existing accounts**: Login to your accounts
- **Persistent credentials**: Same credentials across sessions
- **MFA automation**: Auto-generate TOTP codes

```bash
# One-time setup: store the credential (values expanded from env vars)
notte vaults credentials add --vault-id <vault-id> \
  --url "https://dashboard.example.com" \
  --email "$DASHBOARD_EMAIL" \
  --password "$DASHBOARD_PASSWORD" \
  --mfa-secret "$DASHBOARD_MFA_SECRET"

# Then attach the vault to the session and fill with sentinel placeholders.
# Notte substitutes the real credential before the keystrokes reach the page,
# so the script never contains the secret.
notte sessions start --vault-id <vault-id>
notte page goto "https://dashboard.example.com/login"
notte page fill "input[name='email']" "user@example.org"
notte page fill "input[name='password']" "mycoolpassword"
notte page fill "input[name='otp']" "999779"       # TOTP generated from the stored seed
```

### Combined Pattern

Use both for complex flows:

```bash
# Create persona for new account testing
notte personas create --create-vault

# The persona's vault is linked and can store credentials
# created during the signup process

# After signup completes, credentials are saved to the
# persona's vault for subsequent logins
```

## Security Considerations

### Credential Storage

- Credentials are encrypted at rest
- API key controls access to your vaults
- MFA secrets enable automatic TOTP but require secure storage

### Best Practices

1. **Use separate vaults** for different purposes:
   ```bash
   notte vaults create --name "Production"
   notte vaults create --name "Staging"
   notte vaults create --name "Testing"
   ```

2. **Don't share API keys** - each user should have their own

3. **Use personas for testing** - don't test with real credentials

4. **Rotate credentials** - update vault credentials when you change passwords

5. **Clean up test personas** - delete when no longer needed:
   ```bash
   notte personas delete --persona-id <persona-id>
   ```

## Complete Example: Authenticated Data Collection

```bash
#!/bin/bash
set -euo pipefail

# Setup: Create vault and add credentials (one-time, from a shell you control,
# with values expanded from environment variables - never typed inline)
# notte vaults create --name "Analytics Dashboard"
# notte vaults credentials add --vault-id <vault-id> \
#   --url "https://analytics.example.com" \
#   --email "$ANALYTICS_EMAIL" \
#   --password "$ANALYTICS_PASSWORD" \
#   --mfa-secret "$ANALYTICS_MFA_SECRET"

VAULT_ID="vault_abc123"

# Start the session with the vault attached - this is what enables sentinel
# substitution. Without --vault-id the sentinels are filled literally.
notte sessions start --vault-id "$VAULT_ID"

# Navigate to login and fill with sentinels, not real values
notte page goto "https://analytics.example.com/login"
notte page fill "input[name='email']" "user@example.org"
notte page fill "input[name='password']" "mycoolpassword"
notte page click "button[type='submit']"

# If the site prompts for MFA, fill the MFA sentinel - the TOTP is generated
# from the seed stored in the vault
notte page wait 2000
notte page fill "input[name='otp']" "999779" 2>/dev/null || true

# Now logged in, collect data
notte page goto "https://analytics.example.com/reports/weekly"
REPORT=$(notte page scrape --instructions "Extract the weekly metrics summary")

# Save cookies for faster future logins
notte sessions cookies -o json > analytics_cookies.json

# Cleanup
notte sessions stop

echo "Report collected: $REPORT"
```
