#!/bin/bash
# Data Extraction Template
# Scrape structured data from websites with the notte CLI
#
# Usage: ./data-extraction.sh [url]
#
# Prerequisites:
#   - notte CLI installed and authenticated (notte auth login)
#   - NOTTE_API_KEY environment variable set
#   - jq installed (used to capture the explicit session ID)
#
# Examples:
#   ./data-extraction.sh "https://news.ycombinator.com"
#   ./data-extraction.sh "https://example.com/products"

set -euo pipefail

# Configuration
DEFAULT_URL="https://news.ycombinator.com"
TARGET_URL="${1:-$DEFAULT_URL}"

# Extraction instructions - customize for your data
EXTRACTION_INSTRUCTIONS="Extract the following as a JSON array:
- title: the headline or name
- link: the URL if available
- description: a brief summary or subtitle
- metadata: any relevant dates, authors, or categories"

# Output settings
OUTPUT_FORMAT="json"  # json or text
OUTPUT_FILE=""  # Set to filename to save output, empty for stdout
ONLY_MAIN_CONTENT=true

# Pagination settings
PAGINATE=false
MAX_PAGES=5
NEXT_PAGE_SELECTOR="a:has-text('Next')"  # Selector or observe ID for next page button

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
SESSION_ID=""
SCRAPE_RESULT=""

log_info() { echo -e "${GREEN}[INFO]${NC} $1" >&2; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1" >&2; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1" >&2; }

cleanup() {
    log_info "Cleaning up..."
    if [[ -n "$SESSION_ID" ]]; then
        notte sessions stop --session-id "$SESSION_ID" --yes 2>/dev/null || true
    fi
}

trap cleanup EXIT

# Session-based scrape
session_scrape() {
    local url="$1"
    local instructions="$2"

    log_step "Starting browser session..."
    local session_result
    session_result=$(notte sessions start -o json)
    if ! SESSION_ID=$(echo "$session_result" | jq -er '
        .session_id // .sessionId // .id
        | select(type == "string" and length > 0)
    '); then
        SESSION_ID=""
        log_error "Session start returned no valid session ID"
        return 1
    fi

    log_step "Navigating to: $url"
    notte page goto --session-id "$SESSION_ID" "$url"
    notte page observe --session-id "$SESSION_ID" > /dev/null
    notte page wait --session-id "$SESSION_ID" 1500

    local all_results="[]"
    local page_num=1

    while true; do
        log_step "Scraping page $page_num..."

        local flags=""
        if [[ "$ONLY_MAIN_CONTENT" == "true" ]]; then
            flags="--only-main-content"
        fi

        local page_result
        # shellcheck disable=SC2086
        page_result=$(notte page scrape --session-id "$SESSION_ID" --instructions "$instructions" $flags -o json)

        # With --instructions, `notte page scrape --session-id "$SESSION_ID" -o json` returns the extracted
        # object at the TOP LEVEL (the requested fields are the JSON keys) - there
        # is no wrapper to unpack. Normalise to an array and append.
        if command -v jq &> /dev/null; then
            all_results=$(jq -s '
                .[0] + (.[1] | if type == "array" then . else [.] end)
            ' <(echo "$all_results") <(echo "$page_result"))
        else
            # Fallback: just append
            all_results="$all_results
$page_result"
        fi

        log_info "Page $page_num scraped"

        # Check pagination
        if [[ "$PAGINATE" != "true" ]] || [[ $page_num -ge $MAX_PAGES ]]; then
            break
        fi

        # Try to click next page
        log_step "Looking for next page..."
        if ! notte page click --session-id "$SESSION_ID" "$NEXT_PAGE_SELECTOR" 2>/dev/null; then
            log_info "No more pages found"
            break
        fi

        notte page wait --session-id "$SESSION_ID" 2000
        page_num=$((page_num + 1))
    done

    SCRAPE_RESULT="$all_results"
}

# Scrape multiple URLs
batch_scrape() {
    local urls=("$@")
    local all_results="[]"

    log_step "Starting browser session for batch scrape..."
    local session_result
    session_result=$(notte sessions start -o json)
    if ! SESSION_ID=$(echo "$session_result" | jq -er '
        .session_id // .sessionId // .id
        | select(type == "string" and length > 0)
    '); then
        SESSION_ID=""
        log_error "Session start returned no valid session ID"
        return 1
    fi

    for url in "${urls[@]}"; do
        log_step "Scraping: $url"
        notte page goto --session-id "$SESSION_ID" "$url"
        notte page observe --session-id "$SESSION_ID" > /dev/null
        notte page wait --session-id "$SESSION_ID" 1500

        local flags=""
        if [[ "$ONLY_MAIN_CONTENT" == "true" ]]; then
            flags="--only-main-content"
        fi

        local result
        # shellcheck disable=SC2086
        result=$(notte page scrape --session-id "$SESSION_ID" --instructions "$EXTRACTION_INSTRUCTIONS" $flags -o json)

        # Tag each row with its source URL and append. The scrape result is the
        # extracted object itself (see note above), not a wrapper.
        if command -v jq &> /dev/null; then
            all_results=$(jq -s --arg url "$url" '
                .[0] + (.[1]
                        | if type == "array" then . else [.] end
                        | map(. + {source_url: $url}))
            ' <(echo "$all_results") <(echo "$result"))
        fi

        log_info "Completed: $url"
    done

    SCRAPE_RESULT="$all_results"
}

format_output() {
    local data="$1"

    if [[ "$OUTPUT_FORMAT" == "json" ]] && command -v jq &> /dev/null; then
        echo "$data" | jq '.'
    else
        echo "$data"
    fi
}

save_output() {
    local data="$1"
    local file="$2"

    if [[ -n "$file" ]]; then
        echo "$data" > "$file"
        log_info "Output saved to: $file"
    else
        echo "$data"
    fi
}

main() {
    log_info "=== Data Extraction ==="
    log_info "Target: $TARGET_URL"
    log_info "Instructions: ${EXTRACTION_INSTRUCTIONS:0:50}..."

    local result

    # Use session-based scrape
    if [[ "$PAGINATE" == "true" ]]; then
        log_info "Mode: Multi-page session scrape"
    else
        log_info "Mode: Single-page session scrape"
    fi
    session_scrape "$TARGET_URL" "$EXTRACTION_INSTRUCTIONS"
    result="$SCRAPE_RESULT"

    # Format and output
    local formatted
    formatted=$(format_output "$result")

    save_output "$formatted" "$OUTPUT_FILE"

    log_info "=== Extraction complete ==="
}

# Handle batch mode if multiple URLs provided
if [[ $# -gt 1 ]]; then
    log_info "Batch mode: ${#} URLs"
    batch_scrape "$@"
    result="$SCRAPE_RESULT"
    formatted=$(format_output "$result")
    save_output "$formatted" "$OUTPUT_FILE"
else
    main
fi
