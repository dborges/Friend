"""
One-time script to get a Threads long-lived access token and user ID.
Run after creating a Meta app with Threads API enabled.

Steps before running:
1. Go to developers.facebook.com → Create App → Consumer or Business type
2. Add "Threads API" product to your app
3. Under Threads API → Settings, add your Instagram account as a Tester
4. Copy your App ID and App Secret below (or set in .env)
5. Set redirect URI to http://localhost:8765/callback in the app settings
6. Run this script
"""
import base64
import hashlib
import json
import os
import re
import secrets
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import httpx
from dotenv import load_dotenv

load_dotenv()

APP_ID       = os.getenv("THREADS_APP_ID") or input("Threads App ID: ").strip()
APP_SECRET   = os.getenv("THREADS_APP_SECRET") or input("Threads App Secret: ").strip()
REDIRECT_URI = "http://localhost:8765/callback"
SCOPE        = "threads_basic,threads_content_publish"

captured = {}


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
        captured.update(params)
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h2>Done. You can close this tab.</h2>")

    def log_message(self, *args):
        pass


def run():
    auth_url = (
        f"https://threads.net/oauth/authorize"
        f"?client_id={APP_ID}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&scope={SCOPE}"
        f"&response_type=code"
    )

    print("Opening Threads authorization in your browser...")
    webbrowser.open(auth_url)
    print("Waiting for callback...")

    HTTPServer(("localhost", 8765), CallbackHandler).handle_request()

    code = captured.get("code", "").split("#")[0]  # strip #_ suffix Meta sometimes adds
    if not code:
        print("No code received:", captured)
        return

    print("Exchanging code for short-lived token...")
    resp = httpx.post(
        "https://graph.threads.net/oauth/access_token",
        data={
            "client_id":     APP_ID,
            "client_secret": APP_SECRET,
            "grant_type":    "authorization_code",
            "redirect_uri":  REDIRECT_URI,
            "code":          code,
        },
    )
    resp.raise_for_status()
    data = resp.json()
    short_token = data["access_token"]
    user_id     = str(data["user_id"])
    print(f"User ID: {user_id}")

    print("Exchanging for long-lived token (60 days)...")
    resp = httpx.get(
        "https://graph.threads.net/access_token",
        params={
            "grant_type":    "th_exchange_token",
            "client_secret": APP_SECRET,
            "access_token":  short_token,
        },
    )
    resp.raise_for_status()
    long_token = resp.json()["access_token"]
    print(f"Long-lived token: {long_token[:40]}...")

    # Save to .env
    env_path = Path(".env")
    env_text = env_path.read_text() if env_path.exists() else ""

    def set_env(text, key, value):
        if re.search(rf"^{key}=", text, re.MULTILINE):
            return re.sub(rf"^{key}=.*$", f"{key}={value}", text, flags=re.MULTILINE)
        return text + f"\n{key}={value}"

    env_text = set_env(env_text, "THREADS_APP_ID",       APP_ID)
    env_text = set_env(env_text, "THREADS_APP_SECRET",   APP_SECRET)
    env_text = set_env(env_text, "THREADS_USER_ID",      user_id)
    env_text = set_env(env_text, "THREADS_ACCESS_TOKEN", long_token)
    env_path.write_text(env_text)

    print("\nSaved to .env:")
    print(f"  THREADS_USER_ID      = {user_id}")
    print(f"  THREADS_ACCESS_TOKEN = {long_token[:40]}...")
    print("\nToken expires in 60 days. Re-run this script to refresh.")


if __name__ == "__main__":
    run()
