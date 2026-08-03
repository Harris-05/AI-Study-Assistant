"""
Stage 1: Video -> Audio extraction.

Zoom recordings are usually .mp4. ElevenLabs' STT API can technically accept
video files too, but we extract audio separately because:
  - it drastically reduces upload size for long (1-5hr) lectures
  - it lets us normalize format/sample rate for more consistent STT results
  - it decouples this step so you can later swap in a different STT provider
    that may only accept audio
"""
import subprocess
from pathlib import Path
from loguru import logger

import config

# Extensions we treat as "already audio" -- these can be sent straight to
# ElevenLabs without running through ffmpeg first (see uploader.py's
# AUDIO_VIDEO_FILETYPES for the matching upload filter).
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma"}


def is_audio_file(path: str) -> bool:
    """
    Return True if `path` is already an audio file (based on extension),
    False if it's a video container (or anything else) that needs ffmpeg to
    pull the audio track out first.
    """
    return Path(path).suffix.lower() in AUDIO_EXTENSIONS


def extract_audio(video_path: str, output_name: str | None = None) -> Path:
    """
    Extract mono 16kHz WAV audio from a video file using ffmpeg.
    16kHz mono is the sweet spot most STT models are trained on -- it keeps
    file size small without losing speech-relevant frequency content.

    Args:
        video_path: path to the input video (mp4, mov, etc.)
        output_name: optional filename (without extension) for the output audio

    Returns:
        Path to the extracted .wav file
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    if output_name is None:
        output_name = video_path.stem

    output_path = config.AUDIO_DIR / f"{output_name}.wav"

    cmd = [
        "ffmpeg",
        "-y",  # overwrite if exists
        "-i", str(video_path),
        "-vn",  # no video
        "-acodec", "pcm_s16le",  # uncompressed WAV, safest for STT
        "-ar", "16000",  # 16kHz sample rate
        "-ac", "1",  # mono
        str(output_path),
    ]

    logger.info(f"Extracting audio from {video_path.name} -> {output_path.name}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error(f"ffmpeg failed: {result.stderr}")
        raise RuntimeError(f"ffmpeg audio extraction failed:\n{result.stderr}")

    logger.info(f"Audio extraction complete: {output_path}")
    return output_path


def get_audio_duration_seconds(audio_path: str) -> float:
    """Return duration of an audio file in seconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    return float(result.stdout.strip())