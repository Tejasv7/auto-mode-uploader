import os
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from config.settings import (
    FFMPEG_PATH,
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    ENABLE_ANTI_COPYRIGHT,
    SPEED_MULTIPLIER,
    COLOR_BOOST
)

class VideoEditor:
    """
    Renders video clips into high-engagement vertical YouTube Shorts (9:16 - 1080x1920) with:
    1. Anti-Copyright Bypass Filters (1.03x-1.05x audio/video speed shift, color grading, pitch shift, metadata strip)
    2. Ambient blurred background framing (1080x1920)
    3. High-Contrast 2-Line Viral Hook Overlay:
       Line 1: Scene Hook (Bold White)
       Line 2: 'WAIT FOR THE END!' (Vibrant Golden Yellow)
    """
    def __init__(self, ffmpeg_path: str = FFMPEG_PATH, width: int = VIDEO_WIDTH, height: int = VIDEO_HEIGHT):
        self.ffmpeg_path = ffmpeg_path
        self.width = width
        self.height = height

    def create_banner_overlay(self, hook: tuple, output_path: Path) -> Path:
        """
        Generates a 2-line high-contrast viral banner overlay:
        - Semi-transparent dark pill container (ensures 100% readability over bright gameplay)
        - Line 1: Main Hook (Bold White with outline)
        - Line 2: 'WAIT FOR THE END!' (Vibrant Golden Yellow with outline)
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGBA", (self.width, 270), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Cross-platform bold font loading
        bundled_font = Path(__file__).resolve().parent / "config" / "impact.ttf"
        font_path = None
        for candidate in [
            bundled_font,
            "C:/Windows/Fonts/impact.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        ]:
            if os.path.exists(str(candidate)):
                font_path = str(candidate)
                break

        if font_path:
            try:
                font_l1 = ImageFont.truetype(font_path, 64)
                font_l2 = ImageFont.truetype(font_path, 54)
            except Exception:
                font_l1 = ImageFont.load_default()
                font_l2 = ImageFont.load_default()
        else:
            font_l1 = ImageFont.load_default()
            font_l2 = ImageFont.load_default()

        if isinstance(hook, (tuple, list)):
            line1 = str(hook[0]).strip().upper() if hook[0] else "VIRAL MOMENT"
            line2 = str(hook[1]).strip().upper() if len(hook) > 1 and hook[1] else "WAIT FOR THE END!"
        else:
            line1 = str(hook).strip().upper() if hook else "VIRAL MOMENT"
            line2 = "WAIT FOR THE END!"

        # Stylish Dark Glass Box container (Guarantees text pops on any gameplay/video background)
        draw.rounded_rectangle(
            [(30, 15), (self.width - 30, 245)],
            radius=22,
            fill=(0, 0, 0, 190),
            outline=(255, 255, 255, 35),
            width=2
        )

        # Line 1: Main Title / Hook (White)
        draw.text(
            (self.width // 2, 75),
            line1,
            font=font_l1,
            fill=(255, 255, 255, 255),
            stroke_width=6,
            stroke_fill=(0, 0, 0, 255),
            anchor="mm"
        )

        # Line 2: Hook (Vibrant Yellow - ALWAYS 'WAIT FOR THE END!')
        draw.text(
            (self.width // 2, 170),
            line2,
            font=font_l2,
            fill=(255, 215, 0, 255),
            stroke_width=6,
            stroke_fill=(0, 0, 0, 255),
            anchor="mm"
        )

        img.save(output_path, "PNG")
        return output_path

    def format_shorts_clip(self, input_clip: Path, output_clip: Path, hook: tuple = None) -> bool:
        """
        Format any video clip (16:9, 4:3, or vertical) into 9:16 (1080x1920) YouTube Shorts.
        Applies Anti-Copyright Protection Filters:
        - 1.04x speed shift (video & audio)
        - Color curve, brightness & contrast booster
        - Ambient blurred background
        - High-contrast 2-line bold hook overlay
        - Sanitized metadata (strips Content ID tags)
        """
        output_clip.parent.mkdir(parents=True, exist_ok=True)
        banner_file = output_clip.parent / f"banner_{output_clip.stem}.png"
        chosen_hook = hook or ("VIRAL MOMENT", "WAIT FOR THE END!")
        self.create_banner_overlay(chosen_hook, banner_file)

        speed = SPEED_MULTIPLIER if ENABLE_ANTI_COPYRIGHT else 1.0
        setpts_val = round(1.0 / speed, 4)
        
        color_filter = "eq=contrast=1.08:brightness=0.02:saturation=1.18," if (ENABLE_ANTI_COPYRIGHT and COLOR_BOOST) else ""
        fg_scaled_w = int(self.width * 1.04)

        # Robust multi-aspect ratio filter graph with even dimension protection
        # Places hook banner comfortably at y=100 from top (perfect for Shorts UI)
        filter_str = (
            f"[0:v]scale={self.width}:{self.height}:force_original_aspect_ratio=increase,"
            f"crop={self.width}:{self.height},boxblur=25:5,{color_filter}format=yuv420p[bg];"
            f"[0:v]scale={fg_scaled_w}:-2,crop={self.width}:min(ih\\,{self.height}),{color_filter}format=yuv420p[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2[merged];"
            f"[merged][1:v]overlay=0:100,"
            f"setpts={setpts_val}*PTS[v];"
            f"[0:a]asetrate=44100*{speed},aresample=44100,aformat=channel_layouts=stereo[a]"
        )

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", str(input_clip),
            "-i", str(banner_file),
            "-filter_complex", filter_str,
            "-map", "[v]",
            "-map", "[a]",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-c:a", "aac",
            "-b:a", "192k",
            "-map_metadata", "-1",
            str(output_clip)
        ]

        res = subprocess.run(cmd, capture_output=True, text=True)

        if banner_file.exists():
            try:
                banner_file.unlink()
            except Exception:
                pass

        return res.returncode == 0 and output_clip.exists() and output_clip.stat().st_size > 50000
