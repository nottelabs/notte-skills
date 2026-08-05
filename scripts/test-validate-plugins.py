#!/usr/bin/env python3
"""Fixtures for the agents/openai.yaml checks in validate-plugins.py.

Runs in CI (.github/workflows/test-skills.yml) and locally:

    python3 scripts/test-validate-plugins.py

The metadata checker parses a YAML subset by hand rather than depending on
PyYAML, and it enforces constraints Codex documents but does not itself
reject - an unreadable file and a file with a camelCase key both load "fine"
at runtime and simply render nothing. These fixtures pin down what the checker
accepts, so a future relaxation of it fails here instead of shipping.

Stdlib only, matching validate-plugins.py.
"""

from __future__ import annotations

import importlib.util
import sys
import textwrap
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parent / "validate-plugins.py"
_spec = importlib.util.spec_from_file_location("validate_plugins", MODULE_PATH)
assert _spec and _spec.loader
validate_plugins = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate_plugins)

check_openai_yaml = validate_plugins.check_openai_yaml
parse_simple_yaml = validate_plugins.parse_simple_yaml
YamlError = validate_plugins.YamlError

VALID = """\
interface:
  display_name: "Notte Browser"
  short_description: "Drive a Notte cloud browser from the CLI"
  default_prompt: "Use $notte-browser to scrape this page."
"""


def fixture(body: str) -> str:
    return textwrap.dedent(body)


class ParserTests(unittest.TestCase):
    def test_parses_nested_mappings_and_scalars(self) -> None:
        parsed = parse_simple_yaml(
            fixture(
                """\
                interface:
                  display_name: "Name"
                  brand_color: '#000000'
                policy:
                  allow_implicit_invocation: false
                """
            )
        )
        self.assertEqual(
            parsed,
            {
                "interface": {"display_name": "Name", "brand_color": "#000000"},
                "policy": {"allow_implicit_invocation": False},
            },
        )

    def test_parses_a_sequence_of_mappings(self) -> None:
        parsed = parse_simple_yaml(
            fixture(
                """\
                dependencies:
                  tools:
                    - type: "mcp"
                      value: "notte-browser"
                      url: "https://api.notte.cc/mcp"
                    - type: "mcp"
                      value: "anything-api"
                """
            )
        )
        self.assertEqual(
            parsed["dependencies"]["tools"],
            [
                {
                    "type": "mcp",
                    "value": "notte-browser",
                    "url": "https://api.notte.cc/mcp",
                },
                {"type": "mcp", "value": "anything-api"},
            ],
        )

    def test_ignores_comments_and_blank_lines(self) -> None:
        parsed = parse_simple_yaml("# leading\n\ninterface:\n  display_name: \"N\"\n")
        self.assertEqual(parsed, {"interface": {"display_name": "N"}})

    def test_rejects_constructs_it_cannot_represent(self) -> None:
        # Each of these would otherwise be silently dropped, leaving a file that
        # looks validated but carries metadata the checker never saw.
        unsupported = {
            "tab indentation": 'interface:\n\tdisplay_name: "N"\n',
            "block scalar": "interface:\n  display_name: |\n    Name\n",
            "flow mapping": 'interface: {display_name: "N"}\n',
            "anchor": "interface: &ref\n  display_name: \"N\"\n",
            "document marker": '---\ninterface:\n  display_name: "N"\n',
            "duplicate key": 'interface:\n  display_name: "A"\n  display_name: "B"\n',
            "ragged indentation": 'interface:\n  display_name: "A"\n     brand_color: "#000"\n',
            "missing colon": "interface\n",
            "empty document": "# only a comment\n",
        }
        for label, text in unsupported.items():
            with self.subTest(label):
                with self.assertRaises(YamlError):
                    parse_simple_yaml(text)


class MalformedFileTests(unittest.TestCase):
    def test_empty_file_is_reported(self) -> None:
        self.assertEqual(check_openai_yaml("   \n", "notte-browser"), ["file is empty"])

    def test_unparseable_file_is_reported(self) -> None:
        problems = check_openai_yaml('interface: {display_name: "N"}\n', "notte-browser")
        self.assertTrue(any("could not parse YAML" in p for p in problems))

    def test_scalar_document_is_reported(self) -> None:
        self.assertEqual(
            check_openai_yaml("interface:\n", "notte-browser"),
            ["'interface' must be a mapping, got nothing"],
        )


class UnknownKeyTests(unittest.TestCase):
    def test_unknown_top_level_key(self) -> None:
        problems = check_openai_yaml(VALID + 'policies:\n  x: "y"\n', "notte-browser")
        self.assertTrue(any("unknown top-level key(s) policies" in p for p in problems))

    def test_camel_case_interface_key_is_caught(self) -> None:
        # plugin.json's interface block is camelCase and openai.yaml is
        # snake_case, so this is the mistake most likely to be made here.
        problems = check_openai_yaml(
            fixture(
                """\
                interface:
                  displayName: "Notte Browser"
                  short_description: "Drive a Notte cloud browser from the CLI"
                  default_prompt: "Use $notte-browser to scrape this page."
                """
            ),
            "notte-browser",
        )
        self.assertTrue(any("interface.displayName" in p for p in problems))
        self.assertTrue(any("interface.display_name is missing" in p for p in problems))


