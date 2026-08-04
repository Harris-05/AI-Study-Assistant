"""
Scoped rate throttles. Each expensive endpoint (lecture ingestion, chat,
quiz generation) gets its own scope and rate -- see settings.REST_FRAMEWORK
DEFAULT_THROTTLE_RATES for the actual numbers (env-overridable). Scoping
them separately means a burst of chat questions can't also starve the
ingest quota, and vice versa.

All are per-client-IP (DRF's default ScopedRateThrottle key), since there's
no auth yet (per project decision). Once accounts exist, swap the key
function to use the user id instead of IP.
"""
from rest_framework.throttling import ScopedRateThrottle


class IngestRateThrottle(ScopedRateThrottle):
    scope = "ingest"


class ChatRateThrottle(ScopedRateThrottle):
    scope = "chat"


class QuizRateThrottle(ScopedRateThrottle):
    scope = "quiz"


class NotesRateThrottle(ScopedRateThrottle):
    scope = "notes"
