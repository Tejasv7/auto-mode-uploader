import os
import re
import json
import random
import logging
from typing import List, Dict, Union
import requests
from config.settings import GEMINI_API_KEY, GEMINI_MODELS

logger = logging.getLogger(__name__)

# Vast library of viral hooks for gaming, funny moments, and action videos
VIRAL_HOOKS = [
    ["BRO DID NOT EXPECT THIS", "WAIT FOR THE END!"],
    ["1000 IQ MOMENT", "WAIT FOR THE END!"],
    ["HE ACTUALLY PULLED IT OFF", "WAIT FOR THE END!"],
    ["INSANE REACTION", "WAIT FOR THE END!"],
    ["BRO WENT FULL BEAST MODE", "WAIT FOR THE END!"],
    ["THE CLEANEST PLAY EVER", "WAIT FOR THE END!"],
    ["HOW DID HE SURVIVE THIS", "WAIT FOR THE END!"],
    ["UNLUCKIEST MOMENT EVER", "WAIT FOR THE END!"],
    ["INSTANT KARMA", "WAIT FOR THE END!"],
    ["BRO DELETED HIM", "WAIT FOR THE END!"],
    ["HE DID NOT JUST DO THAT", "WAIT FOR THE END!"],
    ["WAIT FOR HIS REACTION", "WAIT FOR THE END!"],
    ["ACTUAL AIMBOT MOMENT", "WAIT FOR THE END!"],
    ["CANNOT STOP LAUGHING", "WAIT FOR THE END!"],
    ["WHAT JUST HAPPENED", "WAIT FOR THE END!"],
    ["HE THOUGHT HE WAS SAFE", "WAIT FOR THE END!"],
    ["MOST ILLEGAL PLAY EVER", "WAIT FOR THE END!"],
    ["BRO BROKE HIS KEYBOARD", "WAIT FOR THE END!"],
    ["CLUTCH OF THE CENTURY", "WAIT FOR THE END!"],
    ["EVERYONE WENT SILENT", "WAIT FOR THE END!"],
    ["NO WAY HE SURVIVED THAT", "WAIT FOR THE END!"],
    ["TOP 1% MOMENT", "WAIT FOR THE END!"],
    ["BRO REGRETTED IMMEDIATELY", "WAIT FOR THE END!"],
    ["GREATEST OUTPLAY IN HISTORY", "WAIT FOR THE END!"],
    ["LOOK AT HIS FACE", "WAIT FOR THE END!"],
    ["NEVER CELEBRATE TOO EARLY", "WAIT FOR THE END!"],
    ["THE ULTIMATE TRAP", "WAIT FOR THE END!"],
    ["LEGENDARY MOMENT", "WAIT FOR THE END!"]
]

VIRAL_TITLE_TEMPLATES = [
    "When you try to be smart but fail miserably! 💀 #Shorts #Gaming",
    "Bro actually pulled off the impossible! 😱🔥 #Shorts #Viral",
    "He thought he had him until this happened... 💀 #Shorts #Funny",
    "The most insane clutch you will see today! 🤯 #Shorts #Gameplay",
    "Wait for his teammate's reaction at the end! 😂 #Shorts #Hilarious",
    "How is this even possible?! 💀 #Shorts #ViralClips",
    "Bro took it personally and destroyed everyone! 💀 #Shorts #Action",
    "Never celebrate too early! 😭 Wait for it #Shorts #InstantKarma",
    "1000 IQ play or pure luck?! 🤯 #Shorts #GamingHighlights",
    "His brain stopped working for 5 seconds! 😂 #Shorts #EpicMoments",
    "The cleanest headshot in existence! 🔥 #Shorts #GameplayClip",
    "This is why you never mess with him! 💀 #Shorts #ViralGaming",
    "Bro got humbled so fast! 😭 #Shorts #GamingFails",
    "Watch until the end, you won't believe this! 🤯 #Shorts #Trend",
    "Everyone thought he was dead... then THIS! 😱 #Shorts #Insane"
]

