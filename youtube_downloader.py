import os
import re
import json
import logging
import subprocess
from pathlib import Path
import yt_dlp
from config.settings import FFMPEG_PATH, GENERATED_DIR

logger = logging.getLogger(__name__)

class YouTubeDownloader:
    """
    Handles downloading YouTube video information, transcripts/subtitles,
    and fast segment extraction via stream or local download.
    """
    def __init__(self, ffmpeg_path: str = FFMPEG_PATH):
        self.ffmpeg_path = ffmpeg_path
        self.ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }

    def get_video_info(self, youtube_url: str) -> dict:
        """
        Extract video metadata: title, duration, description, chapters, available subtitles.
        Does NOT download the actual video file.
        """
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            
            # Format chapters if available
            chapters = []
            if info.get("chapters"):
                for ch in info["chapters"]:
                    chapters.append({
                        "title": ch.get("title", ""),
                        "start_time": int(ch.get("start_time", 0)),
                        "end_time": int(ch.get("end_time", 0))
                    })

            return {
                "id": info.get("id"),
                "title": info.get("title"),
                "duration": int(info.get("duration", 0)),
                "description": info.get("description", ""),
                "channel": info.get("uploader", ""),
                "chapters": chapters,
                "thumbnail": info.get("thumbnail"),
                "webpage_url": info.get("webpage_url", youtube_url),
            }

    def get_direct_stream_urls(self, youtube_url: str) -> dict:
        """
        Extract direct playable stream URL(s) for fast seeking without full file download.
        """
        opts = {
            "quiet": True,
            "no_warnings": True,
            "format": "best[ext=mp4]/best",
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            return {
                "video_url": info.get("url"),
                "duration": info.get("duration", 0),
                "title": info.get("title", "")
            }

    def extract_transcript(self, youtube_url: str) -> list:
        """
        Fetches transcript/subtitles (auto-generated or manual) with timestamps.
        Returns a list of dicts: [{'start': seconds, 'duration': seconds, 'text': '...'}]
        """
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en", "hi", "en-US", "en-orig"],
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                subtitles = info.get("subtitles") or info.get("automatic_captions")
                if not subtitles:
                    return []

                # Find best matching language
                target_lang = None
                for lang in ["en", "hi", "en-US", "en-orig"]:
                    if lang in subtitles:
                        target_lang = lang
                        break
                if not target_lang:
                    target_lang = next(iter(subtitles.keys()))

                formats = subtitles.get(target_lang, [])
                json3_format = next((f for f in formats if f.get("ext") == "json3"), None)
                if json3_format and json3_format.get("url"):
                    import requests
                    resp = requests.get(json3_format["url"], timeout=15)
                    if resp.status_code == 200:
                        data = resp.json()
                        events = data.get("events", [])
                        transcript_items = []
                        for ev in events:
                            t_start = ev.get("tStartMs", 0) / 1000.0
                            t_dur = ev.get("dDurationMs", 0) / 1000.0
                            segs = ev.get("segs", [])
                            text = "".join(s.get("utf8", "") for s in segs).strip()
                            if text and text != "\n":
                                transcript_items.append({
                                    "start": round(t_start, 1),
                                    "duration": round(t_dur, 1),
                                    "text": text
                                })
                        return transcript_items
        except Exception as e:
            logger.warning(f"Could not extract transcript via yt-dlp: {e}")
        return []

    def extract_clip(self, youtube_url_or_file: str, start_sec: int, duration_sec: int, output_file: Path) -> bool:
        """
        Extracts a clean section directly using FFmpeg.
        Works with both direct stream URLs and downloaded files.
        """
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # If it's a YouTube URL, get direct media stream URL
        target_source = youtube_url_or_file
        if youtube_url_or_file.startswith("http://") or youtube_url_or_file.startswith("https://"):
            if "youtube.com" in youtube_url_or_file or "youtu.be" in youtube_url_or_file:
                stream_info = self.get_direct_stream_urls(youtube_url_or_file)
                if stream_info.get("video_url"):
                    target_source = stream_info["video_url"]

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-reconnect", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "5",
            "-ss", str(start_sec),
            "-i", target_source,
            "-t", str(duration_sec),
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-c:a", "aac",
            str(output_file)
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            return res.returncode == 0 and output_file.exists() and output_file.stat().st_size > 100000
        except Exception as e:
            logger.error(f"Failed to extract clip from {youtube_url_or_file}: {e}")
            return False
