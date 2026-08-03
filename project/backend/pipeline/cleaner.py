"""
Stage 3: Raw Transcript -> Clean Transcript (grammar, script, language fixes).

This is the core "intelligence" stage described in the spec:
  - detect language per sentence (Urdu/English/Arabic/Mixed)
  - convert any Hindi-script output to Urdu script (same meaning)
  - preserve technical terms in Latin script (don't translate "Inheritance" -> "وراثت")
  - preserve Arabic religious/quoted phrases verbatim, only fixing ASR typos
  - fix ASR errors: punctuation, grammar, broken sentences -- WITHOUT inventing content
  - group sentences into logical paragraphs
  - rewrite in the user's chosen OUTPUT_LANGUAGE, or keep the natural code-mixed
    style if OUTPUT_LANGUAGE = "mixed"

Long lectures are cleaned in overlapping chunks (see config.CLEAN_CHUNK_*)
because a 1-3hr lecture transcript won't fit in a single LLM call. Overlap
gives the model context from the previous chunk so it doesn't cut sentences
awkwardly at chunk boundaries.

Built with LangChain (LCEL) so the underlying LLM provider is swappable --
currently wired to Gemini, but langchain-openai / langchain-anthropic drop
in with the same interface.
"""
from loguru import logger
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

import config

SYSTEM_PROMPT = """You are an expert transcript editor for university lecture recordings. \
The lectures are commonly a mix of Urdu, English, and Arabic (code-switching), and were \
transcribed automatically, so they contain errors.

Your job is to clean the transcript chunk given to you, following these rules EXACTLY:

1. LANGUAGE HANDLING
   - If any part of the text was transcribed in Hindi (Devanagari) script, convert it to \
Urdu (Nastaliq/Arabic) script WITHOUT changing the meaning. Example: "आप कैसे हैं" -> "آپ کیسے ہیں".
   - Target output language for this transcript: {output_language}.
     - If "mixed": preserve the natural code-switching exactly as spoken (don't force \
everything into one language).
     - If "urdu"/"english"/"arabic": rewrite EVERY sentence into that language, with NO \
exceptions other than rules 2 and 3 below.

   CRITICAL -- do not confuse "written in Arabic script" with "is Arabic". Urdu is normally \
written using the Arabic/Nastaliq alphabet, but Urdu is a DIFFERENT LANGUAGE from Arabic. \
An ordinary Urdu sentence (e.g. "آپ inheritance کے concept کو سمجھیں") is NOT a protected \
Arabic phrase just because it uses Arabic-derived script -- if output_language is "english", \
translate that whole sentence into English (keeping "inheritance"/"concept" as technical \
terms per rule 2). Only the specific categories in rule 3 (Quranic verses, Hadith, religious \
expressions) are protected from translation, regardless of what script they happen to share \
with Urdu.

2. PRESERVE TECHNICAL TERMS
   - Never translate technical/academic/CS/engineering terms (e.g. Inheritance, Class, \
Object, Database, API, Docker, React, Algorithm). Keep them in their original Latin script \
exactly as said, even inside Urdu or English sentences.

3. PRESERVE ARABIC RELIGIOUS/QURANIC CONTENT ONLY
   - Never translate actual Quranic verses, Hadith, or short Arabic religious expressions \
(e.g. Bismillah, InshaAllah, MashaAllah, SubhanAllah, Alhamdulillah). Only fix obvious \
transcription typos in them, do not alter wording or meaning.
   - This protection is narrow: it does NOT cover ordinary Urdu speech, even though Urdu is \
written in the same script family. If in doubt whether something is "Urdu speech" vs. \
"Arabic religious content", ask: would a listener recognize this as a specific Quranic verse, \
Hadith, or common religious phrase? If not, it's Urdu -- translate it per rule 1.

4. FIX ASR ERRORS
   - Correct punctuation, capitalization, grammar, and broken/garbled sentences.
   - Do NOT invent, add, or infer any content that was not said. If a phrase is \
unintelligible, leave a [inaudible] marker instead of guessing.

5. PARAGRAPHS
   - Group related sentences into logical paragraphs (topic-based), not one sentence per line.

6. OUTPUT FORMAT
   - Return ONLY the cleaned transcript text. No preamble, no explanations, no markdown \
headers, no commentary about what you changed.
   - This is a middle chunk of a longer transcript -- do not add an introduction or \
conclusion that isn't part of the actual lecture speech.
"""

USER_PROMPT = """Previous chunk's tail (for context only, do NOT repeat it in your output):
---
{previous_context}
---

Clean this transcript chunk:
---
{chunk}
---
"""

ENFORCE_SYSTEM_PROMPT = """You are proofreading an already-cleaned lecture transcript that \
was supposed to be fully rewritten in {output_language}, but may still contain leftover \
Urdu sentences or phrases that the previous cleaning pass missed -- this can happen because \
Urdu and Arabic share the same script, so Urdu speech sometimes gets mistaken for protected \
Arabic religious content and left untranslated.

Your ONLY job: find any remaining Urdu-language text that is NOT one of the two protected \
categories below, and translate it into {output_language}. Leave everything else EXACTLY as \
given -- do not rephrase, reformat, or "improve" sentences that are already correctly in \
{output_language}.

PROTECTED (do NOT translate, leave exactly as-is):
1. Technical/academic/CS/engineering terms in Latin script (Inheritance, Class, API, Docker, etc).
2. Actual Quranic verses, Hadith, or short Arabic religious expressions (Bismillah, \
InshaAllah, MashaAllah, SubhanAllah, Alhamdulillah, etc).

Everything else that is still in Urdu must be translated into {output_language}.

Return ONLY the corrected full text, same paragraph structure as given, no commentary, no \
markdown, no preamble.
"""


