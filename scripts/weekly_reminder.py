import os
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

SENDER    = os.getenv("REMINDER_EMAIL_SENDER")
PASSWORD  = os.getenv("REMINDER_EMAIL_PASSWORD")
RECEIVERS = os.getenv("REMINDER_EMAIL_RECEIVERS", "").split(",")


def get_latest_data() -> dict:
    """Load data from committed JSON snapshot."""
    paths = [
        Path("memory/latest_snapshot.json"),
        Path("../memory/latest_snapshot.json"),
    ]
    for path in paths:
        if path.exists():
            print(f"Loading snapshot from {path}")
            return json.loads(path.read_text())
    print("No snapshot found")
    return {}


def build_html(data: dict) -> str:
    if not data:
        return """
        <div style="padding:32px;text-align:center;">
          <p style="color:#64748b;font-size:14px;">No data available yet — run CareerPilot first.</p>
          <a href="https://github.com/omerfarooq223/CareerPilot-Agent"
             style="display:inline-block;margin-top:16px;background:#0ea5e9;color:white;
                    padding:10px 24px;border-radius:8px;text-decoration:none;font-weight:600;">
            Open CareerPilot →
          </a>
        </div>"""

    score        = data.get("score", 0)
    gaps         = data.get("critical_gaps", [])
    strengths    = data.get("strengths", [])
    verdict      = data.get("verdict", "")
    last_updated = data.get("last_updated", "Unknown")
    history      = data.get("score_history", [])
    days_post    = data.get("days_since_post")
    last_repo    = data.get("last_post_repo")
    score_delta  = data.get("score_delta", 0)
    closed_gaps  = data.get("closed_gaps", [])

    # Score color
    score_color = "#059669" if score >= 8 else "#0ea5e9" if score >= 6 else "#e11d48"

    # Trend
    if score_delta > 0:
        trend_html = f'<span style="color:#059669;font-weight:700;font-size:14px;">↑ +{score_delta} from last session</span>'
    elif score_delta < 0:
        trend_html = f'<span style="color:#e11d48;font-weight:700;font-size:14px;">↓ {score_delta} from last session</span>'
    else:
        trend_html = f'<span style="color:#94a3b8;font-weight:600;font-size:14px;">→ No change from last session</span>'

    # Sessions this week
    sessions_count = len(history) if history else 0

    # LinkedIn nudge
    if days_post is None:
        linkedin_color = "#e11d48"
        linkedin_icon  = "⚠️"
        linkedin_msg   = "You haven't posted on LinkedIn yet — your profile is invisible to recruiters."
    elif days_post == 0:
        linkedin_color = "#059669"
        linkedin_icon  = "✅"
        linkedin_msg   = f"You posted today about <strong>{last_repo}</strong>. Excellent consistency!"
    elif days_post == 1:
        linkedin_color = "#059669"
        linkedin_icon  = "✅"
        linkedin_msg   = f"You posted yesterday about <strong>{last_repo}</strong>. Keep it up."
    elif days_post >= 7:
        linkedin_color = "#e11d48"
        linkedin_icon  = "⚠️"
        linkedin_msg   = f"It's been <strong>{days_post} days</strong> since your last post about {last_repo}. Time to post again."
    else:
        linkedin_color = "#0ea5e9"
        linkedin_icon  = "📌"
        linkedin_msg   = f"You posted <strong>{days_post} days ago</strong> about {last_repo}. Keep the momentum going."

    # Gaps HTML
    gaps_html = "".join(
        f'<div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid #f1f5f9;">'
        f'<div style="width:6px;height:6px;border-radius:50%;background:#e11d48;flex-shrink:0;"></div>'
        f'<span style="font-size:13px;color:#334155;">{g}</span></div>'
        for g in gaps
    )

    # Strengths HTML
    strengths_html = "".join(
        f'<div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid #f1f5f9;">'
        f'<div style="width:6px;height:6px;border-radius:50%;background:#059669;flex-shrink:0;"></div>'
        f'<span style="font-size:13px;color:#334155;">{s}</span></div>'
        for s in strengths
    )

    # Closed gaps banner
    closed_banner = ""
    if closed_gaps:
        closed_list = ", ".join(closed_gaps)
        closed_banner = f"""
        <div style="background:#ecfdf5;border:1px solid #a7f3d0;border-radius:8px;
                    padding:12px 16px;margin-bottom:16px;">
          <div style="font-size:12px;font-weight:700;color:#059669;margin-bottom:4px;">
            🎉 Gaps closed since last session
          </div>
          <div style="font-size:13px;color:#065f46;">{closed_list}</div>
        </div>"""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Segoe UI',Arial,sans-serif;">
