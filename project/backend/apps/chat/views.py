from django.shortcuts import get_object_or_404
from loguru import logger
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pipeline_bridge import pipeline_chat, pipeline_config
from apps.common.throttles import ChatRateThrottle
from apps.lectures.models import Lecture
from .models import ChatMessage
from .serializers import AskSerializer, ChatMessageSerializer


class LectureChatView(APIView):
    """
    GET  -- chat history for a lecture (most recent last)
    POST -- ask a question; runs the LangGraph RAG loop and persists the
            exchange. Throttled since each call is at least one, often
            several, LLM calls (plan -> retrieve -> [retry] -> generate).

            Recent prior turns from this lecture's chat history are passed
            in as short-term memory so follow-up questions ("what about
            its subtypes?") resolve correctly -- see pipeline/chat.py and
            the RAG_MEMORY_* settings in pipeline/config.py for how much
            history is actually used and how to disable it.
    """

    def get_throttles(self):
        if self.request.method == "POST":
            return [ChatRateThrottle()]
        return super().get_throttles()

    def get(self, request, lecture_id):
        lecture = get_object_or_404(Lecture, lecture_id=lecture_id, owner_id=request.user.id)
        messages = lecture.chat_messages.all()
        return Response(ChatMessageSerializer(messages, many=True).data)

    def post(self, request, lecture_id):
        lecture = get_object_or_404(Lecture, lecture_id=lecture_id, owner_id=request.user.id)
        if lecture.status != Lecture.STATUS_COMPLETED:
            return Response(
                {
                    "error": {
                        "code": "lecture_not_ready",
                        "message": f"Lecture status is '{lecture.status}' -- not ready for chat yet.",
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )

        serializer = AskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question = serializer.validated_data["question"]

        # Pull just enough recent history for the pipeline's memory window --
        # no point fetching the whole conversation when chat.py will only
        # use the last RAG_MEMORY_MAX_TURNS anyway. Fetched newest-first
        # then reversed so it ends up oldest-first, matching what chat.py
        # expects ("most recent last").
        recent = list(
            lecture.chat_messages.order_by("-created_at")[: pipeline_config.RAG_MEMORY_MAX_TURNS]
        )
        history = [{"question": m.question, "answer": m.answer} for m in reversed(recent)]

        try:
            result = pipeline_chat.ask(lecture.lecture_id, question, history=history)
        except Exception as exc:
            logger.error(f"Chat failed for lecture '{lecture_id}': {exc}")
            return Response(
                {"error": {"code": "chat_failed", "message": "Could not generate an answer -- please try again."}},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        message = ChatMessage.objects.create(
            lecture=lecture,
            question=question,
            answer=result["answer"],
            sources=result["sources"],
        )
        return Response(ChatMessageSerializer(message).data, status=status.HTTP_201_CREATED)