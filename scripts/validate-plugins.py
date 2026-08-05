#!/usr/bin/env python3
"""Validate the Notte skills marketplace manifests and skill packaging.

Runs in CI (.github/workflows/test-skills.yml) and locally:

    python3 scripts/validate-plugins.py

Checks performed:
  * .claude-plugin/marketplace.json and .cursor-plugin/plugin.json are valid JSON
  * every plugins/*/.claude-plugin/plugin.json is valid JSON
  * every path referenced by marketplace.json (plugins[].source) exists on disk
  * every path referenced by the Cursor manifest (skills, rules, logo) exists
  * every path referenced by a plugin.json (skills, mcpServers) exists
  * every SKILL.md has YAML frontmatter with a non-empty name and description
  * every SKILL.md's name matches the directory that contains it

Stdlib only, no third-party dependencies (including no PyYAML: the frontmatter
subset used by skills is parsed directly).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

MARKETPLACE = Path(".claude-plugin/marketplace.json")
CURSOR_MANIFEST = Path(".cursor-plugin/plugin.json")

errors: list[str] = []
checks = 0


def fail(message: str) -> None:
    errors.append(message)


def ok(message: str) -> None:
    global checks
    checks += 1
    print(f"  ok  {message}")


def load_json(rel_path: Path) -> dict | None:
    """Read and parse a JSON manifest, recording an error on failure."""
    path = REPO_ROOT / rel_path
    if not path.is_file():
        fail(f"{rel_path}: file is missing")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{rel_path}: invalid JSON ({exc})")
        return None
    ok(f"{rel_path} is valid JSON")
    return data


def is_remote(value: str) -> bool:
    return value.startswith(("http://", "https://", "git@", "github:"))


def check_path(rel_path: Path, field: str, value: object) -> None:
    """Assert that a manifest-declared relative path resolves on disk."""
    if not isinstance(value, str):
        fail(f"{rel_path}: {field} must be a string, got {type(value).__name__}")
        return
    if is_remote(value):
        ok(f"{rel_path}: {field} -> {value} (remote, not checked)")
        return
    # removeprefix, not lstrip: lstrip("./") would eat the leading dot of a
    # dotfile path such as "./.mcp.json".
    target = (REPO_ROOT / value.removeprefix("./")).resolve()
    try:
        target.relative_to(REPO_ROOT)
    except ValueError:
        fail(f"{rel_path}: {field} -> {value} escapes the repository root")
        return
    if not target.exists():
        fail(f"{rel_path}: {field} -> {value} does not exist on disk")
        return
    ok(f"{rel_path}: {field} -> {value}")


def check_paths(rel_path: Path, field: str, value: object) -> None:
    """Same as check_path but tolerates a list of paths."""
    if isinstance(value, list):
        for index, item in enumerate(value):
            check_path(rel_path, f"{field}[{index}]", item)
    else:
        check_path(rel_path, field, value)


def parse_frontmatter(text: str) -> dict[str, str] | None:
    """Parse the top-level scalar keys of a YAML frontmatter block.

    Supports plain scalars (`name: value`) and folded/literal block scalars
    (`description: >` followed by an indented body), which is the full range
    used by SKILL.md frontmatter in this repo.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        return None

    fields: dict[str, str] = {}
    key: str | None = None
    block: list[str] = []

    def flush() -> None:
        if key is not None:
            fields[key] = " ".join(part.strip() for part in block).strip()

    for line in lines[1:end]:
        if line.strip() and not line[0].isspace() and ":" in line:
            flush()
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            block = [] if value in (">", "|", ">-", "|-", "") else [value]
        elif key is not None:
            block.append(line)
    flush()
    return fields


def validate_marketplace() -> None:
    data = load_json(MARKETPLACE)
    if data is None:
        return
    plugins = data.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        fail(f"{MARKETPLACE}: plugins must be a non-empty array")
        return
    for entry in plugins:
        if not isinstance(entry, dict):
            fail(f"{MARKETPLACE}: every plugins[] entry must be an object")
            continue
        name = entry.get("name") or "<unnamed>"
        if not entry.get("name"):
            fail(f"{MARKETPLACE}: a plugins[] entry has no name")
        if not entry.get("description"):
            fail(f"{MARKETPLACE}: plugin '{name}' has no description")
        source = entry.get("source")
        if source is None:
            fail(f"{MARKETPLACE}: plugin '{name}' has no source")
            continue
        check_path(MARKETPLACE, f"plugins['{name}'].source", source)


def validate_cursor_manifest() -> None:
    data = load_json(CURSOR_MANIFEST)
    if data is None:
        return
    for field in ("skills", "rules", "logo"):
        if field in data:
            check_paths(CURSOR_MANIFEST, field, data[field])


def validate_plugin_manifests() -> None:
    manifests = sorted((REPO_ROOT / "plugins").glob("*/.claude-plugin/plugin.json"))
    if not manifests:
        fail("plugins/: no plugins/*/.claude-plugin/plugin.json found")
        return
    for path in manifests:
        rel = path.relative_to(REPO_ROOT)
        data = load_json(rel)
        if data is None:
            continue
        for field in ("name", "version", "description"):
            if not data.get(field):
                fail(f"{rel}: missing or empty '{field}'")
        plugin_dir = path.parent.parent
        if data.get("name") and data["name"] != plugin_dir.name:
            fail(
                f"{rel}: name '{data['name']}' does not match "
                f"directory '{plugin_dir.name}'"
            )
        for field in ("skills", "mcpServers", "hooks", "commands", "agents"):
            if field in data:
                value = data[field]
                if isinstance(value, list):
                    for index, item in enumerate(value):
                        check_path(rel, f"{field}[{index}]", _rel_to_root(plugin_dir, item))
                else:
                    check_path(rel, field, _rel_to_root(plugin_dir, value))


def _rel_to_root(plugin_dir: Path, value: object) -> object:
    """Rewrite a plugin-relative path into a repo-root-relative one."""
    if not isinstance(value, str) or is_remote(value):
        return value
    prefix = plugin_dir.relative_to(REPO_ROOT)
    return f"./{prefix}/{value.removeprefix('./')}"


def validate_skills() -> None:
    skill_files = sorted((REPO_ROOT / "plugins").rglob("SKILL.md"))
    if not skill_files:
        fail("plugins/: no SKILL.md files found")
        return
    for path in skill_files:
        rel = path.relative_to(REPO_ROOT)
        fields = parse_frontmatter(path.read_text(encoding="utf-8"))
        if fields is None:
            fail(f"{rel}: missing or unterminated YAML frontmatter block")
            continue
        name = fields.get("name", "").strip()
        description = fields.get("description", "").strip()
        if not name:
            fail(f"{rel}: frontmatter has no non-empty 'name'")
        if not description:
            fail(f"{rel}: frontmatter has no non-empty 'description'")
        directory = path.parent.name
        if name and name != directory:
            fail(f"{rel}: frontmatter name '{name}' does not match directory '{directory}'")
        if name and description and name == directory:
            ok(f"{rel}: name '{name}' matches directory, description present")


def main() -> int:
    print(f"Validating {REPO_ROOT}\n")
    validate_marketplace()
    validate_cursor_manifest()
    validate_plugin_manifests()
    validate_skills()

    print()
    if errors:
        print(f"FAILED: {len(errors)} problem(s) found after {checks} passing check(s):\n")
        for error in errors:
            print(f"  error  {error}")
        return 1
    print(f"PASSED: {checks} check(s), no problems found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
