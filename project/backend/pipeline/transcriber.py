"""
Stage 2: Audio -> Raw Transcript using ElevenLabs Speech-to-Text (Scribe).

Scribe v2 supports 90+ languages and speaker diarization, which is what we
need for mixed Urdu/English/Arabic lectures with a single instructor voice
(diarization also helps if students ask questions on the recording).
"""
import json
from pathlib import Path
from elevenlabs.client import ElevenLabs
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_not_exception_type
from groq import Groq
import config


def _get_client() -> Groq:
    if not config.GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY is not set. Create a .env file next to this script "
            "(copy .env.example) and set GROQ_API_KEY=your_actual_key there."
        )
    return Groq(api_key=config.GROQ_API_KEY)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=30),
    retry=retry_if_not_exception_type(ValueError),  # don't retry config errors -- they'll never succeed
    reraise=True,  # raise the ORIGINAL exception on final failure, not tenacity's RetryError wrapper
)
def transcribe_audio(audio_path: str, language_code: str | None = None) -> dict:
    """
    Send an audio file to Groq and get back a structured transcript.

    Args:
        audio_path: path to a local audio file (wav/mp3/etc.)
        language_code: ISO 639-3 code (e.g. "eng", "urd", "ara") to hint the
            language, or None to let Groq auto-detect. Since our lectures
            mix Urdu/English/Arabic in the same recording, we default to
            None (auto-detect) so Groq can switch per-segment.

    Returns:
        Raw response dict from Groq (includes text + word/segment-level
        timing and, if available, speaker labels).
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    client = _get_client()
    logger.info(f"Sending {audio_path.name} to Groq Whisper for transcription...")

    with open(audio_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=f,
            model=config.GROQ_MODEL,
            prompt=None,
            response_format="verbose_json",    
            language=language_code,  
            temperature=0.0,            
        )

    # SDK returns a pydantic-like object; normalize to plain dict for storage
    result = transcription.dict() if hasattr(transcription, "dict") else dict(transcription)
    logger.info(f"Transcription complete for {audio_path.name}")
    return result


def save_raw_transcript(transcript: dict, lecture_id: str) -> Path:
    """Persist the raw Groq response to disk as JSON."""
    output_path = config.RAW_TRANSCRIPT_DIR / f"{lecture_id}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(transcript, f, ensure_ascii=False, indent=2)
    logger.info(f"Raw transcript saved: {output_path}")
    return output_path


def transcript_to_segments(transcript: dict) -> list[dict]:
    """
    Normalize ElevenLabs' response into a simple list of segments:
    [{ "start": float, "end": float, "speaker": str|None, "text": str }, ...]

    NOTE: ElevenLabs' exact response schema can vary by model/version.
    This function is intentionally defensive -- it checks for a few known
    shapes. If ElevenLabs changes their schema, update the parsing here;
    the rest of the pipeline only depends on this normalized format.
    """
    segments = []

    # Preferred: word/segment-level data with speaker + timing
    words = transcript.get("words") or transcript.get("segments")
    if words:
        current = None
        for w in words:
            speaker = w.get("speaker_id") or w.get("speaker")
            start = w.get("start")
            end = w.get("end")
            text = w.get("text", "")

            if current and current["speaker"] == speaker:
                current["text"] += text
                current["end"] = end
            else:
                if current:
                    segments.append(current)
                current = {"start": start, "end": end, "speaker": speaker, "text": text}
        if current:
            segments.append(current)
        return segments

    # Fallback: just a flat transcript string, no timing/speaker info
    if transcript.get("text"):
        segments.append({"start": 0.0, "end": None, "speaker": None, "text": transcript["text"]})

    return segments