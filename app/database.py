from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "friend.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    of_message_id = Column(String, unique=True, nullable=False)
    subscriber_id = Column(String, nullable=False)
    subscriber_name = Column(String)
    subscriber_tier = Column(String, default="standard")
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    processed = Column(Boolean, default=False)


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    of_post_id = Column(String, unique=True)
    caption = Column(Text)
    image_path = Column(String)
    posted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String, default="pending")  # pending, posted, failed


class SocialPost(Base):
    __tablename__ = "social_posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String, nullable=False)   # "reddit" | "twitter"
    subreddit = Column(String)                  # Reddit only
    post_url = Column(String)
    caption = Column(Text)
    image_path = Column(String)
    posted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String, default="posted")   # posted | failed


def init_db():
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_conversation_history(db, subscriber_id: str, limit: int = 20) -> list[dict]:
    messages = (
        db.query(Message)
        .filter(Message.subscriber_id == subscriber_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )
    return [{"role": m.role, "content": m.content} for m in reversed(messages)]


def save_message(db, of_message_id: str, subscriber_id: str, subscriber_name: str,
                 subscriber_tier: str, role: str, content: str):
    msg = Message(
        of_message_id=of_message_id,
        subscriber_id=subscriber_id,
        subscriber_name=subscriber_name,
        subscriber_tier=subscriber_tier,
        role=role,
        content=content,
        processed=True,
    )
    db.add(msg)
    db.commit()
    return msg


def is_processed(db, of_message_id: str) -> bool:
    return db.query(Message).filter(Message.of_message_id == of_message_id).first() is not None