class IncompleteInterfaceTests(unittest.TestCase):
    def test_missing_interface_section(self) -> None:
        problems = check_openai_yaml("policy:\n  allow_implicit_invocation: true\n", "s")
        self.assertEqual(problems, ["no 'interface' section, so the skill renders with no display metadata"])

    def test_each_required_field_is_required(self) -> None:
        for key in ("display_name", "short_description", "default_prompt"):
            with self.subTest(key):
                text = "\n".join(
                    line for line in VALID.splitlines() if not line.strip().startswith(key)
                )
                problems = check_openai_yaml(text + "\n", "notte-browser")
                self.assertIn(f"interface.{key} is missing or empty", problems)

    def test_empty_value_counts_as_missing(self) -> None:
        problems = check_openai_yaml(VALID.replace('"Notte Browser"', '""'), "notte-browser")
        self.assertIn("interface.display_name is missing or empty", problems)

    def test_short_description_length_bounds(self) -> None:
        low, high = validate_plugins.SHORT_DESCRIPTION_RANGE
        for length, expected_bad in ((low - 1, True), (low, False), (high, False), (high + 1, True)):
            with self.subTest(length=length):
                text = VALID.replace(
                    "Drive a Notte cloud browser from the CLI", "x" * length
                )
                problems = check_openai_yaml(text, "notte-browser")
                self.assertEqual(
                    any("short_description is" in p for p in problems), expected_bad
                )

    def test_default_prompt_must_invoke_the_skill(self) -> None:
        problems = check_openai_yaml(
            VALID.replace("$notte-browser", "the browser skill"), "notte-browser"
        )
        self.assertIn(
            "interface.default_prompt must invoke the skill as '$notte-browser'", problems
        )

    def test_valid_fixture_is_accepted(self) -> None:
        self.assertEqual(check_openai_yaml(VALID, "notte-browser"), [])


class PolicyAndDependencyTests(unittest.TestCase):
    def test_non_boolean_policy_is_reported(self) -> None:
        problems = check_openai_yaml(
            VALID + 'policy:\n  allow_implicit_invocation: "no"\n', "notte-browser"
        )
        self.assertTrue(
            any("allow_implicit_invocation must be true or false" in p for p in problems)
        )

    def test_boolean_policy_is_accepted(self) -> None:
        self.assertEqual(
            check_openai_yaml(
                VALID + "policy:\n  allow_implicit_invocation: false\n", "notte-browser"
            ),
            [],
        )

    def test_incomplete_tool_dependency_is_reported(self) -> None:
        problems = check_openai_yaml(
            VALID + 'dependencies:\n  tools:\n    - type: "mcp"\n', "notte-browser"
        )
        self.assertIn("dependencies.tools[0].value is missing or empty", problems)

    def test_unsupported_dependency_type_is_reported(self) -> None:
        problems = check_openai_yaml(
            VALID + 'dependencies:\n  tools:\n    - type: "cli"\n      value: "notte"\n',
            "notte-browser",
        )
        self.assertTrue(any("must be 'mcp'" in p for p in problems))

    def test_unknown_dependency_key_is_reported(self) -> None:
        problems = check_openai_yaml(
            VALID
            + 'dependencies:\n  tools:\n    - type: "mcp"\n      value: "n"\n      uri: "x"\n',
            "notte-browser",
        )
        self.assertTrue(any("unknown key(s) uri" in p for p in problems))

    def test_complete_tool_dependency_is_accepted(self) -> None:
        self.assertEqual(
            check_openai_yaml(
                VALID
                + fixture(
                    """\
                    dependencies:
                      tools:
                        - type: "mcp"
                          value: "notte-browser"
                          description: "Hosted Notte MCP server"
                          transport: "streamable_http"
                          url: "https://api.notte.cc/mcp"
                    """
                ),
                "notte-browser",
            ),
            [],
        )


class ShippedFileTests(unittest.TestCase):
    def test_every_metadata_file_in_the_repository_passes(self) -> None:
        repo_root = MODULE_PATH.parent.parent
        paths = sorted((repo_root / "plugins").rglob("agents/openai.yaml"))
        self.assertTrue(paths, "no agents/openai.yaml files found")
        for path in paths:
            with self.subTest(path.relative_to(repo_root)):
                skill_name = path.parent.parent.name
                problems = check_openai_yaml(path.read_text(encoding="utf-8"), skill_name)
                self.assertEqual(problems, [])


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
