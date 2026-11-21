import os
import sys
import threading
import logging
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config.settings import LOGS_DIR, CONFIG_DIR, GEMINI_API_KEY, AUTO_DELETE_AFTER_UPLOAD
from history_manager import get_history, add_history_entry
from queue_manager import QueueManager
from main import process_youtube_video, upload_next_from_queue, render_and_upload_clip
from youtube_uploader import YouTubeUploader

app = Flask(__name__, template_folder="templates")

# Configure Web & Activity Logs
LOG_FILE = LOGS_DIR / "web_activity.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

recent_logs = []
MAX_BUFFER_LINES = 200

def log_activity(msg: str):
    """Logs message both to file and in-memory buffer for UI."""
    ts = datetime.now().strftime("%H:%M:%S")
    formatted = f"[{ts}] {msg}"
    print(formatted)
    recent_logs.append(formatted)
    if len(recent_logs) > MAX_BUFFER_LINES:
        recent_logs.pop(0)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass

# Global Background Task State
current_job = {
    "is_running": False,
    "task_name": "Idle",
    "progress": 0,
    "last_result": None,
    "error": None
}
job_lock = threading.Lock()

# Global 3-Hour Scheduler Instance (8 Uploads Daily)
scheduler = BackgroundScheduler()
scheduler_active = True
schedule_hours = [0, 3, 6, 9, 12, 15, 18, 21]
schedule_privacy = "public"

def run_scheduled_job(slot_name: str):
    """Executes an automated scheduled upload every 3 hours."""
    log_activity(f"⏰ [SCHEDULER] Triggered 3-Hour Auto-Upload: {slot_name}...")
    q = QueueManager()
    if q.get_stats()["pending"] == 0:
        log_activity("⚠️ [SCHEDULER] Queue is empty. Please add more YouTube videos to keep auto-uploading!")
        return

    def task():
        with job_lock:
            current_job["is_running"] = True
            current_job["task_name"] = f"Auto-Upload {slot_name}"
            current_job["progress"] = 20
        try:
            log_activity(">>> [SCHEDULER] Rendering & uploading next queued clip...")
            res = upload_next_from_queue(privacy=schedule_privacy)
            with job_lock:
                current_job["last_result"] = res
                current_job["progress"] = 100
            log_activity(f"✅ [SCHEDULER] Successfully uploaded: {res.get('youtube_url', 'Completed')}")
        except Exception as e:
            log_activity(f"❌ [SCHEDULER ERROR] Failed: {e}")
            with job_lock:
                current_job["error"] = str(e)
        finally:
            with job_lock:
                current_job["is_running"] = False

    t = threading.Thread(target=task, daemon=True)
    t.start()

def init_scheduler():
    global scheduler
    for hour in schedule_hours:
        time_str = f"{hour:02d}:00"
        slot_name = f"Slot @ {time_str}"
        scheduler.add_job(
            run_scheduled_job,
            CronTrigger(hour=hour, minute=0),
            args=[slot_name],
            id=f"job_slot_{hour}",
            name=slot_name,
            replace_existing=True
        )
    scheduler.start()
    log_activity("🚀 [SCHEDULER INITIALIZED] 8 Upload Slots configured (Every 3 Hours).")

# Initialize scheduler on startup
init_scheduler()

# --- WEB ROUTES ---

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def get_status():
    uploader = YouTubeUploader()
    q = QueueManager()
    stats = q.get_stats()
    
    # Calculate next scheduled run
    jobs = scheduler.get_jobs()
    next_run = None
    if scheduler_active and jobs:
        valid_runs = [j.next_run_time for j in jobs if j.next_run_time]
        if valid_runs:
            next_run = min(valid_runs).strftime("%H:%M:%S")

    return jsonify({
        "job": current_job,
        "scheduler": {
            "active": scheduler_active,
            "next_run": next_run or "Waiting",
            "slots": [f"{h:02d}:00" for h in schedule_hours],
            "frequency": "Every 3 Hours (8/Day)",
            "privacy": schedule_privacy
        },
        "stats": stats,
        "youtube_configured": uploader.is_configured(),
        "gemini_configured": bool(GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here")
    })

@app.route("/api/analyze", methods=["POST"])
def analyze_video():
    """Trigger background analysis and clipping of a YouTube URL."""
    with job_lock:
        if current_job["is_running"]:
            return jsonify({"status": "busy", "message": "Another task is currently running."}), 400

    data = request.json or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"status": "error", "message": "YouTube URL is required!"}), 400

    raw_clips = data.get("max_clips", "auto")
    max_clips = int(raw_clips) if str(raw_clips).isdigit() else "auto"
    upload_first = bool(data.get("upload_first", False))
    privacy = data.get("privacy", "public")

    def background_worker():
        with job_lock:
            current_job["is_running"] = True
            current_job["task_name"] = "Analyzing & Clipping Video"
            current_job["progress"] = 15
            current_job["error"] = None

        log_activity(f"🚀 [ANALYZE] Starting analysis for: {url} (Target: {max_clips} Clips)...")
        try:
            with job_lock:
                current_job["progress"] = 40
            result = process_youtube_video(
                youtube_url=url,
                max_clips=max_clips,
                upload_first=upload_first,
                privacy=privacy
            )
            with job_lock:
                current_job["last_result"] = {
                    "source_title": result["source_title"],
                    "clips_count": len(result["clips"]),
                    "uploaded": result.get("uploaded", False)
                }
                current_job["progress"] = 100
            log_activity(f"✅ [ANALYZE DONE] Added {len(result['clips'])} viral clips to the upload queue!")
        except Exception as e:
            log_activity(f"❌ [ANALYZE ERROR] {e}")
            with job_lock:
                current_job["error"] = str(e)
        finally:
            with job_lock:
                current_job["is_running"] = False

    t = threading.Thread(target=background_worker, daemon=True)
    t.start()

    return jsonify({"status": "started", "message": "Video analysis started in background."})

