# Skill: mock_interview_prep

## What it does
Generates a role-specific interview prep sheet with 10 technical questions,
5 behavioral questions, 5 smart questions to ask the interviewer, red flags
to avoid, and a 30-second elevator pitch template.

## Inputs
- `goals.yaml > target_role` — role being targeted
- `goals.yaml > preferred_stack` — tech stack to focus questions on
- `goals.yaml > self_declared_skills` — skills to reference
- `session.gap_report.critical_gaps` — gaps to address in answers

## Outputs
- `output/mock_interview_prep.md` — full interview prep sheet

## When the planner should use this
- When overall_score >= 7
- When critical gaps are being actively addressed
- NOT on the first session — too early before gaps are closed

## Dependencies
- Groq API
- `memory/short_term.py` — SessionMemory
- `config/goals.yaml`
- `actions/executor.py` — call_groq(), save_output()

## Version
1.0.0