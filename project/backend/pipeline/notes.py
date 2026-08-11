"""
Notes generation: turn a lecture's full CLEAN TRANSCRIPT into a condensed
set of study notes -- a short summary, organized bullet-point sections, and
a glossary of key terms -- keeping only what actually matters for revision
and dropping filler, asides, and repetition.

Source data: the lecture's cleaned transcript TEXT (Lecture.transcript in
Django), not the vector store chunks -- unlike quiz.py, this stage wants
the whole lecture read in order, not similarity-searchable pieces, since
"what matters" is a judgment made over the full arc of the lecture.

Long lectures still won't fit in a single LLM call, so this runs as a
MAP-REDUCE:
  1. MAP    -- split the transcript into batches (config.NOTES_BATCH_CHAR_SIZE)
               and ask the LLM to pull the important points out of each batch
               on its own, as short section drafts.
  2. REDUCE -- if there was more than one batch, feed all the section drafts
               back into a second LLM call that merges, dedupes, and orders
               them into the final notes (plus writes the overall summary
               and glossary, which need the whole-lecture view). A
               single-batch lecture skips straight to a one-shot version of
               this same final step.

This mirrors the batching pattern in cleaner.py/quiz.py, for the same
reason (long input, one LLM call can't hold it all).
"""
import json
from pathlib import Path
from typing import TypedDict

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI
from loguru import logger

import config

MAP_SYSTEM_PROMPT = """You are a university teaching assistant condensing a lecture transcript \
excerpt into study notes for a student to revise from later.

RULES -- follow these exactly:
1. Keep ONLY the important stuff: definitions, key facts, explained concepts, examples that \
illustrate a concept, and conclusions. Drop filler -- greetings, "can everyone hear me", \
repeated phrasing, digressions, and administrative asides (assignment due dates, attendance) \
unless they're an actual academic instruction.
2. Do not invent facts, examples, or details not present in the excerpt.
3. The lecture may mix Urdu, English, and Arabic. Write notes in the same language/mix the \
excerpt uses, EXCEPT keep technical terms (e.g. "Inheritance", "API", "Docker") in their \
original Latin script, and keep Arabic religious/quoted phrases exactly as given, un-translated.
4. Group points under short section headings (topic-based, not one heading per sentence). This \
is a middle excerpt of a longer transcript -- headings only need to cover what THIS excerpt \
discusses, not the whole lecture.
5. Each point should be a single, self-contained bullet -- not a restated sentence from the \
transcript, but the compressed takeaway.
6. If the excerpt defines a term worth remembering, also add it to key_terms.
7. Output ONLY valid JSON matching the schema below. No markdown fences, no preamble, no \
commentary, no trailing text after the closing brace.

Schema:
{{
  "sections": [
    {{"heading": str, "points": [str, ...]}}
  ],
  "key_terms": [
    {{"term": str, "definition": str}}
  ]
}}
"""

MAP_USER_PROMPT = """Extract the important points from this lecture excerpt as condensed study \
notes.

Lecture excerpt:
---
{excerpt}
---
"""

REDUCE_SYSTEM_PROMPT = """You are a university teaching assistant producing the FINAL study \
notes for a lecture, from a set of section drafts already pulled out of the lecture in order.

RULES -- follow these exactly:
1. Merge, deduplicate, and reorder the drafted sections/points into a clean, logically ordered \
set of study notes for the whole lecture. Combine sections that cover the same topic; drop \
near-duplicate points instead of repeating them.
2. Do not invent facts not present in the drafts.
3. Write in the same language/mix the drafts use, keeping technical terms in Latin script and \
Arabic religious/quoted phrases untranslated, exactly as in the drafts.
4. Write a short overall summary (2-4 sentences) capturing what the lecture covered, for someone \
deciding whether they need to read the full notes.
5. Merge and deduplicate key_terms across drafts (keep the clearest definition if a term appears \
more than once).
6. Output ONLY valid JSON matching the schema below. No markdown fences, no preamble, no \
commentary, no trailing text after the closing brace.

Schema:
{{
  "summary": str,
  "sections": [
    {{"heading": str, "points": [str, ...]}}
  ],
  "key_terms": [
    {{"term": str, "definition": str}}
  ]
}}
"""

REDUCE_USER_PROMPT = """Here are the section drafts pulled from this lecture, in order. Merge \
them into the final study notes.

Section drafts (JSON):
---
{drafts}
---
"""

