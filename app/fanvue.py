import mimetypes
import httpx
from app.config import FANVUE_ACCESS_TOKEN, FANVUE_CREATOR_UUID

BASE_URL = "https://api.fanvue.com"
API_VERSION = "2025-06-26"

_HEADERS = {
    "Authorization": f"Bearer {FANVUE_ACCESS_TOKEN}",
    "X-Fanvue-API-Version": API_VERSION,
    "Content-Type": "application/json",
}


def _client() -> httpx.Client:
    return httpx.Client(headers=_HEADERS, timeout=30)


# ── Chats / DMs ───────────────────────────────────────────────────────────────

def get_chats(limit: int = 50) -> list[dict]:
    """Return unread chats, newest first."""
    with _client() as c:
        resp = c.get(f"{BASE_URL}/chats", params={"filter": "unread", "size": min(limit, 50)})
        resp.raise_for_status()
        return resp.json().get("data", [])


def get_chat_messages(user_uuid: str, limit: int = 20) -> list[dict]:
    with _client() as c:
        resp = c.get(
            f"{BASE_URL}/chats/{user_uuid}/messages",
            params={"size": min(limit, 50)},
        )
        resp.raise_for_status()
        return resp.json().get("data", [])


def send_message(user_uuid: str, text: str) -> dict:
    with _client() as c:
        resp = c.post(f"{BASE_URL}/chats/{user_uuid}/message", json={"text": text})
        resp.raise_for_status()
        return resp.json()


def send_message_with_media(user_uuid: str, text: str, media_uuids: list[str]) -> dict:
    with _client() as c:
        resp = c.post(
            f"{BASE_URL}/chats/{user_uuid}/message",
            json={"text": text, "mediaUuids": media_uuids},
        )
        resp.raise_for_status()
        return resp.json()


# ── Media upload ──────────────────────────────────────────────────────────────

def upload_media(file_path: str) -> str:
    """
    Upload a local file via Fanvue's multipart session flow.
    Returns the media UUID to use in messages/posts.

    Endpoint paths are based on the documented flow — verify exact paths
    against https://api.fanvue.com/docs/api-reference/reference/media/ once
    you have API access and can hit a live account.
    """
    mime = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

    with _client() as c:
        # Step 1: create upload session
        resp = c.post(
            f"{BASE_URL}/creators/{FANVUE_CREATOR_UUID}/media/upload-sessions",
            json={"mimeType": mime},
        )
        resp.raise_for_status()
        session = resp.json()
        session_id = session.get("sessionId") or session.get("uuid")

        # Step 2: get signed URL for part 1
        resp = c.get(
            f"{BASE_URL}/creators/{FANVUE_CREATOR_UUID}/media/upload-sessions/{session_id}/parts/1",
        )
        resp.raise_for_status()
        signed_url = resp.json()["signedUrl"]

    # Step 3: upload bytes directly to the signed URL (no auth headers)
    with open(file_path, "rb") as f:
        put_resp = httpx.put(
            signed_url,
            content=f,
            headers={"Content-Type": mime},
            timeout=120,
        )
    put_resp.raise_for_status()

    # Step 4: complete the session
    with _client() as c:
        resp = c.post(
            f"{BASE_URL}/creators/{FANVUE_CREATOR_UUID}/media/upload-sessions/{session_id}/complete",
        )
        resp.raise_for_status()
        result = resp.json()
        return result.get("mediaUuid") or result.get("uuid")


# ── Feed posts ────────────────────────────────────────────────────────────────

def create_post(caption: str, media_uuids: list[str] | None = None) -> dict:
    payload: dict = {"text": caption, "audience": "subscribers"}
    if media_uuids:
        payload["mediaUuids"] = media_uuids
    with _client() as c:
        resp = c.post(f"{BASE_URL}/creators/{FANVUE_CREATOR_UUID}/posts", json=payload)
        resp.raise_for_status()
        return resp.json()


# ── Fans / subscribers ────────────────────────────────────────────────────────

def get_fans(limit: int = 100) -> list[dict]:
    with _client() as c:
        resp = c.get(f"{BASE_URL}/subscribers", params={"size": min(limit, 50)})
        resp.raise_for_status()
        return resp.json().get("data", [])
