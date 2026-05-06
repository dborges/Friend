from dotenv import load_dotenv
import os

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
FANVUE_ACCESS_TOKEN = os.getenv("FANVUE_ACCESS_TOKEN", "")
FANVUE_CREATOR_UUID = os.getenv("FANVUE_CREATOR_UUID", "")
ONLYFANS_API_KEY = os.getenv("ONLYFANS_API_KEY", "")
ONLYFANS_ACCOUNT_ID = os.getenv("ONLYFANS_ACCOUNT_ID", "")  # format: acct_XXXXXXXXXXXXXXX
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
LORA_MODEL = os.getenv("LORA_MODEL", "")  # set automatically by train_lora.py
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")

POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "30"))
POST_SCHEDULE = os.getenv("POST_SCHEDULE", "09:00,15:00,21:00").split(",")
PPV_PRICE_CENTS = int(os.getenv("PPV_PRICE_CENTS", "1500"))  # $15 default

# Reddit
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USERNAME = os.getenv("REDDIT_USERNAME", "")
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "Friend/1.0")
REDDIT_PROMO_SUBS = os.getenv("REDDIT_PROMO_SUBS", "OnlyFansPromotion,SFWNextDoor").split(",")
REDDIT_ORGANIC_SUBS = os.getenv("REDDIT_ORGANIC_SUBS", "relationship_advice,dating_advice").split(",")

# Threads (Meta)
THREADS_APP_ID       = os.getenv("THREADS_APP_ID", "")
THREADS_APP_SECRET   = os.getenv("THREADS_APP_SECRET", "")
THREADS_USER_ID      = os.getenv("THREADS_USER_ID", "")
THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN", "")

# TikTok
TIKTOK_CLIENT_KEY    = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")
TIKTOK_ACCESS_TOKEN  = os.getenv("TIKTOK_ACCESS_TOKEN", "")
TIKTOK_REFRESH_TOKEN = os.getenv("TIKTOK_REFRESH_TOKEN", "")
TIKTOK_OPEN_ID       = os.getenv("TIKTOK_OPEN_ID", "")

# Twitter/X
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET", "")

PROFILE_URL = os.getenv("PROFILE_URL", os.getenv("OF_PROFILE_URL", ""))

PERSONA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "persona")
GENERATED_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "generated")
os.makedirs(GENERATED_DIR, exist_ok=True)

CONVERSATION_HISTORY_LIMIT = 20
