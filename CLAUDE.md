# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app (starts FastAPI server + background scheduler)
python run.py

# App runs at http://localhost:8000
# Dashboard at http://localhost:8000/dashboard
```

## Architecture

**Friend** is an AI persona automation system. A character lives on Fanvue — Claude handles all subscriber DMs in-character, Flux generates photos, ElevenLabs generates voice messages, and APScheduler drives everything automatically.

### The 4 Persona Files (`persona/`)

The entire character is defined in these 4 markdown files. The system prompt Claude receives is assembled from all 4 at startup. Edit these to change the character — no code changes needed.

| File | Purpose |
|---|---|
| `identity.md` | Name, appearance, backstory, personality |
| `voice.md` | Texting style, how she flirts, how she gives advice |
| `knowledge.md` | Opinions, interests, topics she knows, natural references |
| `rules.md` | Content tier limits, image/voice triggers, upsell moments, crisis handling |

Call `POST /dashboard/persona/reload` (or click "Reload Persona" in the dashboard) to pick up edits without restarting the server.

### Request Flow (DM auto-reply)

```
APScheduler (every 30s)
  → fanvue.get_chats()                    # Fanvue REST API (unread chats)
  → database.is_processed()              # skip already-handled messages
  → claude.generate_reply()              # Claude builds reply from persona + history
  → flux.generate_image() [optional]     # triggered by image request keywords in message
  → elevenlabs.generate_voice() [opt]    # triggered by voice request keywords
  → fanvue.send_message_with_media()     # sends reply + any generated media
  → database.save_message()             # stores both sides of conversation
```

### Key Modules

- `app/fanvue.py` — REST client for the [Fanvue API](https://api.fanvue.com/docs). All platform interaction goes through here. Auth uses `FANVUE_ACCESS_TOKEN` (OAuth Bearer token). Chats are identified by `user.uuid`; media upload uses a multipart session flow.
- `app/claude.py` — Generates DM replies and feed captions. Also detects image/voice trigger phrases via regex.
- `app/scheduler.py` — Two jobs: `poll_and_reply` (interval) and `post_to_feed` (cron, configurable times).
- `app/database.py` — SQLite via SQLAlchemy. Stores all messages (both directions) and feed posts. `is_processed()` prevents double-replies.
- `app/persona.py` — Assembles the system prompt from the 4 markdown files. Caches it in memory; `reload()` clears the cache.

### Environment Variables

Copy `.env.example` to `.env` and fill in:

```
ANTHROPIC_API_KEY=          # claude.ai API key
FANVUE_ACCESS_TOKEN=        # OAuth access token from Fanvue Developer Area
FANVUE_CREATOR_UUID=        # your creator user UUID (from Fanvue creator settings)
REPLICATE_API_TOKEN=        # replicate.com (Flux image generation)
ELEVENLABS_API_KEY=         # elevenlabs.io
ELEVENLABS_VOICE_ID=        # clone a voice first, paste the ID here
POLL_INTERVAL_SECONDS=30    # how often to check for new DMs
POST_SCHEDULE=09:00,15:00,21:00  # times to auto-post to feed (24h, comma-separated)
PROFILE_URL=                # your Fanvue profile URL (used in Reddit/Twitter promos)
```

### Fanvue API Notes

- API version header required on every request: `X-Fanvue-API-Version: 2025-06-26`
- Chats are keyed by subscriber `user.uuid` (not a separate chat ID)
- Messages use `uuid` field (not `id`)
- `send_message` returns `{"messageUuid": "..."}` 
- `create_post` returns `{"uuid": "..."}` 
- Media upload (`upload_media`) uses a 4-step multipart session flow — verify exact endpoint paths against the live API docs once you have credentials
- OAuth scopes needed: `read:chat`, `write:chat`, `read:fan`, `write:post`, `write:creator`, `write:media`, `read:creator`

### Content Tiers

`rules.md` defines what's allowed at each tier (`standard`, `intimate`, `premium`). Claude receives the tier in its system prompt and respects the limits defined there. Note: Fanvue's API does not currently return a subscription tier per-subscriber, so all subscribers default to `standard` until tier detection is implemented.

### Adding a New Persona

1. Edit or replace the 4 files in `persona/`
2. Hit `POST /dashboard/persona/reload` — the next Claude call uses the new character
3. Nothing else needs to change
