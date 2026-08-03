"""
Stage 6: RAG Chatbot -- built as a LangGraph graph instead of a single
straight-line LangChain chain, so it can:

  1. RETRY weak retrievals. If the first search comes back with low
     similarity scores (e.g. student used an English term but the lecture
     used the Urdu one, or phrased the question very differently from how
     the instructor said it), the graph rewrites the query and searches
     again -- up to config.RAG_MAX_RETRIES times -- before giving up.

  2. HANDLE BROAD QUESTIONS whose answer is scattered across multiple
     chunks (e.g. "summarize everything about inheritance", "what mistakes
     did the teacher warn about throughout the lecture"). A planning step
     decides if the question is narrow (one search) or broad, and if
     broad, splits it into a few sub-queries that each target a different
     angle, merges all the retrieved chunks, then generates one answer
     from the combined set.

Graph shape:

    question --> plan --> retrieve --> grade --+--> [weak & retries left] --> rewrite --> retrieve (loop)
                                                 |
                                                 +--> [strong enough / out of retries] --> generate --> answer

The final-answer system prompt is unchanged from the original chain
version: ground strictly in retrieved chunks, explicitly say "not covered"
instead of guessing.
"""
import json
from typing import TypedDict

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from loguru import logger

import config
import vectorstore

# ── Prompts ───────────────────────────────────────────────

SYSTEM_PROMPT = """You are a study assistant answering questions about ONE specific university \
lecture, using ONLY the lecture excerpts provided below as context.

RULES -- follow these exactly:
1. Answer using ONLY information present in the provided lecture excerpts. Do not use \
outside knowledge, even if you know the correct answer from general training.
2. If the excerpts do not contain enough information to answer the question, say clearly: \
"The lecture does not cover this topic" (or similarly clear language) -- do NOT guess or \
make up an answer.
3. The lecture may mix Urdu, English, and Arabic -- answer in the same language the student \
asked their question in, unless they ask for a specific language.
4. Preserve technical terms in their original form (don't translate "Inheritance" -> "وراثت", etc).
5. Be concise and direct -- this is a study aid, not an essay. A few sentences is usually enough \
unless the question genuinely needs a longer explanation. If the excerpts cover several distinct \
points relevant to a broad question, synthesize them into one coherent answer rather than listing \
excerpts one by one.
6. Do not mention "the excerpts" or "the context" explicitly to the student -- just answer as \
if you'd watched the lecture yourself.
"""

USER_PROMPT = """Lecture excerpts:
---
{context}
---

Student's question: {question}
"""

PLAN_SYSTEM_PROMPT = """You are deciding how to search a lecture transcript's vector index \
to answer a student's question.

If the question is narrow (asks about one specific concept, definition, or moment), return \
just that one query.

If the question is broad -- asks for a summary, "everything about X", a comparison, a list \
of all examples/mistakes/definitions, or otherwise likely has its answer scattered across \
multiple parts of the lecture -- break it into 2-4 focused sub-queries that together cover \
the different angles of the question.

Return ONLY a JSON array of strings, nothing else. No markdown, no preamble, no explanation.

Example 1
Question: What is polymorphism?
["What is polymorphism?"]

Example 2
Question: Summarize everything the lecture said about inheritance
["definition of inheritance", "examples of inheritance given in the lecture", "problems or common mistakes related to inheritance mentioned", "how inheritance relates to other OOP concepts discussed"]
"""

REWRITE_SYSTEM_PROMPT = """The following search query returned weak/low-relevance results from a \
lecture transcript's vector index. Rewrite it as a DIFFERENT search query that might match how \
the lecture actually phrased this -- try synonyms, the English term if the original looks Urdu \
(or vice versa), a more literal phrasing, or a slightly broader/narrower version. Return ONLY the \
rewritten query text, nothing else -- no quotes, no preamble."""


class ChatState(TypedDict):
    lecture_id: str
    question: str
    k: int
    queries: list[str]
    retrieved: dict  # key -> (Document, score), merged/deduped across retries+subqueries
    attempt: int
    answer: str
    sources: list[dict]


