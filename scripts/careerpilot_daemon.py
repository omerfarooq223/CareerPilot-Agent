import time
import threading
import os
from datetime import datetime, timedelta, time as dt_time
from zoneinfo import ZoneInfo
from scripts.weekly_reminder import send_reminder

try:
    from scripts.send_gmail_api import send_gmail_api as send_via_gmail_api
except Exception:
    send_via_gmail_api = None

REMINDER_TIMEZONE = os.getenv("REMINDER_TIMEZONE", "Asia/Karachi")
REMINDER_WEEKDAY = int(os.getenv("REMINDER_WEEKDAY", "4"))  # Friday, Mon=0
REMINDER_HOUR = int(os.getenv("REMINDER_HOUR", "18"))
REMINDER_MINUTE = int(os.getenv("REMINDER_MINUTE", "0"))


def _reminder_timezone() -> ZoneInfo:
    """Return the configured timezone for weekly reminders."""
    return ZoneInfo(REMINDER_TIMEZONE)


def _next_friday_18(now: datetime | None = None) -> datetime:
    """Return the next Friday 6PM reminder time in the configured timezone."""
    tz = _reminder_timezone()
    now = (now or datetime.now(tz)).astimezone(tz)
    days_ahead = (REMINDER_WEEKDAY - now.weekday()) % 7
    candidate_date = (now.date() + timedelta(days=days_ahead))
    target = datetime.combine(
        candidate_date,
        dt_time(REMINDER_HOUR, REMINDER_MINUTE),
        tzinfo=tz,
    )
    if target <= now:
        target = target + timedelta(days=7)
    return target


def send_weekly_email() -> None:
    """Send the weekly reminder using the strongest configured email method."""
    print("[CareerPilot Daemon] Sending weekly reminder...", flush=True)
    if send_via_gmail_api:
        send_via_gmail_api()
    else:
        send_reminder()


def daemon_loop():
    while True:
        next_run = _next_friday_18()
        wait_seconds = (next_run - datetime.now(_reminder_timezone())).total_seconds()
        print(f"[CareerPilot Daemon] Next run at {next_run.isoformat()} (in {int(wait_seconds)}s)", flush=True)
        # Sleep until the scheduled time
        if wait_seconds > 0:
            time.sleep(wait_seconds)

        try:
            send_weekly_email()
        except Exception as e:
            print(f"[CareerPilot Daemon] Error: {e}", flush=True)


def start_daemon():
    t = threading.Thread(target=daemon_loop, daemon=True)
    t.start()
    print("[CareerPilot Daemon] Started. Press Ctrl+C to stop.")
    t.join()


if __name__ == "__main__":
    start_daemon()
