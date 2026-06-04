import os
import tempfile

from config import genai_client, MODEL_NAME


def call_model(prompt, model_name, temperature=0.9):
    if not genai_client:
        raise RuntimeError("Gemini API key is missing.")
    return genai_client.models.generate_content(
        model=model_name,
        contents=prompt,
        config={"temperature": temperature},
    )


def process_audio_with_gemini(audio_bytes):
    if not genai_client:
        raise RuntimeError("Gemini API key is missing.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_audio.write(audio_bytes)
        temp_audio_path = temp_audio.name

    try:
        sample_file = genai_client.files.upload(
            file=temp_audio_path,
            config={"mime_type": "audio/wav"},
        )
        response = genai_client.models.generate_content(
            model=MODEL_NAME,
            contents=[
                "Transcribe this interview answer accurately. Return only the transcript.",
                sample_file,
            ],
        )
        return response.text.strip()
    finally:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
