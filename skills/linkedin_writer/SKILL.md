# Skill: linkedin_writer

## What it does
Generates a human-sounding LinkedIn post based on the developer's GitHub
repos and profile. Returns a structured JSON payload to the Web UI to trigger 
a Human-in-the-Loop (HITL) approval flow.

## Inputs
- `session.profile` — GitHub profile and repo data
- `session.gap_report` — strengths and score
- `goals.yaml` — target role, skills, credentials
- SQLite action log — detects if first ever post

## Outputs
- `output/linkedin_<type>_<repo>.md` — saved post text
- JSON string — `{status, post_id, post, post_type, repo_name}` sent upwards
- SQLite — saved as `pending` in `linkedin_posts` table

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
- `memory/long_term.py` — saves pending posts to SQLite
- `config/goals.yaml`
- CareerPilot Web UI (handles HITL approval flow)

## Version
1.1.0