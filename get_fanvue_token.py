"""
Fanvue OAuth flow — gets access token + creator UUID and saves to .env
Run this once. Keep Chrome open and logged into Fanvue.
"""
import base64
import hashlib
import json
import os
import secrets
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import httpx

CLIENT_ID     = "4de60145-5172-45e2-93e0-7478f54f1bc7"
CLIENT_SECRET = "ed7905fa04396dd9dc2e6890d68ac911d4a240a422e4b7bc65f5fbaa2bca41d6"
REDIRECT_URI  = "http://localhost:8765/callback"
AUTH_URL      = "https://auth.fanvue.com/oauth2/auth"
TOKEN_URL     = "https://auth.fanvue.com/oauth2/token"
SCOPES        = "openid offline_access read:self read:chat write:chat read:fan read:creator write:creator read:media write:media read:post write:post"
API_VERSION   = "2025-06-26"

# PKCE
code_verifier  = secrets.token_urlsafe(64)
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode()).digest()
).rstrip(b"=").decode()
state = secrets.token_urlsafe(16)

captured = {}


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = dict(urllib.parse.parse_qsl(parsed.query))
        captured.update(params)
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h2>Authorization complete. You can close this tab.</h2>")

    def log_message(self, *args):
        pass


def run():
    params = {
        "client_id":             CLIENT_ID,
        "redirect_uri":          REDIRECT_URI,
        "response_type":         "code",
        "scope":                 SCOPES,
        "state":                 state,
        "code_challenge":        code_challenge,
        "code_challenge_method": "S256",
    }
    auth_url = AUTH_URL + "?" + urllib.parse.urlencode(params)

    print("Opening Fanvue authorization page in your browser...")
    print("Log in if prompted, then click Authorize.\n")
    webbrowser.open(auth_url)

    print("Waiting for callback on http://localhost:8765/callback ...")
    server = HTTPServer(("localhost", 8765), CallbackHandler)
    server.handle_request()

    if "error" in captured:
        print("Authorization error:", captured)
        return

    code = captured.get("code")
    if not code:
        print("No code received:", captured)
        return

    print("Got authorization code. Exchanging for tokens...")
    resp = httpx.post(
        TOKEN_URL,
        data={
            "grant_type":    "authorization_code",
            "code":          code,
            "redirect_uri":  REDIRECT_URI,
            "code_verifier": code_verifier,
        },
        auth=(CLIENT_ID, CLIENT_SECRET),
    )
    resp.raise_for_status()
    tokens = resp.json()
    access_token  = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token", "")

    print(f"\nAccess token:  {access_token[:40]}...")
    if refresh_token:
        print(f"Refresh token: {refresh_token[:40]}...")

    # Get creator UUID
    print("\nFetching creator UUID from /users/me...")
    me = httpx.get(
        "https://api.fanvue.com/users/me",
        headers={
            "Authorization":      f"Bearer {access_token}",
            "X-Fanvue-API-Version": API_VERSION,
        }
    )
    print(f"Status: {me.status_code}")
    me_data = me.json() if me.status_code == 200 else {}
    print(json.dumps(me_data, indent=2))
    creator_uuid = me_data.get("uuid", "")

    # Write to .env
    env_path = Path(".env")
    env_text = env_path.read_text() if env_path.exists() else ""

    def set_env(text, key, value):
        import re
        if re.search(rf"^{key}=", text, re.MULTILINE):
            return re.sub(rf"^{key}=.*$", f"{key}={value}", text, flags=re.MULTILINE)
        return text + f"\n{key}={value}"

    env_text = set_env(env_text, "FANVUE_ACCESS_TOKEN",  access_token)
    env_text = set_env(env_text, "FANVUE_REFRESH_TOKEN", refresh_token)
    env_text = set_env(env_text, "FANVUE_CREATOR_UUID",  creator_uuid)
    env_path.write_text(env_text)

    print(f"\nSaved to .env:")
    print(f"  FANVUE_ACCESS_TOKEN  = {access_token[:40]}...")
    print(f"  FANVUE_CREATOR_UUID  = {creator_uuid}")
    print("\nDone.")


if __name__ == "__main__":
    run()
