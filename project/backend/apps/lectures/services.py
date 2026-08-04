"""
Service layer between the Django views and the pipeline. Keeps views thin
and keeps every pipeline touchpoint in one file per concern.
"""
import shutil
from pathlib import Path

from django.conf import settings
from rest_framework.exceptions import ValidationError

from apps.common.pipeline_bridge import audio_extractor, pipeline_config, pipeline_main, vectorstore
from .models import Lecture


def save_uploaded_file(lecture_id: str, uploaded_file) -> Path:
    """Stream the uploaded file to disk under MEDIA_ROOT/uploads/<lecture_id>/."""
    lecture_dir = settings.UPLOADS_DIR / lecture_id
    lecture_dir.mkdir(parents=True, exist_ok=True)
    dest = lecture_dir / uploaded_file.name
    with open(dest, "wb") as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)
    return dest


def check_duration_guardrail(file_path: Path) -> float | None:
    """
    Reject lectures too long for SYNCHRONOUS processing before spending any
    money calling ElevenLabs/Gemini on them (this deployment processes
    ingestion inline in the request -- see project decision in README).

    Returns the duration in seconds if it could be determined, else None
    (probing failure doesn't block ingestion -- we just skip the guardrail
    for that one file rather than fail the whole upload over it).
    """
    try:
        duration = audio_extractor.get_audio_duration_seconds(str(file_path))
    except Exception:
        return None

    max_allowed = settings.MAX_SYNC_LECTURE_DURATION_SECONDS
    if duration > max_allowed:
        raise ValidationError(
            f"Lecture is {duration / 60:.1f} minutes long, which exceeds the "
            f"{max_allowed / 60:.0f}-minute limit for synchronous processing on "
            f"this deployment. Trim the recording, or split it into shorter parts."
        )
    return duration


def ingest_lecture(lecture: Lecture, file_path: Path) -> None:
    """
    Run the full pipeline (audio -> transcript -> clean -> vector store)
    synchronously, mutating the Lecture row's status/fields in place.

    This blocks the request for as long as the pipeline takes -- a
    deliberate, current project decision (see backend/README.md) rather
    than an oversight. Swap this for a Celery/RQ task later without
    changing the pipeline call itself.
    """
    lecture.status = Lecture.STATUS_PROCESSING
    lecture.save(update_fields=["status"])

    try:
        pipeline_main.run_pipeline(
            input_path=str(file_path),
            lecture_id=lecture.lecture_id,
            language_code=lecture.language_code_hint or None,
            output_language=lecture.output_language,
        )
        chunks = vectorstore.get_all_chunks(lecture.lecture_id)
        lecture.num_chunks = len(chunks)

        # Copy the pipeline's on-disk transcript into Postgres (Supabase)
        # so it survives independently of the Oracle instance's local disk
        # -- the audio file and Chroma index stay local-only (see
        # settings.py), but this small piece of text is the one thing from
        # ingestion worth being durable off-box. Best-effort: a missing
        # transcript file shouldn't fail an otherwise-successful ingestion.
        transcript_path = pipeline_config.CLEAN_TRANSCRIPT_DIR / f"{lecture.lecture_id}.txt"
        if transcript_path.exists():
            lecture.transcript = transcript_path.read_text(encoding="utf-8")

        lecture.status = Lecture.STATUS_COMPLETED
        lecture.error_message = ""
        lecture.save()
    except Exception as exc:
        lecture.status = Lecture.STATUS_FAILED
        lecture.error_message = str(exc)[:2000]
        lecture.save()
        raise


def delete_lecture_data(lecture: Lecture) -> None:
    """Best-effort cleanup of a lecture's uploaded file and vector
    collection. Failures here are swallowed -- deleting the DB row should
    never be blocked by leftover-file/vector-store cleanup issues."""
    try:
        lecture_dir = settings.UPLOADS_DIR / lecture.lecture_id
        if lecture_dir.exists():
            shutil.rmtree(lecture_dir, ignore_errors=True)
    except Exception:
        pass

    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(pipeline_config.VECTOR_DB_DIR))
        client.delete_collection(name=lecture.lecture_id)
    except Exception:
        pass