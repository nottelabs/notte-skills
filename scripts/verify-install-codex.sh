#!/usr/bin/env bash
# Install this repo's plugins into a throwaway Codex home and assert that the
# notte-browser skill and the anything.notte.cc MCP server are wired up.
#
# Runs in CI (.github/workflows/verify-install.yml) and locally:
#
#     scripts/verify-install-codex.sh [repo-root]
#
# Requires: codex (npm i -g @openai/codex), jq, python3.
# No OpenAI credentials needed - every command used here is local-only.
set -euo pipefail

REPO_ROOT=${1:-$(git rev-parse --show-toplevel)}
EXPECTED_SKILL=notte-browser
EXPECTED_MCP_URL=https://anything.notte.cc/mcp

# A fresh CODEX_HOME per run, so a developer's own plugins can never make this pass.
CODEX_HOME=$(mktemp -d)/codex
export CODEX_HOME
mkdir -p "$CODEX_HOME"
trap 'rm -rf "$(dirname "$CODEX_HOME")"' EXIT

fail() { echo "  FAIL  $*" >&2; exit 1; }
ok() { echo "  ok    $*"; }

echo "Codex $(codex --version)"
echo "Installing from $REPO_ROOT into $CODEX_HOME"
echo

# Codex reads .claude-plugin/marketplace.json when a marketplace root has no
# .codex-plugin equivalent, so the same manifests serve both clients.
codex plugin marketplace add "$REPO_ROOT"
notte_install=$(codex plugin add notte@notte --json)
codex plugin add notte-migrate@notte --json >/dev/null
echo

installed=$(codex plugin list --json)

for plugin in notte@notte notte-migrate@notte; do
  jq -e --arg id "$plugin" \
    'any(.installed[]; .pluginId == $id and .installed == true and .enabled == true)' \
    >/dev/null <<<"$installed" \
    || fail "$plugin is not installed and enabled"
  ok "$plugin installed and enabled"
done

# `codex mcp list` reports the servers Codex would actually start, plugin-provided ones included.
servers=$(codex mcp list --json)
jq -e --arg url "$EXPECTED_MCP_URL" \
  'any(.[]; .transport.url == $url and .enabled == true)' >/dev/null <<<"$servers" \
  || { echo "$servers" >&2; fail "no enabled MCP server at $EXPECTED_MCP_URL"; }
ok "MCP server $EXPECTED_MCP_URL enabled after install"

# The installed copy - not the source tree - is what Codex loads skills from.
install_path=$(jq -er '.installedPath' <<<"$notte_install")
[ -f "$install_path/skills/$EXPECTED_SKILL/SKILL.md" ] \
  || fail "$install_path/skills/$EXPECTED_SKILL/SKILL.md is missing from the installed plugin"
ok "skill $EXPECTED_SKILL materialised at $install_path"

# Everything above reads the CLI, which is a reduced projection: it drops the
# `interface` metadata that the plugin browser and the ChatGPT app render. The
# app-server API is where that surface lives, so check it too.
echo
python3 "$(dirname "$0")/verify-codex-app-server.py" "$REPO_ROOT"

echo
echo "PASSED: Codex loads $EXPECTED_SKILL and $EXPECTED_MCP_URL, and exposes its install-surface metadata."
