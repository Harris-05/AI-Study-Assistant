# AI Lecture Companion — Backend (Django)

Wraps the existing `pipeline/` (unchanged from the CLI project) in a Django +
DRF API so a React frontend can upload lectures, chat with them (RAG), and
generate quizzes, instead of using the CLI.

## Architecture decisions (deliberate, current)

- **Synchronous ingestion.** `POST /api/lectures/` blocks for the full
  duration of transcription → cleaning → embedding. No Celery/queue yet.
  A duration guardrail (`MAX_SYNC_LECTURE_DURATION_SECONDS`, default 20
  min) rejects lectures too long to process inline, before any paid API
  call is made. Raise this, or switch to a background queue, once that
  trade-off stops making sense.
- **No auth.** Anyone who can reach the API can upload/chat/quiz. Rate
  limiting (below) is the only abuse guardrail right now.
- **SQLite**, single file, for lecture/chat/quiz metadata. Chroma (unchanged)
  still holds the vectors.

## ⚠️ Known limitation: Render free tier has an EPHEMERAL filesystem

This is the single most important thing to know before relying on this
deployment for anything real:

> Render's free web services lose **all local filesystem changes** — the
> SQLite DB, uploaded audio, transcripts, and the Chroma vector store —
> every time the service redeploys, restarts, or spins down (which happens
> automatically after 15 minutes of inactivity).

Practically: a lecture you ingest today may be **gone** the next time
someone hits the app after it's been idle. This is fine for demos/testing,
but before using this for real coursework you'll want one of:
- A paid Render plan + a persistent disk attached, or
- An external Postgres (metadata) + external object storage (audio/
  transcripts) + a hosted vector DB (Chroma Cloud / Qdrant Cloud) instead of
  local Chroma.

(Separately: Render's HTTP request timeout is generous — up to 100 minutes —
so the *synchronous* ingestion design itself isn't blocked by a short proxy
timeout on Render specifically; the ephemeral disk is the real constraint.)

## Setup (local)

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in ELEVENLABS_API_KEY, GOOGLE_API_KEY
python manage.py migrate
python manage.py runserver
```

You also need `ffmpeg`/`ffprobe` installed locally (same requirement as the
original CLI project) — see the Dockerfile for the apt package if you'd
rather containerize.

## API

| Method | Path | Notes |
|---|---|---|
| GET | `/api/health/` | unthrottled health check |
| GET | `/api/lectures/` | list lectures |
| POST | `/api/lectures/` | multipart upload (`file`, `title`, `course`, `instructor`, `semester`, `lecture_date`, `output_language`, `language_code_hint`) — **blocks until ingestion finishes** |
| GET | `/api/lectures/{lecture_id}/` | lecture detail/status |
| DELETE | `/api/lectures/{lecture_id}/` | deletes DB row + files + vector collection |
| GET | `/api/lectures/{lecture_id}/chat/` | chat history |
| POST | `/api/lectures/{lecture_id}/chat/` | `{"question": "..."}` → `{answer, sources}` |
| GET | `/api/lectures/{lecture_id}/quiz/` | past quizzes |
| POST | `/api/lectures/{lecture_id}/quiz/` | `{"num_mcq": 10, "num_short": 5, "num_long": 3}` |
| GET | `/api/lectures/{lecture_id}/quiz/{quiz_id}/export/?format=md\|json` | download |

All errors return `{"error": {"code": "...", "message": "..."}}`. Rate-limit
responses (`429`) include `retry_after_seconds`.

## Guardrails in this backend (on top of the pipeline's own retries/validation)

- File type whitelist + size cap on upload (`ALLOWED_UPLOAD_EXTENSIONS`, `MAX_UPLOAD_SIZE_MB`)
- Duration cap for synchronous processing (`MAX_SYNC_LECTURE_DURATION_SECONDS`)
- Per-endpoint rate limiting, since every ingest/chat/quiz call costs real
  ElevenLabs/Gemini usage — see `THROTTLE_*` in `.env.example`
- Uniform error shape, no internal tracebacks/exception detail ever returned
  to the client (`apps/common/exceptions.py`)
- CORS locked to `CORS_ALLOWED_ORIGINS` (your Vercel frontend URL)
- Security headers (HSTS, secure cookies, SSL redirect) auto-enabled when `DJANGO_DEBUG=false`

## Deploying to Render

1. Push this repo, create a new **Web Service** on Render pointing at `backend/`, environment **Docker** (uses the included `Dockerfile`).
2. Set env vars from `.env.example` in Render's dashboard — at minimum `ELEVENLABS_API_KEY`, `GOOGLE_API_KEY`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, `DJANGO_ALLOWED_HOSTS=<your-render-hostname>`, `CORS_ALLOWED_ORIGINS=<your-vercel-url>`.
3. Render sets `PORT` automatically — the Dockerfile's `CMD` already uses it.
4. First deploy: migrations aren't run automatically. Either add a Render "pre-deploy command" of `python manage.py migrate`, or exec into the shell once and run it manually.
5. Remember the ephemeral-disk caveat above — re-verify lectures are still there after any idle period before demoing.

## Notes carried over from the pipeline's own known gaps

See the original `pipeline/` docs (now living alongside this backend) for
pipeline-level gaps (no timestamps in chunks, `transcriber.py` parsing
untested against a real API response, no quiz de-dup across batches, etc.)
— none of that changed by wrapping it in Django.

**One dependency gap I found while wiring this up:** the original
`requirements.txt` didn't list `langgraph`, even though `chat.py` imports
it directly. Added it to `backend/requirements.txt` — if you also maintain
the standalone CLI project's requirements.txt separately, add it there too.
