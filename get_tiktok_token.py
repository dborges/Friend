"""
TikTok OAuth token flow using ngrok for a public HTTPS redirect URI.
pyngrok opens a tunnel so TikTok can redirect to our local server.
"""
import base64, hashlib, json, os, re, secrets, urllib.parse, webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import httpx
from dotenv import load_dotenv
from pyngrok import ngrok

load_dotenv()

CLIENT_KEY    = os.getenv("TIKTOK_CLIENT_KEY", "sbaw9oj5r7r20q3tsb")
CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "zzjT2AUhLoRzfHN7y4IYVrTr8kSybPUx")
LOCAL_PORT    = 8765
SCOPE         = "user.info.basic"

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
        self.wfile.write(b"<h2>Authorized! You can close this tab.</h2>")
    def log_message(self, *a): pass


def run():
    # Start ngrok tunnel
    print("Starting ngrok tunnel...")
    tunnel = ngrok.connect(LOCAL_PORT, "http")
    public_url = tunnel.public_url.replace("http://", "https://")
    REDIRECT_URI = f"{public_url}/callback"
    print(f"Public redirect URI: {REDIRECT_URI}")
    print()
    print(">>> ADD THIS AS YOUR REDIRECT URI IN THE TIKTOK PORTAL <<<")
    print(REDIRECT_URI)
    print()
    print("You have 90 seconds to add it to the portal before the browser opens...")
    import time; time.sleep(90)

    auth_url = (
        "https://www.tiktok.com/v2/auth/authorize/"
        f"?client_key={CLIENT_KEY}"
        f"&scope={urllib.parse.quote(SCOPE, safe='')}"
        f"&response_type=code"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI, safe='')}"
        f"&state={state}"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
    )

    print("Opening browser...")
    webbrowser.open(auth_url)
    print("Waiting for TikTok callback...")

    HTTPServer(("localhost", LOCAL_PORT), Handler).handle_request()

    code = captured.get("code", "")
    if not code:
        print("No code received:", captured)
        ngrok.kill()
        return

    print(f"Got authorization code!")
    ngrok.kill()

    print("Exchanging for tokens...")
    resp = httpx.post(
        "https://open.tiktokapis.com/v2/oauth/token/",
        data={
            "client_key":    CLIENT_KEY,
            "client_secret": CLIENT_SECRET,
            "code":          code,
            "grant_type":    "authorization_code",
            "redirect_uri":  REDIRECT_URI,
            "code_verifier": code_verifier,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    print(f"Response ({resp.status_code}):", resp.text)

    tokens = resp.json()
    access_token  = tokens.get("access_token", "")
    refresh_token = tokens.get("refresh_token", "")
    open_id       = tokens.get("open_id", "")

    if not access_token:
        print("No access token in response.")
        return

    env_path = Path(".env")
    env_text = env_path.read_text() if env_path.exists() else ""

    def set_env(text, key, value):
        if re.search(rf"^{key}=", text, re.MULTILINE):
            return re.sub(rf"^{key}=.*$", f"{key}={value}", text, flags=re.MULTILINE)
        return text + f"\n{key}={value}"

    env_text = set_env(env_text, "TIKTOK_ACCESS_TOKEN",  access_token)
    env_text = set_env(env_text, "TIKTOK_REFRESH_TOKEN", refresh_token)
    env_text = set_env(env_text, "TIKTOK_OPEN_ID",       open_id)
    env_path.write_text(env_text)

    print(f"\nSaved to .env:")
    print(f"  TIKTOK_ACCESS_TOKEN = {access_token[:40]}...")
    print(f"  TIKTOK_OPEN_ID      = {open_id}")
    print("\nDone!")


if __name__ == "__main__":
    run()