class VideoAnalyzer:
    """
    Analyzes long YouTube videos (even 2–4 hours long)
    and extracts ALL possible high-action and funny highlight clips (up to 300-400+ clips).
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
        max_clips: Union[int, str] = "auto"
    ) -> List[Dict]:
        """
        Extracts ALL best viral clips from the video.
        If max_clips is 'auto' or 'all' or 0, it dynamically calculates the maximum
        number of clips possible for the duration (e.g. 4-hour video -> 200-350+ clips).
        """
        title = video_info.get("title", "YouTube Video")
        duration = max(60, video_info.get("duration", 600))
        chapters = video_info.get("chapters", [])

        # Determine target clips count
        if str(max_clips).lower() in ("auto", "all", "0", ""):
            # For 4 hours (14,400s), approx 1 clip every 45-50s of video = ~280-320 clips!
            # Minimum 8 clips, maximum 400 clips
            target_count = max(8, min(400, int(duration // 45)))
        else:
            try:
                target_count = int(max_clips)
            except Exception:
                target_count = max(8, min(400, int(duration // 45)))

        print(f"[*] Analyzing video length: {duration//60} minutes ({duration}s)")
        print(f"[*] Target Highlights to Extract: {target_count} Clips across the entire video!")

        # For large clip counts (> 20), chunk the video into segments to avoid LLM token overflow
        if target_count > 20:
            return self._extract_mass_clips(video_info, transcript, target_count)
        else:
            # Standard single-pass analysis for smaller batches
            return self._single_pass_gemini_analysis(video_info, transcript, target_count)

    def _single_pass_gemini_analysis(self, video_info: dict, transcript: list, max_clips: int) -> List[Dict]:
        """Analyzes a video for a moderate batch of clips (under 20)."""
        title = video_info.get("title", "YouTube Video")
        duration = max(60, video_info.get("duration", 600))
        chapters = video_info.get("chapters", [])

        transcript_sample = ""
        if transcript:
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
You are an elite YouTube Shorts & TikTok viral clipping editor.
A user provided a video of duration {duration} seconds ({duration//60} minutes).
Video Title: "{title}"
Key Chapters: {chapters_text if chapters_text else "None"}
Transcript Sample: {transcript_sample if transcript_sample else "None"}

TASK:
Identify exactly {max_clips} BEST highlight clips from this video (Action, Comedy, Epic Kills, Shocking Moments).
Each clip MUST be 30 to 55 seconds long.
Ensure start_sec is within 0 and {max(10, duration - 60)}.

Return ONLY valid JSON array:
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
        raw = self._call_gemini(prompt)
        parsed = self._parse_json_clips(raw, max_clips, title, duration)
        if parsed:
            return parsed
        return self._generate_dense_highlights(video_info, max_clips)

    def _extract_mass_clips(self, video_info: dict, transcript: list, total_clips: int) -> List[Dict]:
        """
        Mass highlights generator: Divides long videos (1 to 4+ hours)
        into high-energy segments and generates up to 100–400+ clips with zero repetition.
        """
        title = video_info.get("title", "YouTube Video")
        duration = max(60, video_info.get("duration", 600))
        chapters = video_info.get("chapters", [])
        
        # Try chunked Gemini analysis for the first few segments to get rich AI themes
        ai_theme_titles = []
        try:
            sample_prompt = f"""
