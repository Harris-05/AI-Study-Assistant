"""
Recovery tool: re-create a Lecture DB row and re-ingest its vector store
collection from an ALREADY-EXISTING clean transcript on disk -- no
ElevenLabs/cleaning calls, since that work already happened and survived
on disk even though the DB row (and possibly the Chroma collection) did not.

Use this when: ingestion partially failed and you deleted the resulting
"failed" Lecture row (which also wipes its Chroma collection via
delete_lecture_data), but work/clean_transcripts/<lecture_id>.txt is
still there. This recovers everything except the original uploaded file
(which delete_lecture_data does remove permanently -- you can't recover
that; only the transcript-derived pipeline output survives).

Usage:
    python manage.py recover_lecture abf5c0da4cc7 --title "Al-Fatihah Tafsir"

    # optional metadata, all default to blank/None if omitted:
    python manage.py recover_lecture abf5c0da4cc7 \
        --title "Al-Fatihah Tafsir" \
        --course "Tafsir 101" \
        --instructor "Sheikh X" \
        --output-language mixed
"""
from django.core.management.base import BaseCommand, CommandError

from apps.lectures.models import Lecture
from pipeline import config as pipeline_config
from pipeline import vectorstore


class Command(BaseCommand):
    help = "Recover a Lecture DB row + vector store from an existing clean transcript on disk."

    def add_arguments(self, parser):
        parser.add_argument("lecture_id", type=str, help="lecture_id matching work/clean_transcripts/<id>.txt")
        parser.add_argument("--title", type=str, default="Recovered lecture", help="Title for the recovered lecture")
        parser.add_argument("--course", type=str, default="")
        parser.add_argument("--instructor", type=str, default="")
        parser.add_argument("--semester", type=str, default="")
        parser.add_argument("--output-language", type=str, default="mixed",
                             choices=["mixed", "urdu", "english", "arabic"])
        parser.add_argument("--force", action="store_true",
                             help="Overwrite an existing Lecture row with this lecture_id, if one exists")

    def handle(self, *args, **options):
        lecture_id = options["lecture_id"]

        clean_path = pipeline_config.CLEAN_TRANSCRIPT_DIR / f"{lecture_id}.txt"
        if not clean_path.exists():
            raise CommandError(
                f"No clean transcript found at {clean_path} -- nothing to recover. "
                "The transcript itself must already exist on disk; this command doesn't re-transcribe."
            )

        existing = Lecture.objects.filter(lecture_id=lecture_id).first()
        if existing and not options["force"]:
            raise CommandError(
                f"A Lecture row with lecture_id='{lecture_id}' already exists (status={existing.status}). "
                "Pass --force to overwrite it, or pick a different approach if that row is actually fine."
            )

        clean_text = clean_path.read_text(encoding="utf-8")
        if not clean_text.strip():
            raise CommandError(f"Clean transcript at {clean_path} is empty -- nothing to recover.")

        self.stdout.write(f"Re-ingesting vector store for lecture_id='{lecture_id}'...")
        num_chunks = vectorstore.ingest_transcript(clean_text, lecture_id)
        self.stdout.write(self.style.SUCCESS(f"Ingested {num_chunks} chunk(s)."))

        defaults = dict(
            title=options["title"],
            course=options["course"],
            instructor=options["instructor"],
            semester=options["semester"],
            original_filename=f"{lecture_id} (recovered -- original file no longer available)",
            output_language=options["output_language"],
            status=Lecture.STATUS_COMPLETED,
            num_chunks=num_chunks,
            error_message="",
        )

        if existing:
            for field, value in defaults.items():
                setattr(existing, field, value)
            existing.save()
            lecture = existing
            self.stdout.write(self.style.SUCCESS(f"Updated existing Lecture row for '{lecture_id}'."))
        else:
            lecture = Lecture.objects.create(lecture_id=lecture_id, **defaults)
            self.stdout.write(self.style.SUCCESS(f"Created new Lecture row for '{lecture_id}'."))

        self.stdout.write(self.style.SUCCESS(
            f"Done. Lecture '{lecture.title}' (id={lecture.lecture_id}) is now status=completed "
            f"and should appear in the frontend."
        ))