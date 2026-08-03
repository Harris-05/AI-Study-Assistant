"""
Stage 4a: Clean Transcript -> Chunks (for embedding/retrieval).

Per the spec: chunks sized to hold one focused explanation (~700-1200 tokens,
~100-200 token overlap). We size chunks by CHARACTER count rather than actual
tokens -- see config.py for why (avoids a tokenizer dependency that requires
a network download and wouldn't accurately count Urdu/Arabic tokens anyway).
"""
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger

import config


def chunk_clean_transcript(clean_text: str, lecture_id: str) -> list[dict]:
    """
    Split a cleaned transcript into overlapping chunks ready for embedding.

    Args:
        clean_text: the full cleaned transcript text
        lecture_id: identifier for this lecture, attached to each chunk's metadata

    Returns:
        List of dicts: [{ "text": str, "metadata": {...} }, ...]

    NOTE: the current cleaning stage (cleaner.py) outputs plain stitched text
    without per-sentence timestamps, so chunk metadata here is limited to
    lecture_id + chunk_index (no timestamp_start/end or chapter yet). If you
    want "jump to lecture timestamp" in chat answers, we'll need to carry
    timestamps through the cleaning stage too -- happy to add that next.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.RAG_CHUNK_CHAR_SIZE,
        chunk_overlap=config.RAG_CHUNK_CHAR_OVERLAP,
        separators=["\n\n", "\n", "۔ ", "؟ ", ". ", "! ", " ", ""],  # Urdu/English sentence-ish boundaries first
    )

    raw_chunks = splitter.split_text(clean_text)

    chunks = []
    for i, chunk_text in enumerate(raw_chunks):
        chunks.append({
            "text": chunk_text,
            "metadata": {
                "lecture_id": lecture_id,
                "chunk_index": i,
            },
        })

    logger.info(f"Split clean transcript for '{lecture_id}' into {len(chunks)} chunk(s)")
    return chunks