# Used instead of the two-stage prompt above when the whole transcript fits in
# one batch -- skips the draft stage and asks for the final schema directly.
ONE_SHOT_SYSTEM_PROMPT = """You are a university teaching assistant condensing a lecture \
transcript into study notes for a student to revise from later.

RULES -- follow these exactly:
1. Keep ONLY the important stuff: definitions, key facts, explained concepts, examples that \
illustrate a concept, and conclusions. Drop filler -- greetings, repeated phrasing, digressions, \
and administrative asides (assignment due dates, attendance) unless they're an actual academic \
instruction.
2. Do not invent facts, examples, or details not present in the transcript.
3. The lecture may mix Urdu, English, and Arabic. Write notes in the same language/mix the \
transcript uses, EXCEPT keep technical terms (e.g. "Inheritance", "API", "Docker") in their \
original Latin script, and keep Arabic religious/quoted phrases exactly as given, un-translated.
4. Group points under short, topic-based section headings, in the order the lecture covers them.
5. Each point should be a single, self-contained bullet -- the compressed takeaway, not a \
restated transcript sentence.
6. Write a short overall summary (2-4 sentences) capturing what the lecture covered.
7. List key terms/definitions worth remembering in key_terms.
8. Output ONLY valid JSON matching the schema below. No markdown fences, no preamble, no \
commentary, no trailing text after the closing brace.

Schema:
{{
  "summary": str,
  "sections": [
    {{"heading": str, "points": [str, ...]}}
  ],
  "key_terms": [
    {{"term": str, "definition": str}}
  ]
}}
"""

ONE_SHOT_USER_PROMPT = """Condense this lecture transcript into study notes.

Lecture transcript:
---
{transcript}
---
"""


class NotesSection(TypedDict):
    heading: str
    points: list[str]


class KeyTerm(TypedDict):
    term: str
    definition: str


def _get_llm():
    if config.LLM_PROVIDER != "openai":
        raise NotImplementedError(
            f"LLM_PROVIDER='{config.LLM_PROVIDER}' not wired yet in cleaner.py. "
            "Add a branch here (e.g. ChatGoogleGenerativeAI, ChatAnthropic) -- LangChain "
            "makes this a drop-in swap since they all implement the same Runnable interface."
        )
    if not config.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set in your environment/.env")

    return ChatOpenAI(
        model=config.LLM_MODEL,
        api_key=config.OPENAI_API_KEY,
        temperature=0.2,  # low temperature: this is correction, not creative writing
    )


def _chain(system_prompt: str):
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{user_prompt}"),
    ])
    return prompt | _get_llm() | StrOutputParser()


def _parse_json(raw: str, keys_with_defaults: dict) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[-1] if "\n" in raw else raw
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {key: parsed.get(key, default) or default for key, default in keys_with_defaults.items()}
    except (json.JSONDecodeError, TypeError):
        pass
    logger.warning(f"Could not parse notes JSON from a response (first 150 chars): '{raw[:150]}'")
    return dict(keys_with_defaults)


