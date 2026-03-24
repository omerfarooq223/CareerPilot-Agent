import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import APIRouter, HTTPException
from memory.short_term import SessionMemory
from memory.long_term import init_db, save_snapshot, log_action
from skills.github_observer.github_observer import fetch_github_profile
from skills.gap_analyzer.gap_analyzer import analyze_gaps, load_goals
from planner.reasoner import make_plan
from actions.executor import execute_plan
from skills.registry import registry

router = APIRouter()

@router.post("/run")
def run_agent():
    """Run the full autonomous agent loop."""
    try:
        init_db()
        session = SessionMemory()

        # Observe
        session.profile = fetch_github_profile()
        goals = load_goals()
        if goals.get("name"):
            session.profile.name = goals["name"]

        # Analyze
        session.gap_report = analyze_gaps(session.profile)
        save_snapshot(session.gap_report)
        log_action("session_start", f"Score: {session.gap_report.overall_score}/10")

        # Plan
        plan = make_plan(session)

        # Act — collect results instead of printing
        results = []
        for action in plan.actions_to_take:
            try:
                skill = registry.get(action)
                if skill and skill.enabled:
                    result = skill.fn(session)
                    results.append({"skill": action, "output": result})
            except Exception as e:
                results.append({"skill": action, "output": f"Error: {e}"})

        return {
            "score":        session.gap_report.overall_score,
            "gaps":         session.gap_report.critical_gaps,
            "strengths":    session.gap_report.strengths,
            "focus":        plan.current_focus,
            "priority":     plan.priority_action,
            "agent_message":plan.message_to_user,
            "actions_run":  [r["skill"] for r in results],
            "results":      results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))