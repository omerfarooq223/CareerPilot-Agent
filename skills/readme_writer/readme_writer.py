import sys, os, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from loguru import logger
from memory.short_term import SessionMemory
from memory.long_term import log_action


def rewrite_readme(session: SessionMemory, repo_name: str = None) -> str:
    from actions.executor import call_groq, save_output

    logger.info("Action: rewrite_readme")

    if not repo_name and session.gap_report and session.gap_report.weakest_repos:
        repo_name = session.gap_report.weakest_repos[0]
    elif not repo_name:
        repo_name = "unknown"

    repo_details = {}
    if session.profile:
        for r in session.profile.repos:
            if r.name == repo_name:
                repo_details = r.model_dump()
                break

    prompt = f"""
You are a technical writer rewriting a GitHub README to be professional and impressive.

Repo: {repo_name}
Current details: {json.dumps(repo_details, indent=2)}

Write a complete, professional README.md that includes:
- A clear project title and one-line description
- Badges (build, language, license)
- What it does (2-3 sentences)
- Key features (bullet list)
- Tech stack
- Installation and usage instructions
- Project structure
- Future improvements
- License section

Make it look like a professional open-source project.
"""

    result = call_groq(prompt)
    save_output(f"readme_{repo_name}.md", result)
    log_action("rewrite_readme", f"README rewritten for: {repo_name}")
    session.remember_action("rewrite_readme")
    return result
