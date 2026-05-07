from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db, Message, Post, SocialPost
from app import fanvue, persona
from app.config import GENERATED_DIR
import asyncio
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
        subscribers = fanvue.get_fans(limit=100)
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


@router.post("/generate-image")
async def generate_image(request: Request):
    body = await request.json()
    scene = (body.get("scene") or "").strip()
    try:
        from app import flux
        loop = asyncio.get_event_loop()
        path = await loop.run_in_executor(None, flux.generate_image, scene or None)
        filename = os.path.basename(path)
        return JSONResponse({"url": f"/dashboard/generated/{filename}", "filename": filename})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/generated-images")
async def list_generated_images():
    files = []
    for f in sorted(os.listdir(GENERATED_DIR), reverse=True):
        if f.lower().endswith((".jpg", ".jpeg", ".png")):
            files.append(f"/dashboard/generated/{f}")
    return JSONResponse({"images": files[:48]})
