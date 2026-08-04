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
- **Auth via Supabase.** The frontend signs users in directly with
  `supabase-js`; this backend never sees passwords. It verifies the resulting
  JWT on every request (`apps/common/authentication.py`) and scopes every
  lecture/chat/quiz to `request.user.id`. See "Authentication" below.
- **Postgres (Supabase)** for lecture/chat/quiz metadata. Chroma (unchanged)
  still holds the vectors, on the server's own local disk (see next section)
  — it's an embedded vector store, not a hosted service.

## Persistence model

| Data | Lives in | Why |
|---|---|---|
| User accounts, sessions | Supabase Auth | not touched by Django at all |
| Lecture/chat/quiz metadata | Supabase Postgres (`DATABASE_URL`) | durable, survives redeploys |
| Original uploaded audio/video | Supabase Storage (`SUPABASE_S3_BUCKET`), or local disk if unset | durable, browsable object storage |
| Transcripts, Chroma vector index, ffmpeg temp files | Local disk (`MEDIA_ROOT`) on the Oracle Cloud instance | Chroma is embedded — always local to the process; put `MEDIA_ROOT` on a persistent OCI Block Volume so it survives container restarts |

This replaces the earlier Render-based design, whose free tier wiped its
entire local filesystem (SQLite DB, uploads, Chroma index) on every
redeploy/restart/idle spin-down. Because metadata now lives in Supabase and
the Oracle instance's disk is a real persistent volume (not ephemeral), that
failure mode no longer applies — the only thing that still needs to survive
on the box itself is the Chroma index + raw transcripts, which now live on a
mounted volume (see `docker-compose.yml`).

## Authentication

- Frontend: `supabase.auth.signUp()` / `signInWithPassword()` create the
  account and session; `frontend/src/api.js` attaches
  `Authorization: Bearer <access_token>` to every API call automatically.
- Backend: `apps/common/authentication.py`'s `SupabaseJWTAuthentication`
  verifies the session token against the project's public JWKS endpoint
  (asymmetric ES256, current default for new Supabase projects — no shared
  secret needed) and trusts its `sub` claim as the user id. It falls back
  to a shared `SUPABASE_JWT_SECRET` only for legacy HS256 tokens, i.e. only
  if the project hasn't been migrated to asymmetric JWT signing keys yet
  (Project Settings → JWT Keys in the dashboard). `IsAuthenticated` is the
  default DRF permission, so every endpoint except `/api/health/` requires
  a valid session.
- Data isolation: `Lecture.owner_id` stores the Supabase user id; every
  lecture/chat/quiz view filters and creates against `request.user.id`, so
  one account can never see another's lectures. Ownership isn't
  additionally enforced at the database level (no Postgres Row Level
  Security policies) — the Django views are the only enforcement point,
  which is fine as long as everything goes through this API and nothing
  else is given a Supabase secret key.

## Setup (local)

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in ELEVENLABS_API_KEY, GOOGLE_API_KEY,
                        # SUPABASE_URL (required -- see note below), and
                        # DATABASE_URL (optional locally, falls back to
                        # SQLite if left blank)
