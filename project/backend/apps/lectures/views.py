from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pipeline_bridge import pipeline_config
from apps.common.throttles import IngestRateThrottle
from .models import Lecture
from .serializers import LectureCreateSerializer, LectureSerializer
from .services import check_duration_guardrail, delete_lecture_data, ingest_lecture, save_uploaded_file


class LectureListCreateView(APIView):
    """
    GET  -- list all lectures (cheap, unthrottled beyond the global anon rate)
    POST -- upload a lecture file and run the FULL pipeline synchronously.
            This request blocks until transcription/cleaning/embedding
            finishes (or fails) -- see project decision in README. Heavily
            throttled since every call costs real ElevenLabs/Gemini usage.
    """

    def get_throttles(self):
        if self.request.method == "POST":
            return [IngestRateThrottle()]
        return super().get_throttles()

    def get(self, request):
        lectures = Lecture.objects.filter(owner_id=request.user.id)
        return Response(LectureSerializer(lectures, many=True).data)

    def post(self, request):
        serializer = LectureCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        lecture = Lecture.objects.create(
            owner_id=request.user.id,
            title=data["title"],
            course=data["course"],
            instructor=data["instructor"],
            semester=data["semester"],
            lecture_date=data["lecture_date"],
            original_filename=data["file"].name,
            output_language=data["output_language"],
            language_code_hint=data["language_code_hint"],
        )

        file_path = save_uploaded_file(lecture.lecture_id, data["file"])
        lecture.stored_file_path = str(file_path)
        lecture.save(update_fields=["stored_file_path"])

        try:
            duration = check_duration_guardrail(file_path)
        except ValidationError as exc:
            lecture.status = Lecture.STATUS_FAILED
            detail = exc.detail[0] if isinstance(exc.detail, list) else exc.detail
            lecture.error_message = str(detail)
            lecture.save()
            raise

        lecture.duration_seconds = duration
        lecture.save(update_fields=["duration_seconds"])

        try:
            ingest_lecture(lecture, file_path)
        except Exception:
            lecture.refresh_from_db()
            return Response(
                {"error": {"code": "ingestion_failed", "message": lecture.error_message}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        return Response(LectureSerializer(lecture).data, status=status.HTTP_201_CREATED)


class LectureDetailView(APIView):
    def get_object(self, request, lecture_id):
        return get_object_or_404(Lecture, lecture_id=lecture_id, owner_id=request.user.id)

    def get(self, request, lecture_id):
        return Response(LectureSerializer(self.get_object(request, lecture_id)).data)

    def delete(self, request, lecture_id):
        lecture = self.get_object(request, lecture_id)
        delete_lecture_data(lecture)
        lecture.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LectureTranscriptView(APIView):
    """GET -- the cleaned transcript text for a lecture. Served from the DB
    (Lecture.transcript, copied there once by services.ingest_lecture) so it
    doesn't depend on the Oracle instance's local disk still having the
    file; falls back to reading straight off disk for old rows ingested
    before this field existed."""

    def get(self, request, lecture_id):
        lecture = get_object_or_404(Lecture, lecture_id=lecture_id, owner_id=request.user.id)

        if lecture.status != Lecture.STATUS_COMPLETED:
            return Response(
                {
                    "error": {
                        "code": "lecture_not_ready",
                        "message": f"Lecture status is '{lecture.status}' -- transcript isn't ready yet.",
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )

        if lecture.transcript:
            return Response({"lecture_id": lecture_id, "text": lecture.transcript})

        transcript_path = pipeline_config.CLEAN_TRANSCRIPT_DIR / f"{lecture_id}.txt"
        if not transcript_path.exists():
            return Response(
                {
                    "error": {
                        "code": "transcript_missing",
                        "message": "This lecture is marked completed but its transcript is missing.",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        text = transcript_path.read_text(encoding="utf-8")
        return Response({"lecture_id": lecture_id, "text": text})