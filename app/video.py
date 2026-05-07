import base64
import os
import random
import subprocess
import httpx
import replicate
from app.config import GENERATED_DIR, REPLICATE_API_TOKEN

os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN

# Wan 2.1 image-to-video on Replicate
_I2V_MODEL = "wavespeed-ai/wan-2.1-i2v-480p"

# Natural motion prompts — keep movement subtle so it reads as real footage
_MOTION_PROMPTS = [
    "natural breathing, subtle hair movement, slight handheld camera shake, realistic candid video",
    "person glances to the side and back, hair sways gently, soft ambient movement",
    "slow natural blink, slight head tilt, gentle background sway, authentic moment",
    "relaxed movement, shifts weight slightly, candid reaction, natural lighting flicker",
    "laughs softly, hair catches light, subtle motion, feels like a real recorded moment",
    "looks down then back up, small smile forms, gentle breeze in hair, phone camera feel",
]

_NEGATIVE_MOTION = (
    "cgi, animation, cartoon, unnatural movement, morphing, dissolving, "
    "glitching, stuttering, jerky, slow motion, time lapse, freeze frame"
)


def _image_to_data_uri(image_path: str) -> str:
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    ext = os.path.splitext(image_path)[1].lstrip(".") or "jpg"
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
    return f"data:{mime};base64,{data}"


def generate_video(image_path: str, motion_prompt: str = "") -> str:
    """
    Animate a Flux image using Wan 2.1 image-to-video.
    Falls back to FFmpeg Ken Burns if Replicate fails.
    Returns path to the output MP4.
    """
    out_path = os.path.join(
        GENERATED_DIR,
        os.path.basename(image_path).replace(".jpg", ".mp4").replace(".png", ".mp4"),
    )

    try:
        prompt = motion_prompt or random.choice(_MOTION_PROMPTS)
        image_uri = _image_to_data_uri(image_path)

        output = replicate.run(
            _I2V_MODEL,
            input={
                "image": image_uri,
                "prompt": prompt,
                "negative_prompt": _NEGATIVE_MOTION,
                "num_frames": 81,
                "frames_per_second": 16,
                "guidance_scale": 5.0,
                "num_inference_steps": 30,
                "fast_mode": "Balanced",
            },
        )

        video_url = str(output[0]) if isinstance(output, list) else str(output)
        with httpx.Client() as client:
            resp = client.get(video_url, timeout=120)
            resp.raise_for_status()
            with open(out_path, "wb") as f:
                f.write(resp.content)

        return out_path

    except Exception:
        return _ken_burns_fallback(image_path, out_path)


def _ken_burns_fallback(image_path: str, out_path: str, duration: int = 8) -> str:
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
        cmd_simple = [
            "ffmpeg", "-y", "-loop", "1", "-i", image_path,
            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
            "-c:v", "libx264", "-t", str(duration), "-pix_fmt", "yuv420p", "-r", "25",
            out_path,
        ]
        subprocess.run(cmd_simple, check=True, capture_output=True)
    return out_path


# Keep old name as alias so TikTok scheduler call still works
def image_to_video(image_path: str, duration: int = 8) -> str:
    return generate_video(image_path)