def _batch_transcript(transcript: str, char_budget: int) -> list[str]:
    """Split the transcript into batches that fit under char_budget, on
    paragraph/sentence-ish boundaries so a batch doesn't cut a thought in
    half -- same splitter chunker.py uses for the same reason."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=char_budget,
        chunk_overlap=0,  # notes don't need retrieval-style overlap; the reduce pass stitches context back
        separators=["\n\n", "\n", "۔ ", "؟ ", ". ", "! ", " ", ""],
    )
    return splitter.split_text(transcript)


def generate_notes(lecture_id: str, transcript: str) -> dict:
    """
    Generate condensed study notes for a lecture from its full clean
    transcript text.

    Args:
        lecture_id: identifier for this lecture (carried through to the result only)
        transcript: the lecture's full clean transcript text

    Returns:
        {
            "lecture_id": str,
            "summary": str,
            "sections": [{"heading": str, "points": [str, ...]}, ...],
            "key_terms": [{"term": str, "definition": str}, ...],
        }
    """
    transcript = (transcript or "").strip()
    if not transcript:
        raise ValueError(f"Transcript for lecture_id='{lecture_id}' is empty -- nothing to summarize.")

    batches = _batch_transcript(transcript, config.NOTES_BATCH_CHAR_SIZE)
    logger.info(f"Generating notes for '{lecture_id}' from {len(transcript)} chars in {len(batches)} batch(es)")

    if len(batches) == 1:
        chain = _chain(ONE_SHOT_SYSTEM_PROMPT)
        raw = chain.invoke({"user_prompt": ONE_SHOT_USER_PROMPT.format(transcript=batches[0])})
        result = _parse_json(raw, {"summary": "", "sections": [], "key_terms": []})
    else:
        # MAP: draft section notes out of each batch independently
        map_chain = _chain(MAP_SYSTEM_PROMPT)
        drafts = []
        for i, batch in enumerate(batches):
            logger.info(f"Notes map batch {i + 1}/{len(batches)} ({len(batch)} chars)")
            raw = map_chain.invoke({"user_prompt": MAP_USER_PROMPT.format(excerpt=batch)})
            parsed = _parse_json(raw, {"sections": [], "key_terms": []})
            drafts.append(parsed)

        # REDUCE: merge the drafts into the final notes (summary needs the whole-lecture view)
        logger.info(f"Notes reduce pass for '{lecture_id}' merging {len(drafts)} draft(s)")
        reduce_chain = _chain(REDUCE_SYSTEM_PROMPT)
        raw = reduce_chain.invoke({
            "user_prompt": REDUCE_USER_PROMPT.format(drafts=json.dumps(drafts, ensure_ascii=False)),
        })
        result = _parse_json(raw, {"summary": "", "sections": [], "key_terms": []})

    logger.info(
        f"Notes generated for '{lecture_id}': {len(result['sections'])} section(s), "
        f"{len(result['key_terms'])} key term(s)"
    )

    return {
        "lecture_id": lecture_id,
        "summary": result["summary"],
        "sections": result["sections"],
        "key_terms": result["key_terms"],
    }


# ── Export ────────────────────────────────────────────────

def save_notes_markdown(notes: dict) -> Path:
    """Write the notes to work/notes/<lecture_id>.md (mirrors quiz.py's Markdown export)."""
    lecture_id = notes["lecture_id"]
    lines = [f"# Notes -- {lecture_id}\n"]

    if notes.get("summary"):
        lines.append(f"{notes['summary']}\n")

    for section in notes.get("sections", []):
        lines.append(f"## {section.get('heading', '')}\n")
        for point in section.get("points", []):
            lines.append(f"- {point}")
        lines.append("")

    if notes.get("key_terms"):
        lines.append("## Key Terms\n")
        for kt in notes["key_terms"]:
            lines.append(f"- **{kt.get('term', '')}:** {kt.get('definition', '')}")
        lines.append("")

    output_path = config.NOTES_DIR / f"{lecture_id}.md"
    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Notes saved: {output_path}")
    return output_path


def save_notes_json(notes: dict) -> Path:
    """Write the notes to work/notes/<lecture_id>.json (structured -- for the frontend)."""
    output_path = config.NOTES_DIR / f"{notes['lecture_id']}.json"
    output_path.write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Notes JSON saved: {output_path}")
    return output_path


# ── CLI ───────────────────────────────────────────────────

def main():
    import vectorstore  # local import -- only the CLI path needs to discover lecture ids this way
    import cleaner  # noqa: F401  (not used directly; kept for parity with quiz.py's CLI imports)

    lecture_ids = vectorstore.get_all_lecture_ids()
    if not lecture_ids:
        print("No lectures have been ingested yet -- run `python main.py` first.")
        return

    print("Available lectures:")
    for i, lid in enumerate(lecture_ids, 1):
        print(f"  {i}. {lid}")

    choice = input(f"Select a lecture [1-{len(lecture_ids)}] (Enter for '{lecture_ids[0]}'): ").strip()
    try:
        lecture_id = lecture_ids[int(choice) - 1] if choice else lecture_ids[0]
    except (ValueError, IndexError):
        print(f"Invalid choice, defaulting to '{lecture_ids[0]}'.")
        lecture_id = lecture_ids[0]

    transcript_path = config.CLEAN_TRANSCRIPT_DIR / f"{lecture_id}.txt"
    if not transcript_path.exists():
        print(f"No clean transcript file found at {transcript_path}.")
        return
    transcript = transcript_path.read_text(encoding="utf-8")

    try:
        notes = generate_notes(lecture_id, transcript)
    except Exception as e:
        logger.error(f"Notes generation failed: {e}")
        return

    md_path = save_notes_markdown(notes)
    save_notes_json(notes)
    print(f"\nNotes saved to: {md_path}")


if __name__ == "__main__":
    main()
