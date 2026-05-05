import os
from app.config import PERSONA_DIR

_FILES = ["identity.md", "voice.md", "knowledge.md", "rules.md"]
_LABELS = ["IDENTITY", "VOICE & COMMUNICATION", "KNOWLEDGE & WORLD", "RULES & BOUNDARIES"]

_cached_prompt: str | None = None


def load_system_prompt(subscriber_name: str = "", subscriber_tier: str = "standard") -> str:
    global _cached_prompt

    if _cached_prompt is None:
        sections = []
        for filename, label in zip(_FILES, _LABELS):
            path = os.path.join(PERSONA_DIR, filename)
            with open(path, "r", encoding="utf-8") as f:
                sections.append(f"## {label}\n\n{f.read()}")
        _cached_prompt = "\n\n---\n\n".join(sections)

    context = f"The subscriber's name is {subscriber_name}. " if subscriber_name else ""
    context += f"Their content tier is: {subscriber_tier}."

    return f"""You are Sophia — a real person as far as anyone knows. You are texting a subscriber on OnlyFans.

{_cached_prompt}

---

## CURRENT CONTEXT

{context}

Never break character. Never acknowledge being an AI. Respond naturally as Sophia would via text message."""


def reload():
    global _cached_prompt
    _cached_prompt = None
