import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
import traceback
from loguru import logger
from planner.reasoner import client, os
from typing import Optional
import uuid
from datetime import datetime

from memory.short_term import SessionMemory
from memory.long_term import init_db, save_snapshot, log_action
from skills.github_observer.github_observer import fetch_github_profile
from skills.gap_analyzer.gap_analyzer import analyze_gaps, load_goals
from planner.reasoner import make_plan
from actions.executor import execute_plan
from skills.registry import registry

router = APIRouter()

# Store conversation history per session
_conversation_history = {}  # session_id -> [(role, content), ...]

class AskRequest(BaseModel):
    message: str
    session_id: Optional[str] = None  # Browser session ID for conversation memory

def _get_or_create_session(session_id: Optional[str]) -> str:
    """Get or create a conversation session."""
    if not session_id:
        session_id = str(uuid.uuid4())
    if session_id not in _conversation_history:
        _conversation_history[session_id] = []
    return session_id

def _add_to_history(session_id: str, role: str, content: str):
    """Add message to conversation history."""
    _conversation_history[session_id].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    })

def _get_history_context(session_id: str, max_messages: int = 5) -> str:
    """Build context string from recent conversation history."""
    if session_id not in _conversation_history or not _conversation_history[session_id]:
        return ""
    
    # Get last N messages
    recent = _conversation_history[session_id][-max_messages:]
    history_text = "RECENT CONVERSATION CONTEXT:\n"
    for msg in recent:
        role = "User" if msg["role"] == "user" else "Assistant"
        history_text += f"• {role}: {msg['content'][:100]}...\n" if len(msg['content']) > 100 else f"• {role}: {msg['content']}\n"
    return history_text

