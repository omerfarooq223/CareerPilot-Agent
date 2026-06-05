"""Weekly email scheduler for long-running CareerPilot processes."""

import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from scripts.careerpilot_daemon import (
    REMINDER_HOUR,
    REMINDER_MINUTE,
    REMINDER_TIMEZONE,
    REMINDER_WEEKDAY,
    send_weekly_email,
)

_scheduler: BackgroundScheduler | None = None


def start_weekly_email_scheduler() -> BackgroundScheduler | None:
    """Start the Friday 6PM reminder scheduler once per process."""
    global _scheduler
    if os.getenv("CAREERPILOT_ENABLE_EMAIL_SCHEDULER", "true").lower() in {"0", "false", "no"}:
        print("[CareerPilot Scheduler] Email scheduler disabled.", flush=True)
        return None

    if _scheduler and _scheduler.running:
        return _scheduler

    trigger = CronTrigger(
        day_of_week=REMINDER_WEEKDAY,
        hour=REMINDER_HOUR,
        minute=REMINDER_MINUTE,
        timezone=REMINDER_TIMEZONE,
    )
    scheduler = BackgroundScheduler(timezone=REMINDER_TIMEZONE)
    scheduler.add_job(
        send_weekly_email,
        trigger=trigger,
        id="careerpilot_weekly_email",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    _scheduler = scheduler
    print(
        "[CareerPilot Scheduler] Weekly email scheduled for "
        f"weekday={REMINDER_WEEKDAY} {REMINDER_HOUR:02d}:{REMINDER_MINUTE:02d} {REMINDER_TIMEZONE}.",
        flush=True,
    )
    return scheduler


def stop_weekly_email_scheduler() -> None:
    """Stop the scheduler if it is running."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None
