import json

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from loguru import logger
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pipeline_bridge import pipeline_quiz
from apps.common.throttles import QuizRateThrottle
from apps.lectures.models import Lecture
from .models import Quiz
from .serializers import QuizGenerateSerializer, QuizSerializer


class LectureQuizListCreateView(APIView):
    """
    GET  -- previously generated quizzes for a lecture (most recent first)
    POST -- generate a fresh quiz from the lecture's vector store chunks.
            Heavily throttled: one call can be several LLM calls (one per
            batch of chunks -- see quiz.py's batching).
    """

    def get_throttles(self):
        if self.request.method == "POST":
            return [QuizRateThrottle()]
        return super().get_throttles()

    def get(self, request, lecture_id):
        lecture = get_object_or_404(Lecture, lecture_id=lecture_id, owner_id=request.user.id)
        return Response(QuizSerializer(lecture.quizzes.all(), many=True).data)

    def post(self, request, lecture_id):
        lecture = get_object_or_404(Lecture, lecture_id=lecture_id, owner_id=request.user.id)
        if lecture.status != Lecture.STATUS_COMPLETED:
            return Response(
                {
                    "error": {
                        "code": "lecture_not_ready",
                        "message": f"Lecture status is '{lecture.status}' -- not ready for quiz generation yet.",
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )

        serializer = QuizGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data

        try:
            quiz_data = pipeline_quiz.generate_quiz(
                lecture.lecture_id,
                num_mcq=params.get("num_mcq"),
                num_short=params.get("num_short"),
                num_long=params.get("num_long"),
            )
        except Exception as exc:
            logger.error(f"Quiz generation failed for lecture '{lecture_id}': {exc}")
            return Response(
                {"error": {"code": "quiz_failed", "message": "Could not generate a quiz -- please try again."}},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        quiz = Quiz.objects.create(
            lecture=lecture,
            num_mcq=len(quiz_data.get("mcqs", [])),
            num_short=len(quiz_data.get("short_questions", [])),
            num_long=len(quiz_data.get("long_questions", [])),
            data=quiz_data,
        )
        return Response(QuizSerializer(quiz).data, status=status.HTTP_201_CREATED)


class LectureQuizExportView(APIView):
    """Download a previously generated quiz as Markdown or JSON, rendered
    straight from the DB-stored JSON -- doesn't depend on the pipeline's
    own work/quizzes/ files still being on disk (those are ephemeral on
    Render's free tier and only meant as a CLI convenience anyway)."""

    def get(self, request, lecture_id, quiz_id):
        quiz = get_object_or_404(
            Quiz, lecture__lecture_id=lecture_id, id=quiz_id, lecture__owner_id=request.user.id
        )
        fmt = request.query_params.get("format", "md")

        if fmt == "json":
            body = json.dumps(quiz.data, ensure_ascii=False, indent=2)
            response = HttpResponse(body, content_type="application/json")
            response["Content-Disposition"] = f'attachment; filename="{lecture_id}-quiz-{quiz_id}.json"'
            return response

        response = HttpResponse(_render_quiz_markdown(quiz.data), content_type="text/markdown")
        response["Content-Disposition"] = f'attachment; filename="{lecture_id}-quiz-{quiz_id}.md"'
        return response


def _render_quiz_markdown(quiz: dict) -> str:
    lecture_id = quiz.get("lecture_id", "")
    lines = [f"# Quiz -- {lecture_id}\n"]

    if quiz.get("mcqs"):
        lines.append("## Multiple Choice Questions\n")
        for i, q in enumerate(quiz["mcqs"], 1):
            lines.append(f"**{i}. ({q.get('difficulty', '?')})** {q.get('question', '')}")
            for j, opt in enumerate(q.get("options", [])):
                marker = "x" if j == q.get("correct_index") else " "
                lines.append(f"- [{marker}] {opt}")
            if q.get("explanation"):
                lines.append(f"  *Explanation:* {q['explanation']}")
            lines.append("")

    if quiz.get("short_questions"):
        lines.append("## Short Answer Questions\n")
        for i, q in enumerate(quiz["short_questions"], 1):
            lines.append(f"**{i}.** {q.get('question', '')}")
            lines.append(f"*Answer:* {q.get('answer', '')}")
            lines.append("")

    if quiz.get("long_questions"):
        lines.append("## Long Answer Questions\n")
        for i, q in enumerate(quiz["long_questions"], 1):
            lines.append(f"**{i}.** {q.get('question', '')}")
            lines.append(f"*Answer guidance:* {q.get('answer_guidance', '')}")
            lines.append("")

    return "\n".join(lines)