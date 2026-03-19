import sys, os, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from loguru import logger
from memory.short_term import SessionMemory
from memory.long_term import log_action, get_score_history


def weekly_nudge(session: SessionMemory) -> str:
    from actions.executor import call_groq, save_output

    logger.info("Action: weekly_nudge")

    history = get_score_history()

    prompt = f"""
You are a brutally honest but supportive career mentor writing a weekly check-in.

Student: {session.profile.name if session.profile else 'Developer'}
Current hirability score: {session.gap_report.overall_score if session.gap_report else 'N/A'}/10
Score history: {json.dumps(history)}
Critical gaps remaining: {session.gap_report.critical_gaps if session.gap_report else []}
Actions taken this session: {session.actions_taken}

Write a weekly nudge that:
1. Opens with an honest assessment of progress (no fluff)
2. Calls out exactly what was done or skipped
3. Sets 3 specific goals for the coming week with deadlines
4. Ends with one motivating sentence that's earned, not cheap

Keep it under 300 words. Be direct. They can handle the truth.
"""

    result = call_groq(prompt)
    save_output("weekly_nudge.md", result)
    log_action("weekly_nudge", "Weekly nudge generated")
    session.remember_action("weekly_nudge")
    return result
