import os
import re
import json
import random
import logging
from typing import List, Dict
import requests
from config.settings import GEMINI_API_KEY, GEMINI_MODELS

logger = logging.getLogger(__name__)

class VideoAnalyzer:
    """
    Analyzes long YouTube videos (transcripts, chapters, or audio cues)
    using Gemini AI to extract the funniest, most action-packed, and viral 30-55s clips.
    """
    def __init__(self, api_key: str = None):
        self.api_key = api_key or GEMINI_API_KEY

    def _call_gemini(self, prompt: str) -> str:
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }
        for model in GEMINI_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            try:
                r = requests.post(url, headers=headers, json=payload, timeout=30)
                if r.status_code == 200:
                    data = r.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
            except Exception as e:
                logger.warning(f"Model {model} failed: {e}")
                continue
        return ""

    def analyze_and_extract_clips(
        self,
        video_info: dict,
        transcript: list = None,
        max_clips: int = 10
    ) -> List[Dict]:
        """
        Main intelligence method: Identifies the best viral moments (Action & Comedy)
        from video metadata, chapters, and transcript.
        """
        title = video_info.get("title", "YouTube Video")
        duration = video_info.get("duration", 0)
        chapters = video_info.get("chapters", [])
        
        # Prepare context for AI
        transcript_sample = ""
        if transcript:
            # Condense transcript with timestamps
            sample_lines = []
            step = max(1, len(transcript) // 100)
            for i in range(0, min(len(transcript), 300), step):
                t = transcript[i]
                start_min = int(t['start'] // 60)
                start_sec = int(t['start'] % 60)
                sample_lines.append(f"[{start_min:02d}:{start_sec:02d}] {t['text']}")
            transcript_sample = "\n".join(sample_lines[:80])

        chapters_text = ""
        if chapters:
            chapters_text = "\n".join(
                [f"[{ch['start_time']//60}:{ch['start_time']%60:02d}] {ch['title']}" for ch in chapters]
            )

        prompt = f"""
You are a top-tier YouTube Shorts & TikTok viral clipping editor.
A user provided a YouTube video of duration {duration} seconds ({duration//60} minutes).
Video Title: "{title}"

Key Chapters:
{chapters_text if chapters_text else "None provided"}

Transcript Sample:
{transcript_sample if transcript_sample else "No transcript available"}

TASK:
Identify exactly {max_clips} BEST highlight clips from this video.
Look for:
1. High-energy action scenes, battles, or stunts.
2. Extremely funny moments, fails, or hilarious reactions.
3. Shocking plot twists, dramatic moments, or unexpected events.

RULES:
- Each clip duration MUST be between 30 and 55 seconds.
- Ensure 'start_sec' is within 0 and {max(10, duration - 60)}.
- 'hook': An array of 2 strings:
  Line 1: Ultra-catchy 2 to 4 words in ALL CAPS (e.g. "BRO DID NOT EXPECT THIS", "WAIT FOR HIS REACTION", "INSANE SKILL")
  Line 2: "WAIT FOR THE END!"
- 'title': Viral YouTube Shorts title with emojis and hashtags #Shorts #Viral
- 'description': Engaging description with call to action.
- 'tags': Array of 5-8 relevant tags.

Return ONLY a valid JSON array of objects:
[
  {{
    "start_sec": 120,
    "duration": 40,
    "hook": ["INSANE MOMENT", "WAIT FOR THE END!"],
    "title": "When Everything Goes Wrong! 💀 Wait for it #Shorts #Viral",
    "description": "Crazy moment from {title}! Subscribe for more epic clips.",
    "tags": ["shorts", "viral", "funny", "action", "youtube shorts"],
    "reason": "Hilarious reaction and high energy"
  }}
]
"""
        raw_output = self._call_gemini(prompt)
        clean = raw_output.strip()
        if "```json" in clean:
            clean = re.search(r"```json\s*(.*?)\s*```", clean, re.DOTALL).group(1)
        elif "```" in clean:
            clean = re.search(r"```\s*(.*?)\s*```", clean, re.DOTALL).group(1)

        try:
            clips = json.loads(clean)
            if isinstance(clips, list) and len(clips) > 0:
                # Validate clips
                validated = []
                for idx, c in enumerate(clips[:max_clips], start=1):
                    start = int(c.get("start_sec", 0))
                    dur = int(c.get("duration", 40))
                    dur = max(25, min(55, dur))
                    if duration > 60 and start >= duration:
                        start = max(10, duration - 60)
                    
                    hook = c.get("hook")
                    if not isinstance(hook, list) or len(hook) < 2:
                        hook = [str(c.get("hook", "WAIT FOR IT")).upper()[:25], "WAIT FOR THE END!"]
                    
                    validated.append({
                        "clip_index": idx,
                        "start_sec": start,
                        "duration": dur,
                        "hook": hook,
                        "title": c.get("title", f"Unbelievable Moment in {title}! #Shorts"),
                        "description": c.get("description", f"Highlights from {title}! Subscribe for daily shorts."),
                        "tags": c.get("tags", ["shorts", "viral", "epic", "funny"]),
                        "reason": c.get("reason", "Action highlight")
                    })
                return validated
        except Exception as e:
            logger.warning(f"Could not parse Gemini JSON response: {e}. Falling back to algorithmic scene detection.")

        # Algorithmic Fallback if AI output couldn't parse
        return self._algorithmic_highlights(video_info, max_clips)

    def _algorithmic_highlights(self, video_info: dict, max_clips: int) -> List[Dict]:
        """
        Mathematical fallback scene generator when Gemini API is unavailable or rate-limited.
        Distributes clips intelligently across chapters or video duration.
        """
        title = video_info.get("title", "Epic Video")
        duration = max(60, video_info.get("duration", 600))
        chapters = video_info.get("chapters", [])
        clips = []

        hook_pool = [
            ["UNREAL MOMENT", "WAIT FOR THE END!"],
            ["HE ACTUALLY DID THIS", "WAIT FOR THE END!"],
            ["INSTANT REGRET", "WAIT FOR THE END!"],
            ["NO WAY THIS HAPPENED", "WAIT FOR THE END!"],
            ["BRO WAS NOT READY", "WAIT FOR THE END!"],
            ["1000 IQ PLAY", "WAIT FOR THE END!"],
            ["HILARIOUS REACTION", "WAIT FOR THE END!"]
        ]

        if chapters and len(chapters) >= max_clips:
            for i, ch in enumerate(chapters[:max_clips], start=1):
                start = ch["start_time"] + 5
                dur = min(42, max(30, ch["end_time"] - ch["start_time"] - 5))
                clips.append({
                    "clip_index": i,
                    "start_sec": start,
                    "duration": dur,
                    "hook": [ch["title"][:22].upper(), "WAIT FOR THE END!"],
                    "title": f"{ch['title']}! 🔥 Wait For End #Shorts #Viral",
                    "description": f"Highlight moment: {ch['title']} from {title}. Subscribe for more!",
                    "tags": ["shorts", "viral", "highlights", "action"],
                    "reason": f"Chapter highlight: {ch['title']}"
                })
            return clips

        # Sample across video duration
        interval = (duration - 60) / (max_clips + 1)
        for i in range(1, max_clips + 1):
            start = int(interval * i)
            dur = 38
            hook = random.choice(hook_pool)
            clips.append({
                "clip_index": i,
                "start_sec": start,
                "duration": dur,
                "hook": hook,
                "title": f"The Best Part Of {title[:40]}! 💀 #Shorts #Viral",
                "description": f"Insane moment from {title}! Like and subscribe for more daily clips.",
                "tags": ["shorts", "viral", "trending", "youtube shorts"],
                "reason": f"Highlight moment at {start//60}:{start%60:02d}"
            })

        return clips
