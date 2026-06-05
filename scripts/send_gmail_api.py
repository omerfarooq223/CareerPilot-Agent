import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / "config" / ".env", override=True)

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

def _clean_receivers() -> list[str]:
    """Return configured reminder recipients without blanks."""
    return [r.strip() for r in RECEIVERS if r.strip()]


def _validate_email_settings() -> list[str]:
    """Return email configuration problems that would prevent sending."""
    problems = []
    if not SENDER:
        problems.append("REMINDER_EMAIL_SENDER is not set")
    if not _clean_receivers():
        problems.append("REMINDER_EMAIL_RECEIVERS is not set")
    if not (BASE_DIR / "credentials" / "token.json").exists():
        problems.append("credentials/token.json is missing")
    if not (BASE_DIR / "credentials" / "credentials.json").exists():
        problems.append("credentials/credentials.json is missing")
    return problems


def send_gmail_api() -> dict:
    """Send the weekly CareerPilot reminder through the Gmail API."""
    problems = _validate_email_settings()
    if problems:
        raise RuntimeError("; ".join(problems))

    creds = None
    token_path = BASE_DIR / "credentials" / "token.json"
    creds_path = BASE_DIR / "credentials" / "credentials.json"
    # Load token if present
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    # If there are no (valid) credentials available, try to refresh or prompt login.
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not creds or not creds.valid:
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
    receivers_clean = _clean_receivers()
    msg["To"] = ", ".join(receivers_clean)
    msg.attach(MIMEText(html, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    message = {"raw": raw}

    sent = service.users().messages().send(userId="me", body=message).execute()
    print(f"✓ Sent to {receivers_clean}: Message ID {sent['id']}")
    return sent

if __name__ == "__main__":
    send_gmail_api()
