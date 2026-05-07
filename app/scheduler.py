import logging
import random
from apscheduler.schedulers.background import BackgroundScheduler
from app import fanvue, claude, flux, elevenlabs, video as video_mod
from app.database import (
    SessionLocal, get_conversation_history, save_message, is_processed, SocialPost,
    upsert_subscriber, get_unwelcomed, mark_welcome_sent, get_segment, set_segment,
)
from app.config import (
    POLL_INTERVAL_SECONDS, POST_SCHEDULE, PPV_PRICE_CENTS,
    REDDIT_CLIENT_ID, REDDIT_PROMO_SUBS, REDDIT_ORGANIC_SUBS,
    TWITTER_API_KEY, THREADS_ACCESS_TOKEN, TIKTOK_ACCESS_TOKEN, PROFILE_URL,
    ONLYFANS_API_KEY,
)

log = logging.getLogger(__name__)


def poll_and_reply():
    db = SessionLocal()
    try:
        chats = fanvue.get_chats()
        for chat in chats:
            user = chat.get("user", {})
            subscriber_id = user.get("uuid", "")
            subscriber_name = user.get("displayName") or user.get("handle", "")
            subscriber_tier = "standard"

            if not subscriber_id:
                continue

            upsert_subscriber(db, subscriber_id, user.get("handle", ""), subscriber_name)
            segment = get_segment(db, subscriber_id)
            subscriber_tier = "premium" if segment == "whale" else "standard"

            messages = fanvue.get_chat_messages(subscriber_id, limit=1)
            if not messages:
                continue

            latest = messages[0]
            message_id = str(latest.get("uuid", ""))
            content = (latest.get("text") or "").strip()

            if not content:
                continue
            if is_processed(db, message_id):
                continue

            save_message(db, message_id, subscriber_id, subscriber_name,
                         subscriber_tier, "user", content)

            history = get_conversation_history(db, subscriber_id)
            result = claude.generate_reply(subscriber_name, subscriber_tier, history[:-1], content)

            reply_text = result["text"]
            media_ids: list[str] = []

            if result["wants_video"]:
                try:
                    image_path = flux.generate_image()
                    video_path = video_mod.generate_video(image_path)
                    media_id = fanvue.upload_media(video_path)
                    media_ids.append(media_id)
                except Exception as e:
                    log.error("Video generation failed: %s", e)
            elif result["wants_image"]:
                try:
                    image_path = flux.generate_image()
                    media_id = fanvue.upload_media(image_path)
                    media_ids.append(media_id)
                except Exception as e:
                    log.error("Image generation failed: %s", e)

            if result["wants_voice"]:
                try:
                    audio_path = elevenlabs.generate_voice(reply_text)
                    media_id = fanvue.upload_media(audio_path)
                    media_ids.append(media_id)
                except Exception as e:
                    log.error("Voice generation failed: %s", e)

            try:
                if media_ids:
                    sent = fanvue.send_message_with_media(subscriber_id, reply_text, media_ids)
                else:
                    sent = fanvue.send_message(subscriber_id, reply_text)

                reply_id = str(sent.get("messageUuid", f"reply_{message_id}"))
                save_message(db, reply_id, subscriber_id, subscriber_name,
                             subscriber_tier, "assistant", reply_text)
                log.info("Replied to %s (%s)", subscriber_name, subscriber_id)
            except Exception as e:
                log.error("Failed to send reply to %s: %s", subscriber_id, e)

    except Exception as e:
        log.error("Poll cycle error: %s", e)
    finally:
        db.close()


def post_to_feed():
    try:
        caption = claude.generate_feed_caption()
        image_path = flux.generate_image("lifestyle photo, Miami, golden hour, casual and candid")
        media_id = fanvue.upload_media(image_path)
        result = fanvue.create_post(caption, [media_id])
        log.info("Posted to feed: %s", result.get("uuid"))
    except Exception as e:
        log.error("Feed post failed: %s", e)


def post_to_reddit_promo():
    if not REDDIT_CLIENT_ID:
        return
    try:
        from app import reddit
        sub = random.choice(REDDIT_PROMO_SUBS)
        image_path = flux.generate_image("lifestyle photo, Miami beach, candid, natural light")
        post_data = claude.generate_reddit_post(sub, PROFILE_URL)
        url = reddit.post_image_to_sub(sub, post_data["title"], image_path)
        db = SessionLocal()
        try:
            db.add(SocialPost(platform="reddit", subreddit=sub, post_url=url,
                              caption=post_data["title"], image_path=image_path))
            db.commit()
        finally:
            db.close()
        log.info("Reddit promo posted to r/%s: %s", sub, url)
    except Exception as e:
        log.error("Reddit promo failed: %s", e)


