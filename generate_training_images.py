"""
Generates a batch of Heather images optimized for LoRA training.
Covers: face angles, lighting types, distances, expressions, settings.
"""
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))
from app.flux import _build_prompt, _run_flux, _save_output

TRAINING_SCENES = [
    # --- Close-up face shots (most important for LoRA face training) ---
    "close-up portrait, looking directly at camera, soft natural window light, neutral expression",
    "close-up face, slight smile, golden hour light from the side, outdoors",
    "close-up portrait, laughing at something off-camera, candid, warm indoor light",
    "close-up selfie, bathroom mirror, fluorescent light, just woke up, no makeup",
    "close-up face, 3/4 angle to the right, outdoor shade, relaxed expression",

    # --- Medium shots (chest up) ---
    "waist-up shot, sitting at a cafe table, iced coffee in hand, looking down at phone",
    "chest-up, leaning against a wall outside, arms crossed loosely, slight smirk",
    "medium shot, standing in her kitchen, casual t-shirt, glancing over shoulder at camera",
    "waist-up photo, standing in living room, casual outfit, afternoon light through blinds",
    "chest-up, seated on couch, one knee pulled up, cat in background, relaxed",

    # --- Full body / environmental ---
    "full body, walking on Miami sidewalk, sundress, palm trees behind, candid stride",
    "full body, sitting on apartment balcony steps, evening light, legs stretched out",
    "full body, at the beach, standing at water's edge, wind in hair, looking away",
    "full body, yoga mat on balcony, post-workout, hair in messy bun, water bottle nearby",

    # --- Side and back angles (helps LoRA learn full head shape) ---
    "profile shot, left side, looking out a window, soft daylight, contemplative mood",
    "3/4 profile, sitting at a rooftop bar, golden hour, cocktail in hand, candid",
    "back of head and shoulders, looking out at Miami skyline, evening, hair down",
]

def main():
    output_dir = os.path.join(os.path.dirname(__file__), "generated", "training")
    os.makedirs(output_dir, exist_ok=True)

    print(f"Generating {len(TRAINING_SCENES)} training images...\n")

    for i, scene in enumerate(TRAINING_SCENES, 1):
        print(f"[{i}/{len(TRAINING_SCENES)}] {scene[:60]}...")
        try:
            prompt = _build_prompt(scene)
            output = _run_flux(prompt)
            dest, _ = _save_output(output)

            # Move to training dir with descriptive name
            import shutil
            slug = scene[:40].replace(" ", "_").replace(",", "").replace("/", "-")
            final_path = os.path.join(output_dir, f"{i:02d}_{slug}.jpg")
            shutil.move(dest, final_path)
            print(f"    saved -> {os.path.basename(final_path)}")
        except Exception as e:
            print(f"    ERROR: {e}")

        # Rate limit: 6 req/min with <$5 credit = wait 12s between calls
        if i < len(TRAINING_SCENES):
            time.sleep(12)

    print(f"\nDone. Training images saved to: {output_dir}")

if __name__ == "__main__":
    main()
