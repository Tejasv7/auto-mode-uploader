import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory of Project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(BASE_DIR / ".env")

# Project Directories
CONFIG_DIR = BASE_DIR / "config"
FINAL_VIDEOS_DIR = BASE_DIR / "final_videos"
GENERATED_DIR = BASE_DIR / "generated"
LOGS_DIR = BASE_DIR / "logs"

for folder in [CONFIG_DIR, FINAL_VIDEOS_DIR, GENERATED_DIR, LOGS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# Google Gemini API Settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODELS = [
    os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
    "gemini-3.5-flash-lite",
    "gemini-flash-latest",
    "gemini-3.8-flash",
]

# Video Dimensions (Vertical 9:16 Shorts)
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

# Anti-Copyright Auto-Bypass Settings
ENABLE_ANTI_COPYRIGHT = os.getenv("ENABLE_ANTI_COPYRIGHT", "true").lower() == "true"
SPEED_MULTIPLIER = float(os.getenv("SPEED_MULTIPLIER", "1.06"))
COLOR_BOOST = os.getenv("COLOR_BOOST", "true").lower() == "true"

# Storage Optimization (Auto-delete video after successful YouTube upload)
AUTO_DELETE_AFTER_UPLOAD = os.getenv("AUTO_DELETE_AFTER_UPLOAD", "true").lower() == "true"

# FFmpeg Executable Path
try:
    import imageio_ffmpeg
    FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_PATH = "ffmpeg"