def comment_on_reddit_organic():
    if not REDDIT_CLIENT_ID:
        return
    try:
        from app import reddit
        sub = random.choice(REDDIT_ORGANIC_SUBS)
        post_data = claude.generate_reddit_post(sub, PROFILE_URL)
        url = reddit.comment_on_top_post(sub, post_data["body"])
        if url:
            db = SessionLocal()
            try:
                db.add(SocialPost(platform="reddit", subreddit=sub, post_url=url,
                                  caption=post_data["body"]))
                db.commit()
            finally:
                db.close()
            log.info("Reddit organic comment on r/%s: %s", sub, url)
    except Exception as e:
        log.error("Reddit organic comment failed: %s", e)


def post_to_twitter():
    if not TWITTER_API_KEY:
        return
    try:
        from app import twitter
        scenes = [
            "morning yoga on a Miami balcony",
            "beach afternoon in Miami",
            "freelance design work from home",
            "sunset walk on the boardwalk",
            "cozy morning coffee",
        ]
        scene = random.choice(scenes)
        image_path = flux.generate_image(f"lifestyle photo, {scene}, natural light, candid")
        tweet_text = claude.generate_tweet(scene, PROFILE_URL)
        url = twitter.post_tweet(tweet_text, image_path)
        db = SessionLocal()
        try:
            db.add(SocialPost(platform="twitter", post_url=url,
                              caption=tweet_text, image_path=image_path))
            db.commit()
        finally:
            db.close()
        log.info("Tweet posted: %s", url)
    except Exception as e:
        log.error("Twitter post failed: %s", e)


def welcome_new_subscribers():
    """Detect new subscribers and send a personal welcome DM with a PPV hook."""
    db = SessionLocal()
    try:
        fans = fanvue.get_fans(limit=50)
        for fan in fans:
            uuid = fan.get("uuid", "")
            handle = fan.get("handle", "")
            name = fan.get("displayName") or handle
            if not uuid:
                continue
            upsert_subscriber(db, uuid, handle, name)

        unwelcomed = get_unwelcomed(db)
        for sub in unwelcomed:
            try:
                msg = claude.generate_welcome_message(sub.display_name or sub.handle)
                fanvue.send_message(sub.subscriber_uuid, msg)
                mark_welcome_sent(db, sub.subscriber_uuid)
                log.info("Welcome sent to %s (%s)", sub.display_name, sub.subscriber_uuid)
            except Exception as e:
                log.error("Failed to welcome %s: %s", sub.subscriber_uuid, e)
    except Exception as e:
        log.error("welcome_new_subscribers error: %s", e)
    finally:
        db.close()


def send_ppv_blast():
    """Send a locked PPV mass message to all subscribers (2x/week)."""
    try:
        price_dollars = PPV_PRICE_CENTS // 100
        text = claude.generate_ppv_pitch(price_dollars)
        image_path = flux.generate_image("intimate lifestyle photo, soft lighting, Miami apartment")
        media_uuid = fanvue.upload_media(image_path)
        result = fanvue.send_mass_message(text, media_uuids=[media_uuid], price_cents=PPV_PRICE_CENTS)
        log.info("PPV blast sent: %s", result)
    except Exception as e:
        log.error("PPV blast failed: %s", e)


def post_to_tiktok():
    if not TIKTOK_ACCESS_TOKEN:
        return
    try:
        from app import tiktok, video as video_mod
        scenes = [
            "morning yoga on a Miami balcony",
            "iced coffee walk in Wynwood",
            "beach day golden hour",
            "sunset drive, windows down",
            "getting ready, bathroom mirror selfie",
        ]
        scene = random.choice(scenes)
        caption = claude.generate_tiktok_caption(scene, PROFILE_URL)
        image_path = flux.generate_image(f"lifestyle photo, {scene}, natural light, candid")
        video_path = video_mod.image_to_video(image_path, duration=8)
        publish_id = tiktok.post_video(video_path, caption, privacy="PUBLIC_TO_EVERYONE")
        db = SessionLocal()
        try:
            db.add(SocialPost(platform="tiktok", post_url=publish_id, caption=caption))
            db.commit()
        finally:
            db.close()
        log.info("TikTok posted: %s", publish_id)
    except Exception as e:
        log.error("TikTok post failed: %s", e)


