import json

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from loguru import logger
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pipeline_bridge import pipeline_notes
from apps.common.throttles import NotesRateThrottle
from apps.lectures.models import Lecture
from .models import Notes
from .serializers import NotesSerializer


class LectureNotesListCreateView(APIView):
    """
    GET  -- previously generated notes for a lecture (most recent first)
    POST -- generate fresh notes from the lecture's full clean transcript.
            Can be several LLM calls for long lectures (map-reduce -- see
            notes.py's batching), so this is throttled like quiz generation.
    """

    def get_throttles(self):
        if self.request.method == "POST":
            return [NotesRateThrottle()]
        return super().get_throttles()

    def get(self, request, lecture_id):
        lecture = get_object_or_404(Lecture, lecture_id=lecture_id, owner_id=request.user.id)
        return Response(NotesSerializer(lecture.notes_generations.all(), many=True).data)

    def post(self, request, lecture_id):
        lecture = get_object_or_404(Lecture, lecture_id=lecture_id, owner_id=request.user.id)
        if lecture.status != Lecture.STATUS_COMPLETED:
            return Response(
                {
                    "error": {
                        "code": "lecture_not_ready",
                        "message": f"Lecture status is '{lecture.status}' -- not ready for notes generation yet.",
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )

        try:
            notes_data = pipeline_notes.generate_notes(lecture.lecture_id, lecture.transcript)
        except Exception as exc:
            logger.error(f"Notes generation failed for lecture '{lecture_id}': {exc}")
            return Response(
                {"error": {"code": "notes_failed", "message": "Could not generate notes -- please try again."}},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        notes = Notes.objects.create(
            lecture=lecture,
            num_sections=len(notes_data.get("sections", [])),
            num_key_terms=len(notes_data.get("key_terms", [])),
            data=notes_data,
        )
        return Response(NotesSerializer(notes).data, status=status.HTTP_201_CREATED)


class LectureNotesExportView(APIView):
    """Download previously generated notes as Markdown or JSON, rendered
    straight from the DB-stored JSON -- doesn't depend on the pipeline's own
    work/notes/ files still being on disk (ephemeral on Render's free tier)."""

    def get(self, request, lecture_id, notes_id):
        notes = get_object_or_404(
            Notes, lecture__lecture_id=lecture_id, id=notes_id, lecture__owner_id=request.user.id
        )
        fmt = request.query_params.get("format", "md")

        if fmt == "json":
            body = json.dumps(notes.data, ensure_ascii=False, indent=2)
            response = HttpResponse(body, content_type="application/json")
            response["Content-Disposition"] = f'attachment; filename="{lecture_id}-notes-{notes_id}.json"'
            return response

        response = HttpResponse(_render_notes_markdown(notes.data), content_type="text/markdown")
        response["Content-Disposition"] = f'attachment; filename="{lecture_id}-notes-{notes_id}.md"'
        return response


def _render_notes_markdown(notes: dict) -> str:
    lecture_id = notes.get("lecture_id", "")
    lines = [f"# Notes -- {lecture_id}\n"]

    if notes.get("summary"):
        lines.append(f"{notes['summary']}\n")

    for section in notes.get("sections", []):
        lines.append(f"## {section.get('heading', '')}\n")
        for point in section.get("points", []):
            lines.append(f"- {point}")
        lines.append("")

    if notes.get("key_terms"):
        lines.append("## Key Terms\n")
        for kt in notes["key_terms"]:
            lines.append(f"- **{kt.get('term', '')}:** {kt.get('definition', '')}")
        lines.append("")

    return "\n".join(lines)
