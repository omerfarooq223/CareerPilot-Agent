import os
import json
import smtplib
from datetime import datetime, timezone
import sqlite3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

SENDER    = os.getenv("REMINDER_EMAIL_SENDER")
PASSWORD  = os.getenv("REMINDER_EMAIL_PASSWORD")
RECEIVERS = os.getenv("REMINDER_EMAIL_RECEIVERS", "").split(",")


def get_latest_post_info():
    db_path = Path("memory/careerpilot.db")
    if not db_path.exists():
        return None, None, None, None
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute('''SELECT timestamp, repo_name, post_content FROM linkedin_posts WHERE status="approved" ORDER BY timestamp DESC LIMIT 1''')
    row = cur.fetchone()
    conn.close()
    if not row:
        return None, None, None, None
    ts, repo, content = row
    # Calculate days since post
    post_time = datetime.fromisoformat(ts)
    now = datetime.now(timezone.utc).astimezone()
    days_since = (now.date() - post_time.date()).days
    return repo, content, days_since, ts


def get_latest_data() -> dict:
    """Load data from committed JSON snapshot."""
    data = None
    paths = [
        Path("memory/latest_snapshot.json"),
        Path("../memory/latest_snapshot.json"),
    ]
    for path in paths:
        if path.exists():
            print(f"Loading snapshot from {path}")
            data = json.loads(path.read_text())
            break
    if not data:
        print("No snapshot found")
        data = {}
    # Patch in latest LinkedIn post info
    repo, content, days_since, ts = get_latest_post_info()
    if repo:
        data["last_post_repo"] = repo
        data["days_since_post"] = days_since
        data["last_post_content"] = content
        data["last_post_timestamp"] = ts
    return data


