from secrets import choice
import sys, os, json, yaml, webbrowser
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from loguru import logger
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from memory.short_term import SessionMemory
from memory.long_term import (
    log_action,
    save_linkedin_post,
    get_posted_repos,
    get_linkedin_post_history,
    get_last_post_date
)

console = Console()

POST_TYPES = {
    "new_repo":     "Announcing a newly pushed or updated repo",
    "progress":     "Weekly progress milestone or score improvement",
    "project_done": "A completed project showcase",
    "intro":        "First LinkedIn post introducing yourself and your work",
    "past_repos":   "Showcasing existing repos for visibility"
}


# ── Smart trigger detection ────────────────────────────────────────────────────

def detect_post_opportunity(session: SessionMemory) -> tuple[str, str | None]:
    """
    Analyze history and current state to decide WHAT to post about.
    Returns (post_type, repo_name or None).
    Never repeats a repo that's already been posted about.
    """
    history = get_linkedin_post_history()
    posted_repos = get_posted_repos()
    last_post_date = get_last_post_date()

    # Check if posted too recently (within 5 days)
    if last_post_date:
        last_dt = datetime.fromisoformat(last_post_date)
        days_since = (datetime.now() - last_dt).days
        if days_since < 5:
            logger.info(f"Last post was {days_since} days ago — too soon to post again")
            return "too_soon", None

    # First ever post — do intro
    if not history:
        return "intro", None

    # Find repos not yet posted about
    unposted_repos = []
    if session.profile:
        for repo in session.profile.repos:
            if repo.name not in posted_repos:
                unposted_repos.append(repo)

    if unposted_repos:
        scored = sorted(
            unposted_repos,
            key=lambda r: (len(r.topics) > 0, r.stars, r.commit_count),
            reverse=True
        )
        best_repo = scored[0]
        logger.info(f"Found unposted repo to feature: {best_repo.name}")
        return "new_repo", best_repo.name

    logger.info("All repos posted — generating progress post")
    return "progress", None


# ── Repo narrative builder ─────────────────────────────────────────────────────

def build_repo_narrative(repos: list) -> str:
    """
    Convert raw repo objects into a human-readable narrative block.
    This prevents the LLM from having to interpret raw JSON metadata.
    """
    lines = []
    for r in repos:
        block = f"""Project: {r.get('name', 'Unknown')}
What it does: {r.get('description') or 'No description provided'}
Stack: {r.get('language', 'Unknown')} | Topics: {', '.join(r.get('topics', [])) or 'none tagged'}
Stars: {r.get('stars', 0)} | Commits: {r.get('commit_count', 0)}
URL: {r.get('url', '')}"""
        lines.append(block)
    return "\n\n".join(lines)


# ── Post generator ─────────────────────────────────────────────────────────────