@router.post("/ask")
def ask_agent(request: AskRequest):
    """Interactive chat with the agent to ask questions or trigger skills."""
    try:
        init_db()
        
        # Get or create session
        session_id = _get_or_create_session(request.session_id)
        
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
        
        # Build detailed profile context for better QA answers
        repo_names = ", ".join([r.name for r in session.profile.repos[:5]]) + ("..." if len(session.profile.repos) > 5 else "")
        languages_str = ", ".join(f"{lang} ({count})" for lang, count in sorted(session.profile.languages_used.items(), key=lambda x: x[1], reverse=True))
        
        # Build detailed repo metrics for INTELLIGENT repo analysis (beyond just commits/stars)
        repo_details = []
        repo_scores = []  # For practical value scoring
        
        for repo in session.profile.repos:
            # Calculate a "practicality score" based on:
            # - Has documentation (README)
            # - Has topics/categories
            # - Has description
            # - Recent activity
            # - Meaningful commit count (not just 1-2 commits)
            practicality_score = 0
            if repo.has_readme:
                practicality_score += 2  # Well documented
            if repo.topics and len(repo.topics) > 0:
                practicality_score += 1.5  # Clear categorization
            if repo.description and len(repo.description) > 20:
                practicality_score += 1  # Has meaningful description
            if repo.commit_count >= 5:  # Not a throwaway project
                practicality_score += 1
            if repo.commit_count >= 15:  # Substantial project
                practicality_score += 1
            if repo.forks > 0:  # Others found it useful
                practicality_score += 0.5
            
            topics_str = ", ".join(repo.topics[:3]) if repo.topics else "No topics"
            desc_snippet = (repo.description[:50] + "...") if repo.description and len(repo.description) > 50 else (repo.description or "No description")
            readme_indicator = "📖" if repo.has_readme else "❌"
            
            repo_details.append(
                f"• {repo.name}: {repo.commit_count} commits, {repo.stars}⭐, {repo.forks}🔀, "
                f"Last: {repo.last_updated[:10]}, Lang: {repo.language or 'None'}\n"
                f"  {readme_indicator} Docs: {repo.has_readme} | Topics: {topics_str}\n"
                f"  Description: {desc_snippet}\n"
                f"  Practicality Score: {practicality_score:.1f}/7.0"
            )
            repo_scores.append((repo.name, practicality_score, repo.commit_count, repo.stars, repo.has_readme))
        
        repos_list_str = "\n".join(repo_details)
        
        # Find best repo by practicality, not just commits
        best_practical_repo = max(repo_scores, key=lambda x: (x[1], x[2], x[3])) if repo_scores else None
        
        # Sort repos by commit count (intensity of development)
        repos_by_commits = sorted(session.profile.repos, key=lambda r: r.commit_count, reverse=True)
        most_developed = repos_by_commits[0] if repos_by_commits else None
        
        # Sort repos by last update
        repos_by_date = sorted(session.profile.repos, key=lambda r: r.last_updated, reverse=True)
        most_recent = repos_by_date[0] if repos_by_date else None
        
        # Get conversation history for context
        history_context = _get_history_context(session_id)
        
        # Build the HTML repos list for context (useful for follow-up questions)
        html_repos = [r.name for r in session.profile.repos if r.language == "HTML"]
        
        prompt = f"""You are CareerPilot, an AI agent with direct access to @{session.profile.username}'s GitHub profile.

{history_context}

FACTS ABOUT THIS USER (KNOWN - USE THESE WHEN ANSWERING):
• GitHub Username: @{session.profile.username}
• Total Public Repositories: {session.profile.public_repos}
• Followers: {session.profile.followers}
• Main Languages: {languages_str}
• Hirability Score: {session.gap_report.overall_score}/10
• Key Strengths: {session.gap_report.strengths}
• Areas to Improve: {session.gap_report.critical_gaps}

DETAILED REPOSITORY METRICS (Use these to answer repo-related questions):
{repos_list_str}

REPO RANKINGS:
• Most developed (by commits): {most_developed.name if most_developed else 'N/A'} ({most_developed.commit_count if most_developed else 0} commits)
• Most recently updated: {most_recent.name if most_recent else 'N/A'} (updated: {most_recent.last_updated[:10] if most_recent else 'N/A'})
• Most developed (by commits): {most_developed.name if most_developed else 'N/A'} ({most_developed.commit_count if most_developed else 0} commits)
• Most recently updated: {most_recent.name if most_recent else 'N/A'} (updated: {most_recent.last_updated[:10] if most_recent else 'N/A'})
• Best overall (by practicality & impact): {best_practical_repo[0] if best_practical_repo else 'N/A'} (Practicality Score: {best_practical_repo[1]:.1f}/7.0)

EVALUATION CRITERIA FOR "BEST REPO":
Practicality Score = Documentation (README) + Topics + Description Quality + Commits + Community (forks)
A good repo has: clear README ✅, good topics, meaningful description, 5+ commits (not throwaway), community adoption.
Raw commits ≠ best repo. A well-documented small project often outweighs an undocumented large one.
AVAILABLE SKILLS (only trigger if explicitly requested):
{json.dumps(enabled_skills, indent=2)}


USER MESSAGE: "{request.message}"

RULES:
1. Remember context from previous messages in this conversation. If user says "name them" or "tell me more", refer to what was discussed earlier.
2. For any question about the user's repos → ALWAYS use the DETAILED REPOSITORY METRICS above. Be specific with numbers.
3. When asked "what is the latest repo?" → Answer with the most recently updated repo from REPO RANKINGS, with its last update date.
4. When asked "which is the best repo?" → Primary: Practicality Score (documentation + description + topics + commits). State reasoning with Practicality Score and specific factors. Good repos have READMEs and real usability, not just activity.
5. When comparing two repos → Use Practicality Score primary metric, then: commits, stars, forks, README quality, description clarity.
6. EMPHASIZE: Usability & documentation matter more than raw commit count. A well-documented 10-commit project beats a 50-commit undocumented one.
6. When asked about repo improvements → Reference the specific metrics and suggest what needs work based on the numbers.
7. If user asks about their profile/repos/score/skills → Answer DIRECTLY using FACTS above. Be specific. No generic advice.
8. If user explicitly requests a skill → Trigger it. Format: {{"intent": "skill", "skill_name": "...", "kwargs": {{}}}}
9. ALWAYS respond with valid JSON only. No other text.

EXAMPLE responses:
- User: "which is my best repo?" → {{"intent": "qa", "answer": "Based on development activity, {most_developed.name} is your best repo with {most_developed.commit_count} commits and {most_developed.stars} stars. It demonstrates significant time investment and project maturity."}}
- User: "what is the latest repo?" → {{"intent": "qa", "answer": "Your most recently updated repo is {most_recent.name}, last updated on {most_recent.last_updated[:10]}."}}
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
        
        # Store user message in history
        _add_to_history(session_id, "user", request.message)
        
        if intention.get("intent") == "skill":
            skill_name = intention.get("skill_name")
            skill = registry.get(skill_name)
            if skill and skill.enabled:
                kwargs = intention.get("kwargs", {})
                result = skill.fn(session, **kwargs)
                agent_msg = f"I've triggered the **{skill_name}** skill for you."
                _add_to_history(session_id, "assistant", agent_msg)
                return {
                    "status": "success", 
                    "intent": "skill", 
                    "skill_name": skill_name, 
                    "output": result,
                    "agent_message": agent_msg,
                    "session_id": session_id
                }
            else:
                err_msg = f"I tried to trigger '{skill_name}', but it seems unavailable or disabled."
                _add_to_history(session_id, "assistant", err_msg)
                return {
                    "status": "success", 
                    "intent": "qa", 
                    "answer": err_msg,
                    "session_id": session_id
                }
        else:
            answer = intention.get("answer", "I didn't understand the intent.")
            _add_to_history(session_id, "assistant", answer)
            return {
                "status": "success", 
                "intent": "qa", 
                "answer": answer,
                "session_id": session_id
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