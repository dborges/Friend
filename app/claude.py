import re
import anthropic
from app.config import ANTHROPIC_API_KEY
from app.persona import load_system_prompt

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

IMAGE_TRIGGERS = re.compile(
    r"\b(send me a pic|can i see you|selfie|what do you look like|photo|picture of you)\b",
    re.IGNORECASE,
)
VOICE_TRIGGERS = re.compile(
    r"\b(voice note|voice message|audio|hear your voice|say that|record)\b",
    re.IGNORECASE,
)


def generate_reply(
    subscriber_name: str,
    subscriber_tier: str,
    history: list[dict],
    new_message: str,
) -> dict:
    system_prompt = load_system_prompt(subscriber_name, subscriber_tier)

    messages = history + [{"role": "user", "content": new_message}]

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        temperature=0.85,
        system=system_prompt,
        messages=messages,
    )

    reply_text = response.content[0].text.strip()

    wants_image = bool(IMAGE_TRIGGERS.search(new_message))
    wants_voice = bool(VOICE_TRIGGERS.search(new_message))

    return {
        "text": reply_text,
        "wants_image": wants_image,
        "wants_voice": wants_voice,
    }


def generate_welcome_message(subscriber_name: str) -> str:
    """Warm first DM sent the moment someone subscribes. Personal + immediate PPV hook."""
    system_prompt = load_system_prompt(subscriber_name, "standard")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=120,
        temperature=0.9,
        system=system_prompt,
        messages=[{
            "role": "user",
            "content": (
                f"Write a welcome DM to {subscriber_name or 'a new subscriber'} who just subscribed. "
                "Be warm, slightly flirty, personal — make them feel special. "
                "End with a soft tease that you have something exclusive waiting for them. "
                "2-3 sentences max. No hashtags. Sound completely natural, not like a bot."
            ),
        }],
    )
    return response.content[0].text.strip()


def generate_ppv_pitch(price_dollars: int = 15) -> str:
    """Mass PPV message — teases locked content, creates urgency."""
    system_prompt = load_system_prompt()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=150,
        temperature=0.9,
        system=system_prompt,
        messages=[{
            "role": "user",
            "content": (
                f"Write a short PPV mass message as Heather to her Fanvue subscribers. "
                f"The locked content costs ${price_dollars}. Tease what's inside without giving it away. "
                "Create a little FOMO or curiosity. 2-3 sentences. Natural, not salesy. "
                "No hashtags. End with something that makes them want to unlock it."
            ),
        }],
    )
    return response.content[0].text.strip()


def generate_feed_caption() -> str:
    system_prompt = load_system_prompt()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        temperature=0.9,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": (
                    "Write a short OnlyFans feed post caption as Heather. "
                    "It should feel natural and personal, like something she'd actually post. "
                    "1-3 sentences max. No hashtags."
                ),
            }
        ],
    )
    return response.content[0].text.strip()


def generate_reddit_post(subreddit: str, of_url: str) -> dict:
    """Generate a Reddit post title + body for a promo or lifestyle sub."""
    system_prompt = load_system_prompt()
    is_promo = any(x in subreddit.lower() for x in ["onlyfans", "promo", "nsfw"])

    if is_promo:
        instruction = (
            f"Write a Reddit post for r/{subreddit} as Heather promoting her OnlyFans. "
            "Write a catchy title (max 12 words) and a short body (2-3 sentences, warm and personal). "
            "End the body with a soft CTA like 'link in bio' or 'come say hi'. "
            "Do NOT include the URL in the body — it will be appended automatically. "
            "Reply with JSON: {\"title\": \"...\", \"body\": \"...\"}"
        )
    else:
        instruction = (
            f"Write a genuine Reddit comment for r/{subreddit} as Heather. "
            "She's engaging with the community naturally — sharing a thought, giving advice, or being relatable. "
            "2-4 sentences. No promotional language. Her OF link is in her Reddit bio so no need to mention it. "
            "Reply with JSON: {\"title\": \"\", \"body\": \"...\"}"
        )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=250,
        temperature=0.9,
        system=system_prompt,
        messages=[{"role": "user", "content": instruction}],
    )

    import json
    text = response.content[0].text.strip()
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return {"title": "Miami girl dropping in 🌊", "body": text}


def generate_tweet(scene_context: str = "", of_url: str = "") -> str:
    """Generate a tweet — punchy, under 240 chars, ends with OF link."""
    system_prompt = load_system_prompt()
    instruction = (
        "Write a single tweet as Heather for her Twitter/X account. "
        f"Context: {scene_context or 'a casual Miami lifestyle moment'}. "
        "Keep it under 200 characters so there's room for a link. "
        "Punchy, real, her voice. No hashtags. No emojis unless it fits naturally. "
        "Just the tweet text — no quotes, no labels."
    )
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=100,
        temperature=0.92,
        system=system_prompt,
        messages=[{"role": "user", "content": instruction}],
    )
    tweet = response.content[0].text.strip().strip('"')
    if of_url:
        tweet = f"{tweet}\n{of_url}"
    return tweet[:280]