def post_to_threads():
    if not THREADS_ACCESS_TOKEN:
        return
    try:
        from app import threads
        scenes = [
            "morning yoga on the Miami balcony",
            "iced coffee and laptop at a local cafe",
            "sunset walk on the boardwalk",
            "beach afternoon, golden hour",
            "cozy night in, candles and a show",
        ]
        scene = random.choice(scenes)
        text = claude.generate_threads_post(scene, PROFILE_URL)
        _, image_url = flux.generate_image_url(f"lifestyle photo, {scene}, natural light, candid")
        post_id = threads.post_image(image_url, text)
        db = SessionLocal()
        try:
            db.add(SocialPost(platform="threads", post_url=post_id, caption=text))
            db.commit()
        finally:
            db.close()
        log.info("Threads post published: %s", post_id)
    except Exception as e:
        log.error("Threads post failed: %s", e)


def poll_and_reply_onlyfans():
    if not ONLYFANS_API_KEY:
        return
    db = SessionLocal()
    try:
        from app import onlyfans
        chats = onlyfans.get_chats()
        for chat in chats:
            chat_id = str(chat.get("id") or chat.get("userId") or chat.get("fan_id", ""))
            subscriber_name = (
                chat.get("userName") or chat.get("name") or chat.get("username", "")
            )
            if not chat_id:
                continue

            upsert_subscriber(db, chat_id, subscriber_name, subscriber_name)
            segment = get_segment(db, chat_id)
            subscriber_tier = "premium" if segment == "whale" else "standard"

            messages = onlyfans.get_chat_messages(chat_id, limit=1)
            if not messages:
                continue

            latest = messages[0]
            message_id = f"of_{chat_id}_{latest.get('id') or latest.get('message_id', '')}"
            content = (latest.get("text") or latest.get("content") or "").strip()

            if not content:
                continue
            if is_processed(db, message_id):
                continue

            save_message(db, message_id, chat_id, subscriber_name,
                         subscriber_tier, "user", content)

            history = get_conversation_history(db, chat_id)
            result = claude.generate_reply(subscriber_name, subscriber_tier, history[:-1], content)
            reply_text = result["text"]
            media_ids: list[str] = []

            if result["wants_video"]:
                try:
                    image_path = flux.generate_image()
                    video_path = video_mod.generate_video(image_path)
                    media_ids.append(onlyfans.upload_media(video_path))
                except Exception as e:
                    log.error("OF video generation failed: %s", e)
            elif result["wants_image"]:
                try:
                    image_path = flux.generate_image()
                    media_ids.append(onlyfans.upload_media(image_path))
                except Exception as e:
                    log.error("OF image generation failed: %s", e)

            if result["wants_voice"]:
                try:
                    audio_path = elevenlabs.generate_voice(reply_text)
                    media_ids.append(onlyfans.upload_media(audio_path))
                except Exception as e:
                    log.error("OF voice generation failed: %s", e)

            try:
                if media_ids:
                    sent = onlyfans.send_message_with_media(chat_id, reply_text, media_ids)
                else:
                    sent = onlyfans.send_message(chat_id, reply_text)
                reply_id = f"of_reply_{message_id}"
                save_message(db, reply_id, chat_id, subscriber_name,
                             subscriber_tier, "assistant", reply_text)
                log.info("OF replied to %s", subscriber_name)
            except Exception as e:
                log.error("OF failed to send reply to %s: %s", chat_id, e)

    except Exception as e:
        log.error("OF poll cycle error: %s", e)
    finally:
        db.close()


def welcome_new_onlyfans_subscribers():
    if not ONLYFANS_API_KEY:
        return
    db = SessionLocal()
    try:
        from app import onlyfans
        fans = onlyfans.get_fans(limit=50)
        for fan in fans:
            fan_id = str(fan.get("id") or fan.get("userId", ""))
            handle = fan.get("username") or fan.get("name", "")
            name = fan.get("name") or handle
            if not fan_id:
                continue
            upsert_subscriber(db, fan_id, handle, name)

        unwelcomed = get_unwelcomed(db)
        for sub in unwelcomed:
            try:
                msg = claude.generate_welcome_message(sub.display_name or sub.handle)
                onlyfans.send_message(sub.subscriber_uuid, msg)
                mark_welcome_sent(db, sub.subscriber_uuid)
                log.info("OF welcome sent to %s", sub.display_name)
            except Exception as e:
                log.error("OF failed to welcome %s: %s", sub.subscriber_uuid, e)
    except Exception as e:
        log.error("OF welcome_new_subscribers error: %s", e)
    finally:
        db.close()