python manage.py migrate
python manage.py runserver
```

You also need `ffmpeg`/`ffprobe` installed locally (same requirement as the
original CLI project) — see the Dockerfile for the apt package if you'd
rather containerize.

**`SUPABASE_URL` is required even for local dev.** Auth is verified against
that project's JWKS endpoint, so without it every request 401s
(`SupabaseJWTAuthentication` refuses to trust unverifiable tokens rather
than silently letting everyone through). You need a real (free) Supabase
project here, and the frontend's `.env` needs the matching
`VITE_SUPABASE_URL`/`VITE_SUPABASE_PUBLISHABLE_KEY` — even if `DATABASE_URL`
is left blank so Django itself still uses local SQLite.

## API

All endpoints below except `/api/health/` require `Authorization: Bearer
<supabase access token>` and are scoped to the caller — you only ever see
your own lectures.

| Method | Path | Notes |
|---|---|---|
| GET | `/api/health/` | unauthenticated, unthrottled health check |
| GET | `/api/lectures/` | list **your** lectures |
| POST | `/api/lectures/` | multipart upload (`file`, `title`, `course`, `instructor`, `semester`, `lecture_date`, `output_language`, `language_code_hint`) — **blocks until ingestion finishes** |
| GET | `/api/lectures/{lecture_id}/` | lecture detail/status (404 if not yours) |
| DELETE | `/api/lectures/{lecture_id}/` | deletes DB row + files + vector collection |
| GET | `/api/lectures/{lecture_id}/chat/` | chat history |
| POST | `/api/lectures/{lecture_id}/chat/` | `{"question": "..."}` → `{answer, sources}` |
| GET | `/api/lectures/{lecture_id}/quiz/` | past quizzes |
| POST | `/api/lectures/{lecture_id}/quiz/` | `{"num_mcq": 10, "num_short": 5, "num_long": 3}` |
| GET | `/api/lectures/{lecture_id}/quiz/{quiz_id}/export/?format=md\|json` | download |

All errors return `{"error": {"code": "...", "message": "..."}}`. Rate-limit
responses (`429`) include `retry_after_seconds`; a missing/expired/invalid
token returns `401` with `code: "request_error"`.

## Guardrails in this backend (on top of the pipeline's own retries/validation)

- File type whitelist + size cap on upload (`ALLOWED_UPLOAD_EXTENSIONS`, `MAX_UPLOAD_SIZE_MB`)
- Duration cap for synchronous processing (`MAX_SYNC_LECTURE_DURATION_SECONDS`)
- Per-endpoint rate limiting, since every ingest/chat/quiz call costs real
  ElevenLabs/Gemini usage — see `THROTTLE_*` in `.env.example`
- Uniform error shape, no internal tracebacks/exception detail ever returned
  to the client (`apps/common/exceptions.py`)
- CORS locked to `CORS_ALLOWED_ORIGINS` (your deployed frontend's URL)
- Security headers (HSTS, secure cookies, SSL redirect) auto-enabled when `DJANGO_DEBUG=false`

## Deploying: Supabase + Oracle Cloud

### 1. Supabase project (5–10 min)

1. Create a project at supabase.com.
2. **Database** — Project Settings → Database → Connection string → copy the
   pooled "Transaction" URI (port `6543`) into `DATABASE_URL`.
3. **Auth** — Project Settings → API → copy the **Project URL** into
   `SUPABASE_URL` for both the backend and frontend `.env` (this is what
   the backend verifies session tokens against — see "Authentication"
   below). Under API Keys, copy the **Publishable key** into the frontend's
   `VITE_SUPABASE_PUBLISHABLE_KEY`. Leave the backend's
   `SUPABASE_JWT_SECRET` blank unless the project still shows a legacy JWT
   Secret (Project Settings → JWT Keys) that you haven't migrated off yet.
   In Authentication → Providers, email/password is on by default; turn
   "Confirm email" off if you want signups to log straight in during
   testing.
4. **Storage** (optional but recommended) — create a private bucket, e.g.
   `lecture-uploads`. Storage → Settings gives you the S3-compatible
   endpoint for `SUPABASE_S3_ENDPOINT_URL`; Storage → Access Keys (or
   Project Settings → API, "S3 Access Keys") gives you
   `SUPABASE_S3_ACCESS_KEY_ID` / `SUPABASE_S3_SECRET_ACCESS_KEY`. Leave
   `SUPABASE_S3_BUCKET` unset to keep original uploads on the Oracle
   instance's local disk instead.
5. Run migrations against Supabase once, from anywhere with `DATABASE_URL`
   set (locally, or from the Oracle instance in step 2 below):
   `python manage.py migrate`.

### 2. Oracle Cloud compute instance (OCI)

Any shape works; the **Always Free Ampere A1** (ARM, 4 OCPU/24GB) tier is
enough for this and costs nothing.

1. Create the instance (Ubuntu 22.04+ image), attach a **Block Volume** for
   persistent lecture data (transcripts + Chroma index), and open port
   `443`/`80` (and `22` for SSH) in its **Security List / Network Security
   Group**.
2. SSH in, install Docker + the compose plugin:
   ```bash
   curl -fsSL https://get.docker.com | sudo sh
   sudo usermod -aG docker $USER   # re-login after this
   ```
3. Mount the block volume at, e.g., `/data` (format it first if it's new —
   OCI's console walks through this), then clone this repo and configure:
   ```bash
   git clone <your-repo-url> lecture-companion && cd lecture-companion
   cp backend/.env.example backend/.env
   # edit backend/.env: DATABASE_URL, SUPABASE_*, ELEVENLABS_API_KEY,
   # GOOGLE_API_KEY, DJANGO_SECRET_KEY, DJANGO_DEBUG=false,
   # DJANGO_ALLOWED_HOSTS / PUBLIC_HOSTNAME, CORS_ALLOWED_ORIGINS
   ```
4. Build and run (see `docker-compose.yml` at the repo root):
   ```bash
   docker compose up -d --build
   ```
   The entrypoint (`entrypoint.sh`) runs `manage.py migrate` automatically
   on every start, then launches gunicorn on `:8000`.
5. Put TLS in front of it — either:
   - **Nginx + certbot** on the same instance, reverse-proxying `/` to a
     static build of `frontend/` and `/api/` (and `/media/`, if you skip
     Supabase Storage) to `127.0.0.1:8000`, with `proxy_read_timeout`
     comfortably above `MAX_SYNC_LECTURE_DURATION_SECONDS`; or
   - A **Cloudflare Tunnel**, which avoids opening inbound ports at all and
     handles TLS for you.
6. Once you have a domain, set `PUBLIC_HOSTNAME` in `backend/.env` to it and
   restart (`docker compose up -d`) so it's added to
   `DJANGO_ALLOWED_HOSTS`/`DJANGO_CSRF_TRUSTED_ORIGINS` automatically.

### 3. Frontend

Build with `VITE_API_BASE_URL` pointing at your Oracle instance's public
URL and `VITE_SUPABASE_URL`/`VITE_SUPABASE_ANON_KEY` from step 1 — see
`frontend/README.md`. You can serve the static build from the same Nginx
in front of the backend, or host it anywhere static (Vercel, Netlify,
another OCI Nginx block) as long as its origin is in `CORS_ALLOWED_ORIGINS`.

### Redeploying

```bash
git pull
docker compose up -d --build   # rebuilds image, re-runs migrate, restarts
```

## Notes carried over from the pipeline's own known gaps

See the original `pipeline/` docs (now living alongside this backend) for
pipeline-level gaps (no timestamps in chunks, `transcriber.py` parsing
untested against a real API response, no quiz de-dup across batches, etc.)
— none of that changed by wrapping it in Django.

**One dependency gap I found while wiring this up:** the original
`requirements.txt` didn't list `langgraph`, even though `chat.py` imports
it directly. Added it to `backend/requirements.txt` — if you also maintain
the standalone CLI project's requirements.txt separately, add it there too.