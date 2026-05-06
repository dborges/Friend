import os
import subprocess
from app.config import GENERATED_DIR


def image_to_video(image_path: str, duration: int = 8) -> str:
    """
    Convert a single image to a short MP4 using FFmpeg.
    Zooms in slightly (Ken Burns effect) to make it feel dynamic.
    Returns path to the output video file.
    """
    out_path = os.path.join(GENERATED_DIR, os.path.basename(image_path).replace(".jpg", ".mp4").replace(".png", ".mp4"))

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-vf", (
            f"scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,"
            f"zoompan=z='min(zoom+0.0015,1.5)':d={duration * 25}:s=1080x1920"
        ),
        "-c:v", "libx264",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        "-r", "25",
        out_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Fallback: simple loop without zoom
        cmd_simple = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", image_path,
            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
            "-c:v", "libx264",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            "-r", "25",
            out_path,
        ]
        subprocess.run(cmd_simple, check=True, capture_output=True)

    return out_path
