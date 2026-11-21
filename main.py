import os
import sys
import shutil
import argparse
import logging
from datetime import datetime
from pathlib import Path

from youtube_downloader import YouTubeDownloader
from video_analyzer import VideoAnalyzer
from video_editor import VideoEditor
from queue_manager import QueueManager
from youtube_uploader import YouTubeUploader
from history_manager import add_history_entry
from config.settings import FINAL_VIDEOS_DIR, GENERATED_DIR, AUTO_DELETE_AFTER_UPLOAD

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

def process_youtube_video(
    youtube_url: str,
    max_clips: int = 8,
    upload_first: bool = False,
    privacy: str = "public"
) -> dict:
    """
    Complete Pipeline for Long YouTube Videos:
    1. Extracts metadata, chapters & subtitles
    2. Analyzes video content with Gemini AI to find the best action & comedy moments
    3. Adds high-engagement clips to the persistent Queue
    4. (Optional) Renders and uploads the first clip immediately
    """
    print("\n" + "="*70)
    print("   AI YOUTUBE SHORTS AUTO-CLIPPER & UPLOADER")
    print(f"   Target Video : {youtube_url}")
    print(f"   Max Clips    : {max_clips}")
    print("="*70)

    downloader = YouTubeDownloader()
    analyzer = VideoAnalyzer()
    queue_mgr = QueueManager()

    # Step 1: Get Video Metadata
    print("\n>>> [STEP 1/3] Reading YouTube Video Information & Chapters...")
    info = downloader.get_video_info(youtube_url)
    dur_min = info['duration'] // 60
    dur_sec = info['duration'] % 60
    print(f"  [+] Title    : {info['title']}")
    print(f"  [+] Duration : {dur_min}m {dur_sec}s ({info['duration']} seconds)")
    print(f"  [+] Chapters : {len(info.get('chapters', []))} detected")

    # Step 2: Extract Transcript (if available)
    print("\n>>> [STEP 2/3] Extracting Subtitles & Transcripts for AI Content Analysis...")
    transcript = downloader.extract_transcript(youtube_url)
    if transcript:
        print(f"  [+] Extracted {len(transcript)} subtitle dialogue lines!")
    else:
        print("  [*] No subtitles found. Proceeding with Chapters / Visual Energy Analysis.")

    # Step 3: Analyze Highlights with Gemini AI
    print(f"\n>>> [STEP 3/3] Gemini AI Analyzing Best Action/Comedy Scenes (Target: {max_clips} Clips)...")
    clips = analyzer.analyze_and_extract_clips(info, transcript=transcript, max_clips=max_clips)
    print(f"  [+] Successfully identified {len(clips)} viral highlight moments!")

    # Add all detected clips to persistent queue
    added_ids = queue_mgr.add_clips(youtube_url, info["title"], clips)
    print(f"  [+] Added {len(added_ids)} clips to the 24/7 Upload Queue!")

    result = {
        "source_title": info["title"],
        "duration": info["duration"],
        "total_clips": len(clips),
        "queued_ids": added_ids,
        "clips": clips,
        "uploaded": False
    }

    # Optional immediate upload of the first clip
    if upload_first and len(clips) > 0:
        first_clip = queue_mgr.get_next_clip()
        if first_clip:
            print("\n>>> [--upload requested] Processing and uploading first clip immediately...")
            upload_res = render_and_upload_clip(first_clip["id"], privacy=privacy)
            result["uploaded"] = True
            result["upload_result"] = upload_res

    print("\n" + "="*70)
    print(f"   DONE! {len(clips)} Clips Ready in Queue for 3-Hour Auto-Uploader.")
    print("="*70 + "\n")
    return result

