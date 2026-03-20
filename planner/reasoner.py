import os
import sys
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from groq import Groq
from loguru import logger
from dotenv import load_dotenv
from pydantic import BaseModel
from memory.short_term import SessionMemory
from memory.long_term import get_last_snapshot, get_score_history, get_gap_trend

load_dotenv(dotenv_path="config/.env")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ── Data model ─────────────────────────────────────────────────────────────────

class AgentPlan(BaseModel):
    current_focus: str               # what the agent is focused on this session
    actions_to_take: list[str]       # ordered list of actions to execute
    skip_reasons: dict[str, str]     # actions skipped and why
    message_to_user: str             # honest note to the developer (you)
    priority_action: str             # the single most important thing right now


# ── Planner ────────────────────────────────────────────────────────────────────

def make_plan(session: SessionMemory) -> AgentPlan:
    """
    Autonomous planner — decides what the agent should do next.

    Reads current gap report, score history, and gap trend from memory.
    Sends structured context to Groq which returns an ordered list of
    actions to execute, skip reasons, and a direct message to the user.

    Args:
        session: Current SessionMemory containing profile and gap report.

    Returns:
        AgentPlan with ordered actions, skip reasons, and priority action.
    """
    logger.info("Planner is reasoning over current state...")

    last_snapshot = get_last_snapshot()
    trend         = get_gap_trend()
    score_history = get_score_history()

    # Build progress context using gap trend
    if trend.get("status") == "ok":
        delta     = trend["score_delta"]
        direction = "improved" if delta > 0 else "declined" if delta < 0 else "stayed the same"
        closed    = trend["closed_gaps"]
        new_gaps  = trend["new_gaps"]
        persisted = trend["persisted_gaps"]
        progress_context = (
            f"Score {direction} from {trend['previous_score']} to {trend['current_score']} "
            f"({'+' if delta >= 0 else ''}{delta}) between {trend['previous_date']} and {trend['current_date']}.\n"
            f"Gaps CLOSED since last session: {closed if closed else 'none'}.\n"
            f"NEW gaps detected: {new_gaps if new_gaps else 'none'}.\n"
            f"Gaps PERSISTING for multiple sessions: {persisted}."
        )
    else:
        progress_context = "First session — no previous data to compare."

    # Current gap report
    gap_context = "No gap report available."
    if session.gap_report:
        gap_context = json.dumps({
            "overall_score": session.gap_report.overall_score,
            "critical_gaps": session.gap_report.critical_gaps,
            "top_3_actions": session.gap_report.top_3_actions,
            "portfolio_ready_repos": session.gap_report.portfolio_ready_repos,
            "weakest_repos": session.gap_report.weakest_repos,
            "strengths": session.gap_report.strengths
        }, indent=2)

    # Actions already taken this session
    taken = session.actions_taken if session.actions_taken else ["none yet"]

    prompt = f"""
You are the planning module of an AI career coach agent for a student developer.
Your job is to decide what actions the agent should take RIGHT NOW based on the 
student's current state. Be decisive, specific, and avoid repeating past actions.

--- PROGRESS OVER TIME ---
{progress_context}

--- CURRENT GAP ANALYSIS ---
{gap_context}

--- ACTIONS ALREADY TAKEN THIS SESSION ---
{json.dumps(taken)}

--- AVAILABLE ACTIONS ---
The agent can perform these actions (use exact names):
1. rewrite_readme      — Rewrite a weak repo's README to be more professional
2. generate_dev_card — Generate developer profile card (use sparingly, max once/week, only when score improves)
3. suggest_project     — Suggest a specific mini-project to fill a skill gap
4. audit_repo          — Deep audit a specific repo for code quality
5. mock_interview_prep — Generate role-specific interview questions
6. weekly_nudge        — Write a motivational + honest weekly progress report

--- YOUR TASK ---
Decide which actions to take this session and in what order.
Return ONLY a valid JSON object with exactly these keys:
{{
  "current_focus": "one sentence describing the session's focus",
  "actions_to_take": ["action1", "action2", ...],
  "skip_reasons": {{"action_name": "reason for skipping"}},
  "message_to_user": "an honest, direct message to the student developer",
  "priority_action": "the single most important action right now"
}}

No markdown, no explanation, just raw JSON.
"""

    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1000
    )

    raw = response.choices[0].message.content.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    data = json.loads(raw)
    plan = AgentPlan(**data)

    logger.success(f"Plan ready — priority action: {plan.priority_action}")
    logger.info(f"Actions to take: {plan.actions_to_take}")
    return plan


# ── Quick test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from rich.pretty import pprint
    from rich.console import Console
    from skills.github_observer.github_observer import fetch_github_profile
    from skills.gap_analyzer.gap_analyzer import analyze_gaps
    from memory.long_term import init_db, save_snapshot, log_action

    console = Console()
    init_db()

    # Build session memory
    session = SessionMemory()
    session.profile = fetch_github_profile()
    session.gap_report = analyze_gaps(session.profile)

    # Save to long-term memory
    save_snapshot(session.gap_report)
    log_action("gap_analysis", f"Score: {session.gap_report.overall_score}/10")

    # Make a plan
    plan = make_plan(session)

    console.rule("[bold green]AGENT PLAN")
    pprint(plan.model_dump())

    console.rule("[bold yellow]MESSAGE TO YOU")
    console.print(f"\n[italic]{plan.message_to_user}[/italic]\n")

    console.rule("[bold red]PRIORITY ACTION")
    console.print(f"\n[bold]{plan.priority_action}[/bold]\n")