def _get_llm(temperature: float) -> ChatGoogleGenerativeAI:
    if not config.GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY is not set. Add it to your .env file.")
    return ChatGoogleGenerativeAI(
        model=config.LLM_MODEL,
        google_api_key=config.GOOGLE_API_KEY,
        temperature=temperature,
    )


def _format_context(docs: list) -> str:
    parts = []
    for i, doc in enumerate(docs):
        chunk_idx = doc.metadata.get("chunk_index", "?")
        parts.append(f"[Excerpt {i + 1} | chunk #{chunk_idx}]\n{doc.page_content}")
    return "\n\n".join(parts)


def _parse_query_list(raw: str, fallback: str) -> list[str]:
    """Parse the planner's JSON array response; fall back to the original
    question if the model didn't return valid JSON (keeps the graph
    resilient to an occasional malformed planning response)."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[-1] if "\n" in raw else raw
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list) and parsed and all(isinstance(q, str) and q.strip() for q in parsed):
            return [q.strip() for q in parsed]
    except (json.JSONDecodeError, TypeError):
        pass
    logger.warning(f"Could not parse planned queries from: '{raw[:120]}' -- using original question only.")
    return [fallback]


# ── Graph nodes ───────────────────────────────────────────

def _plan(state: ChatState) -> dict:
    """Decide narrow vs. broad, and produce the initial search queries."""
    llm = _get_llm(temperature=0.0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", PLAN_SYSTEM_PROMPT),
        ("human", "Question: {question}"),
    ])
    chain = prompt | llm | StrOutputParser()
    raw = chain.invoke({"question": state["question"]})

    queries = _parse_query_list(raw, fallback=state["question"])[: config.RAG_MAX_SUBQUERIES]
    logger.info(f"Planned {len(queries)} search quer{'y' if len(queries) == 1 else 'ies'}: {queries}")
    return {"queries": queries, "retrieved": {}, "attempt": 0}


def _retrieve(state: ChatState) -> dict:
    """Run every query in state['queries'], merge into the running
    `retrieved` dict keyed by chunk_index so the same chunk found via two
    different queries/retries isn't double counted -- keep the higher
    score if it shows up twice."""
    retrieved = dict(state["retrieved"])

    for q in state["queries"]:
        scored_docs = vectorstore.search_with_scores(state["lecture_id"], q, k=state["k"])
        for doc, score in scored_docs:
            key = doc.metadata.get("chunk_index", doc.page_content[:50])
            if key not in retrieved or score > retrieved[key][1]:
                retrieved[key] = (doc, score)

    logger.info(
        f"Have {len(retrieved)} unique chunk(s) after searching "
        f"{len(state['queries'])} quer{'y' if len(state['queries']) == 1 else 'ies'}."
    )
    return {"retrieved": retrieved}


def _grade(state: ChatState) -> dict:
    """No-op -- exists purely as a clean branch point for the conditional
    edge below (keeps retrieve/grade/route concerns separated)."""
    return {}


def _needs_retry(state: ChatState) -> str:
    best_score = max((score for _doc, score in state["retrieved"].values()), default=0.0)

    if best_score < config.RAG_CONFIDENCE_THRESHOLD and state["attempt"] < config.RAG_MAX_RETRIES:
        logger.info(
            f"Best retrieval score {best_score:.2f} < threshold {config.RAG_CONFIDENCE_THRESHOLD} "
            f"-- retrying (attempt {state['attempt'] + 1}/{config.RAG_MAX_RETRIES})."
        )
        return "rewrite"
    return "generate"


def _rewrite(state: ChatState) -> dict:
    """Ask the LLM for an alternate phrasing of the ORIGINAL question
    (not the last sub-query) and search again next loop."""
    llm = _get_llm(temperature=0.3)
    prompt = ChatPromptTemplate.from_messages([
        ("system", REWRITE_SYSTEM_PROMPT),
        ("human", "Original query: {question}"),
    ])
    chain = prompt | llm | StrOutputParser()
    new_query = chain.invoke({"question": state["question"]}).strip()

    logger.info(f"Rewrote query for retry: '{new_query}'")
    return {"queries": [new_query], "attempt": state["attempt"] + 1}


def _generate(state: ChatState) -> dict:
    ranked = sorted(state["retrieved"].values(), key=lambda pair: pair[1], reverse=True)
    # cap context size even for broad (multi-subquery) questions
    ranked = ranked[: max(state["k"], config.RAG_MAX_SUBQUERIES * 2)]

    if not ranked:
        return {
            "answer": "I don't have any lecture content indexed for this lecture yet -- "
                      "make sure it's been ingested into the vector store first.",
            "sources": [],
        }

    docs = [doc for doc, _score in ranked]
    context = _format_context(docs)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", USER_PROMPT),
    ])
    llm = _get_llm(temperature=0.2)
    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke({"context": context, "question": state["question"]})

    sources = [
        {
            "chunk_index": doc.metadata.get("chunk_index", "?"),
            "text": doc.page_content,
            "confidence": round(score, 3),
        }
        for doc, score in ranked
    ]

    return {"answer": answer.strip(), "sources": sources}


# ── Graph assembly ────────────────────────────────────────

def _build_graph():
    graph = StateGraph(ChatState)
    graph.add_node("plan", _plan)
    graph.add_node("retrieve", _retrieve)
    graph.add_node("grade", _grade)
    graph.add_node("rewrite", _rewrite)
    graph.add_node("generate", _generate)

    graph.set_entry_point("plan")
    graph.add_edge("plan", "retrieve")
    graph.add_edge("retrieve", "grade")
    graph.add_conditional_edges("grade", _needs_retry, {"rewrite": "rewrite", "generate": "generate"})
    graph.add_edge("rewrite", "retrieve")
    graph.add_edge("generate", END)

    return graph.compile()


_GRAPH = None


def _get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = _build_graph()
    return _GRAPH


def ask(lecture_id: str, question: str, k: int | None = None) -> dict:
    """
    Answer a question about one lecture using the LangGraph-orchestrated
    RAG loop: plan queries -> retrieve -> grade -> (retry if weak) -> generate.

    Returns:
        {
            "answer": str,
            "sources": [{"chunk_index": int, "text": str, "confidence": float}, ...]
        }
    """
    graph = _get_graph()
    result = graph.invoke({
        "lecture_id": lecture_id,
        "question": question,
        "k": k or config.RAG_TOP_K,
        "queries": [],
        "retrieved": {},
        "attempt": 0,
        "answer": "",
        "sources": [],
    })
    return {"answer": result["answer"], "sources": result["sources"]}


# ── CLI ───────────────────────────────────────────────────

def _print_sources(sources: list[dict]) -> None:
    if not sources:
        return
    print("\nSources:")
    for s in sources:
        snippet = s["text"][:160].replace("\n", " ")
        print(f"  [chunk #{s['chunk_index']} | confidence {s['confidence']}] {snippet}...")


def main():
    """Interactive CLI: pick a lecture, then chat with it until you quit."""
    lecture_ids = vectorstore.get_all_lecture_ids()
    if not lecture_ids:
        print("No lectures have been ingested yet -- run `python main.py` first.")
        return

    print("Available lectures:")
    for i, lid in enumerate(lecture_ids, 1):
        print(f"  {i}. {lid}")

    choice = input(f"Select a lecture [1-{len(lecture_ids)}] (Enter for '{lecture_ids[0]}'): ").strip()
    if choice:
        try:
            lecture_id = lecture_ids[int(choice) - 1]
        except (ValueError, IndexError):
            print(f"Invalid choice, defaulting to '{lecture_ids[0]}'.")
            lecture_id = lecture_ids[0]
    else:
        lecture_id = lecture_ids[0]

    print(f"\nChatting with lecture '{lecture_id}'. Type 'exit' or 'quit' to stop.\n")

    while True:
        question = input("You: ").strip()
        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            break

        try:
            result = ask(lecture_id, question)
        except Exception as e:
            logger.error(f"Failed to answer question: {e}")
            print("Sorry, something went wrong answering that -- check the logs above.")
            continue

        print(f"\nAssistant: {result['answer']}")
        _print_sources(result["sources"])
        print()


if __name__ == "__main__":
    main()