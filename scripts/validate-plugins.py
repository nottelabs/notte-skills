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
  * every agents/openai.yaml sits beside a SKILL.md, parses, uses only the
    keys Codex and ChatGPT read at both levels, carries the interface fields
    those surfaces render, and keeps short_description in Codex's documented
    25-64 character range

Stdlib only, no third-party dependencies (including no PyYAML: the SKILL.md
frontmatter subset and the agents/openai.yaml subset are parsed directly).

scripts/test-validate-plugins.py exercises the agents/openai.yaml checks
against malformed and incomplete fixtures; both run in CI.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

MARKETPLACE = Path(".claude-plugin/marketplace.json")
CODEX_MARKETPLACE = Path(".agents/plugins/marketplace.json")
CURSOR_MANIFEST = Path(".cursor-plugin/plugin.json")

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
    for field in ("skills", "rules", "logo", "mcpServers"):
        if field in data:
            check_paths(CURSOR_MANIFEST, field, data[field])
    # Cursor loads MCP servers from its own manifest; without this the plugin
    # ships skills that reference a browser the client cannot reach.
    if not data.get("mcpServers"):
        fail(f"{CURSOR_MANIFEST}: no mcpServers, so Cursor installs the skills without them")


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


class YamlError(Exception):
    """Raised for input outside the YAML subset agents/openai.yaml needs."""


def parse_simple_yaml(text: str) -> object:
    """Parse the indentation-based YAML subset used by agents/openai.yaml.

    Handles nested mappings, sequences of mappings, quoted and bare scalars,
    booleans, and comments. Everything else - tabs, flow style, anchors, block
    scalars, multiple documents - raises YamlError rather than being skipped,
    so a construct this parser cannot see is reported instead of silently
    dropped. PyYAML would be the obvious tool, but this script is deliberately
    stdlib-only so it runs in CI with no install step.
    """
    lines: list[tuple[int, str, int]] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise YamlError(f"line {number}: tab in indentation")
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped in ("---", "..."):
            raise YamlError(f"line {number}: document markers are not supported")
        lines.append((len(raw) - len(raw.lstrip()), stripped, number))
    if not lines:
        raise YamlError("no content")

    value, index = _parse_block(lines, 0, lines[0][0])
    if index != len(lines):
        raise YamlError(f"line {lines[index][2]}: unexpected indentation")
    return value


def _parse_block(lines: list[tuple[int, str, int]], index: int, indent: int):
    if lines[index][1].startswith("- "):
        return _parse_sequence(lines, index, indent)
    return _parse_mapping(lines, index, indent)


def _parse_mapping(lines: list[tuple[int, str, int]], index: int, indent: int):
    mapping: dict[str, object] = {}
    while index < len(lines):
        line_indent, content, number = lines[index]
        if line_indent < indent:
            break
        if line_indent > indent:
            raise YamlError(f"line {number}: unexpected indentation")
        if content.startswith("- "):
            raise YamlError(f"line {number}: sequence item where a key was expected")
        key, separator, rest = content.partition(":")
        if not separator:
            raise YamlError(f"line {number}: expected 'key: value'")
        key = key.strip()
        if not key:
            raise YamlError(f"line {number}: empty key")
        if key in mapping:
            raise YamlError(f"line {number}: duplicate key '{key}'")
        rest = rest.strip()
        index += 1
        if rest:
            mapping[key] = _parse_scalar(rest, number)
        elif index < len(lines) and lines[index][0] > indent:
            mapping[key], index = _parse_block(lines, index, lines[index][0])
        else:
            mapping[key] = None
    return mapping, index


def _parse_sequence(lines: list[tuple[int, str, int]], index: int, indent: int):
    items: list[object] = []
    while index < len(lines):
        line_indent, content, number = lines[index]
        if line_indent < indent:
            break
        if line_indent > indent:
            raise YamlError(f"line {number}: unexpected indentation")
        if not content.startswith("- "):
            break
        # Re-present "- key: value" as a mapping line indented past the dash so
        # the item's remaining keys parse as one mapping.
        item_indent = indent + 2
        rewritten = [(item_indent, content[2:].strip(), number)]
        index += 1
        while index < len(lines) and lines[index][0] >= item_indent:
            if lines[index][1].startswith("- "):
                break
            rewritten.append(lines[index])
            index += 1
        item, consumed = _parse_block(rewritten, 0, item_indent)
        if consumed != len(rewritten):
            raise YamlError(f"line {number}: could not parse sequence item")
        items.append(item)
    return items, index


