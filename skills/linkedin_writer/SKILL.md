# Skill: linkedin_writer

## What it does
Generates a human-sounding LinkedIn post based on the developer's GitHub
repos and profile, then runs a HITL approval flow — copy to clipboard
and opens LinkedIn on approval.

## Inputs
- `session.profile` — GitHub profile and repo data
- `session.gap_report` — strengths and score
- `goals.yaml` — target role, skills, credentials
- SQLite action log — detects if first ever post

## Outputs
- `output/linkedin_<type>_<repo>.md` — saved post
- Clipboard — post copied on approval
- Browser — LinkedIn opened on approval

## Post types
- `intro` — first post introducing yourself
- `new_repo` — announcing a repo
- `past_repos` — showcasing existing work
- `progress` — milestone or score improvement
- `project_done` — completed project showcase

## When the planner should use this
- When score >= 6 (don't post when profile is weak)
- Maximum once per week
- NOT in the middle of a session — always last action

## Dependencies
- Groq API
- `pyperclip` — clipboard access
- `webbrowser` — opens LinkedIn
- `memory/long_term.py` — checks post history
- `config/goals.yaml`

## Version
1.0.0