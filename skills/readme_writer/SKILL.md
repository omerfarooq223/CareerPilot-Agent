# Skill: rewrite_readme

## What it does
Generates a professional, portfolio-grade README.md for a specified repo —
including badges, features, installation, usage, structure, and future plans.

## Inputs
- `session.profile.repos` — repo details from GitHub observer
- `session.gap_report.weakest_repos` — auto-selects if no repo specified
- Optional: explicit `repo_name` argument

## Outputs
- `output/readme_<repo_name>.md` — complete drop-in README replacement

## When the planner should use this
- After `audit_repo` has run on the same repo
- When a repo has a README score below 6
- When `rewrite_readme` is NOT in session.actions_taken

## Dependencies
- Groq API
- `memory/short_term.py` — SessionMemory
- `actions/executor.py` — call_groq(), save_output()

## Version
1.0.0