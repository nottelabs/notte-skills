#!/usr/bin/env python3
"""Execute the published setup example with a fake CLI, without cloud access."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent / "plugins/notte/skills/notte-browser/SKILL.md"
MOCK_NOTTE = r'''#!/bin/bash
set -euo pipefail
printf '%s\n' "$*" >> "$NOTTE_TEST_LOG"
case "$1 $2" in
  "auth status") exit "${NOTTE_TEST_AUTH_EXIT:-0}" ;;
  "sessions start") printf '%s\n' "$NOTTE_TEST_SESSION_RESPONSE" ;;
  "page goto") exit "${NOTTE_TEST_GOTO_EXIT:-0}" ;;
  "page observe") printf '%s\n' '{"url":"https://docs.notte.cc/","elements":[]}' ;;
  "page screenshot") ;;
  "sessions stop")
    # Model the real CLI's confirmation requirement without waiting for stdin.
    case " $* " in
      *" --yes "*) ;;
      *) echo "Stop requires confirmation" >&2; exit 98 ;;
    esac
    ;;
  *) echo "Unexpected setup action: $*" >&2; exit 99 ;;
esac
'''


class BrowserSetupTests(unittest.TestCase):
    def run_setup(self, **overrides: str) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        section = SKILL.read_text().split("## Quick Start\n", 1)[1].split("\n## ", 1)[0]
        example = re.search(r"```bash\n(.*?)\n```", section, re.DOTALL)
        self.assertIsNotNone(example, "setup example must be executable")
        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp)
            cli = workdir / "notte"
            cli.write_text(MOCK_NOTTE)
            cli.chmod(0o755)
            log = workdir / "commands.log"
            env = {
                **os.environ,
                "PATH": f"{workdir}:{os.environ['PATH']}",
                "NOTTE_TEST_LOG": str(log),
                "NOTTE_TEST_SESSION_RESPONSE": '{"session_id":"sess_setup"}',
                **overrides,
            }
            result = subprocess.run(
                ["bash", "-c", example[1]], cwd=workdir, env=env,
                capture_output=True, text=True, timeout=10, check=False,
            )
            return result, log.read_text().splitlines()

    def test_setup_succeeds_on_a_page_without_interactive_elements(self) -> None:
        result, commands = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"elements":[]', result.stdout)
        targeted = [c for c in commands if c.startswith("page ") or c.startswith("sessions stop ")]
        self.assertTrue(targeted)
        for command in targeted:
            self.assertIn("--session-id sess_setup", command)
        self.assertEqual(commands[-1], "sessions stop --session-id sess_setup --yes")
        self.assertEqual(sum(c.startswith("sessions stop ") for c in commands), 1)

    def test_failed_authentication_does_not_start_a_session(self) -> None:
        result, commands = self.run_setup(NOTTE_TEST_AUTH_EXIT="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(commands, ["auth status"])

    def test_failed_navigation_still_releases_the_session(self) -> None:
        result, commands = self.run_setup(NOTTE_TEST_GOTO_EXIT="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(commands[-1], "sessions stop --session-id sess_setup --yes")
        self.assertFalse(any(c.startswith("page observe") for c in commands))

    def test_invalid_session_ids_do_not_reach_page_commands(self) -> None:
        for response in ("{}", '{"session_id":null}', '{"session_id":""}', '{"session_id":123}', "{"):
            with self.subTest(response=response):
                result, commands = self.run_setup(NOTTE_TEST_SESSION_RESPONSE=response)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(commands, ["auth status", "sessions start -o json"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
