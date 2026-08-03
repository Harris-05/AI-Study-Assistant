"""
Main pipeline orchestrator.

Run it directly -- no CLI flags required, it will pop open a file picker so
you can upload/select your lecture file:
    python main.py

Or call run_pipeline(...) yourself / import it into another script.

This runs the full base pipeline:
    Input file (video OR audio) -> Audio -> Raw Transcript (ElevenLabs) ->
    Clean Transcript (LLM) -> Vector Store (RAG-ready)

After this completes, use chat.py to ask questions about the lecture.

ffmpeg is only used to pull audio out of video containers (.mp4, .mov...).
If your input is already an audio file (.mp3, .wav, .m4a...), it's sent to
ElevenLabs as-is by default -- no ffmpeg required for pure-audio workflows.

Each stage's output is also saved to disk under work/ so you can inspect
raw vs. clean transcripts, or resume from a later stage without re-running
earlier (expensive) stages.
"""
import sys
from pathlib import Path
from loguru import logger

import config
import audio_extractor
import transcriber
import cleaner
import uploader
import vectorstore


def run_pipeline(input_path: str, lecture_id: str | None = None, language_code: str | None = None,
                  output_language: str | None = None, skip_transcription: bool = False,
                  force_normalize_audio: bool = False) -> str:
    """
    Run the full input file -> clean transcript pipeline for one lecture.

    Args:
        input_path: path to the input video (.mp4, .mov...) or audio (.mp3, .wav, .m4a...) file
        lecture_id: unique identifier for this lecture (used for output filenames).
            If None, derived from the input filename.
        language_code: ISO 639-3 hint for STT (e.g. "urd", "eng"), or None to auto-detect
        output_language: target language for the CLEANED transcript
            ("urdu" | "english" | "arabic" | "mixed")
        skip_transcription: if True and a raw transcript already exists for this
            lecture_id, reuse it instead of re-calling ElevenLabs (saves cost
            during development/testing of the cleaning stage)
        force_normalize_audio: if True, always run the file through ffmpeg to
            re-encode to 16kHz mono WAV, even if the input is already an audio
            file. Video files are ALWAYS normalized regardless of this flag
            (ffmpeg is required to pull audio out of a video container).
            Leave False to send audio files (mp3/wav/m4a/...) straight to
            ElevenLabs as-is -- avoids needing ffmpeg installed at all if
            you're only ever working with audio files.

    Returns:
        Path to the final clean transcript file.
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    lecture_id = lecture_id or input_path.stem
    logger.info(f"=== Starting pipeline for lecture_id='{lecture_id}' ===")

    # ── Stage 1: Input -> Audio (normalize only if needed) ───
    # Video files always need ffmpeg (to pull audio out of the container).
    # Audio files (mp3/wav/m4a...) are sent to ElevenLabs as-is by default --
    # normalization is optional polish, not a requirement, for those.
    if audio_extractor.is_audio_file(str(input_path)) and not force_normalize_audio:
        logger.info(f"Input is already an audio file -- skipping ffmpeg normalization, using as-is.")
        audio_path = input_path
    else:
        audio_path = audio_extractor.extract_audio(str(input_path), output_name=lecture_id)

    try:
        duration = audio_extractor.get_audio_duration_seconds(str(audio_path))
        logger.info(f"Audio duration: {duration / 60:.1f} minutes")
    except Exception as e:
        logger.warning(f"Could not determine audio duration ({e}) -- continuing anyway.")

    # ── Stage 2: Audio -> Raw Transcript ─────────────────────
    raw_json_path = config.RAW_TRANSCRIPT_DIR / f"{lecture_id}.json"
    if skip_transcription and raw_json_path.exists():
        logger.info(f"Reusing existing raw transcript: {raw_json_path}")
        import json
        with open(raw_json_path, "r", encoding="utf-8") as f:
            raw_transcript = json.load(f)
    else:
        raw_transcript = transcriber.transcribe_audio(str(audio_path), language_code=language_code)
        transcriber.save_raw_transcript(raw_transcript, lecture_id)

    segments = transcriber.transcript_to_segments(raw_transcript)
    raw_text = " ".join(seg["text"] for seg in segments if seg.get("text"))

    if not raw_text.strip():
        raise RuntimeError("Transcription returned no text -- check the audio file and API response.")

    logger.info(f"Raw transcript length: {len(raw_text)} characters, {len(segments)} segments")

    # ── Stage 3: Raw Transcript -> Clean Transcript ──────────
    clean_text = cleaner.clean_transcript(raw_text, output_language=output_language)
    clean_path = cleaner.save_clean_transcript(clean_text, lecture_id)

    # ── Stage 4: Clean Transcript -> Vector Store (RAG-ready) ─
    num_chunks = vectorstore.ingest_transcript(clean_text, lecture_id)

    logger.info(f"=== Pipeline complete for lecture_id='{lecture_id}' ===")
    logger.info(f"Clean transcript: {clean_path}")
    logger.info(f"Indexed {num_chunks} chunks -- ready for chat.py to ask questions about this lecture.")
    return str(clean_path)


def main():
    # Interactive entry point -- run `python main.py` and a file picker will
    # open so you can upload/select your lecture file. Falls back to a manual
    # path prompt automatically if no display is available (e.g. over SSH).
    print("Opening file picker -- select your lecture audio/video file...")
    input_path = uploader.upload_file()

    lecture_id = input("Lecture ID (Enter to auto-generate from filename): ").strip()
    lecture_id = lecture_id or None

    stt_language = input("STT language hint, ISO 639-3 (Enter to auto-detect): ").strip()
    stt_language = stt_language or None

    output_language = input(
        f"Output language [urdu/english/arabic/mixed] (Enter for default '{config.OUTPUT_LANGUAGE}'): "
    ).strip().lower()
    if output_language and output_language not in {"urdu", "english", "arabic", "mixed"}:
        logger.warning(f"Unrecognized output language '{output_language}', falling back to default.")
        output_language = None
    output_language = output_language or None

    skip_transcription = input("Reuse existing raw transcript if available? [y/N]: ").strip().lower() == "y"

    try:
        run_pipeline(
            input_path=input_path,
            lecture_id=lecture_id,
            language_code=stt_language,
            output_language=output_language,
            skip_transcription=skip_transcription,
        )
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()