def _parse_scalar(raw: str, number: int) -> object:
    if raw[0] in "|>&*!{[":
        raise YamlError(f"line {number}: unsupported YAML construct '{raw[0]}'")
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    if raw in ("true", "false"):
        return raw == "true"
    return raw


# Nested keys Codex reads, per its own agents/openai.yaml reference. Unknown
# keys are ignored at runtime, which makes a snake_case/camelCase slip - easy
# here, since plugin.json's `interface` block uses camelCase - invisible.
OPENAI_YAML_KEYS = {
    "interface": {
        "display_name",
        "short_description",
        "icon_small",
        "icon_large",
        "brand_color",
        "default_prompt",
    },
    "policy": {"allow_implicit_invocation", "products"},
    "dependencies": {"tools"},
}
DEPENDENCY_TOOL_KEYS = {"type", "value", "description", "transport", "command", "url"}

# Optional in the spec, but the point of shipping these files is to give Codex
# and ChatGPT something to render, so this repo requires them.
REQUIRED_INTERFACE_KEYS = ("display_name", "short_description", "default_prompt")

# Codex documents short_description as a 25-64 character UI blurb.
SHORT_DESCRIPTION_RANGE = (25, 64)


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
        problems = check_openai_yaml(path.read_text(encoding="utf-8"), skill_dir.name)
        if problems:
            for problem in problems:
                fail(f"{rel}: {problem}")
            continue
        _check_metadata_icons(rel, skill_dir, path.read_text(encoding="utf-8"))
        ok(f"{rel}: valid metadata for '{skill_dir.name}'")

    missing = sorted(
        str(skill_dir.relative_to(REPO_ROOT))
        for skill_dir in skill_dirs
        if not (skill_dir / "agents" / "openai.yaml").is_file()
    )
    for skill in missing:
        fail(f"{skill}: no agents/openai.yaml, so Codex and ChatGPT get no skill metadata")


def check_openai_yaml(text: str, skill_name: str) -> list[str]:
    """Return every problem in one agents/openai.yaml, or [] when it is usable.

    Pure and free of repository state so it can be exercised against fixtures
    in scripts/test-validate-plugins.py.
    """
    if not text.strip():
        return ["file is empty"]
    try:
        data = parse_simple_yaml(text)
    except YamlError as exc:
        return [f"could not parse YAML ({exc})"]
    if not isinstance(data, dict):
        return ["top level must be a mapping"]
    if not data:
        return ["no top-level keys found"]

    problems: list[str] = []
    unknown = sorted(set(data) - set(OPENAI_YAML_KEYS))
    if unknown:
        allowed = ", ".join(sorted(OPENAI_YAML_KEYS))
        problems.append(
            f"unknown top-level key(s) {', '.join(unknown)}; Codex reads only: {allowed}"
        )
    for section, value in data.items():
        if section not in OPENAI_YAML_KEYS:
            continue
        if not isinstance(value, dict):
            problems.append(f"'{section}' must be a mapping, got {_describe(value)}")
            continue
        unknown_nested = sorted(set(value) - OPENAI_YAML_KEYS[section])
        if unknown_nested:
            allowed = ", ".join(sorted(OPENAI_YAML_KEYS[section]))
            problems.append(
                f"unknown key(s) {', '.join(f'{section}.{key}' for key in unknown_nested)}; "
                f"Codex reads only: {allowed}"
            )

    problems.extend(_check_interface(data, skill_name))
    problems.extend(_check_policy(data.get("policy")))
    problems.extend(_check_dependencies(data.get("dependencies")))
    return problems


def _check_interface(data: dict, skill_name: str) -> list[str]:
    if "interface" not in data:
        return ["no 'interface' section, so the skill renders with no display metadata"]
    interface = data["interface"]
    if not isinstance(interface, dict):
        return []  # already reported as a non-mapping section
    problems: list[str] = []
    for key in REQUIRED_INTERFACE_KEYS:
        value = interface.get(key)
        if not isinstance(value, str) or not value.strip():
            problems.append(f"interface.{key} is missing or empty")
    short = interface.get("short_description")
    if isinstance(short, str) and short.strip():
        low, high = SHORT_DESCRIPTION_RANGE
        if not low <= len(short) <= high:
            problems.append(
                f"interface.short_description is {len(short)} characters; "
                f"Codex documents {low}-{high}"
            )
    prompt = interface.get("default_prompt")
    if isinstance(prompt, str) and prompt.strip() and f"${skill_name}" not in prompt:
        problems.append(
            f"interface.default_prompt must invoke the skill as '${skill_name}'"
        )
    return problems


