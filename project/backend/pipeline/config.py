"""
Central configuration for the lecture pipeline.
Loads settings from environment variables / .env file.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ─────────────────────────────────────────────
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")  # for Gemini
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "whisper-large-v3-turbo") 
# ── LLM Settings ─────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")  # gemini | openai | anthropic
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.5-flash-lite")

# ── Output Language ──────────────────────────────────────
# The language the FINAL cleaned transcript should be written in.
# Options: "urdu", "english", "arabic", "mixed" (preserve original mix)
OUTPUT_LANGUAGE = os.getenv("OUTPUT_LANGUAGE", "mixed")

# ── Chunking Settings (for LLM cleaning stage) ───────────
# Raw transcripts from long lectures are too big for a single LLM call,
# so we clean them in overlapping chunks and stitch the result back together.
CLEAN_CHUNK_CHAR_SIZE = int(os.getenv("CLEAN_CHUNK_CHAR_SIZE", "6000"))
CLEAN_CHUNK_OVERLAP = int(os.getenv("CLEAN_CHUNK_OVERLAP", "500"))

# When True (default) and OUTPUT_LANGUAGE isn't "mixed", cleaner.py runs a
# second corrective LLM pass over the cleaned transcript to catch residual
# Urdu the first pass missed (Urdu/Arabic share a script, so the model can
# mistake ordinary Urdu for protected Arabic religious content). Costs one
# extra LLM call per chunk -- set False to skip it if that matters more
# than catching leftover Urdu.
ENFORCE_OUTPUT_LANGUAGE = os.getenv("ENFORCE_OUTPUT_LANGUAGE", "true").lower() == "true"

# ── Paths ─────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
# Overridable so the Django backend can point this at MEDIA_ROOT/work instead
# of pipeline/work -- standalone CLI usage is unaffected (falls back to the
# original default when PIPELINE_WORK_DIR isn't set).
WORK_DIR = Path(os.getenv("PIPELINE_WORK_DIR", str(BASE_DIR / "work")))
AUDIO_DIR = WORK_DIR / "audio"
RAW_TRANSCRIPT_DIR = WORK_DIR / "raw_transcripts"
CLEAN_TRANSCRIPT_DIR = WORK_DIR / "clean_transcripts"
VECTOR_DB_DIR = WORK_DIR / "vector_db"
QUIZ_DIR = WORK_DIR / "quizzes"

for d in (AUDIO_DIR, RAW_TRANSCRIPT_DIR, CLEAN_TRANSCRIPT_DIR, VECTOR_DB_DIR, QUIZ_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ── RAG Settings ──────────────────────────────────────────
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
# Spec target: ~700-1200 tokens per chunk, ~100-200 token overlap.
# We size chunks by CHARACTER count instead of actual tokens -- avoids
# needing a tokenizer library (tiktoken requires a one-time download from
# openaipublic.blob.core.windows.net, which fails behind some firewalls, and
# it wouldn't accurately count Gemini/Urdu/Arabic tokens anyway). ~4 chars
# per token is a reasonable rule of thumb, so defaults below approximate the
# spec's 1000/150 token target.
RAG_CHUNK_CHAR_SIZE = int(os.getenv("RAG_CHUNK_CHAR_SIZE", "4000"))
RAG_CHUNK_CHAR_OVERLAP = int(os.getenv("RAG_CHUNK_CHAR_OVERLAP", "600"))
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))  # how many chunks to retrieve per question

# ── RAG Chat: LangGraph retry/decomposition settings ─────
# See chat.py -- weak retrievals get one query rewrite + re-search before
# we give up and generate from whatever was found; broad questions get
# split into a few sub-queries so the answer can draw from chunks spread
# across the lecture instead of just the single best-matching one.
RAG_CONFIDENCE_THRESHOLD = float(os.getenv("RAG_CONFIDENCE_THRESHOLD", "0.5"))
RAG_MAX_RETRIES = int(os.getenv("RAG_MAX_RETRIES", "2"))
RAG_MAX_SUBQUERIES = int(os.getenv("RAG_MAX_SUBQUERIES", "4"))

RAG_MEMORY_ENABLED = os.getenv("RAG_MEMORY_ENABLED", "true").lower() == "true"
# How many previous (question, answer) turns to include -- older turns are
# dropped, not summarized. Keep this small; each turn adds real tokens to
# both the planning call and the generation call, on every question.
RAG_MEMORY_MAX_TURNS = int(os.getenv("RAG_MEMORY_MAX_TURNS", "4"))
 
# ── Quiz Generation Settings ──────────────────────────────
# quiz.py sources from already-ingested vector store chunks (not the raw
# transcript file), batched to fit the LLM's context -- see quiz.py docstring.
QUIZ_BATCH_CHAR_SIZE = int(os.getenv("QUIZ_BATCH_CHAR_SIZE", "8000"))
QUIZ_DEFAULT_NUM_MCQ = int(os.getenv("QUIZ_DEFAULT_NUM_MCQ", "10"))
QUIZ_DEFAULT_NUM_SHORT = int(os.getenv("QUIZ_DEFAULT_NUM_SHORT", "5"))
QUIZ_DEFAULT_NUM_LONG = int(os.getenv("QUIZ_DEFAULT_NUM_LONG", "3"))