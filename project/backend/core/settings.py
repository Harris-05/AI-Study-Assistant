"""
Django settings for the AI Lecture Companion backend.

Everything that changes between local/dev and Oracle Cloud/prod is read from
the environment -- see .env.example for the full list. Nothing here should
need editing per-environment; set env vars instead.
"""
import os
import sys
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def env_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# ── Core ──────────────────────────────────────────────────
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "insecure-dev-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

# Public hostname of the Oracle Cloud instance (behind Nginx/Caddy + TLS),
# e.g. lecture-companion.example.com or a bare OCI public IP for testing.
# Kept as its own env var (rather than assuming it's already in
# DJANGO_ALLOWED_HOSTS) so CSRF_TRUSTED_ORIGINS can be derived from it too.
PUBLIC_HOSTNAME = os.getenv("PUBLIC_HOSTNAME")
if PUBLIC_HOSTNAME and PUBLIC_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(PUBLIC_HOSTNAME)

CSRF_TRUSTED_ORIGINS = env_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    f"https://{PUBLIC_HOSTNAME}" if PUBLIC_HOSTNAME else "",
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "apps.common",
    "apps.lectures",
    "apps.chat",
    "apps.quiz",
    "apps.notes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

# ── Database ──────────────────────────────────────────────
# Supabase Postgres in every real environment. DATABASE_URL is the "Connection
# string" (URI / "Transaction pooler" for serverless-style connections) from
# Supabase project settings -> Database -> Connection string, e.g.:
#   postgresql://postgres.xxxxx:[PASSWORD]@aws-0-<region>.pooler.supabase.com:6543/postgres
# Falls back to local SQLite only when DATABASE_URL isn't set (bare
# `python manage.py runserver` with no .env configured yet).
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=int(os.getenv("DATABASE_CONN_MAX_AGE", "60")),
            ssl_require=env_bool("DATABASE_SSL_REQUIRE", True),
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.getenv("SQLITE_PATH", str(BASE_DIR / "db.sqlite3")),
        }
    }

AUTH_PASSWORD_VALIDATORS = []  # accounts live in Supabase Auth, not Django's auth_user table

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Media / pipeline work directory ──────────────────────
# The pipeline (audio extraction, ffmpeg temp files, Chroma's on-disk index)
# needs a real local filesystem to work in regardless of backend -- Chroma
# in particular is an embedded/local vector store, not a hosted service, so
# it always lives on whatever disk the Django process runs on. On Oracle
# Cloud that's the instance's own (persistent, non-ephemeral) block volume,
# which is exactly what this project needed and Render's free tier didn't
# provide -- see README "Architecture decisions".
MEDIA_URL = "media/"
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", str(BASE_DIR / "media")))
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

UPLOADS_DIR = MEDIA_ROOT / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Point the pipeline's own work/ tree (audio, transcripts, chroma, quizzes)
# at a subfolder of MEDIA_ROOT instead of pipeline/work, and add the
# pipeline/ directory to sys.path so its flat `import config` etc. style
# keeps working unchanged, called from Django. This block MUST run before
# anything imports the pipeline package.
PIPELINE_DIR = BASE_DIR / "pipeline"
os.environ.setdefault("PIPELINE_WORK_DIR", str(MEDIA_ROOT / "work"))
if str(PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINE_DIR))

# ── Supabase Storage for the original uploaded audio/video file ─────────
# NOT wired in. The pipeline needs the file on local disk anyway to run
# ffmpeg/transcription on it, and audio/video files routinely exceed
# Supabase's default 50MB per-file bucket limit -- so uploads stay entirely
# on the Oracle Cloud instance's local disk (MEDIA_ROOT, below). Only text
# (transcripts, chat, quizzes) goes to Supabase -- see Lecture.transcript
# in apps/lectures/models.py and the chat/quiz models.

# ── Guardrails (uploads / processing) ────────────────────
# Max upload size, enforced in apps/lectures/validators.py
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "300"))
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE_MB * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # stream anything bigger than 10MB to disk, not RAM

# Max lecture duration accepted for SYNCHRONOUS processing (the request
# blocks until the pipeline finishes -- see project decision to stay sync
# for now). Reject anything longer with a clear error rather than tying up
# a worker/timing out unpredictably. Raise this once ingestion moves to a
# background queue (Celery/RQ).
MAX_SYNC_LECTURE_DURATION_SECONDS = int(os.getenv("MAX_SYNC_LECTURE_DURATION_SECONDS", str(120 * 60)))

ALLOWED_UPLOAD_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma",
                              ".mp4", ".mov", ".mkv", ".webm"}

# ── CORS ──────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5174")
CORS_ALLOW_CREDENTIALS = False  # auth is a Bearer token header, not a cookie -- no credentials needed

# ── Supabase Auth ─────────────────────────────────────────
# The frontend signs users in directly with supabase-js and sends the
# resulting access token as `Authorization: Bearer <jwt>`. The backend never
# sees passwords -- it just verifies the JWT and trusts its `sub` claim as
# the user id (apps/common/authentication.py).
#
# New Supabase projects sign tokens asymmetrically (ES256) by default, and
# are verified against the project's public JWKS endpoint using SUPABASE_URL
# alone -- no secret required. SUPABASE_JWT_SECRET is only needed as a
# fallback for the legacy symmetric (HS256) signing model, i.e. only if this
# project hasn't been migrated to asymmetric JWT signing keys yet (Project
# Settings -> JWT Keys in the Supabase dashboard). Leave it blank once
# you've migrated.
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
SUPABASE_JWT_AUDIENCE = os.getenv("SUPABASE_JWT_AUDIENCE", "authenticated")

# ── DRF: auth is required by default; rate limiting remains the abuse
# guardrail on top of that, since every endpoint triggers paid third-party
# API calls (ElevenLabs / Gemini). ──
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.common.authentication.SupabaseJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("THROTTLE_ANON_RATE", "120/hour"),
        "ingest": os.getenv("THROTTLE_INGEST_RATE", "5/hour"),
        "chat": os.getenv("THROTTLE_CHAT_RATE", "30/hour"),
        "quiz": os.getenv("THROTTLE_QUIZ_RATE", "10/hour"),
        "notes": os.getenv("THROTTLE_NOTES_RATE", "10/hour"),
    },
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
}

# ── Security hardening (only meaningfully active when DEBUG=False) ──────
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.getenv("DJANGO_LOG_LEVEL", "INFO")},
}
