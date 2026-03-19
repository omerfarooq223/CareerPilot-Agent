# Skill: update_goals

## What it does
Auto-updates goals.yaml based on current GitHub profile:
1. Adds new repos to shipped_projects
2. Updates self_declared_skills with newly demonstrated technologies

Note: Gap detection is handled entirely by gap_analyzer — no manual gaps needed.

## Inputs
- `session.profile.repos` — scans all repos for skill signals
- `config/goals.yaml` — reads and writes directly

## Outputs
- Updated `config/goals.yaml`
- Summary of what changed

## When the planner should use this
- Once at the start of every session before gap analysis
- When a new repo is detected that wasn't in shipped_projects

## Dependencies
- PyYAML
- `memory/short_term.py`

## Version
1.1.0