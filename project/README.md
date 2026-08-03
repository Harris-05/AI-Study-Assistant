# AI Lecture Companion

Full-stack wrapper around the existing lecture-processing pipeline
(transcribe → clean → chunk → embed → RAG chat / quiz generation) so it's
usable from a browser instead of the CLI.

```
project/
├── backend/     Django + DRF API, wraps pipeline/ unchanged
│   └── pipeline/  the original CLI pipeline, copied in as-is (see its own docs)
└── frontend/    React (Vite) SPA
```

Start with **`backend/README.md`** and **`frontend/README.md`** — each has
its own setup/deploy steps. This file is just the map + the two things
worth knowing before you deploy anything.

## 1. Architecture decisions made for this build (see backend/README.md for detail)

- Lecture ingestion is **synchronous** (the upload request blocks until done) — no background job queue yet.
- **No auth** yet — anything reaching the API can use it. Rate limiting per endpoint is the current abuse guardrail.
- **SQLite** for metadata, **Chroma** (local, unchanged) for vectors.

These were explicit trade-offs for a first deployable version, not
oversights — each is called out with what to change if/when it stops being
the right call.

## 2. ⚠️ Before you deploy for real use: read about Render's free-tier ephemeral disk

Render's free web services **lose all local filesystem changes** — the
SQLite DB, uploaded lectures, transcripts, and the Chroma vector store —
every time the service redeploys, restarts, or spins down (after 15 minutes
idle). Great for testing the full flow end-to-end; **not** suitable for
storing lectures you actually care about keeping. Full detail and upgrade
paths are in `backend/README.md`.

## 3. Deploy order

1. **Backend → Render**: see `backend/README.md`. You'll get a public URL like `https://your-app.onrender.com`.
2. **Frontend → Vercel**: see `frontend/README.md`, set `VITE_API_BASE_URL` to that Render URL.
3. Back in Render, set `CORS_ALLOWED_ORIGINS` to your Vercel URL (e.g. `https://your-app.vercel.app`) so the browser is allowed to call the API.
4. Visit the Vercel URL, upload a short test lecture first (well under the
   20-minute sync-processing guardrail) to confirm both ends are wired
   together before trying anything longer.

## 4. Everything pipeline-specific (known gaps, config reference, etc.)

Unchanged from before this backend/frontend was built — still applies, see
the original pipeline docs now living under `backend/pipeline/` alongside
this build's `backend/README.md`.
