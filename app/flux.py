import os
import httpx
import replicate
from app.config import REPLICATE_API_TOKEN, PERSONA_DIR, GENERATED_DIR

os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN

_APPEARANCE = None
_LORA_MODEL = os.getenv("LORA_MODEL", "")  # set after training e.g. "username/heather-lora"


def _get_appearance() -> str:
    global _APPEARANCE
    if _APPEARANCE is None:
        path = os.path.join(PERSONA_DIR, "identity.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        for line in content.split("\n"):
            if line.startswith("## Appearance"):
                idx = content.index("## Appearance")
                block = content[idx:].split("##")[1]
                _APPEARANCE = " ".join(block.strip().splitlines()[1:]).strip()
                break
        if not _APPEARANCE:
            _APPEARANCE = "young woman, dark hair, warm brown eyes, casual style"
    return _APPEARANCE


def generate_image(scene_context: str = "selfie, natural light, casual home setting") -> str:
    lora_model = os.getenv("LORA_MODEL", _LORA_MODEL)

    if lora_model:
        # Use trained LoRA — HEATHER trigger word activates her face
        prompt = f"HEATHER, {scene_context}, high quality lifestyle photography, natural light"
        output = replicate.run(
            lora_model,
            input={
                "prompt": prompt,
                "aspect_ratio": "2:3",
                "output_format": "jpg",
                "lora_scale": 1.0,
                "num_inference_steps": 28,
                "guidance_scale": 3.5,
            },
        )
    else:
        # Fallback: no LoRA yet — use appearance description
        appearance = _get_appearance()
        prompt = (
            f"Photorealistic lifestyle photo of a young woman. {appearance}. "
            f"{scene_context}. High quality, natural lighting, lifestyle photography style."
        )
        output = replicate.run(
            "black-forest-labs/flux-1.1-pro",
            input={"prompt": prompt, "aspect_ratio": "2:3", "output_format": "jpg"},
        )

    image_url = str(output)
    filename = f"image_{os.urandom(6).hex()}.jpg"
    dest = os.path.join(GENERATED_DIR, filename)

    with httpx.Client() as client:
        resp = client.get(image_url, timeout=60)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            f.write(resp.content)

    return dest
