#!/usr/bin/env python3
"""Assert that Codex's app-server API exposes our plugin install-surface metadata.

Called by scripts/verify-install-codex.sh once the plugins are installed into a
throwaway CODEX_HOME; can also be run directly against an existing one:

    CODEX_HOME=... python3 scripts/verify-codex-app-server.py [repo-root]

Why a separate surface: `codex plugin list --json` is a reduced projection that
omits `interface` entirely. The Codex /plugins browser and the ChatGPT desktop
app read the app-server JSON-RPC API instead, where marketplaces, plugins, and
individual skills each carry their own `interface` block. Everything the
.codex-plugin manifests and agents/openai.yaml files contribute is invisible to
the CLI, so asserting on the CLI alone would let all of it silently regress -
which is exactly how three of four skills once shipped with no display metadata.

validate-plugins.py checks those files exist and parse; this checks Codex agrees.

Stdlib only. No OpenAI credentials needed.
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

MARKETPLACE = "notte"
PLUGIN_ID = "notte@notte"
# The metadata each surface must carry. Presence, not exact values: this guards
# against the blocks being dropped, not against copy edits.
PLUGIN_INTERFACE_FIELDS = ("displayName", "shortDescription", "category")
SKILL_INTERFACE_FIELDS = ("displayName", "shortDescription", "defaultPrompt")
REPLY_TIMEOUT_SEC = 60

errors: list[str] = []


def fail(message: str) -> None:
    errors.append(message)
    print(f"  FAIL  {message}", file=sys.stderr)


def ok(message: str) -> None:
    print(f"  ok    {message}")


class AppServer:
    """Minimal JSON-RPC client for `codex app-server` over stdio."""

    def __init__(self, cwd: str) -> None:
        self.proc = subprocess.Popen(
            ["codex", "app-server"],
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        self.lines: queue.Queue[str] = queue.Queue()
        # A reader thread keeps a hung or silent server from blocking CI forever.
        threading.Thread(target=self._pump, daemon=True).start()
        self.next_id = 0

    def _pump(self) -> None:
        assert self.proc.stdout is not None
        for line in self.proc.stdout:
            self.lines.put(line)
        self.lines.put("")

    def call(self, method: str, params: dict) -> dict:
        self.next_id += 1
        request_id = self.next_id
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        while True:
            try:
                line = self.lines.get(timeout=REPLY_TIMEOUT_SEC)
            except queue.Empty:
                raise SystemExit(f"  FAIL  codex app-server did not answer {method} in time")
            if not line:
                raise SystemExit(f"  FAIL  codex app-server exited before answering {method}")
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue  # progress notifications and other non-JSON chatter
            if message.get("id") != request_id:
                continue
            if "error" in message:
                raise SystemExit(f"  FAIL  {method} failed: {json.dumps(message['error'])}")
            return message.get("result") or {}

    def _send(self, payload: dict) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()

    def initialize(self) -> None:
        self.call("initialize", {"clientInfo": {"name": "notte-skills-ci",
                                                "title": "notte-skills CI",
                                                "version": "1.0.0"}})
        self._send({"jsonrpc": "2.0", "method": "initialized"})

    def close(self) -> None:
        self.proc.terminate()


def check_interface(label: str, interface: object, fields: tuple[str, ...]) -> None:
    if not isinstance(interface, dict) or not interface:
        fail(f"{label} has no interface metadata (Codex would render it bare)")
        return
    missing = [field for field in fields if not interface.get(field)]
    if missing:
        fail(f"{label} interface is missing {', '.join(missing)}")
        return
    ok(f"{label} exposes {', '.join(fields)}")


def validate_plugins(server: AppServer, repo_root: str) -> None:
    result = server.call("plugin/list", {"cwds": [repo_root]})
    marketplaces = [m for m in result.get("marketplaces", []) if m.get("name") == MARKETPLACE]
    if not marketplaces:
        fail(f"app-server sees no '{MARKETPLACE}' marketplace")
        return
    marketplace = marketplaces[0]
    ok(f"marketplace '{MARKETPLACE}' resolved from {marketplace.get('path')}")

    check_interface(f"marketplace '{MARKETPLACE}'", marketplace.get("interface"), ("displayName",))

    plugins = {p.get("id"): p for p in marketplace.get("plugins", [])}
    plugin = plugins.get(PLUGIN_ID)
    if plugin is None:
        fail(f"app-server does not list {PLUGIN_ID} (saw: {', '.join(sorted(plugins)) or 'none'})")
        return
    check_interface(PLUGIN_ID, plugin.get("interface"), PLUGIN_INTERFACE_FIELDS)
    if not plugin.get("keywords"):
        fail(f"{PLUGIN_ID} exposes no keywords, so it will not surface in search")
    else:
        ok(f"{PLUGIN_ID} exposes {len(plugin['keywords'])} keywords")


def shipped_skills(repo_root: str) -> set[str]:
    """Every skill this repo ships, named the way Codex namespaces them.

    Derived from disk rather than from the API response: checking only the
    skills the API happened to return would pass while a skill was silently
    missing, which is the more serious failure of the two.
    """
    plugins = Path(repo_root) / "plugins"
    return {
        f"{plugin.name}:{skill.parent.name}"
        for plugin in plugins.iterdir()
        if plugin.is_dir()
        for skill in plugin.glob("skills/*/SKILL.md")
    }


def validate_skills(server: AppServer, repo_root: str) -> None:
    expected = shipped_skills(repo_root)
    if not expected:
        fail(f"found no plugins/*/skills/*/SKILL.md under {repo_root} to check against")
        return

    result = server.call("skills/list", {"cwds": [repo_root]})
    returned = {
        s["name"]: s
        for group in result.get("data", [])
        for s in group.get("skills", [])
        if s.get("name")
    }

    for name in sorted(expected - returned.keys()):
        fail(f"app-server does not expose skill {name}, which this repo ships")
    present = expected & returned.keys()
    if present:
        ok(f"app-server exposes all {len(present)}/{len(expected)} shipped skills"
           if present == expected else
           f"app-server exposes {len(present)}/{len(expected)} shipped skills")

    # Checked per skill, because the failure this guards against is one new skill
    # landing without an agents/openai.yaml - invisible until someone opens the
    # plugin browser.
    for name in sorted(present):
        check_interface(f"skill {name}", returned[name].get("interface"), SKILL_INTERFACE_FIELDS)


def main() -> int:
    repo_root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    if not os.environ.get("CODEX_HOME"):
        print("  FAIL  CODEX_HOME is unset; refusing to touch a real Codex install",
              file=sys.stderr)
        return 1

    print(f"Probing the codex app-server API against {repo_root}")
    server = AppServer(repo_root)
    try:
        server.initialize()
        validate_plugins(server, repo_root)
        validate_skills(server, repo_root)
    finally:
        server.close()

    print()
    if errors:
        print(f"FAILED: {len(errors)} problem(s) on the Codex app-server surface.",
              file=sys.stderr)
        return 1
    print("PASSED: Codex exposes our install-surface metadata.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
