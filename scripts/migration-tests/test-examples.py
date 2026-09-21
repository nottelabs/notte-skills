"""Execute the documented Python example with fault-injecting clients, offline."""

from __future__ import annotations

import re
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

DOC = (
    Path(__file__).resolve().parents[2]
    / "plugins/notte-migrate/skills/migrate-to-notte/references/notte-sessions.md"
)
EXAMPLES = re.findall(r"```python\n(.*?)```", DOC.read_text(), re.DOTALL)
if len(EXAMPLES) != 1:
    raise RuntimeError("Expected one Python lifecycle example")


class ExampleTests(unittest.TestCase):
    def run_case(
        self,
        failures=(),
        *,
        empty_page=False,
        missing_context=False,
        cancellation=False,
    ):
        calls = []
        errors = {name: RuntimeError(f"{name} failed") for name in failures}
        if cancellation:
            errors["goto"] = KeyboardInterrupt()

        def hit(name):
            calls.append(name)
            if name in errors:
                raise errors[name]

        page = types.SimpleNamespace(
            goto=lambda url: hit("goto"),
            title=lambda: (hit("title"), "Expected application title")[1],
        )
        context = types.SimpleNamespace(
            pages=[] if empty_page else [page],
            new_page=lambda: (hit("new_page"), page)[1],
        )
        browser = types.SimpleNamespace(
            contexts=[] if missing_context else [context],
            close=lambda: hit("client_cleanup"),
        )
        session = types.SimpleNamespace(
            start=lambda: hit("start"),
            stop=lambda: hit("stop"),
            cdp_url=lambda: (hit("cdp"), "wss://fixture.invalid/browser")[1],
        )
        playwright = types.SimpleNamespace(
            chromium=types.SimpleNamespace(
                connect_over_cdp=lambda url: (hit("connect"), browser)[1]
            ),
            stop=lambda: hit("playwright_stop"),
        )
        factory = types.SimpleNamespace(
            start=lambda: (hit("playwright_start"), playwright)[1]
        )
        notte_module = types.ModuleType("notte_sdk")
        notte_module.NotteClient = lambda: types.SimpleNamespace(
            Session=lambda **options: session
        )
        playwright_module = types.ModuleType("playwright.sync_api")
        playwright_module.sync_playwright = lambda: factory
        namespace = {}
        with patch.dict(
            sys.modules,
            {
                "notte_sdk": notte_module,
                "playwright": types.ModuleType("playwright"),
                "playwright.sync_api": playwright_module,
            },
        ):
            exec(compile(EXAMPLES[0], str(DOC), "exec"), namespace)  # noqa: S102 - execute repository-owned examples
            if failures:
                expected = errors[failures[0]]
                with self.assertRaises(type(expected)) as caught:
                    namespace["read_title"]("https://fixture.invalid")
                self.assertIs(
                    caught.exception,
                    expected,
                    "Cleanup must not replace the primary error",
                )
            elif missing_context:
                with self.assertRaises((IndexError, RuntimeError)):
                    namespace["read_title"]("https://fixture.invalid")
            else:
                self.assertEqual(
                    namespace["read_title"]("https://fixture.invalid"),
                    "Expected application title",
                )
        self.assertEqual(calls.count("stop"), 0 if "start" in failures else 1)
        connected = not any(
            x in failures for x in ("start", "playwright_start", "cdp", "connect")
        )
        self.assertEqual(calls.count("client_cleanup"), int(connected))
        pw_started = not any(x in failures for x in ("start", "playwright_start"))
        self.assertEqual(calls.count("playwright_stop"), int(pw_started))
        if empty_page:
            self.assertEqual(calls.count("new_page"), 1)

    def test_empty_page_reuses_default_context(self):
        self.run_case(empty_page=True)

    def test_missing_context_cleans_up(self):
        self.run_case(missing_context=True)

    def test_keyboard_interrupt_preserved_through_cleanup_failure(self):
        self.run_case(
            ("goto", "client_cleanup", "stop", "playwright_stop"), cancellation=True
        )


for failures in [
    (),
    ("start",),
    ("playwright_start",),
    ("cdp",),
    ("connect",),
    ("goto",),
    ("title",),
    ("client_cleanup",),
    ("stop",),
    ("playwright_stop",),
    ("goto", "client_cleanup"),
    ("goto", "stop"),
    ("goto", "client_cleanup", "stop", "playwright_stop"),
    ("connect", "stop"),
    ("client_cleanup", "stop"),
    ("stop", "playwright_stop"),
]:

    def case(self, failures=failures):
        self.run_case(failures)

    setattr(ExampleTests, "test_" + ("_and_".join(failures) or "success"), case)

if __name__ == "__main__":
    unittest.main(verbosity=2)