def build_html(data: dict) -> str:
    if not data:
        return """
        <div style="padding:32px;text-align:center;font-family:'Segoe UI',Arial,sans-serif;">
          <p style="color:#64748b;font-size:14px;">No data yet — run CareerPilot first.</p>
          <a href="https://github.com/omerfarooq223/CareerPilot-Agent"
             style="display:inline-block;margin-top:16px;background:#0ea5e9;color:white;
                    padding:10px 24px;border-radius:8px;text-decoration:none;font-weight:600;">
            View on GitHub →
          </a>
        </div>"""

    score        = data.get("score", 0) or 0
    gaps         = data.get("critical_gaps", [])
    strengths    = data.get("strengths", [])
    verdict      = data.get("verdict", "")
    last_updated = data.get("last_updated", "Unknown")
    history      = data.get("score_history", [])
    days_post    = data.get("days_since_post")
    last_repo    = data.get("last_post_repo", "")
    score_delta  = data.get("score_delta", 0) or 0
    closed_gaps  = data.get("closed_gaps", [])

    score_color = "#059669" if score >= 8 else "#0ea5e9" if score >= 6 else "#e11d48"

    if score_delta > 0:
        trend = f'<span style="color:#059669;font-weight:700;">&#8593; +{score_delta} since last session</span>'
    elif score_delta < 0:
        trend = f'<span style="color:#e11d48;font-weight:700;">&#8595; {score_delta} since last session</span>'
    else:
        trend = '<span style="color:#94a3b8;">No change since last session</span>'

    if days_post is None:
        li_icon = "&#9888;"
        li_color = "#e11d48"
        li_msg = "You haven't posted on LinkedIn yet."
    elif days_post == 0:
        li_icon = "&#10003;"
        li_color = "#059669"
        li_msg = f"Posted today about <strong>{last_repo}</strong>. Great consistency!"
    elif days_post == 1:
        li_icon = "&#10003;"
        li_color = "#059669"
        li_msg = f"Posted yesterday about <strong>{last_repo}</strong>. Keep it up."
    elif days_post >= 7:
        li_icon = "&#9888;"
        li_color = "#e11d48"
        li_msg = f"<strong>{days_post} days</strong> since your last post. Time to post again."
    else:
        li_icon = "&#128204;"
        li_color = "#0ea5e9"
        li_msg = f"Posted <strong>{days_post} days ago</strong> about {last_repo}."

    gap_rows = "".join(
        f'<tr><td style="padding:7px 0;border-bottom:1px solid #f1f5f9;font-size:13px;color:#334155;">'
        f'<span style="color:#e11d48;margin-right:8px;font-weight:700;">&#10007;</span>{g}</td></tr>'
        for g in gaps
    ) or '<tr><td style="padding:7px 0;font-size:13px;color:#94a3b8;">No gaps detected &#10003;</td></tr>'

    strength_rows = "".join(
        f'<tr><td style="padding:7px 0;border-bottom:1px solid #f1f5f9;font-size:13px;color:#334155;">'
        f'<span style="color:#059669;margin-right:8px;font-weight:700;">&#10003;</span>{s}</td></tr>'
        for s in strengths
    ) or '<tr><td style="padding:7px 0;font-size:13px;color:#94a3b8;">—</td></tr>'

    priorities = gaps[:3]
    priority_items = "".join(
      f'<tr><td style="padding:9px 0;font-size:13px;color:#1e293b;line-height:1.55;">'
      f'<span style="display:inline-block;width:18px;height:18px;line-height:18px;text-align:center;border-radius:50%;'
      f'background:#eff6ff;color:#2563eb;font-size:11px;font-weight:700;margin-right:8px;">{idx+1}</span>{item}</td></tr>'
      for idx, item in enumerate(priorities)
    ) or '<tr><td style="padding:9px 0;font-size:13px;color:#334155;">You are in a strong position this week. Keep shipping quality work.</td></tr>'

    closed_section = ""
    if closed_gaps:
        items = "".join(
            f'<span style="display:inline-block;background:#d1fae5;border:1px solid #6ee7b7;'
            f'border-radius:4px;padding:2px 8px;font-size:12px;color:#065f46;margin:2px;">{g}</span>'
            for g in closed_gaps
        )
        closed_section = f"""
        <div style="padding:16px 32px 0;">
          <div style="background:#ecfdf5;border:1px solid #a7f3d0;border-radius:8px;padding:14px 16px;">
            <div style="font-size:12px;font-weight:700;color:#059669;margin-bottom:8px;">
              &#127881; Gaps closed since last session
            </div>
            <div>{items}</div>
          </div>
        </div>"""

    bar_width = score * 10

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#eef2f7;font-family:'Segoe UI',Arial,sans-serif;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;visibility:hidden;">
  Weekly CareerPilot update: score {score}/10, {len(gaps)} critical gaps, {len(strengths)} confirmed strengths.
