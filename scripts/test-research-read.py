#!/usr/bin/env python3
"""Execute the research page-reading example without contacting Notte."""

import os
from pathlib import Path
import re
import subprocess
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
    def run_example(self, **overrides):
        import json

        example = re.search(r"```bash\n(.*?)\n```", SKILL.read_text(), re.S)[1]
        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp)
            cli = workdir / "notte"
            cli.write_text(MOCK)
            cli.chmod(0o755)
            log = workdir / "calls.jsonl"
            result = subprocess.run(
                ["bash", "-c", example], cwd=workdir, capture_output=True,
                text=True, timeout=10, check=False,
                env={**os.environ, "PATH": f"{temp}:{os.environ['PATH']}",
                     "NOTTE_TEST_LOG": str(log), **overrides},
            )
            return result, [json.loads(line) for line in log.read_text().splitlines()]

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
