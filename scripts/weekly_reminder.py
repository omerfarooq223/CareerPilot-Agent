import os
import smtplib
import sqlite3
import json
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

DB_PATH = "memory/careerpilot.db"

SENDER    = os.getenv("REMINDER_EMAIL_SENDER")
PASSWORD  = os.getenv("REMINDER_EMAIL_PASSWORD")
RECEIVERS = os.getenv("REMINDER_EMAIL_RECEIVERS", "").split(",")


# ── Fetch data from SQLite ─────────────────────────────────────────

def get_latest_data() -> dict:
    if not Path(DB_PATH).exists():
        return {}
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Latest snapshot
    cursor.execute("""
        SELECT overall_score, critical_gaps, strengths, verdict, timestamp
        FROM weekly_snapshots ORDER BY timestamp DESC LIMIT 1
    """)
    row = cursor.fetchone()

    # Score history
    cursor.execute("""
        SELECT overall_score, timestamp FROM weekly_snapshots
        ORDER BY timestamp DESC LIMIT 5
    """)
    history = cursor.fetchall()

    # Last LinkedIn post
    cursor.execute("""
        SELECT repo_name, post_type, timestamp, status
        FROM linkedin_posts WHERE status = 'approved'
        ORDER BY timestamp DESC LIMIT 1
    """)
    last_post = cursor.fetchone()

    conn.close()

    if not row:
        return {}

    score, gaps, strengths, verdict, ts = row
    days_since_post = None
    if last_post:
        last_post_date = datetime.fromisoformat(last_post[2])
        days_since_post = (datetime.now() - last_post_date).days

    return {
        "score":            score,
        "critical_gaps":    json.loads(gaps),
        "strengths":        json.loads(strengths),
        "verdict":          verdict,
        "last_updated":     ts[:10],
        "score_history":    [{"score": r[0], "date": r[1][:10]} for r in history],
        "days_since_post":  days_since_post,
        "last_post_repo":   last_post[0] if last_post else None,
    }


# ── Build email ────────────────────────────────────────────────────

