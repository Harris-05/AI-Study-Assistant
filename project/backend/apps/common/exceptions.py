"""
Central DRF exception handler.

Two goals:
  1. Every error response has the same shape: {"error": {"code": ..., "message": ...}}
     so the frontend can handle errors generically.
  2. Nothing internal (stack traces, exception class names, file paths) ever
     reaches the client -- especially important since several endpoints wrap
     third-party API calls (ElevenLabs/Gemini) whose raw errors shouldn't be
     forwarded verbatim.
"""
import logging

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import Throttled

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, Throttled):
        wait = getattr(exc, "wait", None)
        return Response(
            {
                "error": {
                    "code": "rate_limited",
                    "message": "Too many requests -- please slow down.",
                    "retry_after_seconds": wait,
                }
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    if response is not None:
        detail = response.data.get("detail") if isinstance(response.data, dict) else response.data
        response.data = {"error": {"code": "request_error", "message": str(detail)}}
        return response

    # Unhandled exception -- log full detail server-side, return a generic
    # message to the client (never leak internals from an unexpected 500).
    logger.exception("Unhandled exception in API view")
    return Response(
        {"error": {"code": "server_error", "message": "Something went wrong processing your request."}},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
