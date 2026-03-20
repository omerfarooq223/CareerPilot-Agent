import os
import json
import yaml
from groq import Groq
from loguru import logger
from dotenv import load_dotenv
from pydantic import BaseModel
from skills.github_observer.github_observer import GitHubProfile

from pathlib import Path
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / "config" / ".env", override=True)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ── Data model ─────────────────────────────────────────────────────────────────

class GapReport(BaseModel):
    strengths: list[str]
    critical_gaps: list[str]
    nice_to_have: list[str]
    top_3_actions: list[str]
    portfolio_ready_repos: list[str]
    weakest_repos: list[str]
    overall_score: int        # 1–10 hirability score
    verdict: str              # one honest paragraph summary


# ── Loader ─────────────────────────────────────────────────────────────────────

def load_goals() -> dict:
    """Load and return the user's goals configuration from goals.yaml."""
    with open("config/goals.yaml", "r") as f:
        return yaml.safe_load(f)


# ── Analyzer ───────────────────────────────────────────────────────────────────

def analyze_gaps(profile: GitHubProfile) -> GapReport:
    """
    Send the GitHub profile and goals to Groq for gap analysis.
    Returns a structured GapReport with hirability score, gaps, and actions.
    Uses temperature=0.0 and a fixed rubric for consistent scoring.
    """
    goals = load_goals()

    logger.info("Sending profile + goals to Groq for gap analysis...")

    # Build a clean summary of repos for the prompt
    repo_summary = []
    for r in profile.repos:
        repo_summary.append({
            "name": r.name,
            "description": r.description,
            "language": r.language,
            "topics": r.topics,
            "commit_count": r.commit_count,
            "stars": r.stars,
            "has_readme": r.has_readme
        })

    prompt = f"""
You are a senior software engineering recruiter and technical mentor.
Analyze this student's GitHub profile against their target internship goals.
Be honest, specific, and actionable. Do not sugarcoat.

--- STUDENT PROFILE ---
Name: {profile.name}
Bio: {profile.bio}
Total public repos: {profile.public_repos}
Languages used: {profile.languages_used}
Total commits (sampled): {profile.total_commits_sampled}

Repos:
{json.dumps(repo_summary, indent=2)}

--- GOALS ---
Target role: {goals['target_role']}
Timeline: {goals['target_timeline']}
Target companies: {', '.join(goals['target_companies'])}
Self-declared skills: {', '.join(goals.get('self_declared_skills', []))}
Preferred stack: {', '.join(goals['preferred_stack'])}

--- YOUR TASK ---
--- SCORING RUBRIC (follow this exactly) ---
Score 1-3:  No shipped projects, weak fundamentals, no GitHub activity
Score 4-5:  Some projects but no real-world stack, weak READMEs, no topics
Score 6:    Decent projects, missing key stack (FastAPI/Django/Docker), some gaps
Score 7:    Good projects, 1-2 critical gaps remaining, READMEs present
Score 8:    Strong portfolio, target stack present, minor gaps only
Score 9-10: Production-ready skills, all gaps closed, strong GitHub presence

Apply this rubric strictly. Do not deviate based on tone or writing style.
Return ONLY a valid JSON object with exactly these keys:
{{
  "strengths": ["..."],
  "critical_gaps": ["..."],
  "nice_to_have": ["..."],
  "top_3_actions": ["..."],
  "portfolio_ready_repos": ["repo names only"],
  "weakest_repos": ["repo names only"],
  "overall_score": <integer 1-10>,
  "verdict": "one honest paragraph"
}}
No markdown, no explanation, just the raw JSON.
"""

    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=1500
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown code fences if model adds them
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    data = json.loads(raw)
    report = GapReport(**data)

    logger.success(f"Gap analysis complete — hirability score: {report.overall_score}/10")
    return report


# ── Quick test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from rich.pretty import pprint
    from skills.github_observer import fetch_github_profile

    profile = fetch_github_profile()
    report = analyze_gaps(profile)
    pprint(report.model_dump())
