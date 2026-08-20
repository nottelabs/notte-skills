#!/usr/bin/env python3
"""Behavior tests for explicit session IDs in the browser shell templates."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = REPO_ROOT / "plugins/notte/skills/notte-browser/templates"
TEMPLATES = {
    "authenticated-session.sh": {"NOTTE_VAULT_ID": "vault_test"},
    "data-extraction.sh": {},
    "form-automation.sh": {},
}

MOCK_NOTTE = r"""#!/bin/bash
set -euo pipefail

printf '%q ' "$@" >> "$NOTTE_TEST_LOG"
printf '\n' >> "$NOTTE_TEST_LOG"

case "${1:-} ${2:-}" in
    "sessions start")
        printf '%s\n' "$NOTTE_TEST_SESSION_RESPONSE"
        ;;
    "sessions cookies")
        printf '[]\n'
        ;;
    "page observe")
        printf '{"url":"https://example.com/dashboard"}\n'
        ;;
    "page scrape")
        printf '%s\n' "${NOTTE_TEST_SCRAPE_RESPONSE:-Thank you}"
        ;;
esac
"""


class BrowserTemplateTests(unittest.TestCase):
    def run_template(
        self, template_name: str, session_response: str
    ) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            bin_dir = workdir / "bin"
            bin_dir.mkdir()
            mock_notte = bin_dir / "notte"
            mock_notte.write_text(MOCK_NOTTE, encoding="utf-8")
            mock_notte.chmod(0o755)

            log_path = workdir / "notte.log"
            env = os.environ.copy()
            env.update(TEMPLATES[template_name])
            env.update(
                {
                    "PATH": f"{bin_dir}:{env['PATH']}",
                    "NOTTE_TEST_LOG": str(log_path),
                    "NOTTE_TEST_SESSION_RESPONSE": session_response,
                    "NOTTE_TEST_SCRAPE_RESPONSE": (
                        "[]" if template_name == "data-extraction.sh" else "Thank you"
                    ),
                }
            )

            completed = subprocess.run(
                ["bash", str(TEMPLATE_DIR / template_name)],
                cwd=workdir,
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            commands = log_path.read_text(encoding="utf-8").splitlines()
            return completed, commands

    def test_session_id_is_propagated_to_actions_and_cleanup(self) -> None:
        for template_name in TEMPLATES:
            with self.subTest(template=template_name):
                completed, commands = self.run_template(
                    template_name, '{"session_id":"sess_test"}'
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)

                targeted = [
                    command
                    for command in commands
                    if command.startswith("page ")
                    or command.startswith("sessions stop ")
                    or command.startswith("sessions cookies")
                ]
                self.assertTrue(targeted, "mock did not observe session-targeted commands")
                for command in targeted:
                    self.assertIn("--session-id sess_test", command)

                cleanup = [
                    command for command in commands if command.startswith("sessions stop ")
                ]
                self.assertEqual(len(cleanup), 1)
                self.assertIn("--session-id sess_test", cleanup[0])

    def test_invalid_session_responses_stop_before_browser_actions(self) -> None:
        invalid_responses = ("{}", '{"session_id":123}', "{")
        for template_name in TEMPLATES:
            for response in invalid_responses:
                with self.subTest(template=template_name, response=response):
                    completed, commands = self.run_template(template_name, response)
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertFalse(
                        any(command.startswith("page ") for command in commands),
                        commands,
                    )
                    self.assertFalse(
                        any(command.startswith("sessions stop ") for command in commands),
                        commands,
                    )

    def test_authenticated_template_uses_named_vault_fields(self) -> None:
        completed, commands = self.run_template(
            "authenticated-session.sh", '{"session_id":"sess_test"}'
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

        fills = [command for command in commands if command.startswith("page fill ")]
        self.assertTrue(
            any("--vault-field email" in command for command in fills), fills
        )
        self.assertTrue(
            any("--vault-field password" in command for command in fills), fills
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
