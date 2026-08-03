"""
Django settings for the AI Lecture Companion backend.

Everything that changes between local/dev and Render/prod is read from the
environment -- see .env.example for the full list. Nothing here should need
editing per-environment; set env vars instead.
"""
import os
import sys
from pathlib import Path

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

# Render sets this so we know our own public hostname for ALLOWED_HOSTS/CSRF
RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

CSRF_TRUSTED_ORIGINS = env_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    f"https://{RENDER_EXTERNAL_HOSTNAME}" if RENDER_EXTERNAL_HOSTNAME else "",
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
# SQLite by default (per project decision -- simple now, upgrade later).
# NOTE: on Render's free tier the filesystem is EPHEMERAL -- this file (and
# every uploaded lecture, transcript, and Chroma vector store) is wiped on
# every redeploy, restart, or free-tier spin-down. Fine for demoing; do not
# rely on it for real persistence until a paid plan + persistent disk (or an
# external Postgres) is attached. See backend/README.md.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.getenv("SQLITE_PATH", str(BASE_DIR / "db.sqlite3")),
    }
}

AUTH_PASSWORD_VALIDATORS = []  # no user accounts yet (per project decision)

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
MAX_SYNC_LECTURE_DURATION_SECONDS = int(os.getenv("MAX_SYNC_LECTURE_DURATION_SECONDS", str(20 * 60)))

ALLOWED_UPLOAD_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma",
                              ".mp4", ".mov", ".mkv", ".webm"}

# ── CORS ──────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
CORS_ALLOW_CREDENTIALS = False

# ── DRF: rate limiting is the main abuse guardrail here, since every
# endpoint triggers paid third-party API calls (ElevenLabs / Gemini). ──
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("THROTTLE_ANON_RATE", "120/hour"),
        "ingest": os.getenv("THROTTLE_INGEST_RATE", "5/hour"),
        "chat": os.getenv("THROTTLE_CHAT_RATE", "30/hour"),
        "quiz": os.getenv("THROTTLE_QUIZ_RATE", "10/hour"),
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
