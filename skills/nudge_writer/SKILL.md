# Skill: weekly_nudge

## What it does
Writes a brutally honest weekly progress report — opens with an honest
assessment, calls out what was done or skipped, sets 3 specific goals
for the coming week with deadlines, and closes with one earned motivator.

## Inputs
- `session.profile.name` — developer name
- `session.gap_report` — current gaps and score
- `memory/long_term.get_score_history()` — week-over-week scores
- `session.actions_taken` — what the agent did this session

## Outputs
- `output/weekly_nudge.md` — weekly report (under 300 words)

## When the planner should use this
- At the end of each weekly session
- When score has stayed flat for 2+ sessions (use as a wake-up call)
- NOT mid-session — always the last action in the plan

## Dependencies
- Groq API
- `memory/short_term.py` — SessionMemory
- `memory/long_term.py` — get_score_history()
- `actions/executor.py` — call_groq(), save_output()

## Version
1.0.0