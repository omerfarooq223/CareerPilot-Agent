import json
from datetime import datetime
from pathlib import Path
from loguru import logger
from skills.github_observer.github_observer import GitHubProfile
from skills.gap_analyzer.gap_analyzer import GapReport
from database.db_utils import get_db_pool


def init_db() -> None:
    """Initialize SQLite database and create tables if they do not exist."""
    """Create the database and tables if they don't exist."""
    from database.db_utils import init_db_with_pool
    init_db_with_pool()
    logger.info("Database initialized")
    seed_from_snapshot()


def save_snapshot(report: GapReport) -> None:
    """Persist a GapReport snapshot to the weekly_snapshots table."""
    """Save a gap report snapshot to long-term memory."""
    pool = get_db_pool()

    with pool.get_conn() as conn:
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
    logger.success(f"Snapshot saved — score: {report.overall_score}/10")


def log_action(action_type: str, description: str) -> None:
    """Log an agent action to the actions_log table."""
    """Log an agent action to memory."""
    pool = get_db_pool()

    with pool.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO actions_log (timestamp, action_type, description)
            VALUES (?, ?, ?)
        """, (datetime.now().isoformat(), action_type, description))
        conn.commit()


def get_last_snapshot() -> dict | None:
    """Return the most recent weekly snapshot as a dict, or None if empty."""
    """Retrieve the most recent snapshot."""
    pool = get_db_pool()

    with pool.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM weekly_snapshots ORDER BY timestamp DESC LIMIT 1
        """)
        row = cursor.fetchone()

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
    """Return all historical scores ordered chronologically."""
    """Get all scores over time to track progress."""
    pool = get_db_pool()

    with pool.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, overall_score FROM weekly_snapshots ORDER BY timestamp ASC
        """)
        rows = cursor.fetchall()

        return [{"timestamp": r[0], "score": r[1]} for r in rows]

def save_linkedin_post(post_type: str, repo_name: str, content: str, status: str):
    """Save a LinkedIn post to memory."""
    pool = get_db_pool()

    with pool.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO linkedin_posts (timestamp, post_type, repo_name, post_content, status)
            VALUES (?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), post_type, repo_name, content, status))
        conn.commit()
    logger.info(f"LinkedIn post saved — type: {post_type}, repo: {repo_name}, status: {status}")


def get_posted_repos() -> list[str]:
    """Return list of repo names already posted about."""
    pool = get_db_pool()

    with pool.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT repo_name FROM linkedin_posts
            WHERE status = 'approved' AND repo_name IS NOT NULL
        """)
        rows = cursor.fetchall()

        return [r[0] for r in rows]


def get_linkedin_post_history() -> list[dict]:
    """Return full LinkedIn post history."""
    pool = get_db_pool()

    with pool.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, post_type, repo_name, status
            FROM linkedin_posts
            ORDER BY timestamp DESC
        """)
        rows = cursor.fetchall()

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
    pool = get_db_pool()

    with pool.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp FROM linkedin_posts
            WHERE status = 'approved'
            ORDER BY timestamp DESC LIMIT 1
        """)
        row = cursor.fetchone()

        return row[0] if row else None

def get_gap_trend() -> dict:
    """Compare last two snapshots to show closed, new, and persisted gaps."""
    """Compare current gaps with previous session to show what changed."""
    history = get_score_history()
    if len(history) < 2:
        return {"status": "insufficient_data"}

    pool = get_db_pool()

    with pool.get_conn() as conn:
        cursor = conn.cursor()

        # Get last two snapshots
        cursor.execute("""
            SELECT critical_gaps, strengths, overall_score, timestamp
            FROM weekly_snapshots
            ORDER BY timestamp DESC
            LIMIT 2
        """)
        rows = cursor.fetchall()

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



def log_outcome(company: str, role: str, status: str, notes: str = "") -> None:
    """Log a job application outcome."""
    history = get_score_history()
    score = history[-1]["score"] if history else None
    pool = get_db_pool()
    with pool.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO outcomes (timestamp, company, role, status, score_at_time, applied_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), company, role, status, score,
              datetime.now().strftime("%Y-%m-%d"), notes))
        conn.commit()
    logger.info(f"Outcome logged: {company} — {status}")


