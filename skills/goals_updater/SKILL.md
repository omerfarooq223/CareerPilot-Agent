# Skill: update_goals

## What it does
Auto-updates goals.yaml based on current GitHub profile — adds new repos to
shipped_projects, closes gaps that are now covered, and adds newly demonstrated
skills to self_declared_skills.

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
1.0.0