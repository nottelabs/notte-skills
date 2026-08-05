"""Notte Function skeleton (forged).

A complete, parameterized starting point for a Notte Function. Start from
`notte sessions workflow-code --session-id <id>` to capture the path that
actually worked, then shape it to look like this file:

  - `run(...)` parameters are the business variables -> Function invocation variables
  - the response model is the output schema
  - the HEALTH CONTRACT block + assertions describe what a correct result is,
    so the build-time self-test and notte-functions-doctor have a target

Deploy:
  notte functions create --file function-skeleton.py --name "HN Top Stories" \
    --description "Top Hacker News stories as structured JSON"

This example (Hacker News) is runnable as-is. Replace the CUSTOMIZE sections
with your site's path. Keep the contract honest - bound what you actually
observed during exploration.

Leave out `from __future__ import annotations`. With PEP 563 the Pydantic field
annotations become unresolved forward references, so a deployed Function fails at
`response_format=Model` with `PydanticUserError: Model is not fully defined`
(unless you also call `Model.model_rebuild()`). The `X | None` syntax below works
without it, so the simplest fix is to omit it. (`notte sessions workflow-code`
may emit that import in its export - remove it before deploying.)

Guard the `run()` call at the bottom with `if __name__ == "__main__":`. The Notte
runtime imports this file and calls `run()` itself, so a bare module-level call
executes the Function TWICE - two browser sessions, double the cost, and any
side effect performed twice. The guard keeps the file runnable locally
(`python function-skeleton.py`) while staying single-shot in the cloud.
`notte sessions workflow-code` emits an unguarded call - add the guard.
"""

from notte_sdk import NotteClient
from pydantic import BaseModel

# === HEALTH CONTRACT ===
# schema: { stories: [ { rank: int, title: str, url: str, points: int } ] }
# bounds:
#   - len(stories) >= 5            # the HN front page always lists many stories
#   - every story has a title and a url
#   - points >= 0
# notes: an empty list means the page structure changed, NOT "no data today".
# === END HEALTH CONTRACT ===


class Story(BaseModel):
    rank: int | None = None
    title: str | None = None
    url: str | None = None
    points: int | None = None


class Result(BaseModel):
    stories: list[Story] | None = None


client = NotteClient()


def run(max_stories: int = 10):  # CUSTOMIZE: business variables become parameters
    """Forged Function entry point.

    Parameters become invocation variables. The returned value (JSON-serializable)
    becomes the run result.
    """
    # Run variables arrive as strings (via --var) and are NOT coerced to the
    # annotation - cast anything you use numerically.
    max_stories = int(max_stories)

    # A plain Session is right for scrape/extract. Use
    # client.Session(use_file_storage=True) only for a Function that produces
    # files you need to retrieve.
    with client.Session() as session:
        # CUSTOMIZE: the path you validated during exploration goes here.
        session.execute(type="goto", url="https://news.ycombinator.com")

        result = session.scrape(
            instructions=(
                f"Extract the top {max_stories} stories. For each return: "
                "rank (int), title (str), url (str), points (int)."
            ),
            response_format=Result,
        )

        # --- health contract: fail loud on a structurally broken result ---
        assert result.stories, "health contract violated: 0 stories (page structure likely changed)"
        assert all(
            s.title and s.url for s in result.stories
        ), "health contract violated: a story is missing title or url"

        return result


if __name__ == "__main__":
    run()