<div style="max-width:640px;margin:32px auto;background:#ffffff;border-radius:16px;
            overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#0ea5e9 0%,#0284c7 100%);padding:28px 32px;">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;">
      <span style="font-size:24px;">🤖</span>
      <span style="font-size:22px;font-weight:800;color:white;letter-spacing:-0.5px;">CareerPilot</span>
    </div>
    <div style="font-size:13px;color:rgba(255,255,255,0.8);">
      Your weekly career intelligence report · {datetime.now().strftime('%A, %B %d %Y')}
    </div>
  </div>

  <!-- Score section -->
  <div style="padding:28px 32px;border-bottom:1px solid #e2e8f0;">
    <div style="font-size:10px;font-weight:700;letter-spacing:2px;color:#94a3b8;
                text-transform:uppercase;margin-bottom:16px;">
      Hirability Score — Last updated {last_updated}
    </div>

    <div style="display:flex;align-items:flex-start;gap:24px;">
      <!-- Score circle -->
      <div style="flex-shrink:0;width:90px;height:90px;border-radius:50%;
                  background:{score_color}15;border:3px solid {score_color};
                  display:flex;flex-direction:column;align-items:center;justify-content:center;">
        <div style="font-size:36px;font-weight:800;color:{score_color};line-height:1;">{score}</div>
        <div style="font-size:11px;color:{score_color};font-weight:500;">/10</div>
      </div>

      <!-- Score details -->
      <div style="flex:1;">
        <div style="margin-bottom:8px;">{trend_html}</div>
        <div style="font-size:13px;color:#64748b;line-height:1.65;margin-bottom:12px;">
          {verdict[:280]}{'...' if len(verdict) > 280 else ''}
        </div>
        <!-- Progress bar -->
        <div style="height:6px;background:#e0f2fe;border-radius:3px;overflow:hidden;">
          <div style="height:100%;width:{score*10}%;background:{score_color};border-radius:3px;"></div>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:4px;">
          <span style="font-size:10px;color:#94a3b8;">0</span>
          <span style="font-size:10px;color:#94a3b8;">10</span>
        </div>
      </div>
    </div>
  </div>

  {closed_banner and f'<div style="padding:0 32px 4px;">{closed_banner}</div>' or ''}

  <!-- Gaps & Strengths side by side -->
  <div style="padding:24px 32px;border-bottom:1px solid #e2e8f0;
              display:flex;gap:24px;">
    <div style="flex:1;">
      <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;color:#e11d48;
                  text-transform:uppercase;margin-bottom:10px;">Critical Gaps</div>
      {gaps_html if gaps_html else '<div style="font-size:13px;color:#94a3b8;">None detected ✓</div>'}
    </div>
    <div style="width:1px;background:#e2e8f0;flex-shrink:0;"></div>
    <div style="flex:1;">
      <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;color:#059669;
                  text-transform:uppercase;margin-bottom:10px;">Strengths</div>
      {strengths_html if strengths_html else '<div style="font-size:13px;color:#94a3b8;">Run agent first</div>'}
    </div>
  </div>

  <!-- Stats row -->
  <div style="padding:20px 32px;border-bottom:1px solid #e2e8f0;
              display:flex;gap:16px;background:#f8fafc;">
    <div style="flex:1;text-align:center;">
      <div style="font-size:24px;font-weight:800;color:#0ea5e9;">{sessions_count}</div>
      <div style="font-size:11px;color:#94a3b8;margin-top:2px;">Sessions tracked</div>
    </div>
    <div style="width:1px;background:#e2e8f0;flex-shrink:0;"></div>
    <div style="flex:1;text-align:center;">
      <div style="font-size:24px;font-weight:800;color:{'#059669' if len(gaps)==0 else '#e11d48' if len(gaps)>=3 else '#f59e0b'};">{len(gaps)}</div>
      <div style="font-size:11px;color:#94a3b8;margin-top:2px;">Gaps remaining</div>
    </div>
    <div style="width:1px;background:#e2e8f0;flex-shrink:0;"></div>
    <div style="flex:1;text-align:center;">
      <div style="font-size:24px;font-weight:800;color:#0ea5e9;">{len(strengths)}</div>
      <div style="font-size:11px;color:#94a3b8;margin-top:2px;">Strengths confirmed</div>
    </div>
  </div>

  <!-- LinkedIn -->
  <div style="padding:20px 32px;border-bottom:1px solid #e2e8f0;">
    <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;color:#94a3b8;
                text-transform:uppercase;margin-bottom:10px;">LinkedIn Activity</div>
    <div style="display:flex;align-items:flex-start;gap:10px;">
      <span style="font-size:18px;flex-shrink:0;">{linkedin_icon}</span>
      <div style="font-size:13px;color:{linkedin_color};line-height:1.6;">{linkedin_msg}</div>
    </div>
  </div>

  <!-- CTA -->
  <div style="padding:28px 32px;text-align:center;">
    <div style="font-size:13px;color:#94a3b8;margin-bottom:16px;">
      Run the agent to update your report and stay on track
    </div>
    <a href="https://web-production-e1faa.up.railway.app"
       style="display:inline-block;background:#0ea5e9;color:white;padding:13px 32px;
              border-radius:10px;font-size:14px;font-weight:700;text-decoration:none;
              letter-spacing:0.3px;box-shadow:0 4px 12px rgba(14,165,233,0.3);">
      Open CareerPilot →
    </a>
    <div style="margin-top:12px;">
      <a href="https://github.com/omerfarooq223/CareerPilot-Agent"
         style="font-size:12px;color:#94a3b8;text-decoration:none;">
        View on GitHub
      </a>
    </div>
  </div>

  <!-- Footer -->
  <div style="padding:16px 32px;background:#f8fafc;border-top:1px solid #e2e8f0;
              text-align:center;font-size:11px;color:#94a3b8;">
    CareerPilot · Automated weekly reminder · {datetime.now().strftime('%B %d, %Y')}
    · <a href="https://github.com/omerfarooq223/CareerPilot-Agent"
         style="color:#94a3b8;">Unsubscribe</a>
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

    print(f"✓ Reminder sent to {len(RECEIVERS)} recipients")


if __name__ == "__main__":
    send_reminder()