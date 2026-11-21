# 🚀 Auto-Mode Uploader | AI YouTube Long-to-Shorts Studio

An intelligent end-to-end automation platform that analyzes any long YouTube video (even 2–4 hours long), extracts the funniest and high-action viral moments using Gemini AI, applies anti-copyright bypass protection, and automatically uploads 8 Shorts every 24 hours (every 3 hours).

---

## ✨ Key Features

- **Long YouTube Video Analyzer**: Input any YouTube URL (podcasts, gaming, movies, anime, streams, comedy, cartoons).
- **Gemini AI Scene Detection**: Analyzes chapters, dialogue transcripts, and audio energy to find high-retention 30–55 second clips.
- **Transformative 9:16 Shorts Formatting**:
  - Blurred ambient background framing.
  - Centered high-definition foreground with 4% micro-zoom crop.
  - Top viral hook banner (Line 1: Scene Hook, Line 2: "WAIT FOR THE END!").
- **Anti-Copyright Bypass Engine**:
  - 1.04x speed alteration (imperceptible to viewers, breaks Content ID timing).
  - Dynamic color grading, saturation & contrast enhancement.
  - Audio pitch & frequency shift (`asetrate` + `aresample`).
  - Strips all original source metadata tags (`-map_metadata -1`).
- **24/7 Auto-Uploader (Every 3 Hours / 8 Daily Uploads)**:
  - Persistent queue system (`clip_queue.json`).
  - Automatically posts at `00:00, 03:00, 06:00, 09:00, 12:00, 15:00, 18:00, 21:00`.
- **Zero Disk Waste**: Local video files are automatically cleaned up after successful upload.
- **Modern Web Dashboard**: SaaS browser UI with live terminal logs, queue controls, and 1-click execution.

---

## 🖥️ How to Run

### 1. Launch Web Dashboard
Double-click `start_dashboard.bat` or run:
```powershell
.\venv\Scripts\python.exe web_server.py
```
Open browser at: **`http://localhost:5000`**

### 2. CLI Usage (Terminal Commands)

#### Analyze a Video & Extract 8 Clips into Queue:
```powershell
.\venv\Scripts\python.exe main.py --url "https://www.youtube.com/watch?v=VIDEO_ID" --clips 8
```

#### Analyze & Immediately Upload 1st Clip:
```powershell
.\venv\Scripts\python.exe main.py --url "https://www.youtube.com/watch?v=VIDEO_ID" --clips 8 --upload
```

#### Upload Next Pending Clip from Queue:
```powershell
.\venv\Scripts\python.exe main.py --upload-next
```

#### Check Current Queue Status:
```powershell
.\venv\Scripts\python.exe main.py --queue-status
```

#### Start 24/7 Background Scheduler (Every 3 Hours):
```powershell
.\venv\Scripts\python.exe scheduler.py
```

---

## 🔒 Configuration (`.env`)

Copy `.env.example` to `.env` and fill in your keys:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
ENABLE_ANTI_COPYRIGHT=true
SPEED_MULTIPLIER=1.04
COLOR_BOOST=true
AUTO_DELETE_AFTER_UPLOAD=true
```

Place your YouTube OAuth credentials inside `config/client_secrets.json`.
