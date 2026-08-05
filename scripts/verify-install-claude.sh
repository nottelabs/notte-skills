#!/usr/bin/env bash
# Install this repo's plugins into a throwaway Claude Code config and assert
# that the notte-browser skill and the anything.notte.cc MCP server are wired up.
#
# Runs in CI (.github/workflows/verify-install.yml) and locally:
#
#     scripts/verify-install-claude.sh [repo-root]
#
# Requires: claude (npm i -g @anthropic-ai/claude-code), jq.
# No Anthropic credentials needed - every command used here is local-only.
set -euo pipefail

REPO_ROOT=${1:-$(git rev-parse --show-toplevel)}
EXPECTED_SKILL=notte-browser
EXPECTED_MCP_URL=https://anything.notte.cc/mcp

# A fresh config dir per run, so a developer's own plugins can never make this pass.
CLAUDE_CONFIG_DIR=$(mktemp -d)/claude
export CLAUDE_CONFIG_DIR
mkdir -p "$CLAUDE_CONFIG_DIR"
trap 'rm -rf "$(dirname "$CLAUDE_CONFIG_DIR")"' EXIT

fail() { echo "  FAIL  $*" >&2; exit 1; }
ok() { echo "  ok    $*"; }

echo "Claude Code $(claude --version)"
echo "Installing from $REPO_ROOT into $CLAUDE_CONFIG_DIR"
echo

claude plugin marketplace add "$REPO_ROOT"
claude plugin install notte@notte --scope user
claude plugin install notte-migrate@notte --scope user
echo

installed=$(claude plugin list --json)

for plugin in notte@notte notte-migrate@notte; do
  jq -e --arg id "$plugin" 'any(.[]; .id == $id and .enabled == true)' >/dev/null <<<"$installed" \
    || fail "$plugin is not installed and enabled"
  ok "$plugin installed and enabled"
done

# The MCP server has to arrive through the plugin, not through a stray user config.
jq -e --arg url "$EXPECTED_MCP_URL" \
  'any(.[]; .id == "notte@notte" and (.mcpServers // {} | any(.[]; .url == $url)))' \
  >/dev/null <<<"$installed" \
  || fail "notte@notte does not contribute an MCP server at $EXPECTED_MCP_URL"
ok "MCP server $EXPECTED_MCP_URL contributed by notte@notte"

# `plugin details` is the inventory Claude Code actually loads a session from.
details=$(claude plugin details notte@notte)
grep -qE "^ *Skills \([0-9]+\).*\b${EXPECTED_SKILL}\b" <<<"$details" \
  || { echo "$details" >&2; fail "'$EXPECTED_SKILL' is not listed as a skill of notte@notte"; }
ok "skill $EXPECTED_SKILL listed in the notte@notte component inventory"

grep -qE "^ *MCP servers \([0-9]+\)" <<<"$details" \
  || { echo "$details" >&2; fail "notte@notte reports no MCP servers"; }
ok "notte@notte reports MCP servers in its component inventory"

# And the skill is really on disk in the installed copy, not just in the manifest.
install_path=$(jq -er '.[] | select(.id == "notte@notte") | .installPath' <<<"$installed")
[ -f "$install_path/skills/$EXPECTED_SKILL/SKILL.md" ] \
  || fail "$install_path/skills/$EXPECTED_SKILL/SKILL.md is missing from the installed plugin"
ok "SKILL.md present at $EXPECTED_SKILL in the installed plugin"

echo
echo "PASSED: Claude Code loads $EXPECTED_SKILL and $EXPECTED_MCP_URL."
