import logging
import tweepy
from app.config import (
    TWITTER_API_KEY, TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET,
)

log = logging.getLogger(__name__)

_client: tweepy.Client | None = None
_api: tweepy.API | None = None


def _get_client() -> tweepy.Client:
    global _client
    if _client is None:
        _client = tweepy.Client(
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_SECRET,
        )
    return _client


def _get_api() -> tweepy.API:
    """v1.1 API — needed for media upload."""
    global _api
    if _api is None:
        auth = tweepy.OAuth1UserHandler(
            TWITTER_API_KEY, TWITTER_API_SECRET,
            TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET,
        )
        _api = tweepy.API(auth)
    return _api


def post_tweet(text: str, image_path: str | None = None) -> str:
    """Post a tweet, optionally with an image. Returns tweet URL."""
    media_ids = []

    if image_path:
        api = _get_api()
        media = api.media_upload(filename=image_path)
        media_ids.append(media.media_id)

    client = _get_client()
    kwargs: dict = {"text": text}
    if media_ids:
        kwargs["media_ids"] = media_ids

    response = client.create_tweet(**kwargs)
    tweet_id = response.data["id"]
    url = f"https://x.com/i/web/status/{tweet_id}"
    log.info("Posted tweet: %s", url)
    return url


def reply_to_tweet(tweet_id: str, text: str) -> str:
    """Reply to an existing tweet. Returns reply URL."""
    client = _get_client()
    response = client.create_tweet(text=text, in_reply_to_tweet_id=tweet_id)
    reply_id = response.data["id"]
    url = f"https://x.com/i/web/status/{reply_id}"
    log.info("Replied to tweet %s: %s", tweet_id, url)
    return url


def get_recent_mentions(max_results: int = 10) -> list[dict]:
    """Get recent mentions of the account for reply opportunities."""
    client = _get_client()
    me = client.get_me()
    mentions = client.get_users_mentions(
        id=me.data.id,
        max_results=max_results,
        tweet_fields=["author_id", "text", "created_at"],
    )
    if not mentions.data:
        return []
    return [{"id": str(t.id), "text": t.text} for t in mentions.data]