def _get_llm():
    if config.LLM_PROVIDER != "gemini":
        raise NotImplementedError(
            f"LLM_PROVIDER='{config.LLM_PROVIDER}' not wired yet in cleaner.py. "
            "Add a branch here (e.g. ChatOpenAI, ChatAnthropic) -- LangChain makes "
            "this a drop-in swap since they all implement the same Runnable interface."
        )
    if not config.GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY is not set in your environment/.env")

    return ChatGoogleGenerativeAI(
        model=config.LLM_MODEL,
        google_api_key=config.GOOGLE_API_KEY,
        temperature=0.1,  # low temperature: this is correction, not creative writing
    )


def _build_chain():
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", USER_PROMPT),
    ])
    llm = _get_llm()
    return prompt | llm | StrOutputParser()


def _build_enforce_chain():
    prompt = ChatPromptTemplate.from_messages([
        ("system", ENFORCE_SYSTEM_PROMPT),
        ("human", "Text to proofread:\n---\n{chunk}\n---"),
    ])
    llm = _get_llm()
    return prompt | llm | StrOutputParser()


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    Simple character-based chunking with overlap.
    We chunk on the raw transcript text (already roughly sentence-separated
    by the transcriber), splitting on paragraph/sentence boundaries where
    possible so we don't cut a sentence mid-word.
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))

        # try to break on a sentence boundary near the end, not mid-word
        if end < len(text):
            for boundary in [". ", "۔ ", "؟ ", "! ", "\n\n"]:
                idx = text.rfind(boundary, start, end)
                if idx != -1 and idx > start:
                    end = idx + len(boundary)
                    break

        chunks.append(text[start:end])
        start = end - overlap if end - overlap > start else end

    return chunks


def clean_transcript(raw_text: str, output_language: str | None = None) -> str:
    """
    Run the full cleaning pipeline over a raw transcript string.

    Args:
        raw_text: concatenated raw transcript text (from transcriber.transcript_to_segments)
        output_language: "urdu" | "english" | "arabic" | "mixed" -- defaults to
            config.OUTPUT_LANGUAGE if not provided

    Returns:
        The cleaned, stitched-together transcript as a single string.
    """
    output_language = output_language or config.OUTPUT_LANGUAGE
    chain = _build_chain()

    chunks = chunk_text(raw_text, config.CLEAN_CHUNK_CHAR_SIZE, config.CLEAN_CHUNK_OVERLAP)
    logger.info(f"Cleaning transcript in {len(chunks)} chunk(s), output_language={output_language}")

    cleaned_parts = []
    previous_context = ""

    for i, chunk in enumerate(chunks):
        logger.info(f"Cleaning chunk {i + 1}/{len(chunks)} ({len(chunk)} chars)")
        cleaned = chain.invoke({
            "output_language": output_language,
            "previous_context": previous_context[-500:],  # last ~500 chars for continuity
            "chunk": chunk,
        })
        cleaned_parts.append(cleaned.strip())
        previous_context = cleaned

    stitched = "\n\n".join(cleaned_parts)

    # SECOND PASS: catch residual code-switched Urdu the first pass missed.
    # Urdu and Arabic share the same script, so the model sometimes
    # mistakes ordinary Urdu speech for "protected Arabic religious
    # content" and leaves it untranslated -- this pass specifically hunts
    # for and fixes that, without touching anything already correct. Only
    # runs when a single target language was requested; skipped for
    # "mixed" since code-switching is intentional there.
    if output_language != "mixed" and config.ENFORCE_OUTPUT_LANGUAGE:
        stitched = _enforce_output_language(stitched, output_language)

    return stitched


def _enforce_output_language(cleaned_text: str, output_language: str) -> str:
    """Corrective pass: re-chunk the already-cleaned text and ask the model
    to translate any leftover Urdu it finds, leaving everything else
    untouched. Chunked the same way as the main pass so it stays within
    context limits on long transcripts."""
    enforce_chain = _build_enforce_chain()
    chunks = chunk_text(cleaned_text, config.CLEAN_CHUNK_CHAR_SIZE, config.CLEAN_CHUNK_OVERLAP)
    logger.info(f"Enforcing output_language='{output_language}' in {len(chunks)} chunk(s) (second pass)")

    fixed_parts = []
    for i, chunk in enumerate(chunks):
        logger.info(f"Language-enforcement pass on chunk {i + 1}/{len(chunks)}")
        fixed = enforce_chain.invoke({
            "output_language": output_language,
            "chunk": chunk,
        })
        fixed_parts.append(fixed.strip())

    return "\n\n".join(fixed_parts)


def save_clean_transcript(cleaned_text: str, lecture_id: str) -> "Path":
    from pathlib import Path
    output_path = config.CLEAN_TRANSCRIPT_DIR / f"{lecture_id}.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(cleaned_text)
    logger.info(f"Clean transcript saved: {output_path}")
    return output_path