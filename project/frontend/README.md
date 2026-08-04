# AI Lecture Companion — Frontend (React + Vite)

Plain React (no UI framework dependency) talking to the Django backend's
REST API, with Supabase Auth for sign up/sign in. Upload a lecture, chat
with it, generate/export quizzes.

## Auth

`src/supabaseClient.js` holds the `supabase-js` client, using Supabase's
current key model — a **publishable key** (`sb_publishable_...`,
`VITE_SUPABASE_PUBLISHABLE_KEY`), not the legacy `anon` key JWT (though that
still works as a fallback if your project hasn't migrated yet — see
`.env.example`). `src/context/AuthContext.jsx` exposes the current
session/user plus `signUp`/`signIn`/`signOut` via `useAuth()`.
`src/components/ProtectedRoute.jsx` redirects to `/login` if there's no
session. `src/api.js` reads the current Supabase session and attaches
`Authorization: Bearer <token>` to every backend request automatically — no
manual token plumbing needed elsewhere.

## Local dev

```bash
cd frontend
npm install
cp .env.example .env    # VITE_API_BASE_URL, VITE_SUPABASE_URL, VITE_SUPABASE_PUBLISHABLE_KEY
npm run dev
```

`VITE_SUPABASE_URL` must point at the same Supabase project as the
backend's `SUPABASE_URL` — the backend verifies session tokens against that
project's JWKS endpoint, so a mismatch means every request 401s.

## Notes on the upload flow

Ingestion is synchronous on the backend (see backend README) — the upload
request stays open until transcription/cleaning/embedding finish. For a
1-hour lecture this can take several minutes; the UI shows a spinner and
disables the form, but doesn't paginate/stream progress (no background job
status to poll yet). Don't navigate away mid-upload.

## Deploying

The frontend is a static Vite build (`npm run build` → `dist/`) and doesn't
need to live on the same host as the backend — as long as its origin is in
the backend's `CORS_ALLOWED_ORIGINS`. Two common options:

- **Same Oracle Cloud instance as the backend**: build `dist/`, serve it
  with the Nginx already sitting in front of the Django container (see
  `backend/README.md` step 2.5), proxying `/api/` through to the backend
  container and everything else to `dist/index.html` (SPA fallback, for
  React Router deep links like `/app/lectures/abc123`).
- **Any static host** (Vercel, Netlify, Cloudflare Pages, etc.): import the
  repo, set the project root to `frontend/`, framework preset Vite, and set
  `VITE_API_BASE_URL`/`VITE_SUPABASE_URL`/`VITE_SUPABASE_PUBLISHABLE_KEY` as
  env vars. `vercel.json` here already handles SPA client-side routing so
  deep links don't 404 on refresh if you go this route.