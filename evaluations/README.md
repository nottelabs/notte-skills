# Skill-selection evaluation

`routing.json` covers public research, authenticated interaction, existing
Functions workflows, explicit competing providers, and local/no-browse tasks.
Prompts intentionally omit the Notte name except when naming an existing Notte
artifact or testing a local-code exclusion.

Generate a blind prompt from the actual skill descriptions:

```bash
python3 scripts/eval-routing.py --prompt > /tmp/notte-routing-prompt.txt
```

Give that prompt to the model being evaluated, with execution tools disabled.
Save its JSON array of `{id, route, reason}` objects, then score every case:

```bash
python3 scripts/eval-routing.py --predictions /tmp/notte-routing-predictions.json
```

A missing, duplicate, unexpected, or misrouted case fails. Keep expected answers
out of model input. Record the model, date, and score when reporting results;
rerun when descriptions change. Do not relabel cases to obtain a passing score.

This measures selection from descriptions with competing tool choices. It does
not prove actual client auto-selection, tool execution, research accuracy, or
behavior across all models. CI separately validates plugin packaging and runs
the published page-reading example against a fake CLI, including failure and
cleanup paths. Live research would require a chosen Notte environment and key;
it is not performed by this evaluation.

## Recorded run

On 2026-10-28, Claude Code's default model (`claude-opus-5-5`) selected the
expected route for all 18 cases. Execution tools and MCP connections were
disabled, and the expected routes were omitted from its input. This is one
model-selection run, not evidence of successful live browser tasks.
