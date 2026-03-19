import sqlite3
import json
from datetime import datetime
from loguru import logger
from skills.github_observer.github_observer import GitHubProfile
from skills.gap_analyzer.gap_analyzer import GapReport

import os
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "careerpilot.db")


def init_db():
    """Create the database and tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weekly_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            overall_score INTEGER,
            strengths TEXT,
            critical_gaps TEXT,
            top_3_actions TEXT,
            portfolio_ready_repos TEXT,
            verdict TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS actions_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action_type TEXT,
            description TEXT
        )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS linkedin_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        post_type TEXT,
        repo_name TEXT,
        post_content TEXT,
        status TEXT        -- 'approved', 'discarded', 'regenerated'
        )
    """) 
    conn.commit()
    conn.close()
    logger.info("Database initialized")


def save_snapshot(report: GapReport):
    """Save a gap report snapshot to long-term memory."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO weekly_snapshots
        (timestamp, overall_score, strengths, critical_gaps, top_3_actions, portfolio_ready_repos, verdict)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        report.overall_score,
        json.dumps(report.strengths),
        json.dumps(report.critical_gaps),
        json.dumps(report.top_3_actions),
        json.dumps(report.portfolio_ready_repos),
        report.verdict
    ))
    conn.commit()
    conn.close()
    logger.success(f"Snapshot saved — score: {report.overall_score}/10")


def log_action(action_type: str, description: str):
    """Log an agent action to memory."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO actions_log (timestamp, action_type, description)
        VALUES (?, ?, ?)
    """, (datetime.now().isoformat(), action_type, description))
    conn.commit()
    conn.close()


def get_last_snapshot() -> dict | None:
    """Retrieve the most recent snapshot."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM weekly_snapshots ORDER BY timestamp DESC LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "timestamp": row[1],
        "overall_score": row[2],
        "strengths": json.loads(row[3]),
        "critical_gaps": json.loads(row[4]),
        "top_3_actions": json.loads(row[5]),
        "portfolio_ready_repos": json.loads(row[6]),
        "verdict": row[7]
    }


def get_score_history() -> list[dict]:
    """Get all scores over time to track progress."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, overall_score FROM weekly_snapshots ORDER BY timestamp ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [{"timestamp": r[0], "score": r[1]} for r in rows]

def save_linkedin_post(post_type: str, repo_name: str, content: str, status: str):
    """Save a LinkedIn post to memory."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO linkedin_posts (timestamp, post_type, repo_name, post_content, status)
        VALUES (?, ?, ?, ?, ?)
    """, (datetime.now().isoformat(), post_type, repo_name, content, status))
    conn.commit()
    conn.close()
    logger.info(f"LinkedIn post saved — type: {post_type}, repo: {repo_name}, status: {status}")


def get_posted_repos() -> list[str]:
    """Return list of repo names already posted about."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT repo_name FROM linkedin_posts
        WHERE status = 'approved' AND repo_name IS NOT NULL
    """)
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_linkedin_post_history() -> list[dict]:
    """Return full LinkedIn post history."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, post_type, repo_name, status
        FROM linkedin_posts
        ORDER BY timestamp DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "timestamp": r[0],
            "post_type": r[1],
            "repo_name": r[2],
            "status": r[3]
        }
        for r in rows
    ]


def get_last_post_date() -> str | None:
    """Return timestamp of last approved post."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp FROM linkedin_posts
        WHERE status = 'approved'
        ORDER BY timestamp DESC LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def get_gap_trend() -> dict:
    """Compare current gaps with previous session to show what changed."""
    history = get_score_history()
    if len(history) < 2:
        return {"status": "insufficient_data"}

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get last two snapshots
    cursor.execute("""
        SELECT critical_gaps, strengths, overall_score, timestamp
        FROM weekly_snapshots
        ORDER BY timestamp DESC
        LIMIT 2
    """)
    rows = cursor.fetchall()
    conn.close()

    if len(rows) < 2:
        return {"status": "insufficient_data"}

    current_gaps  = set(json.loads(rows[0][0]))
    previous_gaps = set(json.loads(rows[1][0]))
    current_score  = rows[0][2]
    previous_score = rows[1][2]

    closed_gaps = previous_gaps - current_gaps
    new_gaps    = current_gaps - previous_gaps
    persisted   = current_gaps & previous_gaps

    return {
        "status":         "ok",
        "current_score":  current_score,
        "previous_score": previous_score,
        "score_delta":    current_score - previous_score,
        "closed_gaps":    list(closed_gaps),
        "new_gaps":       list(new_gaps),
        "persisted_gaps": list(persisted),
        "current_date":   rows[0][3][:10],
        "previous_date":  rows[1][3][:10],
    }

import json
from pathlib import Path

def export_latest_snapshot():
    """Export latest data to a JSON file that GitHub Actions can read."""
    snapshot = get_last_snapshot()
    history  = get_score_history()
    trend    = get_gap_trend()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT repo_name, post_type, timestamp, status
        FROM linkedin_posts WHERE status = 'approved'
        ORDER BY timestamp DESC LIMIT 1
    """)
    last_post = cursor.fetchone()
    conn.close()

    data = {
        "score":           snapshot["overall_score"] if snapshot else None,
        "critical_gaps":   snapshot["critical_gaps"] if snapshot else [],
        "strengths":       snapshot["strengths"] if snapshot else [],
        "verdict":         snapshot["verdict"] if snapshot else "",
        "last_updated":    snapshot["timestamp"][:10] if snapshot else None,
        "score_history":   history[-5:] if history else [],
        "score_delta":     trend.get("score_delta", 0) if trend.get("status") == "ok" else 0,
        "closed_gaps":     trend.get("closed_gaps", []) if trend.get("status") == "ok" else [],
        "days_since_post": None,
        "last_post_repo":  None,
    }

    if last_post:
        last_post_date = datetime.fromisoformat(last_post[2])
        data["days_since_post"] = (datetime.now() - last_post_date).days
        data["last_post_repo"]  = last_post[0]

    # Save to memory/ so it can be committed
    path = Path("memory/latest_snapshot.json")
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.success(f"Snapshot exported → {path}")

# ── Quick test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from rich.pretty import pprint

    init_db()

    from skills.github_observer.github_observer import fetch_github_profile
    from skills.gap_analyzer.gap_analyzer import analyze_gaps
    profile = fetch_github_profile()
    report = analyze_gaps(profile)

    save_snapshot(report)
    log_action("gap_analysis", f"Score: {report.overall_score}/10 — {len(report.critical_gaps)} gaps found")

    print("\n--- Last Snapshot ---")
    pprint(get_last_snapshot())

    print("\n--- Score History ---")
    pprint(get_score_history())
