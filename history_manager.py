import json
from datetime import datetime
from pathlib import Path
from config.settings import LOGS_DIR

HISTORY_FILE = LOGS_DIR / "upload_history.json"

def get_history():
    """Returns list of all logged videos."""
    if not HISTORY_FILE.exists():
        # Initialize with the user's initial test uploads
        initial_history = [
            {
                "id": "vid_2",
                "timestamp": "2026-11-16 17:55:00",
                "episode": "The Flying Cat (1952)",
                "sequence": "Aerial lawnmower & dog chase",
                "title": "THE FLYING CAT! Tom and Jerry Chase #Shorts",
                "duration": "36.3s",
                "status": "uploaded",
                "youtube_url": "https://youtu.be/oLVR99IL7wc",
                "privacy": "public"
            },
            {
                "id": "vid_1",
                "timestamp": "2026-11-16 17:35:00",
                "episode": "Cat Napping (1951)",
                "sequence": "Lawnmower chase & dog tackle",
                "title": "LAWNMOWER CHASE! Tom & Jerry Fun #Shorts",
                "duration": "36.3s",
                "status": "uploaded",
                "youtube_url": "https://youtu.be/jhf7UaMy9tI",
                "privacy": "public"
            }
        ]
        save_history(initial_history)
        return initial_history

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_history(history_list):
    """Saves history list to JSON."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_list, f, indent=2, ensure_ascii=False)

def add_history_entry(episode, sequence, title, duration, youtube_url=None, privacy="public", status="uploaded"):
    """Adds a new entry to upload history."""
    history = get_history()
    entry = {
        "id": f"vid_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "episode": episode,
        "sequence": sequence,
        "title": title,
        "duration": f"{duration}s" if isinstance(duration, (int, float)) else str(duration),
        "status": status,
        "youtube_url": youtube_url,
        "privacy": privacy
    }
    history.insert(0, entry) # Most recent first
    save_history(history)
    return entry
