import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from memory.short_term import SessionMemory
from memory.long_term import init_db, save_snapshot
from skills.github_observer.github_observer import fetch_github_profile
from skills.gap_analyzer.gap_analyzer import analyze_gaps, load_goals
from actions.executor import execute_plan
from skills.registry import registry

router = APIRouter()

class SkillRequest(BaseModel):
    repo_name: Optional[str] = None

def build_session() -> SessionMemory:
    init_db()
    session = SessionMemory()
    session.profile    = fetch_github_profile()
    
    goals = load_goals()
    if goals.get("name"):
        session.profile.name = goals["name"]
        
    session.gap_report = analyze_gaps(session.profile)
    save_snapshot(session.gap_report)
    return session

@router.get("/skills")
def list_skills():
    return {
        "skills": [
            {
                "id":          s["name"],
                "label":       s["name"].replace("_", " ").title(),
                "description": s["description"],
                "enabled":     s["enabled"],
                "has_repo_picker": s["name"] in ["audit_repo", "rewrite_readme", "deep_audit_repo"]
            }
            for s in registry.list_all()
        ]
    }

@router.post("/skills/{skill_name}")
def run_skill(skill_name: str, body: SkillRequest = SkillRequest()):
    try:
        session = build_session()

        # If skill needs a repo, inject it
        skill = registry.get(skill_name)
        if not skill:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

        if body.repo_name and skill_name in ["audit_repo", "rewrite_readme", "deep_audit_repo"]:
            result = skill.fn(session, repo_name=body.repo_name)
        else:
            result = skill.fn(session)

        return {
            "skill":  skill_name,
            "result": result,
            "score":  session.gap_report.overall_score if session.gap_report else None,
            "gaps":   session.gap_report.critical_gaps if session.gap_report else [],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/repos")
def list_repos():
    try:
        profile = fetch_github_profile()
        return {
            "repos": [
                {"name": r.name, "language": r.language, "description": r.description}
                for r in profile.repos
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))