#!/usr/bin/env bash
# Verify that Cursor loads the notte-browser skill and the anything.notte.cc MCP server.
#
# Runs in CI (.github/workflows/verify-install.yml) and locally:
#
#     scripts/verify-install-cursor.sh [repo-root]
#
# Two modes, because the Cursor CLI has no offline "install and inspect" surface:
#
#   1. Manifest resolution (always). Resolves .cursor-plugin/plugin.json the way
#      cursor-agent does and asserts the skill and MCP server it would expose.
#      Cursor falls back to .claude-plugin/{marketplace,plugin}.json, which the
#      Claude Code and Codex jobs already install for real - this covers the
#      Cursor-specific root manifest, which is the one that drifts.
#   2. Live probe (only when CURSOR_API_KEY is set). Boots a real cursor-agent
#      session with the plugin loaded and asks it what it can see. This costs a
#      few model tokens, so CI runs it on main and on a schedule, not per PR.
#
# Set CURSOR_REQUIRE_LIVE=1 to make a missing CURSOR_API_KEY a hard failure
# rather than a skip. CI sets it on every run that is meant to include the live
# probe, so an unset secret turns the job red instead of reporting a pass for a
# check that never ran.
#
# Requires: jq. Live probe additionally requires cursor-agent and CURSOR_API_KEY.
set -euo pipefail

REPO_ROOT=${1:-$(git rev-parse --show-toplevel)}
MANIFEST="$REPO_ROOT/.cursor-plugin/plugin.json"
EXPECTED_SKILL=notte-browser
EXPECTED_MCP_URL=https://anything.notte.cc/mcp

fail() { echo "  FAIL  $*" >&2; exit 1; }
ok() { echo "  ok    $*"; }

# Strip a leading "./" and resolve against the plugin root, which for the Cursor
# manifest is the repository root.
resolve() { local p=${1#./}; echo "$REPO_ROOT/${p%/}"; }

echo "Resolving $MANIFEST"
[ -f "$MANIFEST" ] || fail ".cursor-plugin/plugin.json is missing"
manifest=$(jq -e . "$MANIFEST") || fail ".cursor-plugin/plugin.json is not valid JSON"

# --- skills -----------------------------------------------------------------
# `skills` is a path or a list of paths, each pointing at a directory of skills.
skill_roots=$(jq -r '.skills // empty | if type == "array" then .[] else . end' <<<"$manifest")
[ -n "$skill_roots" ] || fail ".cursor-plugin/plugin.json declares no skills"

found_skill=""
while IFS= read -r root; do
  candidate="$(resolve "$root")/$EXPECTED_SKILL/SKILL.md"
  [ -f "$candidate" ] && found_skill=$candidate
done <<<"$skill_roots"
[ -n "$found_skill" ] \
  || fail "no skills root in .cursor-plugin/plugin.json contains $EXPECTED_SKILL/SKILL.md"
ok "skill $EXPECTED_SKILL resolves to ${found_skill#"$REPO_ROOT"/}"

# --- mcpServers -------------------------------------------------------------
# `mcpServers` is either a path to an .mcp.json or an inline server map.
mcp_field=$(jq -r 'if has("mcpServers") then (.mcpServers | type) else "missing" end' <<<"$manifest")
case "$mcp_field" in
  missing)
    fail ".cursor-plugin/plugin.json has no mcpServers - Cursor would load the skills but no MCP server"
    ;;
  string)
    mcp_path=$(resolve "$(jq -r '.mcpServers' <<<"$manifest")")
    [ -f "$mcp_path" ] || fail "mcpServers points at $mcp_path, which does not exist"
    servers=$(jq -e '.mcpServers' "$mcp_path") || fail "$mcp_path has no mcpServers object"
    ;;
  object)
    servers=$(jq -e '.mcpServers' <<<"$manifest")
    ;;
  *)
    fail "mcpServers must be a path or an object, got $mcp_field"
    ;;
esac

jq -e --arg url "$EXPECTED_MCP_URL" 'any(.[]; .url == $url)' >/dev/null <<<"$servers" \
  || { echo "$servers" >&2; fail "no MCP server declared at $EXPECTED_MCP_URL"; }
ok "MCP server $EXPECTED_MCP_URL declared for Cursor"

# --- live probe -------------------------------------------------------------
# A missing key must not quietly downgrade this to a manifest check that still
# reports success. Callers that expect the live probe set CURSOR_REQUIRE_LIVE=1
# and get a hard failure instead; everyone else gets a loud skip notice.
if [ -z "${CURSOR_API_KEY:-}" ]; then
  if [ "${CURSOR_REQUIRE_LIVE:-}" = "1" ]; then
    fail "CURSOR_REQUIRE_LIVE=1 but CURSOR_API_KEY is unset - refusing to report a pass for a check that did not run"
  fi
  echo
  if [ -n "${GITHUB_ACTIONS:-}" ]; then
    echo "::warning title=Cursor live probe skipped::No CURSOR_API_KEY, so only manifest resolution was checked. Nothing verified that Cursor loads the skill or MCP server."
  fi
  echo "SKIPPED the live probe: no CURSOR_API_KEY, so only the manifest was resolved."
  echo "PASSED (manifest only) - this did NOT verify that Cursor loads anything."
  exit 0
fi

echo
echo "Probing a live cursor-agent session with --plugin-dir $REPO_ROOT"
probe=$(cd "$(mktemp -d)" && cursor-agent \
  --plugin-dir "$REPO_ROOT" \
  --mode ask \
  --trust \
  --approve-mcps \
  --output-format text \
  -p "List every skill name and every MCP server name available to you, one per line, nothing else.")

grep -q "$EXPECTED_SKILL" <<<"$probe" \
  || { echo "$probe" >&2; fail "live cursor-agent session does not see the $EXPECTED_SKILL skill"; }
ok "live session sees the $EXPECTED_SKILL skill"

# Cursor namespaces plugin MCP servers as plugin-<Plugin>-<server>, so match on the server name.
grep -qE 'anything-api' <<<"$probe" \
  || { echo "$probe" >&2; fail "live cursor-agent session does not see the anything-api MCP server"; }
ok "live session sees the anything-api MCP server ($EXPECTED_MCP_URL)"

echo
echo "PASSED: Cursor loads $EXPECTED_SKILL and $EXPECTED_MCP_URL."
