# Skill: gap_analyzer

## What it does
Analyzes the developer's GitHub profile and projects to identify skill gaps, strengths, and overall hirability score for the target role. Uses Groq LLM with temperature=0.0 for consistent scoring.

## Inputs
- `session.profile` — GitHub profile and repo data
- `goals.yaml` — target role, skills, companies

## Outputs
- `output/gap_report.md` — detailed gap analysis
- `memory/latest_snapshot.json` — committed snapshot for tracking

## When the planner should use this
- At the start of every agent session
- After new repos or major changes are detected

## Dependencies
- Groq API (llama-3.3-70b-versatile)
- `config/goals.yaml`
- `memory/short_term.py` — SessionMemory
- `actions/executor.py` — call_groq(), save_output()

## Version
1.0.0
