from dotenv import load_dotenv
load_dotenv("config/.env")

import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
# Try relative import if direct import fails
try:
    from scripts.weekly_reminder import get_latest_data, build_html
except ModuleNotFoundError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from scripts.weekly_reminder import get_latest_data, build_html

# If modifying these SCOPES, delete token.json and re-authenticate
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# Load recipients from .env or set manually
RECEIVERS = os.getenv("REMINDER_EMAIL_RECEIVERS", "").split(",")
SENDER = os.getenv("REMINDER_EMAIL_SENDER")

def send_gmail_api():
    creds = None
    token_path = Path("credentials/token.json")
    creds_path = Path("credentials/credentials.json")
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    else:
        # If there are no (valid) credentials available, let the user log in.
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_path, "w") as token:
            token.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)
    data = get_latest_data()
    score = data.get("score", "N/A")
    subject = f"CareerPilot Weekly · Score {score}/10"
    html = build_html(data)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SENDER
    receivers_clean = [r.strip() for r in RECEIVERS if r.strip()]
    msg["To"] = ", ".join(receivers_clean)
    msg.attach(MIMEText(html, "html"))

    import base64
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    message = {"raw": raw, "to": ", ".join(receivers_clean)}

    sent = service.users().messages().send(userId="me", body=message).execute()
    print(f"✓ Sent to {receivers_clean}: Message ID {sent['id']}")

if __name__ == "__main__":
    send_gmail_api()
