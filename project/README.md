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


