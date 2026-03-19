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
        # Pick the most impressive unposted repo
        # Prioritize: has topics > has stars > most commits
        scored = sorted(
            unposted_repos,
            key=lambda r: (len(r.topics) > 0, r.stars, r.commit_count),
            reverse=True
        )
        best_repo = scored[0]
        logger.info(f"Found unposted repo to feature: {best_repo.name}")
        return "new_repo", best_repo.name

    # All repos posted — do a progress/milestone post
    logger.info("All repos posted — generating progress post")
    return "progress", None


# ── Post generator ─────────────────────────────────────────────────────────────

def generate_linkedin_post(
    session: SessionMemory,
    post_type: str,
    repo_name: str = None
) -> str:
    from actions.executor import call_groq, save_output

    with open("config/goals.yaml") as f:
        goals = yaml.safe_load(f)

    # Build repo context
    repo_context = []
    if session.profile:
        for r in session.profile.repos:
            if repo_name and r.name != repo_name:
                continue
            repo_context.append({
                "name": r.name,
                "description": r.description,
                "language": r.language,
                "topics": r.topics,
                "stars": r.stars,
                "url": r.url,
                "commit_count": r.commit_count
            })

    if not repo_name:
        repo_context = repo_context[:5]

    # Build history context so agent avoids repeating angles
    history = get_linkedin_post_history()
    history_summary = []
    for h in history[:5]:
        history_summary.append(
            f"- {h['timestamp'][:10]}: {h['post_type']} about {h['repo_name'] or 'general'} ({h['status']})"
        )

    score = session.gap_report.overall_score if session.gap_report else None

    prompt = f"""
You are a LinkedIn content writer for a student developer.
Write a LinkedIn post that feels HUMAN — not corporate, not cringe, not generic AI-written.

--- DEVELOPER INFO ---
Name: {session.profile.name if session.profile else 'Developer'}
Bio: {session.profile.bio if session.profile else ''}
Target role: {goals.get('target_role')}
Skills: {goals.get('self_declared_skills')}
CGPA: {goals.get('credentials', {}).get('cgpa', '')}
Awards: {goals.get('credentials', {}).get('awards', [])}
Portfolio: {goals.get('portfolio', '')}
GitHub: {goals.get('github', '')}
Hirability score: {score}/10

--- REPOS TO FEATURE ---
{json.dumps(repo_context, indent=2)}

--- POST TYPE ---
{POST_TYPES.get(post_type, post_type)}

--- PREVIOUS POSTS (do NOT repeat these angles or repos) ---
{chr(10).join(history_summary) if history_summary else 'No previous posts'}

--- WRITING RULES ---
1. Start with a bold hook — one punchy line that stops scrolling
2. Tell a real story — what did you build? what was the hardest part?
3. Show your thinking — what did you learn?
4. Mention specific tech naturally in the post
5. Include your GitHub link
6. End with 4-5 hashtags: always include #OpenToWork #Python #Pakistan #AgenticAI
7. AIM FOR 900-1200 characters — do not write short posts
8. Use line breaks every 2-3 lines for readability
9. Sound like a smart ambitious student — not a corporate robot
10. NEVER use "I am pleased to announce" or "I am excited to share"
11. NEVER write less than 800 characters

Write ONE complete LinkedIn post of 900-1200 characters. Nothing else.
    """

    post = call_groq(prompt, max_tokens=800)
    filename = f"linkedin_{post_type}_{repo_name or 'general'}.md"
    save_output(filename, post)
    return post


# ── HITL approval flow ─────────────────────────────────────────────────────────

def linkedin_writer(session: SessionMemory) -> str:
    logger.info("Action: linkedin_writer")

    console.rule("[bold blue]LinkedIn Post Generator")

    # Detect what to post about
    post_type, repo_name = detect_post_opportunity(session)

    # Too soon to post
    if post_type == "too_soon":
        last = get_last_post_date()
        days = (datetime.now() - datetime.fromisoformat(last)).days
        msg = f"Posted {days} days ago — waiting until 5 days have passed before next post."
        console.print(f"[yellow]{msg}[/yellow]")
        session.remember_action("linkedin_writer")
        return msg

    # Show what we're posting about
    if repo_name:
        console.print(f"[yellow]Generating post about: [bold]{repo_name}[/bold][/yellow]")
    else:
        console.print(f"[yellow]Generating post type: [bold]{post_type}[/bold][/yellow]")

    # Show full history
    history = get_linkedin_post_history()
    if history:
        console.print(f"\n[dim]Previously posted about: {', '.join(get_posted_repos()) or 'nothing yet'}[/dim]")

    # Generate post
    console.print("\n[dim]Writing your LinkedIn post...[/dim]\n")
    post = generate_linkedin_post(session, post_type, repo_name)

    # Display post
    console.print(Panel(
        post,
        title="[bold green]📝 Your LinkedIn Post",
        border_style="green",
        padding=(1, 2)
    ))
    console.print(f"[dim]Character count: {len(post)}/1300[/dim]\n")

    # HITL approval loop
    while True:
        console.print("[bold]What would you like to do?[/bold]")
        console.print("  [green]Y[/green] — Approve, copy to clipboard + open LinkedIn")
        console.print("  [yellow]R[/yellow] — Regenerate a different version")
        console.print("  [red]N[/red] — Discard this post")

        choice = input("\nYour choice (Y/R/N): ").strip().upper()
        if not choice:
            console.print("[red]Please type Y, R, or N and press Enter[/red]")
            continue

        if choice == "Y":
            _copy_and_open(post)
            save_linkedin_post(post_type, repo_name, post, "approved")
            log_action("linkedin_posted", f"Approved — {post_type} about {repo_name}")
            session.remember_action("linkedin_writer")
            return "✅ Post copied to clipboard. LinkedIn opened — paste and post!"

        elif choice == "R":
            save_linkedin_post(post_type, repo_name, post, "regenerated")
            console.print("\n[yellow]Regenerating a fresh version...[/yellow]\n")
            post = generate_linkedin_post(session, post_type, repo_name)
            console.print(Panel(
                post,
                title="[bold green]📝 Regenerated Post",
                border_style="green",
                padding=(1, 2)
            ))
            console.print(f"[dim]Character count: {len(post)}/1300[/dim]\n")

        elif choice == "N":
            save_linkedin_post(post_type, repo_name, post, "discarded")
            log_action("linkedin_post_discarded", f"{post_type} about {repo_name}")
            session.remember_action("linkedin_writer")
            return "Post discarded."

        else:
            console.print("[red]Please enter Y, R, or N[/red]")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _copy_and_open(post: str):
    try:
        import pyperclip
        pyperclip.copy(post)
        console.print("\n[green]✓ Copied to clipboard[/green]")
    except Exception:
        console.print("\n[yellow]Could not copy — copy the post manually[/yellow]")
    webbrowser.open("https://www.linkedin.com/feed/")
    console.print("[green]✓ LinkedIn opened in browser[/green]")


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