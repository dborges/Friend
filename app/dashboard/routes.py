from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db, Message, Post, SocialPost
from app import onlyfans, persona
import os

router = APIRouter()
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    recent_messages = (
        db.query(Message)
        .order_by(Message.created_at.desc())
        .limit(50)
        .all()
    )

    try:
        subscribers = onlyfans.get_fans(limit=100)
        subscriber_count = len(subscribers)
    except Exception:
        subscriber_count = "—"

    recent_posts = (
        db.query(Post)
        .order_by(Post.posted_at.desc())
        .limit(10)
        .all()
    )

    social_posts = (
        db.query(SocialPost)
        .order_by(SocialPost.posted_at.desc())
        .limit(20)
        .all()
    )

    reddit_count = db.query(SocialPost).filter(SocialPost.platform == "reddit").count()
    twitter_count = db.query(SocialPost).filter(SocialPost.platform == "twitter").count()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "messages": recent_messages,
        "subscriber_count": subscriber_count,
        "posts": recent_posts,
        "social_posts": social_posts,
        "reddit_count": reddit_count,
        "twitter_count": twitter_count,
    })


@router.post("/persona/reload")
async def reload_persona():
    persona.reload()
    return {"status": "reloaded"}
