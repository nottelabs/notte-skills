#!/usr/bin/env python3
"""Execute the research page-reading example without contacting Notte."""

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "plugins/notte/skills/notte-research/SKILL.md"
MOCK = '''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
with open(os.environ["NOTTE_TEST_LOG"], "a") as log:
    log.write(json.dumps(args) + "\\n")
if args[:2] == ["sessions", "start"]:
    print(os.environ.get("NOTTE_TEST_SESSION", '{"session_id":"sess_read"}'))
elif args[:2] == ["sessions", "stop"]:
    sys.exit(0 if "--yes" in args else 98)
elif args[:2] == ["page", "goto"]:
    sys.exit(int(os.environ.get("NOTTE_TEST_GOTO_EXIT", "0")))
elif args[:2] == ["page", "scrape"]:
    print('{"content":"Read the documentation"}')
    sys.exit(int(os.environ.get("NOTTE_TEST_SCRAPE_EXIT", "0")))
else:
    sys.exit(99)
'''


class ResearchReadTests(unittest.TestCase):
    def run_example(self, *, with_jq=True, **overrides):
        import json

        example = re.search(r"```bash\n(.*?)\n```", SKILL.read_text(), re.S)[1]
        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp)
            cli = workdir / "notte"
            cli.write_text(MOCK)
            cli.chmod(0o755)
            # Keep the mock runnable, but make jq genuinely unavailable even
            # on CI machines that have it installed globally.
            if not with_jq:
                (workdir / "python3").symlink_to(sys.executable)
            path = f"{temp}:{os.environ['PATH']}" if with_jq else temp
            log = workdir / "calls.jsonl"
            result = subprocess.run(
                [shutil.which("bash"), "-c", example], cwd=workdir, capture_output=True,
                text=True, timeout=10, check=False,
                env={**os.environ, "PATH": path,
                     "NOTTE_TEST_LOG": str(log), **overrides},
            )
            calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
            return result, calls

    def test_missing_parser_does_not_start_a_billed_session(self):
        result, calls = self.run_example(with_jq=False)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("jq is required", result.stderr)
        self.assertEqual(calls, [])

    def test_standalone_skill_has_no_missing_sibling_links(self):
        import contextlib
        import importlib.util
        import io

        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location("validator", ROOT / "scripts/validate-plugins.py")
        validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validator)
        with tempfile.TemporaryDirectory() as temp:
            isolated = Path(temp)
            shutil.copytree(SKILL.parent, isolated / "plugins/notte/skills/notte-research")
            validator.REPO_ROOT = isolated
            with contextlib.redirect_stdout(io.StringIO()):
                validator.validate_skill_links()
            self.assertEqual(validator.errors, [])

    def test_read_uses_explicit_session_and_releases_it(self):
        result, calls = self.run_example()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Read the documentation", result.stdout)
        self.assertEqual([call[:2] for call in calls], [
            ["sessions", "start"], ["page", "goto"],
            ["page", "scrape"], ["sessions", "stop"],
        ])
        for call in calls[1:]:
            self.assertEqual(call[call.index("--session-id") + 1], "sess_read")
        self.assertIn("--yes", calls[-1])

    def test_page_failures_propagate_and_release_session(self):
        for stage in ("GOTO", "SCRAPE"):
            with self.subTest(stage=stage):
                result, calls = self.run_example(**{f"NOTTE_TEST_{stage}_EXIT": "7"})
                self.assertEqual(result.returncode, 7, result.stderr)
                self.assertEqual(calls[-1], ["sessions", "stop", "--session-id", "sess_read", "--yes"])
                if stage == "GOTO":
                    self.assertFalse(any(call[:2] == ["page", "scrape"] for call in calls))

    def test_invalid_session_never_reaches_page_commands(self):
        for response in ("{}", '{"session_id":null}', '{"session_id":""}', '{"session_id":42}', "{"):
            with self.subTest(response=response):
                result, calls = self.run_example(NOTTE_TEST_SESSION=response)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(calls, [["sessions", "start", "-o", "json"]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
