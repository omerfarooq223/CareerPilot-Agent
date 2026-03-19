import sys, os, yaml
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from loguru import logger
from memory.short_term import SessionMemory
from memory.long_term import log_action


def mock_interview_prep(session: SessionMemory) -> str:
    from actions.executor import call_groq, save_output

    logger.info("Action: mock_interview_prep")

    with open("config/goals.yaml") as f:
        goals = yaml.safe_load(f)

    prompt = f"""
Generate a mock interview prep sheet for a student targeting: {goals.get('target_role')}
Their stack: {goals.get('preferred_stack')}
Their skills: {goals.get('self_declared_skills')}
Their gaps: {session.gap_report.critical_gaps if session.gap_report else []}

## Mock Interview Prep — {goals.get('target_role')}

### Likely Technical Questions (10 questions)
(specific to their stack and target role, with brief ideal answer hints)

### Behavioral Questions (5 questions)
(with notes on what interviewers are looking for)

### Questions to Ask the Interviewer (5 questions)
(smart questions that show curiosity and preparation)

### Red Flags to Avoid
(common mistakes for this role)

### 30-Second Elevator Pitch Template
(fill-in-the-blank template they can customize)
"""

    result = call_groq(prompt)
    save_output("mock_interview_prep.md", result)
    log_action("mock_interview_prep", f"Role: {goals.get('target_role')}")
    session.remember_action("mock_interview_prep")
    return result