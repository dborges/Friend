"""
One-time script to get a TikTok access token via OAuth 2.0 + PKCE.
Run after creating a TikTok developer app at developers.tiktok.com.

Requires:
- App created with Content Posting API product enabled
- Redirect URI set to http://localhost:8765/callback
- Client Key and Client Secret from the app dashboard
"""
import base64, hashlib, json, os, re, secrets, urllib.parse, webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import httpx
from dotenv import load_dotenv

load_dotenv()

CLIENT_KEY    = os.getenv("TIKTOK_CLIENT_KEY") or input("TikTok Client Key: ").strip()
CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET") or input("TikTok Client Secret: ").strip()
REDIRECT_URI  = "http://localhost:8765/callback"
SCOPE         = "user.info.basic,video.publish,video.upload"

code_verifier  = secrets.token_urlsafe(64)
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode()).digest()
).rstrip(b"=").decode()
state = secrets.token_urlsafe(16)

captured = {}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        captured.update(dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query)))
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h2>Done. You can close this tab.</h2>")
    def log_message(self, *a): pass


def run():
    auth_url = (
        "https://www.tiktok.com/v2/auth/authorize/"
        f"?client_key={CLIENT_KEY}"
        f"&scope={urllib.parse.quote(SCOPE)}"
        f"&response_type=code"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&state={state}"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
    )

    print("Opening TikTok authorization in your browser...")
    webbrowser.open(auth_url)
    print("Waiting for callback on http://localhost:8765/callback ...")
    HTTPServer(("localhost", 8765), Handler).handle_request()

    code = captured.get("code", "")
    if not code:
        print("No code received:", captured)
        return

    print("Exchanging code for tokens...")
    resp = httpx.post(
        "https://open.tiktokapis.com/v2/oauth/token/",
        data={
            "client_key":     CLIENT_KEY,
            "client_secret":  CLIENT_SECRET,
            "code":           code,
            "grant_type":     "authorization_code",
            "redirect_uri":   REDIRECT_URI,
            "code_verifier":  code_verifier,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    resp.raise_for_status()
    tokens = resp.json()
    print(json.dumps(tokens, indent=2))

    access_token  = tokens.get("access_token", "")
    refresh_token = tokens.get("refresh_token", "")
    open_id       = tokens.get("open_id", "")

    # Save to .env
    env_path = Path(".env")
    env_text = env_path.read_text() if env_path.exists() else ""

    def set_env(text, key, value):
        if re.search(rf"^{key}=", text, re.MULTILINE):
            return re.sub(rf"^{key}=.*$", f"{key}={value}", text, flags=re.MULTILINE)
        return text + f"\n{key}={value}"

    env_text = set_env(env_text, "TIKTOK_CLIENT_KEY",    CLIENT_KEY)
    env_text = set_env(env_text, "TIKTOK_CLIENT_SECRET",  CLIENT_SECRET)
    env_text = set_env(env_text, "TIKTOK_ACCESS_TOKEN",   access_token)
    env_text = set_env(env_text, "TIKTOK_REFRESH_TOKEN",  refresh_token)
    env_text = set_env(env_text, "TIKTOK_OPEN_ID",        open_id)
    env_path.write_text(env_text)

    print(f"\nSaved to .env:")
    print(f"  TIKTOK_ACCESS_TOKEN  = {access_token[:40]}...")
    print(f"  TIKTOK_OPEN_ID       = {open_id}")
    print("\nNote: access token expires in 24h. Refresh token lasts 365 days.")


if __name__ == "__main__":
    run()
