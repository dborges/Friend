import time
import httpx
from app.config import TIKTOK_ACCESS_TOKEN, TIKTOK_OPEN_ID

BASE_URL = "https://open.tiktokapis.com/v2"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
        "Content-Type": "application/json; charset=UTF-8",
    }


# ── Creator info ───────────────────────────────────────────────────────────────

def get_creator_info() -> dict:
    with httpx.Client(timeout=15) as c:
        resp = c.post(f"{BASE_URL}/post/publish/creator_info/query/", headers=_headers())
        resp.raise_for_status()
        return resp.json().get("data", {})


# ── Post video ────────────────────────────────────────────────────────────────

def post_video(video_path: str, caption: str, privacy: str = "SELF_ONLY") -> str:
    """
    Upload a local video file and post it.
    Returns publish_id.
    privacy: SELF_ONLY | MUTUAL_FOLLOW_FRIENDS | FOLLOWER_OF_CREATOR | PUBLIC_TO_EVERYONE
    """
    file_size = __import__("os").path.getsize(video_path)

    with httpx.Client(timeout=30) as c:
        # Step 1: init upload
        resp = c.post(
            f"{BASE_URL}/post/publish/video/init/",
            headers=_headers(),
            json={
                "post_info": {
                    "title": caption[:150],
                    "privacy_level": privacy,
                    "disable_duet": False,
                    "disable_comment": False,
                    "disable_stitch": False,
                },
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": file_size,
                    "chunk_size": file_size,
                    "total_chunk_count": 1,
                },
            },
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        publish_id = data["publish_id"]
        upload_url = data["upload_url"]

    # Step 2: upload video bytes
    with open(video_path, "rb") as f:
        video_bytes = f.read()

    with httpx.Client(timeout=120) as c:
        upload_resp = c.put(
            upload_url,
            content=video_bytes,
            headers={
                "Content-Type": "video/mp4",
                "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
                "Content-Length": str(file_size),
            },
        )
        upload_resp.raise_for_status()

    return publish_id


def get_post_status(publish_id: str) -> dict:
    with httpx.Client(timeout=15) as c:
        resp = c.post(
            f"{BASE_URL}/post/publish/status/fetch/",
            headers=_headers(),
            json={"publish_id": publish_id},
        )
        resp.raise_for_status()
        return resp.json().get("data", {})


# ── Token refresh ──────────────────────────────────────────────────────────────

def refresh_token(client_key: str, client_secret: str, refresh_token: str) -> dict:
    with httpx.Client(timeout=15) as c:
        resp = c.post(
            f"{BASE_URL}/oauth/token/",
            data={
                "client_key":    client_key,
                "client_secret": client_secret,
                "grant_type":    "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        resp.raise_for_status()
        return resp.json()
