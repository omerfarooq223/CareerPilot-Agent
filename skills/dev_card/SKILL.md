# Skill: generate_dev_card

## What it does
Generates a concise markdown developer profile card (under 400 words)
summarizing the developer's strongest skills, top 3 projects, academic
achievements, and what they're looking for.

## Inputs
- `session.profile` — full GitHubProfile
- `goals.yaml > target_role` — role being targeted
- `goals.yaml > self_declared_skills` — self-reported skills
- `goals.yaml > credentials` — CGPA, awards, program

## Outputs
- `output/developer_card.md` — ready to paste on LinkedIn or portfolio

## When the planner should use this
- ONLY when explicitly requested by the user
- OR when score crosses a new threshold (e.g. jumps from 6 to 7+)
- Maximum ONCE per week — never on consecutive runs
- NOT when critical gaps exist and haven't been addressed

## Dependencies
- Groq API
- `memory/short_term.py` — SessionMemory
- `config/goals.yaml`
- `actions/executor.py` — call_groq(), save_output()

## Version
1.0.0