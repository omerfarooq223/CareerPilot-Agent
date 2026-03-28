import time
import threading
from scripts.weekly_reminder import send_reminder

# Run every Friday at 6PM PKT (UTC+5)
# For demo: run every 60 seconds (change to 604800 for weekly)
SEND_INTERVAL_SECONDS = 604800  # 1 week = 604800 seconds


def daemon_loop():
    while True:
        print("[CareerPilot Daemon] Sending weekly reminder...")
        try:
            send_reminder()
        except Exception as e:
            print(f"[CareerPilot Daemon] Error: {e}")
        print(f"[CareerPilot Daemon] Sleeping for {SEND_INTERVAL_SECONDS} seconds...")
        time.sleep(SEND_INTERVAL_SECONDS)


def start_daemon():
    t = threading.Thread(target=daemon_loop, daemon=True)
    t.start()
    print("[CareerPilot Daemon] Started. Press Ctrl+C to stop.")
    t.join()


if __name__ == "__main__":
    start_daemon()