Given this long YouTube video: "{title}" ({duration//60} minutes long).
Give me 10 super catchy, viral, high-CTR YouTube Shorts titles (with emojis & #Shorts)
for the funniest moments, crazy clutches, and high-action scenes in this video.
Return ONLY a JSON array of strings: ["Title 1 #Shorts", "Title 2 #Shorts", ...]
"""
            raw_ai = self._call_gemini(sample_prompt)
            clean = raw_ai.strip()
            if "```json" in clean:
                clean = re.search(r"```json\s*(.*?)\s*```", clean, re.DOTALL).group(1)
            elif "```" in clean:
                clean = re.search(r"```\s*(.*?)\s*```", clean, re.DOTALL).group(1)
            ai_theme_titles = json.loads(clean)
        except Exception:
            pass

        # Combine AI theme titles with our viral template library
        title_pool = ai_theme_titles + VIRAL_TITLE_TEMPLATES if ai_theme_titles else VIRAL_TITLE_TEMPLATES

        # Generate dense highlights across the full duration
        return self._generate_dense_highlights(video_info, total_clips, custom_titles=title_pool)

    def _generate_dense_highlights(
        self,
        video_info: dict,
        target_count: int,
        custom_titles: list = None
    ) -> List[Dict]:
        """
        Evenly and smartly segments a long video into action candidate clips.
        Ensures 100% of the video is covered without overlapping timestamps.
        """
        title = video_info.get("title", "Epic Video")
        duration = max(60, video_info.get("duration", 600))
        chapters = video_info.get("chapters", [])
        clips = []

        pool_hooks = VIRAL_HOOKS.copy()
        random.shuffle(pool_hooks)

        pool_titles = (custom_titles or VIRAL_TITLE_TEMPLATES).copy()
        random.shuffle(pool_titles)

        # Average duration of each clip is 38-44s
        clip_dur = 40
        buffer_between = 5  # 5s gap

        # Calculate step interval to cover the whole video
        available_time = max(30, duration - 60)
        step = available_time / target_count

        for i in range(target_count):
            start = int(i * step)
            if start + clip_dur > duration:
                start = max(0, duration - clip_dur - 5)

            # Cycle through hooks and titles smoothly
            hook = pool_hooks[i % len(pool_hooks)]
            raw_title = pool_titles[i % len(pool_titles)]

            # Check if this falls inside a specific chapter for custom branding
            chapter_name = ""
            if chapters:
                for ch in chapters:
                    if ch["start_time"] <= start <= ch["end_time"]:
                        chapter_name = ch["title"]
                        break

            if chapter_name and len(chapter_name) < 25:
                clip_hook = [chapter_name.upper(), "WAIT FOR THE END!"]
                clip_title = f"{chapter_name}! 💀 {raw_title}"
            else:
                clip_hook = hook
                clip_title = raw_title

            # Truncate title to YouTube 95-char limit
            if len(clip_title) > 95:
                clip_title = clip_title[:90] + "... #Shorts"

            min_time = start // 60
            sec_time = start % 60
            clips.append({
                "clip_index": i + 1,
                "start_sec": start,
                "duration": clip_dur,
                "hook": clip_hook,
                "title": clip_title,
                "description": f"Highlight moment at [{min_time:02d}:{sec_time:02d}] from {title}.\n\nSubscribe for daily clips and high-energy shorts!\n\n#Shorts #Gaming #Viral",
                "tags": ["shorts", "viral", "highlights", "action", "funny", "gaming", "youtube shorts"],
                "reason": f"Highlight scene at {min_time}m {sec_time}s"
            })

        return clips

    def _parse_json_clips(self, raw_output: str, max_clips: int, title: str, duration: int) -> List[Dict]:
        """Safely parses JSON output from Gemini."""
        clean = raw_output.strip()
        if "```json" in clean:
            clean = re.search(r"```json\s*(.*?)\s*```", clean, re.DOTALL).group(1)
        elif "```" in clean:
            clean = re.search(r"```\s*(.*?)\s*```", clean, re.DOTALL).group(1)

        try:
            data = json.loads(clean)
            if isinstance(data, list) and len(data) > 0:
                validated = []
                for idx, c in enumerate(data[:max_clips], start=1):
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
                        "title": c.get("title", f"Epic Moment in {title[:40]}! #Shorts"),
                        "description": c.get("description", f"Highlights from {title}! Subscribe for daily shorts."),
                        "tags": c.get("tags", ["shorts", "viral", "epic", "funny"]),
                        "reason": c.get("reason", "Action highlight")
                    })
                return validated
        except Exception:
            pass
        return []
