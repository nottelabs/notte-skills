---
name: session-management
description: Complete guide to managing browser sessions with the notte CLI
---

# Session Management Reference

Complete guide to managing browser sessions with the notte CLI.

## Session Lifecycle

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   start     │ -> │   observe   │ -> │    page     │ -> │    stop     │
│  sessions   │    │   (page)    │    │  commands   │    │  sessions   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

## Starting Sessions

### Basic Start

```bash
# Start with defaults (headless chromium)
notte sessions start

# Start with a visible browser
notte sessions start --headed
```

### Browser Selection

```bash
# Chromium (default)
notte sessions start --browser-type chromium

# Google Chrome
notte sessions start --browser-type chrome
```

Only `chromium` and `chrome` are supported. `chrome-nightly` and `chrome-turbo`
are accepted as legacy aliases for `chrome`. There is no Firefox option.

### Session Configuration

```bash
notte sessions start \
  --headed \                      # Show a browser window (headless is default)
  --browser-type chromium \       # chromium or chrome
  --idle-timeout-minutes 10 \     # Close after 10 min of inactivity
  --max-duration-minutes 60 \     # Maximum 60 min session lifetime
  --proxy \                       # Use rotating proxies
  --no-solve-captchas \           # Turn OFF captcha solving (on by default)
  --vault-id <vault-id> \         # Attach a vault for sentinel credential fills
  --profile-id <profile-id> \     # Load browser state from a profile
  --profile-persist \             # Save browser state on session close
  --viewport-width 1920 \         # Custom viewport
  --viewport-height 1080 \
  --user-agent "Custom UA" \      # Custom user agent
  --no-file-storage               # Detach FileStorage (attached by default)
```

See the main SKILL.md for the full flag list, including `--aspect-ratio`,
`--screenshot-type`, `--chrome-args`, `--extra-http-headers`, `--web-bot-auth`,
and the external/Tailscale proxy flags.

### Browser Profiles

Profiles store browser state such as cookies, `localStorage`, and `sessionStorage`. Create one with `notte profiles create`, then start a session with `--profile-id <profile-id>` to load that saved state; add `--profile-persist` when starting the session if changes should be saved back to the profile when the session closes.

```bash
PROFILE_ID=$(notte profiles create -o json | jq -r '.profile_id')
notte profiles list
notte profiles show --profile-id "$PROFILE_ID"
notte profiles delete --profile-id "$PROFILE_ID"
```

### Remote Browser Connection

Connect to an external browser via CDP (Chrome DevTools Protocol):

```bash
notte sessions start --cdp-url "ws://localhost:9222/devtools/browser/..."
```

## Session ID Management

### Capture and Pass the ID

Capture the ID returned by `sessions start`, then pass it on every command that
targets that session:

```bash
SESSION_ID=$(notte sessions start -o json | jq -r '.session_id')
notte page observe --session-id "$SESSION_ID"
notte page click --session-id "$SESSION_ID" "B3"
notte page scrape --session-id "$SESSION_ID"
notte sessions stop --session-id "$SESSION_ID"
```

### Explicit Session ID

```bash
# Via --session-id flag
notte page observe --session-id sess_abc123
```

Skill rule: always pass `--session-id`. Do not rely on the CLI's
environment-variable or local-current-session fallback behavior.

## Observing Page State

The `observe` command returns the current page state including available actions:

```bash
# Observe the current page. `observe` takes no arguments - navigate first.
notte page goto --session-id <session-id> "https://example.com"
notte page observe --session-id <session-id>
```

### Observe Response

The response includes:
- **url**: Current page URL
- **title**: Page title
- **actions**: Available interactive elements with IDs

Example response (JSON output):
```json
{
  "url": "https://example.com/login",
  "title": "Login - Example",
  "actions": [
    {"id": "I1", "type": "input", "description": "Email input field"},
    {"id": "I2", "type": "input", "description": "Password input field"},
    {"id": "B1", "type": "button", "description": "Login button"}
  ]
}
```

IDs are prefixed by element class - `I*` for inputs, `B*` for buttons, `L*` for
links. Use them directly in page commands:

```bash
notte page fill --session-id <session-id> "I1" "user@example.com"
notte page fill --session-id <session-id> "I2" "password"
notte page click --session-id <session-id> "B1"
```

## Executing Actions

Use the `page` commands for interacting with the browser:

```bash
# Navigate
notte page goto --session-id <session-id> "https://example.com"

# Click
notte page click --session-id <session-id> "B3"

# Fill
notte page fill --session-id <session-id> "B1" "hello"

# Select dropdown
notte page select --session-id <session-id> "select[name='country']" "Option 1"

# Press key
notte page press --session-id <session-id> "Enter"
```

See the main SKILL.md for complete page command reference.

## Scraping Content

### Basic Scraping

