import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import yaml
from loguru import logger
from rich.console import Console
from rich.rule import Rule
from rich.panel import Panel
from rich.text import Text
from dotenv import load_dotenv

from skills.github_observer.github_observer import fetch_github_profile
from skills.gap_analyzer.gap_analyzer import analyze_gaps
from skills.registry import registry
from planner.reasoner import make_plan
from actions.executor import execute_plan
from actions.security import check_env_vars, validate_goals
from memory.short_term import SessionMemory
from memory.long_term import init_db, save_snapshot, log_action, get_score_history, export_latest_snapshot
from pathlib import Path
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / "config" / ".env", override=True)
console = Console()


# ── Boot screen ────────────────────────────────────────────────────────────────

def print_banner():
    console.print(Panel.fit(
        Text("🤖 CareerPilot Agent", style="bold green", justify="center"),
        subtitle="Your personal internship prep co-pilot",
        border_style="green"
    ))


# ── Progress tracker ───────────────────────────────────────────────────────────

def print_progress(history: list[dict]):
    if len(history) < 2:
        console.print("[dim]First run — no history to compare yet.[/dim]")
        return
    first = history[0]["score"]
    latest = history[-1]["score"]
    delta = latest - first
    arrow = "📈" if delta > 0 else "📉" if delta < 0 else "➡️"
    console.print(
        f"{arrow} Score over {len(history)} sessions: "
        f"[bold]{first}[/bold] → [bold green]{latest}[/bold green] "
        f"({'+'if delta >= 0 else ''}{delta})"
    )


# ── Core agent loop ────────────────────────────────────────────────────────────

def run():
    print_banner()
    console.print(f"[dim]Loaded skills: {', '.join(registry.list_enabled())}[/dim]")

    init_db()
    check_env_vars()

    with open("config/goals.yaml") as f:
        goals = yaml.safe_load(f)
    validate_goals(goals)
    
    # ── OBSERVE ───────────────────────────────────────────────────────────────
    console.rule("[bold blue]OBSERVE")
    console.print("Fetching your GitHub profile...")
    session = SessionMemory()
    session.profile = fetch_github_profile()
    # Auto-update goals before analysis
    from skills.goals_updater.goals_updater import update_goals
    update_goals(session)
    console.print(f"[green]✓[/green] {session.profile.public_repos} repos loaded for [bold]{session.profile.username}[/bold]")

    # ── ANALYZE ───────────────────────────────────────────────────────────────
    console.rule("[bold yellow]ANALYZE")
    console.print("Analyzing gaps against your goals...")
    session.gap_report = analyze_gaps(session.profile)
    console.print(f"[green]✓[/green] Hirability score: [bold]{session.gap_report.overall_score}/10[/bold]")
    console.print(f"[red]Critical gaps:[/red] {', '.join(session.gap_report.critical_gaps)}")

    # ── REMEMBER ──────────────────────────────────────────────────────────────
    console.rule("[bold cyan]REMEMBER")
    save_snapshot(session.gap_report)
    log_action("session_start", f"Score: {session.gap_report.overall_score}/10")
    history = get_score_history()
    print_progress(history)

    # ── PLAN ──────────────────────────────────────────────────────────────────
    console.rule("[bold magenta]PLAN")
    plan = make_plan(session)
    console.print(f"[green]✓[/green] Focus: [italic]{plan.current_focus}[/italic]")
    console.print(f"[green]✓[/green] Actions: {plan.actions_to_take}")
    console.print(Panel(
        f"[italic]{plan.message_to_user}[/italic]",
        title="💬 Agent says",
        border_style="yellow"
    ))

    # ── ACT ───────────────────────────────────────────────────────────────────
    console.rule("[bold red]ACT")
    execute_plan(plan.actions_to_take, session)

    # ── DONE ──────────────────────────────────────────────────────────────────
    export_latest_snapshot()
    console.rule("[bold green]DONE")
    console.print(f"[green]✓[/green] {len(session.actions_taken)} actions executed")
    console.print(f"[green]✓[/green] All outputs saved to: [bold]output/[/bold]")
    console.print(Panel(
        f"[italic]{plan.priority_action}[/italic]",
        title="🎯 Your #1 priority right now",
        border_style="green"
    ))


if __name__ == "__main__":
    run()
