import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
import traceback
from loguru import logger
from planner.reasoner import client, os

from memory.short_term import SessionMemory
from memory.long_term import init_db, save_snapshot, log_action
from skills.github_observer.github_observer import fetch_github_profile
from skills.gap_analyzer.gap_analyzer import analyze_gaps, load_goals
from planner.reasoner import make_plan
from actions.executor import execute_plan
from skills.registry import registry

router = APIRouter()

class AskRequest(BaseModel):
    message: str

@router.post("/ask")
def ask_agent(request: AskRequest):
    """Interactive chat with the agent to ask questions or trigger skills."""
    try:
        init_db()
        session = SessionMemory()
        session.profile = fetch_github_profile()
        goals = load_goals()
        if goals.get("name"):
            session.profile.name = goals["name"]
        
        # Analyze current gaps to provide updated context
        session.gap_report = analyze_gaps(session.profile)
        
        # Determine available skills
        enabled_skills = {
            s["name"]: s["description"] for s in registry.list_all() if s["enabled"]
        }
        
        prompt = f"""
You are the interactive chat module of the CareerPilot AI agent.
The user sent the following message: "{request.message}"

Available agent skills (commands you can trigger):
{json.dumps(enabled_skills, indent=2)}

User Profile Summary:
Hirability Score: {session.gap_report.overall_score}/10
Strengths: {session.gap_report.strengths}
Critical Gaps: {session.gap_report.critical_gaps}

Instructions:
1. STRICT ROUTING RULE: If the user is asking for general advice, feedback, or asking a question (e.g., "how can I improve my bio?", "how many repos do I have?"), you MUST answer it directly yourself. Set intent to "qa" and write your response.
2. ONLY trigger a skill if the user EXPLICITLY commands you to generate a specific automated artifact (e.g., "audit my repo", "generate my dev card", "write a linkedin post"). Do NOT assume they want a skill triggered just because they are asking for advice on their profile.

Respond ONLY with valid JSON in one of these two formats:
For triggering a skill:
{{"intent": "skill", "skill_name": "the_exact_skill_name", "kwargs": {{"repo_name": "target_repo_name_if_specified"}}}}

For answering a question:
{{"intent": "qa", "answer": "Your clear and concise response here, formatted in markdown if needed."}}
"""
        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=[{"role": "system", "content": prompt}],
            temperature=0.3,
            max_tokens=800
        )
        
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        
        intention = json.loads(raw)
        
        if intention.get("intent") == "skill":
            skill_name = intention.get("skill_name")
            skill = registry.get(skill_name)
            if skill and skill.enabled:
                kwargs = intention.get("kwargs", {})
                result = skill.fn(session, **kwargs)
                return {
                    "status": "success", 
                    "intent": "skill", 
                    "skill_name": skill_name, 
                    "output": result,
                    "agent_message": f"I've triggered the **{skill_name}** skill for you."
                }
            else:
                return {
                    "status": "success", 
                    "intent": "qa", 
                    "answer": f"I tried to trigger '{skill_name}', but it seems unavailable or disabled."
                }
        else:
            return {
                "status": "success", 
                "intent": "qa", 
                "answer": intention.get("answer", "I didn't understand the intent.")
            }
            
    except Exception as e:
        logger.error(f"Ask endpoint error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


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