def render_and_upload_clip(clip_id: str, privacy: str = "public") -> dict:
    """
    Renders a specific queued clip into a 9:16 Short with anti-copyright protection,
    and uploads it to YouTube Shorts.
    """
    queue_mgr = QueueManager()
    all_clips = queue_mgr.get_all_clips()
    clip = next((c for c in all_clips if c["id"] == clip_id), None)
    if not clip:
        raise ValueError(f"Clip with ID {clip_id} not found in queue!")

    downloader = YouTubeDownloader()
    editor = VideoEditor()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = GENERATED_DIR / f"clip_{clip_id}_{timestamp}"
    session_dir.mkdir(parents=True, exist_ok=True)

    raw_clip_path = session_dir / "raw_cut.mp4"
    final_clip_path = FINAL_VIDEOS_DIR / f"Short_{clip_id}_{timestamp}.mp4"

    try:
        queue_mgr.update_clip(clip_id, {"status": "rendering"})
        print(f"\n[*] Cutting clip '{clip['title']}' ({clip['duration']}s at {clip['start_sec']}s)...")
        
        # 1. Cut section from source
        success = downloader.extract_clip(
            clip["source_url"],
            clip["start_sec"],
            clip["duration"],
            raw_clip_path
        )
        if not success:
            raise RuntimeError("Failed to extract video section from source stream!")

        # 2. Format into 9:16 Shorts with Anti-Copyright filters & Hook banner
        print("[*] Applying 9:16 Vertical Formatting, Hook Banner & Anti-Copyright Filters...")
        success = editor.format_shorts_clip(raw_clip_path, final_clip_path, hook=clip.get("hook"))
        if not success:
            raise RuntimeError("Failed to render 9:16 Shorts with FFmpeg!")

        queue_mgr.update_clip(clip_id, {"status": "uploading", "video_file": str(final_clip_path)})

        # 3. Upload to YouTube
        print(f"[*] Uploading to YouTube Shorts (Privacy: {privacy})...")
        uploader = YouTubeUploader()
        if not uploader.is_configured():
            print("  [!] YouTube credentials not configured. Saving formatted video file locally.")
            queue_mgr.update_clip(clip_id, {"status": "ready", "video_file": str(final_clip_path)})
            return {"status": "ready_locally", "video_path": str(final_clip_path)}

        youtube_url = uploader.upload_video(
            video_path=str(final_clip_path),
            title=clip["title"][:95],
            description=clip["description"] + "\n\n#Shorts #Viral",
            tags=clip.get("tags", ["shorts", "viral"]),
            privacy=privacy
        )

        # Mark as uploaded in queue
        queue_mgr.mark_uploaded(clip_id, youtube_url or "uploaded")

        # Record in history
        add_history_entry({
            "timestamp": datetime.now().isoformat(),
            "title": clip["title"],
            "hook": clip.get("hook", ["", ""])[0],
            "youtube_url": youtube_url,
            "source_url": clip.get("source_url"),
            "status": "uploaded"
        })

        # Storage cleanup
        if AUTO_DELETE_AFTER_UPLOAD and final_clip_path.exists():
            try:
                final_clip_path.unlink()
                print(f"  [+] Cleaned up local video file to save disk space.")
            except Exception:
                pass

        if session_dir.exists():
            shutil.rmtree(session_dir, ignore_errors=True)

        return {"status": "uploaded", "youtube_url": youtube_url, "clip_id": clip_id}

    except Exception as e:
        logger.error(f"Error processing clip {clip_id}: {e}", exc_info=True)
        queue_mgr.mark_failed(clip_id, str(e))
        if session_dir.exists():
            shutil.rmtree(session_dir, ignore_errors=True)
        raise

def upload_next_from_queue(privacy: str = "public") -> dict:
    """Finds next pending clip in the queue and uploads it."""
    queue_mgr = QueueManager()
    next_clip = queue_mgr.get_next_clip()
    if not next_clip:
        print("[*] No pending clips in queue! Add more YouTube videos to keep uploading.")
        return {"status": "empty_queue"}

    print(f"\n>>> Uploading Next Queued Clip: '{next_clip['title']}' (ID: {next_clip['id']})...")
    return render_and_upload_clip(next_clip["id"], privacy=privacy)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI YouTube Shorts Auto-Clipper & Uploader")
    parser.add_argument("--url", type=str, help="YouTube video URL to analyze and extract clips from")
    parser.add_argument("--clips", type=int, default=8, help="Number of viral clips to extract (Default: 8)")
    parser.add_argument("--upload", action="store_true", help="Instantly upload first clip after processing")
    parser.add_argument("--upload-all", action="store_true", help="Upload all clips in queue immediately")
    parser.add_argument("--upload-next", action="store_true", help="Upload the next pending clip from the queue")
    parser.add_argument("--privacy", type=str, default="public", choices=["public", "unlisted", "private"])
    parser.add_argument("--queue-status", action="store_true", help="Show current queue statistics")
    parser.add_argument("--clear-queue", action="store_true", help="Clear all queued clips")

    args = parser.parse_args()

    if args.queue_status:
        q = QueueManager()
        stats = q.get_stats()
        print("\n=== QUEUE STATUS ===")
        print(f"Total Clips : {stats['total']}")
        print(f"Pending     : {stats['pending']}")
        print(f"Uploaded    : {stats['uploaded']}")
        print(f"Failed      : {stats['failed']}\n")
        sys.exit(0)

    if args.clear_queue:
        QueueManager().clear_queue()
        print("[+] Queue cleared successfully.")
        sys.exit(0)

    if args.upload_next:
        upload_next_from_queue(privacy=args.privacy)
        sys.exit(0)

    if args.upload_all:
        q = QueueManager()
        pending = q.get_pending_clips()
        print(f"\n[*] Uploading all {len(pending)} pending clips from queue...")
        for c in pending:
            try:
                render_and_upload_clip(c["id"], privacy=args.privacy)
            except Exception as e:
                print(f"  [!] Failed to upload clip {c['id']}: {e}")
        sys.exit(0)

    if args.url:
        process_youtube_video(
            youtube_url=args.url,
            max_clips=args.clips,
            upload_first=args.upload,
            privacy=args.privacy
        )
    else:
        parser.print_help()
