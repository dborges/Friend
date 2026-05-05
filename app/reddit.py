import logging
import praw
from app.config import (
    REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET,
    REDDIT_USERNAME, REDDIT_PASSWORD, REDDIT_USER_AGENT,
    OF_PROFILE_URL,
)

log = logging.getLogger(__name__)

_reddit: praw.Reddit | None = None


def _client() -> praw.Reddit:
    global _reddit
    if _reddit is None:
        _reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            username=REDDIT_USERNAME,
            password=REDDIT_PASSWORD,
            user_agent=REDDIT_USER_AGENT,
        )
    return _reddit


def post_image_to_sub(subreddit: str, title: str, image_path: str) -> str:
    """Submit an image post. Returns the post URL."""
    r = _client()
    sub = r.subreddit(subreddit)
    submission = sub.submit_image(title=title, image_path=image_path)
    log.info("Posted to r/%s: %s", subreddit, submission.url)
    return submission.url


def post_link_to_sub(subreddit: str, title: str, body: str) -> str:
    """Submit a text post with OF link in body. Returns the post URL."""
    r = _client()
    sub = r.subreddit(subreddit)
    full_body = f"{body}\n\n{OF_PROFILE_URL}"
    submission = sub.submit(title=title, selftext=full_body)
    log.info("Posted text to r/%s: %s", subreddit, submission.url)
    return submission.url


def comment_on_top_post(subreddit: str, comment_text: str) -> str | None:
    """Find a recent post in subreddit and leave a comment as Heather. Returns comment URL."""
    r = _client()
    sub = r.subreddit(subreddit)
    for post in sub.hot(limit=10):
        if post.locked or post.archived:
            continue
        comment = post.reply(comment_text)
        log.info("Commented on r/%s post '%s'", subreddit, post.title[:50])
        return f"https://reddit.com{comment.permalink}"
    return None


def get_account_karma() -> dict:
    r = _client()
    me = r.user.me()
    return {"link_karma": me.link_karma, "comment_karma": me.comment_karma}
