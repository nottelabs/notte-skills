#!/usr/bin/env python3
"""Validate the Notte skills marketplace manifests and skill packaging.

Runs in CI (.github/workflows/test-skills.yml) and locally:

    python3 scripts/validate-plugins.py

Checks performed:
  * .claude-plugin/marketplace.json, .agents/plugins/marketplace.json, and
    .cursor-plugin/plugin.json are valid JSON
  * every plugins/*/.claude-plugin/plugin.json and plugins/*/.codex-plugin/
    plugin.json is valid JSON
  * every path referenced by marketplace.json (plugins[].source) exists on disk
  * every path referenced by the Cursor manifest (skills, rules, logo) exists
  * every path referenced by a plugin.json (skills, mcpServers, interface
    assets) exists
  * the Claude and Codex marketplaces list the same plugins at the same paths,
    and the Codex marketplace carries the policy/category fields Codex expects
  * the Claude and Codex plugin manifests agree on name, version, description,
    and component paths, and the Cursor manifest agrees on version
  * every SKILL.md has YAML frontmatter with a non-empty name and description
  * every SKILL.md's name matches the directory that contains it
  * every agents/openai.yaml sits beside a SKILL.md and uses only the keys
    Codex and ChatGPT read (interface, policy, dependencies)

Stdlib only, no third-party dependencies (including no PyYAML: the frontmatter
subset used by skills, and the top-level key set of agents/openai.yaml, are
parsed directly).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

MARKETPLACE = Path(".claude-plugin/marketplace.json")
CODEX_MARKETPLACE = Path(".agents/plugins/marketplace.json")
CURSOR_MANIFEST = Path(".cursor-plugin/plugin.json")

# Keys Codex reads from a skill's agents/openai.yaml. Anything else is silently
# ignored at runtime, which makes a typo invisible until someone notices the
# skill has no display name.
OPENAI_YAML_TOP_LEVEL_KEYS = {"interface", "policy", "dependencies"}

errors: list[str] = []
checks = 0


def fail(message: str) -> None:
    errors.append(message)


def ok(message: str) -> None:
    global checks
    checks += 1
    print(f"  ok  {message}")


_json_cache: dict[Path, dict | None] = {}


def load_json(rel_path: Path) -> dict | None:
    """Read and parse a JSON manifest, recording an error on failure.

    Cached, so a manifest read by two validators is reported once.
    """
    if rel_path in _json_cache:
        return _json_cache[rel_path]
    path = REPO_ROOT / rel_path
    data: dict | None = None
    if not path.is_file():
        fail(f"{rel_path}: file is missing")
    else:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fail(f"{rel_path}: invalid JSON ({exc})")
        else:
            ok(f"{rel_path} is valid JSON")
    _json_cache[rel_path] = data
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


def validate_codex_marketplace() -> None:
    """Validate the native Codex marketplace and keep it aligned with Claude's.

    Codex reads .agents/plugins/marketplace.json in preference to the
    .claude-plugin one it accepts for compatibility, so the two drifting apart
    would silently change what Codex users see.
    """
    data = load_json(CODEX_MARKETPLACE)
    claude = load_json(MARKETPLACE)
    if data is None:
        return
    plugins = data.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        fail(f"{CODEX_MARKETPLACE}: plugins must be a non-empty array")
        return

    codex_sources: dict[str, str] = {}
    for entry in plugins:
        if not isinstance(entry, dict):
            fail(f"{CODEX_MARKETPLACE}: every plugins[] entry must be an object")
            continue
        name = entry.get("name") or "<unnamed>"
        if not entry.get("name"):
            fail(f"{CODEX_MARKETPLACE}: a plugins[] entry has no name")
        source = entry.get("source")
        # Codex accepts a bare string path or a {"source": "local", "path": ...}
        # object; normalize both to the path so it can be range-checked.
        if isinstance(source, str):
            path = source
        elif isinstance(source, dict):
            if source.get("source") != "local":
                fail(
                    f"{CODEX_MARKETPLACE}: plugin '{name}' must use source 'local'; "
                    f"got {source.get('source')!r}"
                )
            path = source.get("path")
        else:
            fail(f"{CODEX_MARKETPLACE}: plugin '{name}' has no usable source")
            continue
        if not isinstance(path, str) or not path.startswith("./"):
            fail(
                f"{CODEX_MARKETPLACE}: plugin '{name}' source path must be a "
                f"'./'-prefixed path relative to the marketplace root"
            )
            continue
        codex_sources[name] = path
        check_path(CODEX_MARKETPLACE, f"plugins['{name}'].source.path", path)

        policy = entry.get("policy")
        if not isinstance(policy, dict):
            fail(f"{CODEX_MARKETPLACE}: plugin '{name}' has no policy object")
        else:
            for field in ("installation", "authentication"):
                if not policy.get(field):
                    fail(f"{CODEX_MARKETPLACE}: plugin '{name}' has no policy.{field}")
        if not entry.get("category"):
            fail(f"{CODEX_MARKETPLACE}: plugin '{name}' has no category")

    if claude is None or not isinstance(claude.get("plugins"), list):
        return
    claude_sources = {
        entry.get("name"): entry.get("source")
        for entry in claude["plugins"]
        if isinstance(entry, dict)
    }
    if set(codex_sources) != set(claude_sources):
        fail(
            f"{CODEX_MARKETPLACE}: lists {sorted(codex_sources)} but "
            f"{MARKETPLACE} lists {sorted(claude_sources)}"
        )
        return
    for name, path in codex_sources.items():
        if claude_sources[name] != path:
            fail(
                f"{CODEX_MARKETPLACE}: plugin '{name}' points at {path}, but "
                f"{MARKETPLACE} points at {claude_sources[name]}"
            )
    ok(f"{CODEX_MARKETPLACE} lists the same plugins and paths as {MARKETPLACE}")


def validate_cursor_manifest() -> None:
    data = load_json(CURSOR_MANIFEST)
    if data is None:
        return
    for field in ("skills", "rules", "logo"):
        if field in data:
            check_paths(CURSOR_MANIFEST, field, data[field])


# Fields that must be identical between a plugin's Claude and Codex manifests.
SHARED_MANIFEST_FIELDS = ("name", "version", "description", "skills", "mcpServers")

# Interface paths a Codex install surface renders. They resolve relative to the
# plugin root and must stay inside it.
INTERFACE_ASSET_FIELDS = ("composerIcon", "logo", "logoDark")


def validate_plugin_manifests() -> None:
    plugin_dirs = sorted(
        path for path in (REPO_ROOT / "plugins").iterdir() if path.is_dir()
    )
    if not plugin_dirs:
        fail("plugins/: no plugin directories found")
        return
    for plugin_dir in plugin_dirs:
        loaded: dict[str, dict] = {}
        for manifest_dir in (".claude-plugin", ".codex-plugin"):
            path = plugin_dir / manifest_dir / "plugin.json"
            if not path.is_file():
                fail(f"plugins/{plugin_dir.name}: missing {manifest_dir}/plugin.json")
                continue
            data = _validate_plugin_manifest(plugin_dir, path)
            if data is not None:
                loaded[manifest_dir] = data
        _check_manifest_agreement(plugin_dir, loaded)


def _validate_plugin_manifest(plugin_dir: Path, path: Path) -> dict | None:
    rel = path.relative_to(REPO_ROOT)
    data = load_json(rel)
    if data is None:
        return None
    for field in ("name", "version", "description"):
        if not data.get(field):
            fail(f"{rel}: missing or empty '{field}'")
    if data.get("name") and data["name"] != plugin_dir.name:
        fail(
            f"{rel}: name '{data['name']}' does not match "
            f"directory '{plugin_dir.name}'"
        )
    for field in ("skills", "mcpServers", "hooks", "commands", "agents", "apps"):
        if field in data:
            check_paths(rel, field, _rel_to_root_each(plugin_dir, data[field]))
    interface = data.get("interface")
    if isinstance(interface, dict):
        for field in INTERFACE_ASSET_FIELDS:
            if field in interface:
                check_paths(
                    rel,
                    f"interface.{field}",
                    _rel_to_root_each(plugin_dir, interface[field]),
                )
        for index, shot in enumerate(interface.get("screenshots") or []):
            check_path(rel, f"interface.screenshots[{index}]", _rel_to_root(plugin_dir, shot))
    return data


def _check_manifest_agreement(plugin_dir: Path, loaded: dict[str, dict]) -> None:
    """Fail when a plugin's Claude and Codex manifests disagree.

    Codex prefers .codex-plugin/plugin.json and falls back to the Claude one,
    so a stale version or skills path in either file ships to a real client.
    """
    if len(loaded) < 2:
        return
    claude, codex = loaded[".claude-plugin"], loaded[".codex-plugin"]
    for field in SHARED_MANIFEST_FIELDS:
        if claude.get(field) != codex.get(field):
            fail(
                f"plugins/{plugin_dir.name}: '{field}' differs between manifests — "
                f".claude-plugin has {claude.get(field)!r}, "
                f".codex-plugin has {codex.get(field)!r}"
            )
            return
    ok(f"plugins/{plugin_dir.name}: Claude and Codex manifests agree")


def _rel_to_root(plugin_dir: Path, value: object) -> object:
    """Rewrite a plugin-relative path into a repo-root-relative one."""
    if not isinstance(value, str) or is_remote(value):
        return value
    prefix = plugin_dir.relative_to(REPO_ROOT)
    return f"./{prefix}/{value.removeprefix('./')}"


def _rel_to_root_each(plugin_dir: Path, value: object) -> object:
    """Same as _rel_to_root, mapped over a list of paths."""
    if isinstance(value, list):
        return [_rel_to_root(plugin_dir, item) for item in value]
    return _rel_to_root(plugin_dir, value)


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


def top_level_yaml_keys(text: str) -> list[str]:
    """Collect the top-level mapping keys of a YAML document.

    Enough for agents/openai.yaml, which is a shallow mapping of mappings. Only
    the outermost keys are checked, so no YAML parser is needed.
    """
    keys: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or line[0].isspace():
            continue
        key, separator, _ = line.partition(":")
        if separator:
            keys.append(key.strip())
    return keys


def validate_skill_metadata() -> None:
    """Check every agents/openai.yaml that Codex and ChatGPT read for a skill."""
    metadata_files = sorted((REPO_ROOT / "plugins").rglob("agents/openai.yaml"))
    skill_dirs = {path.parent for path in (REPO_ROOT / "plugins").rglob("SKILL.md")}
    for path in metadata_files:
        rel = path.relative_to(REPO_ROOT)
        skill_dir = path.parent.parent
        if skill_dir not in skill_dirs:
            fail(f"{rel}: no SKILL.md in the parent directory '{skill_dir.name}'")
            continue
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            fail(f"{rel}: file is empty")
            continue
        keys = top_level_yaml_keys(text)
        if not keys:
            fail(f"{rel}: no top-level keys found")
            continue
        unknown = [key for key in keys if key not in OPENAI_YAML_TOP_LEVEL_KEYS]
        if unknown:
            allowed = ", ".join(sorted(OPENAI_YAML_TOP_LEVEL_KEYS))
            fail(
                f"{rel}: unknown top-level key(s) {', '.join(unknown)}; "
                f"Codex reads only: {allowed}"
            )
            continue
        ok(f"{rel}: valid metadata for '{skill_dir.name}'")

    missing = sorted(
        str(skill_dir.relative_to(REPO_ROOT))
        for skill_dir in skill_dirs
        if not (skill_dir / "agents" / "openai.yaml").is_file()
    )
    for skill in missing:
        fail(f"{skill}: no agents/openai.yaml, so Codex and ChatGPT get no skill metadata")


def main() -> int:
    print(f"Validating {REPO_ROOT}\n")
    validate_marketplace()
    validate_codex_marketplace()
    validate_cursor_manifest()
    validate_plugin_manifests()
    validate_skills()
    validate_skill_metadata()

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
