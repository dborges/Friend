"""
Fanvue site explorer — logs in and captures screenshots + page structure
so we understand the UI before building automation.

Usage:
    python explore_fanvue.py <email> <password>
"""
import sys
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path("fanvue_explore")
OUTPUT_DIR.mkdir(exist_ok=True)


def snap(page, name: str):
    path = OUTPUT_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"  [screenshot] {path}")


def dump_network(responses: list, name: str):
    path = OUTPUT_DIR / f"{name}_network.json"
    path.write_text(json.dumps(responses, indent=2))
    print(f"  [network]    {path}")


def explore():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=False, slow_mo=300)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()

        api_calls = []

        def on_response(resp):
            if "fanvue.com" in resp.url and resp.request.resource_type == "fetch":
                try:
                    body = resp.json()
                except Exception:
                    body = None
                api_calls.append({
                    "url": resp.url,
                    "method": resp.request.method,
                    "status": resp.status,
                    "body": body,
                })

        page.on("response", on_response)

        # ── Login via Google OAuth ─────────────────────────────────────────────
        print("\n[1] Opening Fanvue...")
        page.goto("https://www.fanvue.com")
        page.wait_for_load_state("networkidle")
        snap(page, "01_home")

        print("\n--- ACTION REQUIRED ---")
        print("Sign in with Google in the browser window.")
        print("When you are fully logged in, click RESUME in the Playwright inspector.\n")
        page.pause()  # opens inspector with a Resume button

        page.wait_for_load_state("networkidle")
        snap(page, "03_after_login")
        print(f"     URL after login: {page.url}")

        # ── Dashboard / home ───────────────────────────────────────────────────
        print("[3] Navigating to creator dashboard...")
        page.goto("https://fanvue.com/creator/dashboard")
        page.wait_for_load_state("networkidle")
        snap(page, "04_dashboard")

        # ── Messages / inbox ───────────────────────────────────────────────────
        print("[4] Opening messages...")
        page.goto("https://fanvue.com/creator/messages")
        page.wait_for_load_state("networkidle")
        snap(page, "05_messages_inbox")

        # Open first conversation if any
        first_chat = page.locator("[data-testid='chat-item'], .chat-item, [class*='conversation']").first
        if first_chat.count() > 0:
            first_chat.click()
            page.wait_for_load_state("networkidle")
            snap(page, "06_open_conversation")
        else:
            print("     (no conversations visible)")

        # ── Settings / API ─────────────────────────────────────────────────────
        print("[5] Checking settings for API keys...")
        for url in [
            "https://fanvue.com/creator/settings",
            "https://fanvue.com/creator/settings/api",
            "https://fanvue.com/settings/api",
        ]:
            page.goto(url)
            page.wait_for_load_state("networkidle")
            slug = url.split("/")[-1] or "settings"
            snap(page, f"07_settings_{slug}")

        # ── Capture user UUID from /users/me ───────────────────────────────────
        print("[6] Fetching /users/me to get creator UUID...")
        me = page.evaluate("""async () => {
            const r = await fetch('https://api.fanvue.com/users/me', {
                headers: { 'X-Fanvue-API-Version': '2025-06-26' },
                credentials: 'include'
            });
            return { status: r.status, body: await r.json().catch(() => null) };
        }""")
        print(f"     /users/me → status {me['status']}")
        print(f"     body: {json.dumps(me['body'], indent=2)}")
        (OUTPUT_DIR / "users_me.json").write_text(json.dumps(me, indent=2))

        # ── Dump all captured API calls ────────────────────────────────────────
        dump_network(api_calls, "session")

        print("\nDone. Screenshots and API responses saved to ./fanvue_explore/")
        print("Check users_me.json for your creator UUID.\n")

        input("Press Enter to close the browser...")
        browser.close()


if __name__ == "__main__":
    explore()
