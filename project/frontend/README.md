# AI Lecture Companion — Frontend (React + Vite)

Plain React (no UI framework dependency) talking to the Django backend's
REST API. Upload a lecture, chat with it, generate/export quizzes.

## Local dev

```bash
cd frontend
npm install
cp .env.example .env    # point VITE_API_BASE_URL at your backend
npm run dev
```

## Notes on the upload flow

Ingestion is synchronous on the backend (see backend README) — the upload
request stays open until transcription/cleaning/embedding finish. For a
1-hour lecture this can take several minutes; the UI shows a spinner and
disables the form, but doesn't paginate/stream progress (no background job
status to poll yet). Don't navigate away mid-upload.

## Deploying to Vercel

1. Import the repo in Vercel, set the project root to `frontend/`.
2. Framework preset: Vite.
3. Set env var `VITE_API_BASE_URL` to your deployed backend's URL (e.g. your Render service URL).
4. `vercel.json` here handles SPA client-side routing (React Router) so deep links like `/lectures/abc123` don't 404 on refresh.
