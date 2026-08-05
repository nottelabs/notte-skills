#!/bin/bash
# Authenticated Session Template
# Login to a website using vault credentials with optional MFA support.
#
# Usage: NOTTE_VAULT_ID=vault_abc123 ./authenticated-session.sh
#
# Prerequisites:
#   - notte CLI installed and authenticated (notte auth login)
#   - A vault holding the credential for the target site. Add it ONCE, from a
#     shell you control, with values expanded from environment variables:
#
#     notte vaults create --name "MyVault"
#     notte vaults credentials add --vault-id <vault-id> \
#       --url "https://example.com" \
#       --email "$MYSITE_EMAIL" \
#       --password "$MYSITE_PASSWORD" \
#       --mfa-secret "$MYSITE_MFA_SECRET"   # Optional
#
# HOW THIS WORKS - read before editing:
#   This script never reads your password. It attaches the vault to the session
#   with --vault-id and fills SENTINEL PLACEHOLDERS; Notte substitutes the real
#   credential server-side, before the keystrokes reach the page. That keeps the
#   secret out of argv, out of `ps`, out of this file, and out of your logs.
#
#   Do NOT "improve" this by calling `notte vaults credentials get` and filling
#   the returned password - that pulls the plaintext secret into the shell and
#   into argv, which is exactly what the vault exists to prevent.

set -euo pipefail

# Configuration - customize these for your site
LOGIN_URL="https://example.com/login"
DASHBOARD_URL="https://example.com/dashboard"  # URL after successful login
VAULT_ID="${NOTTE_VAULT_ID:-}"                 # Required: set via env or edit here

# Login form selectors (use Playwright-compatible selectors, or IDs from observe)
EMAIL_SELECTOR="input[type='email']"
PASSWORD_SELECTOR="input[type='password']"
SUBMIT_SELECTOR="button[type='submit']"
MFA_SELECTOR="input[name='otp']"  # Optional: selector for MFA input

# Sentinel placeholders - these exact strings are replaced with the matching
# vault credential at fill time. Do not substitute real values here.
SENTINEL_EMAIL="user@example.org"
SENTINEL_USERNAME="cooljohnny1567"
SENTINEL_PASSWORD="mycoolpassword"
SENTINEL_MFA="999779"

# Set to true if the site's first field takes a username rather than an email
USE_USERNAME=false

# Cookie persistence
SAVE_COOKIES=true
COOKIES_FILE="./session_cookies.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

cleanup() {
    if [[ "${KEEP_SESSION:-false}" != "true" ]]; then
        log_info "Stopping session..."
        notte sessions stop --yes 2>/dev/null || true
    else
        log_info "Keeping session alive (KEEP_SESSION=true)"
    fi
}

trap cleanup EXIT

# Decide whether we are logged in.
#
# Prefer a positive signal (we reached an authenticated URL) over scanning page
# text for words like "error" - plenty of legitimate pages contain that word,
# and a text scan cannot distinguish "login failed" from a cookie banner. If we
# cannot prove success, return failure rather than assuming it.
check_login_success() {
    local current_url
    current_url=$(notte page observe -o json | jq -r '.url // empty')

    if [[ -z "$current_url" ]]; then
        log_warn "Could not read current URL from observe"
        return 1
    fi

    # Still sitting on the login page means the login did not go through.
    if [[ "$current_url" == "$LOGIN_URL"* ]] || [[ "$current_url" == *"/login"* ]]; then
        return 1
    fi

    # Reached the expected post-login destination.
    if [[ "$current_url" == "$DASHBOARD_URL"* ]]; then
        return 0
    fi

    # Anywhere else off the login page: treat as success only if the dashboard
    # itself loads without bouncing back to login.
    notte page goto "$DASHBOARD_URL"
    notte page wait 1500
    current_url=$(notte page observe -o json | jq -r '.url // empty')
    [[ "$current_url" == "$DASHBOARD_URL"* ]]
}

restore_cookies() {
    if [[ -f "$COOKIES_FILE" ]]; then
        log_step "Restoring saved cookies..."
        if notte sessions cookies-set --file "$COOKIES_FILE" 2>/dev/null; then
            log_info "Cookies restored"
            return 0
        fi
    fi
    return 1
}

