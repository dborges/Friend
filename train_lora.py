"""
Run this once to train Heather's LoRA on Replicate.
Training takes ~20-40 minutes. The script starts training and polls until done,
then saves the model URL to .env automatically.
"""
import os
import sys
import time
import zipfile
import replicate
from dotenv import load_dotenv, set_key

load_dotenv()

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
GENERATED_DIR = os.path.join(os.path.dirname(__file__), "generated")
ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")

TRAINING_IMAGES = [
    "image_eb4f5831aaa4.jpg",
    "post_morning_yoga.jpg",
    "post_beach_afternoon.jpg",
    "post_work_from_home.jpg",
    "post_coffee_morning.jpg",
    "post_sunset_walk.jpg",
    "post_advice_post.jpg",
    "post_cat_post.jpg",
    "post_friday_night.jpg",
]

os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN


def zip_images() -> str:
    zip_path = os.path.join(GENERATED_DIR, "heather_training.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename in TRAINING_IMAGES:
            full_path = os.path.join(GENERATED_DIR, filename)
            if os.path.exists(full_path):
                zf.write(full_path, filename)
                print(f"  + {filename}")
            else:
                print(f"  ! missing: {filename}")
    print(f"Zip created: {zip_path}")
    return zip_path


def upload_zip(zip_path: str) -> str:
    print("Uploading training images to Replicate...")
    with open(zip_path, "rb") as f:
        file_obj = replicate.files.create(f)
    url = file_obj.urls["get"]
    print(f"Uploaded: {url}")
    return url


def get_replicate_username() -> str:
    import httpx
    resp = httpx.get(
        "https://api.replicate.com/v1/account",
        headers={"Authorization": f"Bearer {REPLICATE_API_TOKEN}"},
        timeout=10,
    )
    return resp.json()["username"]


def start_training(zip_url: str, username: str):
    destination = f"{username}/heather-lora"

    # Create the destination model if it doesn't exist
    try:
        replicate.models.create(
            owner=username,
            name="heather-lora",
            visibility="private",
            hardware="gpu-a40-large",
            description="Heather persona LoRA for consistent character generation",
        )
        print(f"Created model: {destination}")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"Model {destination} already exists, reusing.")
        else:
            print(f"Model creation note: {e}")

    print(f"Starting training → {destination}")
    training = replicate.trainings.create(
        model="ostris/flux-dev-lora-trainer",
        version="26dce37af90b9d997eeb970d92e47de3064d46c300504ae376c75bef6a9022d2",
        input={
            "input_images": zip_url,
            "trigger_word": "HEATHER",
            "steps": 1500,
            "lora_rank": 16,
            "learning_rate": 0.0004,
            "autocaption": True,
            "autocaption_prefix": "a photo of HEATHER, a young woman, ",
        },
        destination=destination,
    )
    print(f"Training started. ID: {training.id}")
    print(f"Track progress: https://replicate.com/p/{training.id}")
    return training


def poll_training(training) -> str:
    print("\nWaiting for training to complete (this takes 20-40 minutes)...")
    print("You can close this script and check back — training runs on Replicate's servers.\n")

    dots = 0
    while training.status not in ("succeeded", "failed", "canceled"):
        time.sleep(30)
        training.reload()
        dots += 1
        print(f"  [{training.status}] {dots * 30}s elapsed...", end="\r")

    print()
    if training.status == "succeeded":
        weights_url = training.output.get("weights") if training.output else None
        print(f"Training complete! Weights: {weights_url}")
        return weights_url
    else:
        print(f"Training {training.status}. Check logs at https://replicate.com/p/{training.id}")
        sys.exit(1)


def save_to_env(model_destination: str):
    """Save the trained model reference to .env."""
    set_key(ENV_FILE, "LORA_MODEL", model_destination)
    print(f"Saved LORA_MODEL={model_destination} to .env")


if __name__ == "__main__":
    print("=== Heather LoRA Training ===\n")

    print("Step 1: Zipping training images...")
    zip_path = zip_images()

    print("\nStep 2: Uploading to Replicate...")
    zip_url = upload_zip(zip_path)

    print("\nStep 3: Getting your Replicate username...")
    username = get_replicate_username()
    print(f"Username: {username}")

    print("\nStep 4: Starting training...")
    training = start_training(zip_url, username)

    destination = f"{username}/heather-lora"
    save_to_env(destination)

    print(f"\nTraining is running on Replicate.")
    print(f"Track it at: https://replicate.com/p/{training.id}")
    print(f"\nWhen done, the model will be at: replicate.com/{destination}")
    print("The bot will automatically use it for all future image generation.")
    print("\nPoll for completion? (y/n): ", end="")

    if input().strip().lower() == "y":
        poll_training(training)
        print(f"\nDone! Future images will use replicate.com/{destination}")
    else:
        print("\nTraining is running in the background on Replicate's servers.")
        print("Come back and check https://replicate.com/trainings when it's done.")
        print(f"LORA_MODEL is already saved to .env as: {destination}")
