import os
import random
import httpx
import replicate
from app.config import REPLICATE_API_TOKEN, PERSONA_DIR, GENERATED_DIR

os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN

_APPEARANCE = None
_LORA_MODEL = os.getenv("LORA_MODEL", "")

# Camera/lens descriptors that push Flux toward photographic realism
_CAMERA_STYLES = [
    "shot on iPhone 15 Pro, natural light, slight lens flare, shallow depth of field",
    "candid photo, Sony a7III, 50mm f/1.8, bokeh background, true-to-life colors",
    "casual selfie, front camera, slightly grainy sensor noise, fluorescent bathroom light",
    "shot by a friend, Canon EOS R, 35mm, unposed, mid-conversation moment",
    "Instagram Story capture, overexposed highlights, warm golden hour window light",
    "phone camera, slightly motion-blurred background, crisp subject, real skin texture",
    "candid outdoor shot, dappled sunlight through trees, slight chromatic aberration",
    "mirror selfie, phone visible in frame, natural bathroom lighting, slightly overexposed",
    "low-angle friend selfie, cloudy outdoor light, no flash, natural shadow under chin",
    "caught mid-laugh, portrait mode, slight edge blur artifact, natural hair flyaways",
]

# Scene contexts grounded in Heather's Miami life
_DEFAULT_SCENES = [
    "sitting at a cafe in Miami, iced coffee on the table, casual afternoon",
    "mirror selfie at home, crop top and jeans, bedroom in background slightly messy",
    "at the beach, hair wind-blown, not posing, looking away at something",
    "couch at home with her cat, lazy Sunday afternoon, natural window light",
    "standing in her kitchen, cooking something, glancing at camera over shoulder",
    "walking on a Miami sidewalk, palm trees in background, squinting slightly in sun",
    "at a rooftop bar, golden hour, cocktail in hand, laughing at something offscreen",
    "post-yoga, workout clothes, hair up messy, slightly flushed, genuine smile",
    "sitting on apartment balcony, evening light, casual t-shirt, relaxed expression",
    "at a friend's house, group setting implied, looking at phone, candid moment",
]

# Realism anchors — included in every non-LoRA prompt
_REALISM_ANCHORS = (
    "real person, natural skin texture with pores and fine lines, "
    "authentic expression, slight asymmetry, no retouching, "
    "photojournalistic quality, not a model, not a photoshoot"
)

# Concepts to steer away from — passed as negative prompt where supported
_NEGATIVE_PROMPT = (
    "painting, illustration, anime, cgi, render, 3d, plastic skin, "
    "overly smooth, airbrushed, symmetrical, studio lighting, glamour shot, "
    "watermark, signature, perfect teeth, artificial bokeh, oversaturated"
)


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
            _APPEARANCE = "tall athletic woman, long dark hair, warm brown eyes, casual style"
    return _APPEARANCE


def _build_prompt(scene_context: str) -> str:
    appearance = _get_appearance()
    camera = random.choice(_CAMERA_STYLES)
    return (
        f"24-year-old woman, {appearance}, {scene_context}, "
        f"{camera}, {_REALISM_ANCHORS}"
    )


def _run_flux(prompt: str) -> object:
    return replicate.run(
        "black-forest-labs/flux-1.1-pro",
        input={
            "prompt": prompt,
            "aspect_ratio": "2:3",
            "output_format": "jpg",
            "output_quality": 95,
            "prompt_upsampling": True,
        },
    )


def _run_lora(lora_ref: str, prompt: str) -> object:
    return replicate.run(
        lora_ref,
        input={
            "prompt": prompt,
            "aspect_ratio": "2:3",
            "output_format": "jpg",
            "output_quality": 95,
            "lora_scale": 0.85,
            "num_inference_steps": 32,
            "guidance_scale": 3.5,
        },
    )


def _save_output(output) -> tuple[str, str]:
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


def generate_image_url(scene_context: str = "") -> tuple[str, str]:
    """Returns (local_path, public_url). URL valid ~24h — enough for Threads posting."""
    if not scene_context:
        scene_context = random.choice(_DEFAULT_SCENES)

    lora_model = os.getenv("LORA_MODEL", _LORA_MODEL)

    if lora_model:
        if ":" not in lora_model:
            model = replicate.models.get(lora_model)
            lora_ref = f"{lora_model}:{model.latest_version.id}"
        else:
            lora_ref = lora_model
        camera = random.choice(_CAMERA_STYLES)
        prompt = f"HEATHER, {scene_context}, {camera}, {_REALISM_ANCHORS}"
        output = _run_lora(lora_ref, prompt)
    else:
        output = _run_flux(_build_prompt(scene_context))

    return _save_output(output)


def generate_image(scene_context: str = "") -> str:
    if not scene_context:
        scene_context = random.choice(_DEFAULT_SCENES)

    lora_model = os.getenv("LORA_MODEL", _LORA_MODEL)

    if lora_model:
        if ":" not in lora_model:
            model = replicate.models.get(lora_model)
            lora_ref = f"{lora_model}:{model.latest_version.id}"
        else:
            lora_ref = lora_model
        camera = random.choice(_CAMERA_STYLES)
        prompt = f"HEATHER, {scene_context}, {camera}, {_REALISM_ANCHORS}"
        output = _run_lora(lora_ref, prompt)
    else:
        output = _run_flux(_build_prompt(scene_context))

    dest, _ = _save_output(output)
    return dest