def get_outcomes() -> list[dict]:
    """Return all logged outcomes ordered by date."""
    pool = get_db_pool()
    with pool.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, timestamp, company, role, status, score_at_time, applied_date, notes
            FROM outcomes ORDER BY timestamp DESC
        """)
        rows = cursor.fetchall()
        return [
            {
                "id": r[0], "timestamp": r[1], "company": r[2],
                "role": r[3], "status": r[4], "score_at_time": r[5],
                "applied_date": r[6], "notes": r[7]
            }
            for r in rows
        ]


def get_outcome_stats() -> dict:
    """Return outcome statistics — response rates by score."""
    outcomes = get_outcomes()
    if not outcomes:
        return {"total": 0, "by_status": {}, "by_score": {}}

    by_status = {}
    by_score  = {}

    for o in outcomes:
        status = o["status"]
        score  = o["score_at_time"]
        by_status[status] = by_status.get(status, 0) + 1
        if score:
            if score not in by_score:
                by_score[score] = {"applied": 0, "responses": 0}
            by_score[score]["applied"] += 1
            if status in ["interview", "offer"]:
                by_score[score]["responses"] += 1

    return {
        "total":     len(outcomes),
        "by_status": by_status,
        "by_score":  by_score,
    }


def save_feedback(skill_name: str, output_file: str, rating: int, comment: str = "") -> None:
    """Save user feedback (thumbs up/down) for a skill output."""
    pool = get_db_pool()
    with pool.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO skill_feedback (timestamp, skill_name, output_file, rating, comment)
            VALUES (?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), skill_name, output_file, rating, comment))
        conn.commit()
    logger.info(f"Feedback saved: {skill_name} → {'👍' if rating == 1 else '👎'}")


def get_feedback_summary() -> list[dict]:
    """Return aggregated feedback per skill."""
    pool = get_db_pool()
    with pool.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT skill_name,
                   COUNT(*) as total,
                   SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) as thumbs_up,
                   SUM(CASE WHEN rating = -1 THEN 1 ELSE 0 END) as thumbs_down
            FROM skill_feedback
            GROUP BY skill_name
        """)
        rows = cursor.fetchall()
        return [
            {
                "skill": r[0],
                "total": r[1],
                "thumbs_up": r[2],
                "thumbs_down": r[3],
                "score": round((r[2] / r[1]) * 100) if r[1] > 0 else 0
            }
            for r in rows
        ]


def export_latest_snapshot():
    """Export latest data to a JSON file that GitHub Actions can read."""
    snapshot = get_last_snapshot()
    history  = get_score_history()
    trend    = get_gap_trend()

    pool = get_db_pool()
    with pool.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT repo_name, post_type, timestamp, status
            FROM linkedin_posts WHERE status = 'approved'
            ORDER BY timestamp DESC LIMIT 1
        """)
        last_post = cursor.fetchone()

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

def seed_from_snapshot():
    """On fresh deployment, seed DB from latest_snapshot.json if DB is empty."""
    import json
    from pathlib import Path

    snapshot_path = Path(__file__).resolve().parent / "latest_snapshot.json"
    if not snapshot_path.exists():
        return

    history = get_score_history()
    if history:
        return  # DB already has data

    try:
        data = json.loads(snapshot_path.read_text())
        if not data.get("score"):
            return

        pool = get_db_pool()
        with pool.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO weekly_snapshots
                (timestamp, overall_score, strengths, critical_gaps, top_3_actions, portfolio_ready_repos, verdict)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("last_updated", datetime.now().isoformat()),
                data["score"],
                json.dumps(data.get("strengths", [])),
                json.dumps(data.get("critical_gaps", [])),
                json.dumps(data.get("score_history", [{}])[-1:]),
                json.dumps([]),
                "Seeded from latest_snapshot.json"
            ))
            conn.commit()
        logger.info("DB seeded from latest_snapshot.json")
    except Exception as e:
        logger.warning(f"Could not seed from snapshot: {e}")

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
