# Skill: suggest_project

## What it does
Analyzes the agent's current gap report and suggests one specific mini-project
the developer can build in 5–7 days to address their most critical skill gap.

## Inputs
- `session.gap_report.critical_gaps` — list of skill gaps
- `session.gap_report.overall_score` — current hirability score
- `goals.yaml > target_role` — the role being targeted
- `goals.yaml > preferred_stack` — preferred technologies

## Outputs
- `output/suggested_project.md` — structured project proposal with title,
  tech stack, features, file structure, and first step

## When the planner should use this
- First session with no previous suggestions
- When critical gaps haven't changed after 2+ sessions
- When overall_score < 8
- When `suggest_project` is NOT in session.actions_taken

## Dependencies
- Groq API
- `memory/short_term.py` — SessionMemory
- `config/goals.yaml`
- `actions/executor.py` — call_groq(), save_output()

## Version
1.0.0