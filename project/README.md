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
- **Auth via Supabase Auth.** The frontend signs users in with `supabase-js`;
  the backend verifies the resulting JWT on every request and scopes all
  data to the caller. Rate limiting per endpoint is the abuse guardrail on
  top of that.
- **Supabase Postgres** for metadata, **Supabase Storage** (optional) for
  original uploaded audio/video, **Chroma** (local, unchanged) for vectors
  on the Oracle Cloud instance's own persistent disk.

These were explicit trade-offs, not oversights — each is called out with
what to change if/when it stops being the right call. See `backend/README.md`
→ "Persistence model" for the full data-placement table.

## 2. Deploy order

1. **Supabase project**: create it, grab `DATABASE_URL` + `SUPABASE_JWT_SECRET`
   + (optionally) Storage S3 credentials. See `backend/README.md` → "Deploying:
   Supabase + Oracle Cloud", step 1.
2. **Backend → Oracle Cloud**: `docker compose up -d --build` on an OCI
   compute instance, per `backend/README.md` step 2 and the root
   `docker-compose.yml`. You'll end up with a public URL, e.g.
   `https://api.yourdomain.com`.
3. **Frontend → build/host anywhere static**: see `frontend/README.md`. Set
   `VITE_API_BASE_URL` to the Oracle backend URL and
   `VITE_SUPABASE_URL`/`VITE_SUPABASE_ANON_KEY` from step 1.
4. On the Oracle instance, set `CORS_ALLOWED_ORIGINS` to wherever the
   frontend ends up so the browser is allowed to call the API.
5. Visit the frontend, sign up for an account, then upload a short test
   lecture first (well under the 20-minute sync-processing guardrail) to
   confirm everything is wired together before trying anything longer.

## 3. Everything pipeline-specific (known gaps, config reference, etc.)

Unchanged from before this backend/frontend was built — still applies, see
the original pipeline docs now living under `backend/pipeline/` alongside
this build's `backend/README.md`.