</div>
<div style="max-width:620px;margin:26px auto;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 8px 30px rgba(15,23,42,0.10);">

  <div style="background:linear-gradient(135deg,#0ea5e9,#2563eb);padding:26px 30px;">
    <div style="font-size:22px;font-weight:800;color:#ffffff;letter-spacing:0.2px;">CareerPilot Weekly Brief</div>
    <div style="font-size:12px;color:rgba(255,255,255,0.9);margin-top:6px;line-height:1.4;">
      Internship readiness snapshot for {datetime.now().strftime('%A, %B %d, %Y')}
    </div>
  </div>

  <div style="padding:26px 30px;border-bottom:1px solid #e2e8f0;">
    <div style="font-size:10px;font-weight:700;letter-spacing:1.8px;color:#64748b;text-transform:uppercase;margin-bottom:15px;">
      Hirability Score  |  Last updated {last_updated}
    </div>
    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td width="90" valign="top" style="padding-right:18px;">
          <div style="width:76px;height:76px;border-radius:50%;border:3px solid {score_color};background:{score_color}15;text-align:center;line-height:76px;">
            <span style="font-size:29px;font-weight:800;color:{score_color};line-height:76px;">{score}</span>
          </div>
          <div style="text-align:center;font-size:11px;color:#64748b;margin-top:5px;">out of 10</div>
        </td>
        <td valign="top">
          <div style="margin-bottom:7px;">{trend}</div>
          <div style="font-size:13px;color:#475569;line-height:1.65;margin-bottom:12px;">
            {verdict[:300]}{'...' if len(verdict) > 300 else ''}
          </div>
          <div style="height:6px;background:#dbeafe;border-radius:6px;">
            <div style="height:100%;width:{bar_width}%;background:{score_color};border-radius:6px;"></div>
          </div>
        </td>
      </tr>
    </table>
  </div>

  {closed_section}

  <div style="padding:22px 30px;border-bottom:1px solid #e2e8f0;">
    <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;color:#2563eb;text-transform:uppercase;margin-bottom:10px;">
      This Week Priorities
    </div>
    <table width="100%" cellpadding="0" cellspacing="0" border="0">{priority_items}</table>
  </div>

  <div style="padding:24px 30px;border-bottom:1px solid #e2e8f0;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td width="48%" valign="top" style="padding-right:14px;">
          <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;color:#e11d48;text-transform:uppercase;margin-bottom:10px;">Critical Gaps</div>
          <table width="100%">{gap_rows}</table>
        </td>
        <td width="4%" style="border-right:1px solid #e2e8f0;">&nbsp;</td>
        <td width="48%" valign="top" style="padding-left:14px;">
          <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;color:#059669;text-transform:uppercase;margin-bottom:10px;">Strengths</div>
          <table width="100%">{strength_rows}</table>
        </td>
      </tr>
    </table>
  </div>

  <div style="background:#f8fafc;padding:20px 30px;border-bottom:1px solid #e2e8f0;">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="text-align:center;">
          <div style="font-size:28px;font-weight:800;color:#0ea5e9;">{len(history)}</div>
          <div style="font-size:11px;color:#94a3b8;margin-top:2px;">Sessions tracked</div>
        </td>
        <td style="text-align:center;border-left:1px solid #e2e8f0;">
          <div style="font-size:28px;font-weight:800;color:{'#059669' if len(gaps)==0 else '#e11d48' if len(gaps)>=3 else '#f59e0b'};">{len(gaps)}</div>
          <div style="font-size:11px;color:#94a3b8;margin-top:2px;">Gaps remaining</div>
        </td>
        <td style="text-align:center;border-left:1px solid #e2e8f0;">
          <div style="font-size:28px;font-weight:800;color:#059669;">{len(strengths)}</div>
          <div style="font-size:11px;color:#94a3b8;margin-top:2px;">Strengths confirmed</div>
        </td>
      </tr>
    </table>
  </div>

  <div style="padding:20px 30px;border-bottom:1px solid #e2e8f0;">
    <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;color:#94a3b8;text-transform:uppercase;margin-bottom:10px;">LinkedIn Activity</div>
    <div style="font-size:13px;color:{li_color};line-height:1.6;">
      <span style="margin-right:6px;">{li_icon}</span>{li_msg}
    </div>
  </div>

  <div style="padding:28px 30px;text-align:center;">
    <div style="font-size:13px;color:#64748b;margin-bottom:16px;">Keep momentum this week. Run the agent after shipping a meaningful improvement.</div>
    <a href="https://github.com/omerfarooq223/CareerPilot-Agent" style="display:inline-block;background:#2563eb;color:white;padding:13px 32px;border-radius:10px;font-size:14px;font-weight:700;text-decoration:none;box-shadow:0 6px 18px rgba(37,99,235,0.25);">
      Open CareerPilot &#8594;
    </a>
  </div>

  <div style="padding:14px 30px;background:#f8fafc;border-top:1px solid #e2e8f0;text-align:center;font-size:11px;color:#64748b;">
    CareerPilot  |  {datetime.now().strftime('%B %d, %Y')}  |  Weekly coaching reminder
  </div>

</div>
</body>
</html>"""


def send_reminder():
    print("Fetching CareerPilot data...")
    data = get_latest_data()
    score   = data.get("score", "N/A")
    subject = f"CareerPilot Weekly · Score {score}/10 · {datetime.now().strftime('%b %d')}"
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
    print(f"✓ Sent to {len(RECEIVERS)} recipients")


if __name__ == "__main__":
    send_reminder()