def post_to_onlyfans_feed():
    if not ONLYFANS_API_KEY:
        return
    try:
        from app import onlyfans
        caption = claude.generate_feed_caption()
        image_path = flux.generate_image("lifestyle photo, Miami, golden hour, casual and candid")
        media_id = onlyfans.upload_media(image_path)
        result = onlyfans.create_post(caption, [media_id])
        log.info("Posted to OnlyFans feed: %s", result)
    except Exception as e:
        log.error("OnlyFans feed post failed: %s", e)


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()

    scheduler.add_job(poll_and_reply, "interval", seconds=POLL_INTERVAL_SECONDS, id="dm_poller")
    scheduler.add_job(welcome_new_subscribers, "interval", minutes=5, id="welcome_poller")

    # PPV blast — Wednesday and Saturday at 7pm
    scheduler.add_job(send_ppv_blast, "cron", day_of_week="wed,sat", hour=19, minute=0, id="ppv_blast")

    for time_str in POST_SCHEDULE:
        hour, minute = time_str.strip().split(":")
        scheduler.add_job(
            post_to_feed,
            "cron",
            hour=int(hour),
            minute=int(minute),
            id=f"feed_post_{time_str.replace(':', '')}",
        )

    # Reddit promo — 2x/day (10am + 6pm)
    if REDDIT_CLIENT_ID:
        scheduler.add_job(post_to_reddit_promo, "cron", hour=10, minute=0, id="reddit_promo_am")
        scheduler.add_job(post_to_reddit_promo, "cron", hour=18, minute=0, id="reddit_promo_pm")
        # Organic comments — 3x/day
        scheduler.add_job(comment_on_reddit_organic, "cron", hour=9,  minute=30, id="reddit_organic_1")
        scheduler.add_job(comment_on_reddit_organic, "cron", hour=14, minute=0,  id="reddit_organic_2")
        scheduler.add_job(comment_on_reddit_organic, "cron", hour=20, minute=0,  id="reddit_organic_3")
        log.info("Reddit jobs scheduled")

    # TikTok — 3x/day (10am, 3pm, 9pm)
    if TIKTOK_ACCESS_TOKEN:
        scheduler.add_job(post_to_tiktok, "cron", hour=10, minute=0,  id="tiktok_1")
        scheduler.add_job(post_to_tiktok, "cron", hour=15, minute=0,  id="tiktok_2")
        scheduler.add_job(post_to_tiktok, "cron", hour=21, minute=0,  id="tiktok_3")
        log.info("TikTok jobs scheduled")

    # Threads — 3x/day (9am, 2pm, 8pm)
    if THREADS_ACCESS_TOKEN:
        scheduler.add_job(post_to_threads, "cron", hour=9,  minute=0,  id="threads_1")
        scheduler.add_job(post_to_threads, "cron", hour=14, minute=0,  id="threads_2")
        scheduler.add_job(post_to_threads, "cron", hour=20, minute=0,  id="threads_3")
        log.info("Threads jobs scheduled")

    # Twitter — 3x/day (8am, 1pm, 8pm)
    if TWITTER_API_KEY:
        scheduler.add_job(post_to_twitter, "cron", hour=8,  minute=0,  id="twitter_1")
        scheduler.add_job(post_to_twitter, "cron", hour=13, minute=0,  id="twitter_2")
        scheduler.add_job(post_to_twitter, "cron", hour=20, minute=30, id="twitter_3")
        log.info("Twitter jobs scheduled")

    # OnlyFans — DM polling, welcome flow, feed posts (offset from Fanvue times)
    if ONLYFANS_API_KEY:
        scheduler.add_job(poll_and_reply_onlyfans, "interval", seconds=POLL_INTERVAL_SECONDS, id="of_dm_poller")
        scheduler.add_job(welcome_new_onlyfans_subscribers, "interval", minutes=5, id="of_welcome_poller")
        scheduler.add_job(post_to_onlyfans_feed, "cron", hour=10, minute=30, id="of_feed_1")
        scheduler.add_job(post_to_onlyfans_feed, "cron", hour=16, minute=0,  id="of_feed_2")
        scheduler.add_job(post_to_onlyfans_feed, "cron", hour=21, minute=30, id="of_feed_3")
        log.info("OnlyFans jobs scheduled")

    scheduler.start()
    log.info("Scheduler started — polling every %ds, posting at %s", POLL_INTERVAL_SECONDS, POST_SCHEDULE)
    return scheduler