save_cookies() {
    if [[ "$SAVE_COOKIES" == "true" ]]; then
        log_step "Saving session cookies..."
        notte sessions cookies -o json > "$COOKIES_FILE"
        chmod 600 "$COOKIES_FILE"
        log_info "Cookies saved to $COOKIES_FILE (mode 600 - these are session secrets)"
    fi
}

perform_login() {
    log_step "Navigating to login page..."
    notte page goto "$LOGIN_URL"
    notte page observe > /dev/null
    notte page wait 1000

    # Fill the identifier field with a sentinel - the vault supplies the value
    if [[ "$USE_USERNAME" == "true" ]]; then
        log_info "Filling username (vault-substituted)"
        notte page fill "$EMAIL_SELECTOR" "$SENTINEL_USERNAME"
    else
        log_info "Filling email (vault-substituted)"
        notte page fill "$EMAIL_SELECTOR" "$SENTINEL_EMAIL"
    fi
    notte page wait 300

    log_info "Filling password (vault-substituted)"
    notte page fill "$PASSWORD_SELECTOR" "$SENTINEL_PASSWORD"
    notte page wait 300

    log_step "Submitting login form..."
    notte page click "$SUBMIT_SELECTOR"
    notte page wait 2000

    # Check for an MFA prompt
    local observe_result
    observe_result=$(notte page observe -o json)

    if echo "$observe_result" | grep -qiE "(mfa|two.?factor|verification|authenticator|2fa|one.?time)"; then
        log_step "MFA prompt detected"
        handle_mfa
    fi
}

handle_mfa() {
    # The MFA sentinel is replaced with a TOTP generated from the --mfa-secret
    # stored in the vault. If no MFA secret was stored, this fill will submit
    # the literal sentinel and fail - store the secret instead of hardcoding a
    # code here.
    log_info "Filling MFA code (vault-generated TOTP)"
    notte page fill "$MFA_SELECTOR" "$SENTINEL_MFA" --enter
    notte page wait 3000

    local current_url
    current_url=$(notte page observe -o json | jq -r '.url // empty')

    if echo "$current_url" | grep -qiE "(mfa|verify|2fa)"; then
        log_warn "Still on the MFA page."
        log_warn "Confirm the vault credential for $LOGIN_URL has --mfa-secret set:"
        log_warn "  notte vaults credentials list --vault-id $VAULT_ID"
    fi
}

main() {
    log_info "=== Authenticated Session ==="
    log_info "Target: $LOGIN_URL"

    if [[ -z "$VAULT_ID" ]]; then
        log_error "No vault configured. Set NOTTE_VAULT_ID or edit VAULT_ID."
        log_info "To set up a vault (run once, from a shell you control):"
        log_info "  notte vaults create --name 'MyVault'"
        log_info "  notte vaults credentials add --vault-id <vault-id> \\"
        log_info "    --url '$LOGIN_URL' \\"
        log_info "    --email \"\$MYSITE_EMAIL\" \\"
        log_info "    --password \"\$MYSITE_PASSWORD\""
        exit 1
    fi

    # Attach the vault to the session. Without this, the sentinels above are
    # filled literally and the login will fail.
    log_step "Starting browser session with vault attached..."
    notte sessions start --vault-id "$VAULT_ID" > /dev/null
    log_info "Session started"

    # Try to restore cookies first (skip login if still valid)
    if restore_cookies; then
        log_step "Checking if the saved session is still valid..."
        notte page goto "$DASHBOARD_URL"
        notte page wait 2000

        if check_login_success; then
            log_info "=== Login successful (restored from cookies) ==="
            save_cookies  # Refresh
            return 0
        fi
        log_warn "Saved session expired, performing fresh login..."
    fi

    perform_login

    if check_login_success; then
        log_info "=== Login successful ==="
        save_cookies
    else
        log_error "=== Login failed ==="
        log_error "Check: the vault holds a credential for $LOGIN_URL, the"
        log_error "selectors match the live form, and the session was started"
        log_error "with --vault-id."
        exit 1
    fi

    log_step "Navigating to dashboard..."
    notte page goto "$DASHBOARD_URL"
    notte page wait 1000

    log_info "Ready for authenticated actions"
    log_info "Session ID: $(notte sessions status -o json | jq -r '.session_id // empty')"

    # Example: Scrape data from the authenticated page
    # notte page scrape --instructions "Extract user profile information"
}

main "$@"
