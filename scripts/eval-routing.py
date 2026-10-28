#!/usr/bin/env python3
"""Emit a blind skill-selection prompt or score an external model's decisions.

This is a selection simulation, not a browser or client integration test.
It does not invoke a model or contact any service itself.
"""

import argparse
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
ROUTES = {
    "research": "notte-research", "browser": "notte-browser",
    "build": "notte-functions-build", "repair": "notte-functions-doctor",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", action="store_true", help="emit cases without expected answers")
    parser.add_argument("--predictions", type=Path, help="JSON array of {id, route, reason}")
    args = parser.parse_args()
    if bool(args.prompt) == bool(args.predictions):
        parser.error("choose exactly one of --prompt or --predictions")
    cases = json.loads((ROOT / "evaluations/routing.json").read_text())
    if args.prompt:
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location("validator", ROOT / "scripts/validate-plugins.py")
        validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validator)
        skills = []
        for route, name in ROUTES.items():
            text = (ROOT / f"plugins/notte/skills/{name}/SKILL.md").read_text()
            fields = validator.parse_frontmatter(text)
            skills.append({"route": route, "name": name, "description": fields["description"]})
        print("Choose the primary skill for each independent user request. Available alternatives "
              "include built-in WebSearch/WebFetch, a local browser, and local coding tools. "
              "Choose other when none of these skills applies. Do not execute any request. "
              "Return only a JSON array of objects with id, route, and a short reason. "
              "Routes: research, browser, build, repair, other.")
        print(json.dumps({"skills": skills, "requests": [
            {"id": case["id"], "prompt": case["prompt"]} for case in cases
        ]}, indent=2))
        return 0
    predictions = json.loads(args.predictions.read_text())
    if not isinstance(predictions, list):
        raise ValueError("predictions must be a JSON array")
    actual = {}
    for prediction in predictions:
        identifier, route = prediction["id"], prediction["route"]
        if identifier in actual:
            raise ValueError(f"duplicate prediction: {identifier}")
        if route not in {*ROUTES, "other"}:
            raise ValueError(f"unknown route: {route}")
        actual[identifier] = route
    expected = {case["id"]: case["expected"] for case in cases}
    if actual.keys() != expected.keys():
        raise ValueError(f"case mismatch: missing={expected.keys() - actual.keys()}, extra={actual.keys() - expected.keys()}")
    failures = 0
    for identifier, route in expected.items():
        passed = actual[identifier] == route
        failures += not passed
        print(f"{'PASS' if passed else 'FAIL'} {identifier}: {actual[identifier]} (expected {route})")
    print(f"{len(cases) - failures}/{len(cases)} routing cases passed")
    return int(failures > 0)


if __name__ == "__main__":
    sys.exit(main())