def _check_policy(policy: object) -> list[str]:
    if not isinstance(policy, dict):
        return []
    allow = policy.get("allow_implicit_invocation")
    if "allow_implicit_invocation" in policy and not isinstance(allow, bool):
        return [
            "policy.allow_implicit_invocation must be true or false, "
            f"got {_describe(allow)}"
        ]
    return []


def _check_dependencies(dependencies: object) -> list[str]:
    if not isinstance(dependencies, dict):
        return []
    tools = dependencies.get("tools")
    if tools is None:
        return []
    if not isinstance(tools, list):
        return [f"dependencies.tools must be a list, got {_describe(tools)}"]
    problems: list[str] = []
    for index, tool in enumerate(tools):
        where = f"dependencies.tools[{index}]"
        if not isinstance(tool, dict):
            problems.append(f"{where} must be a mapping, got {_describe(tool)}")
            continue
        unknown = sorted(set(tool) - DEPENDENCY_TOOL_KEYS)
        if unknown:
            allowed = ", ".join(sorted(DEPENDENCY_TOOL_KEYS))
            problems.append(
                f"{where}: unknown key(s) {', '.join(unknown)}; Codex reads only: {allowed}"
            )
        for key in ("type", "value"):
            if not tool.get(key):
                problems.append(f"{where}.{key} is missing or empty")
        if tool.get("type") not in (None, "mcp"):
            problems.append(f"{where}.type must be 'mcp'; got {tool['type']!r}")
    return problems


def _check_metadata_icons(rel: Path, skill_dir: Path, text: str) -> None:
    """Check that interface icon paths resolve, relative to the skill directory."""
    try:
        data = parse_simple_yaml(text)
    except YamlError:
        return
    interface = data.get("interface") if isinstance(data, dict) else None
    if not isinstance(interface, dict):
        return
    prefix = skill_dir.relative_to(REPO_ROOT)
    for key in ("icon_small", "icon_large"):
        value = interface.get(key)
        if isinstance(value, str) and value:
            check_path(rel, f"interface.{key}", f"./{prefix}/{value.removeprefix('./')}")


def _describe(value: object) -> str:
    if value is None:
        return "nothing"
    return {dict: "a mapping", list: "a list", bool: "a boolean"}.get(
        type(value), f"the value {value!r}"
    )


def validate_skill_links() -> None:
    """Every relative markdown link inside a skill must resolve.

    Renaming a skill directory silently breaks the cross-references that point
    at it - notte-functions-doctor links into notte-functions-build, and both
    link back into notte-browser. Nothing else in this repo would catch that,
    so check it here.

    Only relative targets are followed. External URLs, bare anchors, and the
    literal `...` placeholder used in notte-migrate's report templates are
    skipped.
    """
    link_re = re.compile(r"\[[^\]]+\]\((?!https?://|#|mailto:)([^)#\s]+)(?:#[^)]*)?\)")
    md_files = sorted(
        path
        for path in (REPO_ROOT / "plugins").rglob("*.md")
        if path.name != "CHANGELOG.md"
    )
    if not md_files:
        fail("plugins/: no markdown files found to link-check")
        return

    broken = 0
    for md in md_files:
        rel = md.relative_to(REPO_ROOT)
        for match in link_re.finditer(md.read_text(encoding="utf-8")):
            target = match.group(1).strip()
            if target == "..." or not target:
                continue
            if not (md.parent / target).exists():
                fail(f"{rel}: link target does not exist -> {target}")
                broken += 1
    if not broken:
        ok(f"{len(md_files)} skill markdown file(s): all relative links resolve")


def main() -> int:
    print(f"Validating {REPO_ROOT}\n")
    validate_marketplace()
    validate_codex_marketplace()
    validate_cursor_manifest()
    validate_plugin_manifests()
    validate_skills()
    validate_skill_metadata()
    validate_skill_links()

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