def generate_linkedin_post(
    session: SessionMemory,
    post_type: str,
    repo_name: str = None
) -> str:
    from actions.executor import call_groq, save_output

    with open("config/goals.yaml") as f:
        goals = yaml.safe_load(f)

    # Build repo context as raw dicts first
    repo_dicts = []
    if session.profile:
        for r in session.profile.repos:
            if repo_name and r.name != repo_name:
                continue
            repo_dicts.append({
                "name": r.name,
                "description": r.description,
                "language": r.language,
                "topics": r.topics,
                "stars": r.stars,
                "url": r.url,
                "commit_count": r.commit_count
            })

    if not repo_name:
        repo_dicts = repo_dicts[:5]

    # Convert to human-readable narrative — LLM handles voice, not data parsing
    repo_narrative = build_repo_narrative(repo_dicts)

    # Build history context so agent avoids repeating angles
    history = get_linkedin_post_history()
    history_summary = []
    for h in history[:5]:
        history_summary.append(
            f"- {h['timestamp'][:10]}: {h['post_type']} about {h['repo_name'] or 'general'} ({h['status']})"
        )

    score = session.gap_report.overall_score if session.gap_report else None
    name = session.profile.name if session.profile else "Developer"
    bio = session.profile.bio if session.profile else ""
    github_url = goals.get("github", "")

    prompt = f"""
You are ghostwriting a LinkedIn post for {name}, a AI student who builds real projects and is actively looking for internships. 

--- VOICE ---
Write like someone who genuinely loves building things and is proud but not arrogant.
Use short punchy sentences. Occasional fragments are fine.
The reader should feel like they're hearing from a real person at 1am who just got something working.

--- ABOUT THE BUILDER ---
Bio: {bio}
Target role: {goals.get('target_role')}
Core skills: {goals.get('self_declared_skills')}
CGPA: {goals.get('credentials', {}).get('cgpa', '')}
Awards: {goals.get('credentials', {}).get('awards', [])}
Portfolio: {goals.get('portfolio', '')}
GitHub: {github_url}
Hirability score: {score}/10

--- PROJECT TO WRITE ABOUT ---
{repo_narrative}

--- POST TYPE ---
{POST_TYPES.get(post_type, post_type)}

--- DO NOT REPEAT THESE (already posted) ---
{chr(10).join(history_summary) if history_summary else 'No previous posts — this is the first one'}

--- POST STRUCTURE ---

Line 1 (HOOK): One sentence. What does it do and why does it matter to you personally?

Lines 2–6 (WHAT YOU BUILT): 
- What problem does it solve?
- What's the most interesting technical decision you made?
- Name specific components — don't just say "backend", say FastAPI + SQLite + Groq
- What does the output actually look like? (e.g. "spits out a hirability score out of 10")

Lines 7–9 (WHY IT'S DIFFERENT):
What makes this project non-trivial? What would a recruiter find impressive?
One concrete capability, not a vague claim.

Line 10: GitHub link as a natural sentence
Line 11: 6–7 hashtags

--- EXAMPLE OF THE RIGHT VOICE ---
"Built a rate limiter for my API last week. Thought it'd take 2 hours. Took 11.
The issue wasn't the algorithm — Redis expiry keys behave differently under
concurrent load than in tests. Spent 8 hours convinced my logic was wrong. It wasn't.
Code's on my GitHub if you want to see the mess."

Match this energy — specific tech, no corporate language, proud but not hype.

--- HARD RULES ---
- 900–1200 characters total. Count carefully.
- Never use: "excited to share", "pleased to announce", "game-changer", "this has the potential to", "I think this can really"
- Every sentence must be specific to THIS project — if it could appear in any developer's post, cut it
- Line breaks every 2–3 lines for LinkedIn readability
- No bullet points
- ALWAYS include these fixed hashtags: #OpenToWork #Pakistan #BuildInPublic #AIAgents
- Then generate 3–4 additional hashtags that are:
  - Specific to THIS project (not generic like #Python or #AI)
  - Niche enough to stand out but real enough that people follow them
  - Examples of the right kind: #LLMEngineering, #Groq, #StudentDeveloper, #FastAPI
  - Never use: #Coding, #Tech, #Developer, #Programming, #MachineLearning
- Total hashtags: 7–8

Write ONE complete LinkedIn post. Nothing else.
"""

    post = call_groq(prompt, max_tokens=800)
    filename = f"linkedin_{post_type}_{repo_name or 'general'}.md"
    save_output(filename, post)
    return post


# ── HITL approval flow ─────────────────────────────────────────────────────────

def linkedin_writer(session: SessionMemory) -> str:
    logger.info("Action: linkedin_writer")

    console.rule("[bold blue]LinkedIn Post Generator")

    post_type, repo_name = detect_post_opportunity(session)

    if post_type == "too_soon":
        last = get_last_post_date()
        days = (datetime.now() - datetime.fromisoformat(last)).days
        msg = f"Posted {days} days ago — waiting until 5 days have passed before next post."
        console.print(f"[yellow]{msg}[/yellow]")
        session.remember_action("linkedin_writer")
        return json.dumps({"status": "error", "message": msg})

    if repo_name:
        console.print(f"[yellow]Generating post about: [bold]{repo_name}[/bold][/yellow]")
    else:
        console.print(f"[yellow]Generating post type: [bold]{post_type}[/bold][/yellow]")

    history = get_linkedin_post_history()
    if history:
        console.print(f"\n[dim]Previously posted about: {', '.join(get_posted_repos()) or 'nothing yet'}[/dim]")

    console.print("\n[dim]Writing your LinkedIn post...[/dim]\n")
    post = generate_linkedin_post(session, post_type, repo_name)

    console.print(Panel(
        post,
        title="[bold green]📝 Your LinkedIn Post",
        border_style="green",
        padding=(1, 2)
    ))
    console.print(f"[dim]Character count: {len(post)}/1300[/dim]\n")

    # Save as pending and return structured json to UI
    post_id = save_linkedin_post(post_type, repo_name, post, "pending")
    session.remember_action("linkedin_writer")
    
    return json.dumps({
        "status": "pending",
        "post_id": post_id,
        "post": post,
        "post_type": post_type,
        "repo_name": repo_name
    })


# ── Quick test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from skills.github_observer.github_observer import fetch_github_profile
    from skills.gap_analyzer.gap_analyzer import analyze_gaps
    from memory.long_term import init_db

    init_db()
    session = SessionMemory()
    session.profile = fetch_github_profile()
    session.gap_report = analyze_gaps(session.profile)

    result = linkedin_writer(session)
    console.print(f"\n[bold]{result}[/bold]")