def build_html(data: dict) -> str:
    if not data:
        return """
        <p>No data available yet — run CareerPilot first to generate your profile.</p>
        <p><a href="https://github.com/omerfarooq223/careerpilot">Open CareerPilot →</a></p>
        """

    score        = data.get("score", "N/A")
    gaps         = data.get("critical_gaps", [])
    strengths    = data.get("strengths", [])
    verdict      = data.get("verdict", "")
    last_updated = data.get("last_updated", "Unknown")
    history      = data.get("score_history", [])
    days_post    = data.get("days_since_post")
    last_repo    = data.get("last_post_repo")

    # Score color
    score_color = "#059669" if score >= 8 else "#0ea5e9" if score >= 6 else "#e11d48"

    # LinkedIn nudge
    if days_post is None:
        linkedin_msg = "⚠️ You haven't posted on LinkedIn yet — your profile is invisible to recruiters."
    elif days_post >= 7:
        linkedin_msg = f"⚠️ It's been {days_post} days since your last post (about {last_repo}). Time to post again."
    else:
        linkedin_msg = f"✅ Good — you posted {days_post} days ago about {last_repo}. Keep it up."

    # Score trend
    trend_html = ""
    if len(history) >= 2:
        delta = history[0]["score"] - history[1]["score"]
        arrow = "↑" if delta > 0 else "↓" if delta < 0 else "→"
        trend_color = "#059669" if delta > 0 else "#e11d48" if delta < 0 else "#64748b"
        trend_html = f'<span style="color:{trend_color};font-weight:700;">{arrow} {"+"+str(delta) if delta > 0 else delta} from last session</span>'

    gaps_html = "".join(
        f'<li style="color:#e11d48;margin-bottom:6px;">✗ {g}</li>' for g in gaps
    )
    strengths_html = "".join(
        f'<li style="color:#059669;margin-bottom:6px;">✓ {s}</li>' for s in strengths
    )

    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Segoe UI',Arial,sans-serif;">
  <div style="max-width:600px;margin:32px auto;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.08);">

    <!-- Header -->
    <div style="background:#0ea5e9;padding:28px 32px;">
      <div style="font-size:22px;font-weight:800;color:white;letter-spacing:-0.5px;">🤖 CareerPilot</div>
      <div style="font-size:13px;color:rgba(255,255,255,0.8);margin-top:4px;">Your weekly career intelligence report</div>
    </div>

    <!-- Score section -->
    <div style="padding:28px 32px;border-bottom:1px solid #e2e8f0;">
      <div style="font-size:11px;font-weight:700;letter-spacing:1.5px;color:#94a3b8;text-transform:uppercase;margin-bottom:12px;">
        Hirability Score — Last updated {last_updated}
      </div>
      <div style="display:flex;align-items:center;gap:16px;">
        <div style="font-size:56px;font-weight:800;color:{score_color};line-height:1;letter-spacing:-2px;">
          {score}<span style="font-size:20px;color:#cbd5e1;font-weight:500;">/10</span>
        </div>
        <div>
          {trend_html}
          <div style="font-size:13px;color:#64748b;margin-top:6px;line-height:1.5;max-width:340px;">{verdict[:200]}...</div>
        </div>
      </div>
      <!-- Score bar -->
      <div style="height:6px;background:#e0f2fe;border-radius:3px;margin-top:16px;overflow:hidden;">
        <div style="height:100%;width:{score*10}%;background:#0ea5e9;border-radius:3px;"></div>
      </div>
    </div>

    <!-- Gaps & Strengths -->
    <div style="padding:24px 32px;border-bottom:1px solid #e2e8f0;display:flex;gap:32px;">
      <div style="flex:1;">
        <div style="font-size:11px;font-weight:700;letter-spacing:1px;color:#94a3b8;text-transform:uppercase;margin-bottom:10px;">
          Critical Gaps
        </div>
        <ul style="list-style:none;margin:0;padding:0;font-size:13px;">
          {gaps_html if gaps_html else '<li style="color:#94a3b8;">None detected</li>'}
        </ul>
      </div>
      <div style="flex:1;">
        <div style="font-size:11px;font-weight:700;letter-spacing:1px;color:#94a3b8;text-transform:uppercase;margin-bottom:10px;">
          Strengths
        </div>
        <ul style="list-style:none;margin:0;padding:0;font-size:13px;">
          {strengths_html if strengths_html else '<li style="color:#94a3b8;">Run agent first</li>'}
        </ul>
      </div>
    </div>

    <!-- LinkedIn nudge -->
    <div style="padding:20px 32px;background:#f8fafc;border-bottom:1px solid #e2e8f0;">
      <div style="font-size:13px;color:#334155;font-weight:500;">
        LinkedIn Activity
      </div>
      <div style="font-size:13px;color:#64748b;margin-top:6px;">{linkedin_msg}</div>
    </div>

    <!-- CTA -->
    <div style="padding:24px 32px;text-align:center;">
      <div style="font-size:13px;color:#64748b;margin-bottom:16px;">
        Open CareerPilot and run the agent to update your report
      </div>
      <a href="https://github.com/omerfarooq223/careerpilot"
         style="display:inline-block;background:#0ea5e9;color:white;padding:12px 28px;
                border-radius:8px;font-size:13px;font-weight:600;text-decoration:none;
                letter-spacing:0.3px;">
        Open CareerPilot →
      </a>
    </div>

    <!-- Footer -->
    <div style="padding:16px 32px;background:#f8fafc;border-top:1px solid #e2e8f0;
                font-size:11px;color:#94a3b8;text-align:center;">
      CareerPilot · Automated weekly reminder · {datetime.now().strftime('%B %d, %Y')}
    </div>

  </div>
</body>
</html>
"""


# ── Send email ─────────────────────────────────────────────────────

def send_reminder():
    print("Fetching CareerPilot data...")
    data = get_latest_data()

    subject = f"CareerPilot Weekly — Score: {data.get('score','N/A')}/10 · {datetime.now().strftime('%b %d')}"
    html    = build_html(data)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SENDER
    msg["To"]      = ", ".join(RECEIVERS)
    msg.attach(MIMEText(html, "html"))

    print(f"Sending to: {RECEIVERS}")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER, PASSWORD)
        server.sendmail(SENDER, RECEIVERS, msg.as_string())

    print(f"✓ Reminder sent to {len(RECEIVERS)} recipients")


if __name__ == "__main__":
    send_reminder()