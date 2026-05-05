import os
from elevenlabs.client import ElevenLabs
from app.config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, GENERATED_DIR

client = ElevenLabs(api_key=ELEVENLABS_API_KEY)


def generate_voice(text: str) -> str:
    audio = client.text_to_speech.convert(
        voice_id=ELEVENLABS_VOICE_ID,
        text=text,
        model_id="eleven_turbo_v2_5",
        output_format="mp3_44100_128",
    )

    filename = f"voice_{os.urandom(6).hex()}.mp3"
    dest = os.path.join(GENERATED_DIR, filename)

    with open(dest, "wb") as f:
        for chunk in audio:
            f.write(chunk)

    return dest
