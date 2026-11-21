import os
import sys
import time
import logging
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config.settings import LOGS_DIR
from main import upload_next_from_queue
from queue_manager import QueueManager

# Configure Scheduler Logging
log_file = LOGS_DIR / "scheduler.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(str(log_file), encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

# 8 slots in 24 hours (Every 3 hours)
DEFAULT_HOURS = [0, 3, 6, 9, 12, 15, 18, 21]

def scheduled_upload_job(slot_name: str, privacy: str = "public"):
    """
    Executes a single automated scheduled upload from the persistent queue.
    """
    logging.info(f"⏰ [SCHEDULER] Triggered 3-Hour Upload Slot: {slot_name} (Privacy: {privacy})...")
    q = QueueManager()
    stats = q.get_stats()
    logging.info(f"[*] Queue Status: {stats['pending']} pending clips available.")

    if stats["pending"] == 0:
        logging.warning("⚠️ [QUEUE EMPTY] No clips in queue. Please add YouTube videos via Web Dashboard or main.py!")
        return

    try:
        res = upload_next_from_queue(privacy=privacy)
        logging.info(f"✅ [SUCCESS] Uploaded {slot_name} video: {res}")
    except Exception as e:
        logging.error(f"❌ [ERROR] Failed upload in {slot_name}: {e}", exc_info=True)

def start_3_hour_scheduler(privacy: str = "public", interval_hours: int = 3):
    """
    Starts 24/7 background scheduler:
    Uploads 8 clips per 24 hours (Every 3 Hours: 00:00, 03:00, 06:00, 09:00, 12:00, 15:00, 18:00, 21:00).
    """
    scheduler = BlockingScheduler()

    print("\n" + "="*70)
    print("   24/7 YOUTUBE SHORTS AUTO-UPLOAD SCHEDULER")
    print(f"   Target Frequency : Every {interval_hours} Hours (8 Videos Per 24-Hour Day)")
    print("   Scheduled Slots  : 00:00, 03:00, 06:00, 09:00, 12:00, 15:00, 18:00, 21:00")
    print(f"   Privacy Setting  : {privacy.upper()}")
    print("="*70 + "\n")

    # Add 8 scheduled cron triggers
    for hour in DEFAULT_HOURS:
        time_str = f"{hour:02d}:00"
        slot_name = f"Slot @ {time_str}"
        scheduler.add_job(
            scheduled_upload_job,
            CronTrigger(hour=hour, minute=0),
            args=[slot_name, privacy],
            id=f"job_slot_{hour}",
            name=slot_name,
            replace_existing=True
        )
        print(f"  [+] Registered Daily Slot: {time_str} UTC/Local")

    logging.info("[*] Scheduler active and waiting for next slot...")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logging.info("[*] Scheduler stopped gracefully.")

if __name__ == "__main__":
    privacy_arg = "public"
    if len(sys.argv) > 1 and sys.argv[1] in ("public", "unlisted", "private"):
        privacy_arg = sys.argv[1]
    start_3_hour_scheduler(privacy=privacy_arg)
