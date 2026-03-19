import sys, os, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import yaml
from loguru import logger
from memory.short_term import SessionMemory
from memory.long_term import log_action


def suggest_project(session: SessionMemory) -> str:
    from actions.executor import call_groq, save_output

    logger.info("Action: suggest_project")

    gaps = session.gap_report.critical_gaps if session.gap_report else ["FastAPI", "Docker"]

    with open("config/goals.yaml") as f:
        goals = yaml.safe_load(f)

    prompt = f"""
You are a senior developer mentoring a student targeting: {goals.get('target_role')}

Their critical skill gaps are:
{json.dumps(gaps, indent=2)}

Their preferred stack: {goals.get('preferred_stack')}

Suggest ONE specific mini-project they can build in 5-7 days that:
1. Directly addresses their most critical gap
2. Is small enough to finish but impressive enough to show in interviews
3. Uses their existing strength in Python and AI/ML

Format your response as:
## Project Title
**What to build:** (2-3 sentences)
**Tech stack:** (exact libraries/tools)
**Key features to implement:** (bullet list of 4-5 features)
**Why this impresses interviewers:** (2-3 sentences)
**Starter file structure:** (show the folder/file layout)
**First step to start RIGHT NOW:** (one concrete action)
"""

    result = call_groq(prompt)
    save_output("suggested_project.md", result)
    log_action("suggest_project", f"Gaps addressed: {', '.join(gaps)}")
    session.remember_action("suggest_project")
    return result
