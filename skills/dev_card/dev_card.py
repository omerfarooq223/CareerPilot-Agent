import sys, os, json, yaml
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from loguru import logger
from memory.short_term import SessionMemory
from memory.long_term import log_action


def generate_dev_card(session: SessionMemory) -> str:
    from actions.executor import call_groq, save_output

    logger.info("Action: generate_dev_card")

    profile = session.profile
    goals = {}
    with open("config/goals.yaml") as f:
        goals = yaml.safe_load(f)

    prompt = f"""
You are writing a developer profile card in markdown for a student's portfolio.

Developer info:
- Name: {profile.name if profile else 'Unknown'}
- Bio: {profile.bio if profile else ''}
- Total repos: {profile.public_repos if profile else 0}
- Languages: {profile.languages_used if profile else {}}
- Top repos: {[r.name for r in profile.repos[:5]] if profile else []}
- Target role: {goals.get('target_role', '')}
- Skills: {goals.get('self_declared_skills', [])}
- CGPA: {goals.get('credentials', {}).get('cgpa', '')}
- Awards: {goals.get('credentials', {}).get('awards', [])}
- Portfolio: {goals.get('portfolio', '')}

Write a markdown developer card that:
1. Starts with a strong one-liner capturing who they are
2. Lists their strongest 5 skills with context (not just names)
3. Highlights their 3 best projects with what makes each special
4. Shows academic achievements naturally
5. Ends with what they're looking for and how to reach them

Keep it honest, confident, and under 400 words.
"""

    result = call_groq(prompt)
    save_output("developer_card.md", result)
    log_action("generate_dev_card", "Developer card generated")
    session.remember_action("generate_dev_card")
    return result