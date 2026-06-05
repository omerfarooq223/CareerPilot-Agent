from datetime import datetime
from zoneinfo import ZoneInfo

from scripts.careerpilot_daemon import _next_friday_18


def test_next_run_is_this_friday_6pm_pkt_before_target():
    now = datetime(2026, 6, 5, 17, 30, tzinfo=ZoneInfo("Asia/Karachi"))

    next_run = _next_friday_18(now)

    assert next_run == datetime(2026, 6, 5, 18, 0, tzinfo=ZoneInfo("Asia/Karachi"))


def test_next_run_rolls_to_next_friday_after_target():
    now = datetime(2026, 6, 5, 18, 1, tzinfo=ZoneInfo("Asia/Karachi"))

    next_run = _next_friday_18(now)

    assert next_run == datetime(2026, 6, 12, 18, 0, tzinfo=ZoneInfo("Asia/Karachi"))


def test_next_run_uses_pkt_even_when_process_time_is_utc():
    now = datetime(2026, 6, 5, 12, 30, tzinfo=ZoneInfo("UTC"))

    next_run = _next_friday_18(now)

    assert next_run == datetime(2026, 6, 5, 18, 0, tzinfo=ZoneInfo("Asia/Karachi"))
