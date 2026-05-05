import os
import random
import httpx
import replicate
from app.config import REPLICATE_API_TOKEN, PERSONA_DIR, GENERATED_DIR

os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN

_APPEARANCE = None
_LORA_MODEL = os.getenv("LORA_MODEL", "")

_CANDID_STYLES = [
    "shot on iPhone, slightly grainy, natural imperfect lighting",
    "casual phone selfie, unposed, real person vibe",
    "candid snapshot, not a photoshoot, authentic moment",
    "amateur phone camera, slightly overexposed, natural",
    "instagram selfie style, informal, genuine expression",
]


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


def generate_image_url(scene_context: str = "mirror selfie at home, casual outfit") -> tuple[str, str]:
    """Like generate_image() but also returns the Replicate public URL.
    Returns (local_path, public_url). URL is valid ~24h — enough for Threads posting."""
    lora_model = os.getenv("LORA_MODEL", _LORA_MODEL)
    candid_style = random.choice(_CANDID_STYLES)

    if lora_model:
        if ":" not in lora_model:
            model = replicate.models.get(lora_model)
            lora_ref = f"{lora_model}:{model.latest_version.id}"
        else:
            lora_ref = lora_model
        prompt = f"HEATHER, {scene_context}, {candid_style}"
        output = replicate.run(lora_ref, input={
            "prompt": prompt, "aspect_ratio": "2:3", "output_format": "jpg",
            "lora_scale": 1.0, "num_inference_steps": 28, "guidance_scale": 3.5,
        })
    else:
        appearance = _get_appearance()
        prompt = (
            f"young woman, {appearance}, {scene_context}, {candid_style}, "
            "not a model, real person, no studio lighting"
        )
        output = replicate.run(
            "black-forest-labs/flux-1.1-pro",
            input={"prompt": prompt, "aspect_ratio": "2:3", "output_format": "jpg"},
        )

    filename = f"image_{os.urandom(6).hex()}.jpg"
    dest = os.path.join(GENERATED_DIR, filename)

    if isinstance(output, list):
        file_output = output[0]
        public_url = str(file_output)
        with open(dest, "wb") as f:
            f.write(file_output.read())
    else:
        public_url = str(output)
        with httpx.Client() as client:
            resp = client.get(public_url, timeout=60)
            resp.raise_for_status()
            with open(dest, "wb") as f:
                f.write(resp.content)

    return dest, public_url


def generate_image(scene_context: str = "mirror selfie at home, casual outfit") -> str:
    lora_model = os.getenv("LORA_MODEL", _LORA_MODEL)
    candid_style = random.choice(_CANDID_STYLES)

    if lora_model:
        # Resolve to versioned ref if no version pinned
        if ":" not in lora_model:
            model = replicate.models.get(lora_model)
            lora_ref = f"{lora_model}:{model.latest_version.id}"
        else:
            lora_ref = lora_model

        prompt = f"HEATHER, {scene_context}, {candid_style}"
        output = replicate.run(
            lora_ref,
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
        appearance = _get_appearance()
        prompt = (
            f"young woman, {appearance}, {scene_context}, {candid_style}, "
            "not a model, real person, no studio lighting"
        )
        output = replicate.run(
            "black-forest-labs/flux-1.1-pro",
            input={"prompt": prompt, "aspect_ratio": "2:3", "output_format": "jpg"},
        )

    filename = f"image_{os.urandom(6).hex()}.jpg"
    dest = os.path.join(GENERATED_DIR, filename)

    # LoRA model returns list of FileOutput; flux-1.1-pro returns a URL string
    if isinstance(output, list):
        file_output = output[0]
        with open(dest, "wb") as f:
            f.write(file_output.read())
    else:
        with httpx.Client() as client:
            resp = client.get(str(output), timeout=60)
            resp.raise_for_status()
            with open(dest, "wb") as f:
                f.write(resp.content)

    return dest