```bash
# Scrape entire page
notte page scrape --session-id <session-id>

# With extraction instructions
notte page scrape --session-id <session-id> --instructions "Extract all product names and prices as JSON"

# Only main content (skip headers, footers, ads)
notte page scrape --session-id <session-id> --only-main-content
```

### Structured Extraction

Extraction instructions accept natural language:

```bash
notte page scrape --session-id <session-id> --instructions "Extract:
- Article title
- Author name
- Publication date
- Main content (first 500 words)"
```

## Session Timeouts

Defaults are **3 minutes idle** and **15 minutes total** - short enough that a
long exploration or a pause for user confirmation will hit them. When that
happens the next command fails with `Session closed`, which does not say why, so
raise them up front for anything slow.

### Idle Timeout

Session closes after period of inactivity (default: 3 minutes):

```bash
# Close after 10 minutes of no activity
notte sessions start --idle-timeout-minutes 10
```

Activity includes any command: observe, execute, scrape, etc.

### Max Duration

Absolute maximum session lifetime (default: 15 minutes):

```bash
# Session closes after 60 minutes regardless of activity
notte sessions start --max-duration-minutes 60
```

### Combining Timeouts

```bash
# Close after 10 min idle OR 60 min total, whichever comes first
notte sessions start --idle-timeout-minutes 10 --max-duration-minutes 60
```

### Network Logs

Download the network logs (HAR) and print where they landed:

```bash
notte sessions network --session-id <session-id>                  # downloads to a temp directory
notte sessions network --session-id <session-id> --path ./har     # choose the output directory
notte sessions network --session-id <session-id> --urls-only      # print request URLs inline, no download
```

Useful for debugging API calls, failed requests, and for finding a site's
internal data API during exploration.

### Session Replay

Download the session replay video:

```bash
notte sessions replay --session-id <session-id>
```

To watch a session live instead, use
`notte sessions viewer --session-id <session-id>`.

### Export Code

Export session steps as reusable code:

```bash
notte sessions workflow-code --session-id <session-id>
```

Generates a workflow script from your session actions, in the shape
`notte functions create` expects. `notte sessions code --session-id <session-id>` hits the same endpoint
without the workflow wrapper and returns a plain replay script - prefer
`workflow-code` when the target is a Function.

## Cookie Management

### Get Cookies

```bash
notte sessions cookies --session-id <session-id>
```

Returns all cookies for the specified session.

### Set Cookies

Restore cookies from a previous session:

```bash
# cookies.json format:
# [{"name": "session", "value": "abc123", "domain": ".example.com", ...}]

notte sessions cookies-set --session-id <session-id> --file cookies.json
```

### Cookie Persistence Pattern

```bash
# Save cookies after login
notte sessions cookies --session-id <session-id> -o json > cookies.json

# Restore in new session
NEW_SESSION_ID=$(notte sessions start -o json | jq -r '.session_id')
notte sessions cookies-set --session-id "$NEW_SESSION_ID" --file cookies.json
notte page goto --session-id "$NEW_SESSION_ID" "https://example.com/dashboard"  # Already logged in
```

## Session Status

Check if session is still active:

```bash
notte sessions status --session-id <session-id>
```

### List All Sessions

```bash
# List all sessions
notte sessions list

# With pagination and filters
notte sessions list --page 2 --page-size 10   # running only; add -a/--all for stopped
```

## Stopping Sessions

```bash
# Stop a specific session
notte sessions stop --session-id sess_abc123

# Skip confirmation prompt
notte sessions stop --session-id <session-id> --yes
```

## Best Practices

### 1. Always Stop Sessions

Sessions consume resources. Always stop when done:

```bash
# In scripts, capture the ID and use it in the cleanup trap
SESSION_ID=$(notte sessions start -o json | jq -r '.session_id')
trap 'notte sessions stop --session-id "$SESSION_ID" --yes 2>/dev/null' EXIT
```

### 2. Use Appropriate Timeouts

Set timeouts based on your use case:

```bash
# Short task (login check)
notte sessions start --idle-timeout-minutes 2 --max-duration-minutes 5

# Long task (data collection)
notte sessions start --idle-timeout-minutes 15 --max-duration-minutes 120
```

### 3. Observe Before Acting

Always observe to get current element IDs:

```bash
notte page goto --session-id <session-id> "https://example.com"
notte page observe --session-id <session-id>
# Now you know the element IDs
notte page click --session-id <session-id> "B3"
```

### 4. Use JSON Output for Scripts

```bash
# Parse response in scripts
RESULT=$(notte page observe --session-id <session-id> -o json)
URL=$(echo "$RESULT" | jq -r '.url')
```

### 5. Handle Errors Gracefully

```bash
if ! notte page click --session-id <session-id> "button[type='submit']"; then
  echo "Click failed, retrying..."
  notte page wait --session-id <session-id> 1000
  notte page click --session-id <session-id> "button[type='submit']"
fi
```
