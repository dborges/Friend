import time
import httpx
from app.config import THREADS_ACCESS_TOKEN, THREADS_USER_ID

BASE_URL = "https://graph.threads.net/v1.0"


def _uid() -> str:
    return THREADS_USER_ID or "me"


def _params(**extra) -> dict:
    return {"access_token": THREADS_ACCESS_TOKEN, **extra}


# ── Posts ──────────────────────────────────────────────────────────────────────

def post_text(text: str) -> str:
    """Post a text-only Thread. Returns the published post ID."""
    return _create_and_publish(text=text, media_type="TEXT")


def post_image(image_url: str, text: str = "") -> str:
    """Post a Thread with an image (must be a public URL). Returns the published post ID."""
    return _create_and_publish(text=text, media_type="IMAGE", image_url=image_url)


def _create_and_publish(text: str, media_type: str, image_url: str = "") -> str:
    with httpx.Client(timeout=30) as c:
        # Step 1 — create media container
        payload = _params(media_type=media_type, text=text[:500])
        if image_url:
            payload["image_url"] = image_url

        resp = c.post(f"{BASE_URL}/{_uid()}/threads", params=payload)
        resp.raise_for_status()
        creation_id = resp.json()["id"]

        # Step 2 — wait for container to be ready, then publish
        time.sleep(5)
        resp = c.post(
            f"{BASE_URL}/{_uid()}/threads_publish",
            params=_params(creation_id=creation_id),
        )
        resp.raise_for_status()
        return resp.json()["id"]


# ── Token refresh ──────────────────────────────────────────────────────────────

def refresh_long_lived_token(app_secret: str, current_token: str) -> dict:
    """Exchange current long-lived token for a fresh 60-day one."""
    with httpx.Client(timeout=15) as c:
        resp = c.get(
            f"{BASE_URL.replace('/v1.0', '')}/access_token",
            params={
                "grant_type":    "th_exchange_token",
                "client_secret": app_secret,
                "access_token":  current_token,
            },
        )
        resp.raise_for_status()
        return resp.json()
