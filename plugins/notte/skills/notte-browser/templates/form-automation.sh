#!/bin/bash
# Form Automation Template
# Fill and submit forms with the notte CLI
#
# Usage: ./form-automation.sh
#
# Prerequisites:
#   - notte CLI installed and authenticated (notte auth login)
#   - NOTTE_API_KEY environment variable set
#   - jq installed (used to capture the explicit session ID)
#
# Customize the variables below for your form

set -euo pipefail

# Configuration - customize these for your form
TARGET_URL="https://example.com/contact"
FORM_DATA=(
    # Format: "selector|value"
    # Use IDs from observe, or Playwright selectors
    # Examples:
    #   "I1|value"                     - Element ID from observe
    #   "#name|value"                  - CSS ID selector
    #   "input[name='email']|value"    - Attribute selector
    #   ".form-input >> nth=0|value"   - First match when multiple elements
    "input[name='name']|John Doe"
    "input[type='email']|john@example.com"
    "textarea[name='message']|Hello, this is a test message."
)
# Tip: If the observe ID doesn't work, try: "button:has-text('Submit')" or "#submit-button"
SUBMIT_SELECTOR="button[type='submit']"
SUCCESS_INDICATOR="Thank you"  # Text that appears on success

# Optional: Screenshot settings
TAKE_SCREENSHOTS=true
SCREENSHOT_DIR="./screenshots"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color
SESSION_ID=""

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

cleanup() {
    log_info "Cleaning up..."
    if [[ -n "$SESSION_ID" ]]; then
        notte sessions stop --session-id "$SESSION_ID" --yes 2>/dev/null || true
    fi
}

# Ensure cleanup on exit
trap cleanup EXIT

main() {
    log_info "Starting form automation"

    # Create screenshot directory if needed
    if [[ "$TAKE_SCREENSHOTS" == "true" ]]; then
        mkdir -p "$SCREENSHOT_DIR"
    fi

    # Start browser session
    log_info "Starting browser session..."
    SESSION_RESULT=$(notte sessions start -o json)
    if ! SESSION_ID=$(echo "$SESSION_RESULT" | jq -er '
        .session_id // .sessionId // .id
        | select(type == "string" and length > 0)
    '); then
        SESSION_ID=""
        log_error "Session start returned no valid session ID"
        exit 1
    fi
    log_info "Session started: $SESSION_ID"

    # Navigate to form page
    log_info "Navigating to: $TARGET_URL"
    notte page goto --session-id "$SESSION_ID" "$TARGET_URL"
    notte page observe --session-id "$SESSION_ID" > /dev/null

    # Wait for page to load
    notte page wait --session-id "$SESSION_ID" 1000

    # Fill form fields
    log_info "Filling form fields..."
    for field in "${FORM_DATA[@]}"; do
        selector="${field%%|*}"
        value="${field#*|}"

        log_info "  Filling $selector"
        if ! notte page fill --session-id "$SESSION_ID" "$selector" "$value"; then
            log_warn "Failed to fill $selector, continuing..."
        fi
        notte page wait --session-id "$SESSION_ID" 200
    done

    # Take screenshot before submit
    if [[ "$TAKE_SCREENSHOTS" == "true" ]]; then
        log_info "Taking pre-submit screenshot..."
        notte page screenshot --session-id "$SESSION_ID"
    fi

    # Submit form
    log_info "Submitting form..."
    notte page click --session-id "$SESSION_ID" "$SUBMIT_SELECTOR"

    # Wait for response
    notte page wait --session-id "$SESSION_ID" 2000

    # Verify submission
    log_info "Verifying submission..."
    SCRAPE_RESULT=$(notte page scrape --session-id "$SESSION_ID" --instructions "Check if the page shows a success message")

    if echo "$SCRAPE_RESULT" | grep -qi "$SUCCESS_INDICATOR"; then
        log_info "Form submitted successfully!"

        # Take success screenshot
        if [[ "$TAKE_SCREENSHOTS" == "true" ]]; then
            log_info "Taking success screenshot..."
            notte page screenshot --session-id "$SESSION_ID"
        fi
    else
        log_warn "Could not verify success. Check the result manually."
        echo "Scrape result: $SCRAPE_RESULT"
    fi

    log_info "Form automation completed"
}

# Run main function
main "$@"
