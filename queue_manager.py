import os
import json
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from config.settings import BASE_DIR

logger = logging.getLogger(__name__)

QUEUE_FILE = BASE_DIR / "clip_queue.json"

class QueueManager:
    """
    Manages the persistent queue of video clips to be uploaded.
    Supports status transitions: pending -> ready -> uploading -> uploaded / failed.
    """
    def __init__(self, queue_file: Path = QUEUE_FILE):
        self.queue_file = queue_file

    def _read_data(self) -> dict:
        if not self.queue_file.exists():
            return {"clips": [], "created_at": datetime.now().isoformat()}
        try:
            with open(self.queue_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading queue file: {e}")
            return {"clips": [], "created_at": datetime.now().isoformat()}

    def _write_data(self, data: dict):
        try:
            with open(self.queue_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error writing queue file: {e}")

    def add_clips(self, source_url: str, source_title: str, clips: List[Dict]) -> List[str]:
        """Adds a list of analyzed clips into the upload queue."""
        data = self._read_data()
        existing = data.get("clips", [])
        added_ids = []

        now = datetime.now().isoformat()
        for c in clips:
            clip_id = str(uuid.uuid4())[:8]
            entry = {
                "id": clip_id,
                "source_url": source_url,
                "source_title": source_title,
                "start_sec": c.get("start_sec", 0),
                "duration": c.get("duration", 40),
                "hook": c.get("hook", ["VIRAL MOMENT", "WAIT FOR THE END!"]),
                "title": c.get("title", f"Epic Clip from {source_title}"),
                "description": c.get("description", "Subscribe for more viral shorts!"),
                "tags": c.get("tags", ["shorts", "viral"]),
                "reason": c.get("reason", ""),
                "status": "pending",  # pending | ready | uploading | uploaded | failed
                "video_file": None,
                "created_at": now,
                "uploaded_at": None,
                "youtube_url": None,
                "error": None
            }
            existing.append(entry)
            added_ids.append(clip_id)

        data["clips"] = existing
        self._write_data(data)
        return added_ids

    def get_all_clips(self) -> List[Dict]:
        """Returns all clips in queue."""
        data = self._read_data()
        return data.get("clips", [])

    def get_pending_clips(self) -> List[Dict]:
        """Returns all clips awaiting upload."""
        clips = self.get_all_clips()
        return [c for c in clips if c.get("status") in ("pending", "ready")]

    def get_next_clip(self) -> Optional[Dict]:
        """Pops the next pending clip to be uploaded."""
        pending = self.get_pending_clips()
        return pending[0] if pending else None

    def update_clip(self, clip_id: str, updates: dict):
        """Update fields of a specific clip."""
        data = self._read_data()
        for c in data.get("clips", []):
            if c.get("id") == clip_id:
                c.update(updates)
                break
        self._write_data(data)

    def mark_uploaded(self, clip_id: str, youtube_url: str):
        """Mark clip as successfully uploaded."""
        self.update_clip(clip_id, {
            "status": "uploaded",
            "uploaded_at": datetime.now().isoformat(),
            "youtube_url": youtube_url,
            "error": None
        })

    def mark_failed(self, clip_id: str, error_msg: str):
        """Mark clip as failed."""
        self.update_clip(clip_id, {
            "status": "failed",
            "error": str(error_msg)
        })

    def remove_clip(self, clip_id: str):
        """Delete clip from queue."""
        data = self._read_data()
        data["clips"] = [c for c in data.get("clips", []) if c.get("id") != clip_id]
        self._write_data(data)

    def clear_queue(self):
        """Clear all clips."""
        self._write_data({"clips": [], "created_at": datetime.now().isoformat()})

    def get_stats(self) -> dict:
        """Returns summary statistics for UI dashboard."""
        clips = self.get_all_clips()
        return {
            "total": len(clips),
            "pending": sum(1 for c in clips if c.get("status") in ("pending", "ready")),
            "uploaded": sum(1 for c in clips if c.get("status") == "uploaded"),
            "failed": sum(1 for c in clips if c.get("status") == "failed"),
        }