@app.route("/api/upload-next", methods=["POST"])
def trigger_upload_next():
    """Upload next pending clip right now."""
    with job_lock:
        if current_job["is_running"]:
            return jsonify({"status": "busy", "message": "Another task is in progress."}), 400

    data = request.json or {}
    privacy = data.get("privacy", "public")

    def worker():
        with job_lock:
            current_job["is_running"] = True
            current_job["task_name"] = "Instant Clip Upload"
            current_job["progress"] = 25
            current_job["error"] = None

        log_activity("⚡ [UPLOAD NOW] Rendering & uploading next pending clip...")
        try:
            res = upload_next_from_queue(privacy=privacy)
            with job_lock:
                current_job["last_result"] = res
                current_job["progress"] = 100
            log_activity(f"✅ [UPLOAD SUCCESS] Result: {res.get('youtube_url', 'Completed')}")
        except Exception as e:
            log_activity(f"❌ [UPLOAD ERROR] {e}")
            with job_lock:
                current_job["error"] = str(e)
        finally:
            with job_lock:
                current_job["is_running"] = False

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return jsonify({"status": "started", "message": "Clip upload initiated."})

@app.route("/api/upload-clip/<clip_id>", methods=["POST"])
def upload_specific_clip(clip_id):
    """Upload a specific queued clip by ID."""
    with job_lock:
        if current_job["is_running"]:
            return jsonify({"status": "busy", "message": "Another task is in progress."}), 400

    data = request.json or {}
    privacy = data.get("privacy", "public")

    def worker():
        with job_lock:
            current_job["is_running"] = True
            current_job["task_name"] = f"Upload Clip {clip_id}"
            current_job["progress"] = 25
            current_job["error"] = None

        log_activity(f"⚡ [UPLOAD] Rendering & uploading specific clip: {clip_id}...")
        try:
            res = render_and_upload_clip(clip_id, privacy=privacy)
            with job_lock:
                current_job["last_result"] = res
                current_job["progress"] = 100
            log_activity(f"✅ [UPLOAD SUCCESS] Clip {clip_id} uploaded: {res.get('youtube_url', '')}")
        except Exception as e:
            log_activity(f"❌ [UPLOAD ERROR] {e}")
            with job_lock:
                current_job["error"] = str(e)
        finally:
            with job_lock:
                current_job["is_running"] = False

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return jsonify({"status": "started", "message": f"Upload for clip {clip_id} started."})

@app.route("/api/queue")
def get_queue():
    q = QueueManager()
    return jsonify({
        "clips": q.get_all_clips(),
        "stats": q.get_stats()
    })

@app.route("/api/clip/<clip_id>", methods=["DELETE"])
def delete_clip(clip_id):
    q = QueueManager()
    q.remove_clip(clip_id)
    log_activity(f"🗑️ [QUEUE] Removed clip {clip_id} from queue.")
    return jsonify({"status": "success", "message": f"Clip {clip_id} removed."})

@app.route("/api/clear-queue", methods=["POST"])
def clear_all_queue():
    q = QueueManager()
    q.clear_queue()
    log_activity("🧹 [QUEUE] Cleared all clips from queue.")
    return jsonify({"status": "success", "message": "Queue cleared."})

@app.route("/api/scheduler/toggle", methods=["POST"])
def toggle_scheduler():
    global scheduler_active
    scheduler_active = not scheduler_active
    if scheduler_active:
        scheduler.resume()
        log_activity("▶️ [SCHEDULER] 3-Hour Auto-Uploader Resumed.")
    else:
        scheduler.pause()
        log_activity("⏸️ [SCHEDULER] 3-Hour Auto-Uploader Paused.")
    return jsonify({"status": "success", "active": scheduler_active})

@app.route("/api/history")
def history_endpoint():
    return jsonify(get_history())

@app.route("/api/logs")
def logs_endpoint():
    return jsonify({"logs": recent_logs})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"\n🚀 AI YouTube Shorts Auto-Uploader Web Server running on http://127.0.0.1:{port}\n")
    app.run(host="127.0.0.1", port=port, debug=False)
