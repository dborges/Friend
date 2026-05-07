import httpx
from app.config import ONLYFANS_API_KEY, ONLYFANS_ACCOUNT_ID

BASE_URL = "https://app.onlyfansapi.com/api"

_HEADERS = {
    "Authorization": f"Bearer {ONLYFANS_API_KEY}",
    "Content-Type": "application/json",
}

# Prepended to every post per OnlyFans AI disclosure policy.
# Must appear at the start of content, not buried in hashtags.
AI_DISCLOSURE = "[AI-Generated Content] #AIGenerated #AICreator"


def _url(path: str) -> str:
    return f"{BASE_URL}/{ONLYFANS_ACCOUNT_ID}{path}"


def _client() -> httpx.Client:
    return httpx.Client(headers=_HEADERS, timeout=30)


# ── Chats / DMs ───────────────────────────────────────────────────────────────

def get_chats(limit: int = 50) -> list[dict]:
    with _client() as c:
        resp = c.get(_url("/chats"), params={"limit": limit})
        resp.raise_for_status()
        body = resp.json()
        return body.get("data", {}).get("list", body.get("data", []))


def get_chat_messages(chat_id: str, limit: int = 20) -> list[dict]:
    with _client() as c:
        resp = c.get(_url(f"/chats/{chat_id}/messages"), params={"limit": limit})
        resp.raise_for_status()
        body = resp.json()
        return body.get("data", {}).get("list", body.get("data", []))


def send_message(chat_id: str, text: str) -> dict:
    with _client() as c:
        resp = c.post(_url(f"/chats/{chat_id}/messages"), json={"text": text})
        resp.raise_for_status()
        return resp.json()


def send_message_with_media(chat_id: str, text: str, media_ids: list[str]) -> dict:
    with _client() as c:
        resp = c.post(
            _url(f"/chats/{chat_id}/messages"),
            json={"text": text, "mediaFiles": media_ids},
        )
        resp.raise_for_status()
        return resp.json()


# ── Media upload ──────────────────────────────────────────────────────────────

def upload_media(file_path: str) -> str:
    """Upload a local file. Returns the prefixed media ID (ofapi_media_xxx)."""
    headers = {"Authorization": f"Bearer {ONLYFANS_API_KEY}"}
    with httpx.Client(headers=headers, timeout=60) as c:
        with open(file_path, "rb") as f:
            resp = c.post(_url("/media/upload"), files={"file": f})
        resp.raise_for_status()
        return resp.json()["prefixed_id"]


def upload_media_from_url(url: str) -> str:
    """Upload media via URL (up to 1 GB). Returns prefixed media ID."""
    with _client() as c:
        resp = c.post(_url("/media/upload"), json={"file_url": url})
        resp.raise_for_status()
        return resp.json()["prefixed_id"]


# ── Feed posts ────────────────────────────────────────────────────────────────

def create_post(caption: str, media_ids: list[str] | None = None) -> dict:
    full_text = f"{AI_DISCLOSURE}\n\n{caption}"
    payload: dict = {"text": full_text}
    if media_ids:
        payload["mediaFiles"] = media_ids
    with _client() as c:
        resp = c.post(_url("/posts"), json=payload)
        resp.raise_for_status()
        return resp.json()


def send_mass_message(text: str, media_ids: list[str] | None = None, price_cents: int = 0) -> dict:
    """Send a PPV mass message to all subscribers."""
    full_text = f"{AI_DISCLOSURE}\n\n{text}"
    payload: dict = {"text": full_text}
    if media_ids:
        payload["mediaFiles"] = media_ids
    if price_cents:
        payload["price"] = price_cents / 100
    with _client() as c:
        resp = c.post(_url("/messages/mass"), json=payload)
        resp.raise_for_status()
        return resp.json()


# ── Fans / subscribers ────────────────────────────────────────────────────────

def get_fans(limit: int = 100) -> list[dict]:
    with _client() as c:
        resp = c.get(_url("/fans/active"), params={"limit": limit})
        resp.raise_for_status()
        body = resp.json()
        return body.get("data", {}).get("list", body.get("data", []))


def get_fan_info(fan_id: str) -> dict:
    with _client() as c:
        resp = c.get(_url(f"/fans/{fan_id}"))
        resp.raise_for_status()
        return resp.json()
