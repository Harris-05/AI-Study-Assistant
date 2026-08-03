"""
Stage 4b: Chunks -> Vector Store (embed + store), and retrieval for RAG chat.

Uses Chroma as the vector DB -- runs fully local (no server to set up), which
matches the spec's suggested options (Qdrant/Chroma/Weaviate) and is the
simplest to develop against on Windows. Swapping to Qdrant/Weaviate later is
a small change since LangChain wraps all three with the same interface.

Embeddings come from Gemini (gemini-embedding-001) so you don't need a
separate embeddings provider/API key beyond the GOOGLE_API_KEY you already
have for the cleaning stage.

Each lecture gets its own Chroma "collection" (namespace), named after its
lecture_id, so retrieval can be scoped to one lecture or you can query across
all of them by iterating collections (see get_all_lecture_ids()).
"""
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
from loguru import logger

import config
import chunker


def _get_embeddings() -> GoogleGenerativeAIEmbeddings:
    if not config.GOOGLE_API_KEY:
        raise ValueError(
            "GOOGLE_API_KEY is not set. Add it to your .env file -- the same "
            "key used for the cleaning stage also covers embeddings."
        )
    return GoogleGenerativeAIEmbeddings(
        model=config.EMBEDDING_MODEL,
        google_api_key=config.GOOGLE_API_KEY,
    )


def _get_store(lecture_id: str) -> Chroma:
    """Get (or create) the Chroma collection for one lecture."""
    return Chroma(
        collection_name=lecture_id,
        embedding_function=_get_embeddings(),
        persist_directory=str(config.VECTOR_DB_DIR),
    )


def ingest_transcript(clean_text: str, lecture_id: str) -> int:
    """
    Chunk + embed + store a cleaned transcript for a lecture.

    This is idempotent-ish: it recreates the collection for this lecture_id
    each time, so re-running ingestion after editing a transcript won't leave
    stale/duplicate chunks behind.

    Returns:
        Number of chunks ingested.
    """
    chunks = chunker.chunk_clean_transcript(clean_text, lecture_id)
    if not chunks:
        raise ValueError(f"No chunks produced for lecture_id='{lecture_id}' -- is the transcript empty?")

    documents = [
        Document(page_content=c["text"], metadata=c["metadata"])
        for c in chunks
    ]

    store = _get_store(lecture_id)

    # Clear any existing vectors for this lecture before re-ingesting, so
    # editing/re-cleaning a transcript and re-running doesn't accumulate
    # duplicate/stale chunks in the collection.
    try:
        existing = store.get()
        if existing and existing.get("ids"):
            store.delete(ids=existing["ids"])
    except Exception as e:
        logger.warning(f"Could not clear existing vectors for '{lecture_id}' before re-ingest: {e}")

    store.add_documents(documents)
    logger.info(f"Ingested {len(documents)} chunk(s) into vector store for lecture_id='{lecture_id}'")
    return len(documents)


def get_retriever(lecture_id: str, k: int | None = None):
    """Return a LangChain retriever scoped to one lecture's collection."""
    store = _get_store(lecture_id)
    return store.as_retriever(search_kwargs={"k": k or config.RAG_TOP_K})


def search_with_scores(lecture_id: str, query: str, k: int | None = None) -> list[tuple[Document, float]]:
    """
    Like get_retriever(), but also returns a relevance score (0-1, higher is
    more relevant) per chunk -- used to surface a confidence score in chat
    answers per the spec's "Chat Features" section.

    NOTE: Chroma's relevance score is a normalized distance, not a calibrated
    probability -- treat it as a rough "how close is this chunk" signal, not
    a statement about answer correctness.
    """
    store = _get_store(lecture_id)
    return store.similarity_search_with_relevance_scores(query, k=k or config.RAG_TOP_K)


def get_all_chunks(lecture_id: str) -> list[Document]:
    """
    Fetch every chunk stored for one lecture, sorted by chunk_index.

    Unlike get_retriever()/search_with_scores(), which do a similarity
    search against a query, this pulls the ENTIRE collection -- used by
    quiz.py, which needs comprehensive coverage of the whole lecture rather
    than the chunks most relevant to one question.
    """
    store = _get_store(lecture_id)
    raw = store.get()  # {"ids": [...], "documents": [...], "metadatas": [...]}
    docs = [
        Document(page_content=text, metadata=meta)
        for text, meta in zip(raw.get("documents", []), raw.get("metadatas", []))
    ]
    docs.sort(key=lambda d: d.metadata.get("chunk_index", 0))
    return docs


def get_all_lecture_ids() -> list[str]:
    """
    List lecture_ids that have been ingested into the vector store, by
    inspecting Chroma's persisted collections directly.
    """
    import chromadb
    client = chromadb.PersistentClient(path=str(config.VECTOR_DB_DIR))
    return [c.name for c in client.list_collections()]