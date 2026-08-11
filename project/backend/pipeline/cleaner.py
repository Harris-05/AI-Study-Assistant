import re

from langdetect import detect, DetectorFactory, LangDetectException
from loguru import logger
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

import config

# langdetect's detect() samples internally and is non-deterministic run-to-run
# unless seeded -- pin it so the same input always gets the same verdict.
DetectorFactory.seed = 0

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
Hindi sentences or phrases that the previous cleaning pass missed.
Your ONLY job: find any remaining Hindi-language text that is NOT one of the two protected \
categories below, and translate it into {output_language}. Leave everything else EXACTLY as \
given -- do not rephrase, reformat, or "improve" sentences that are already correctly in \
{output_language}.

PROTECTED (do NOT translate, leave exactly as-is):
1. Technical/academic/CS/engineering terms in Latin script (Inheritance, Class, API, Docker, etc).
2. Actual Quranic verses, Hadith, or short Arabic religious expressions (Bismillah, \
InshaAllah, MashaAllah, SubhanAllah, Alhamdulillah, etc).

Everything else that is still in Hindi must be translated into {output_language}.

Return ONLY the corrected full text, same paragraph structure as given, no commentary, no \
markdown, no preamble.
"""

# Narrow follow-up prompt. Unlike ENFORCE_SYSTEM_PROMPT above (which asks the model
# to *judge* whether something "is Hindi"), this prompt is only ever invoked on
# paragraphs where langdetect has already told us the dominant language doesn't
# match the requested output_language -- so the model's job here is just "convert
# whatever language/script this currently is into {output_language}", not "go
# hunting for leftover Hindi" specifically. This makes it work for ANY mismatch
# (Hindi, stray English, misplaced Arabic, etc), not just Devanagari script.
LANGUAGE_FIX_SYSTEM_PROMPT = """You are fixing one specific, narrow issue in an \
already-cleaned lecture transcript paragraph: part or all of it is not actually \
written in the required output language.

Required output language: {output_language}.
Detected language of this paragraph: {detected_language}.

Convert/translate every part of this paragraph that is NOT in {output_language} into \
{output_language}, regardless of what language or script it is currently in (Hindi/\
Devanagari, English, Arabic, or anything else). If the mismatched text is Urdu written \
in a different script, or vice versa, treat it as a SCRIPT conversion (same words, same \
meaning) rather than a translation. Otherwise, translate for meaning.

PROTECTED -- do NOT alter these, even if they sit inside mismatched-language text:
1. Technical/academic/CS/engineering terms in Latin script (Inheritance, Class, API, \
Docker, etc) -- keep exactly as given, do not translate or transliterate them.
2. Actual Quranic verses, Hadith, or short Arabic religious expressions (Bismillah, \
InshaAllah, MashaAllah, SubhanAllah, Alhamdulillah, etc) -- keep exactly as given.
3. Any part of the paragraph that is already correctly in {output_language} -- leave \
it completely untouched, character for character. Do not rephrase or "improve" it.

Return ONLY the corrected paragraph, no commentary, no markdown, no preamble.
"""

# Map our config-level language names to the ISO 639-1 codes langdetect returns.
# Hindi ("hi") deliberately has no entry here -- it should never be a valid target,
# it only ever shows up as something to be *caught* by the mismatch check below.
LANGDETECT_CODE_MAP = {
    "urdu": "ur",
    "english": "en",
    "arabic": "ar",
}

# langdetect is unreliable on very short strings (single words, numbers, a lone
# technical term) -- below this word count we skip detection on that unit rather
# than risk a false-positive flag.
MIN_WORDS_FOR_DETECTION = 4

# Sentence-ending punctuation across Urdu/Arabic/English, used to split a paragraph
# into detectable units without pulling in a full NLP sentence tokenizer.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.۔؟!])\s+")


def _detect_language(text: str) -> str | None:
    """Best-effort language detection. Returns an ISO 639-1 code, or None if
    the text is too short/ambiguous to trust a verdict on."""
    if len(text.split()) < MIN_WORDS_FOR_DETECTION:
        return None
    try:
        return detect(text)
    except LangDetectException:
        return None


def _paragraph_matches_language(paragraph: str, target_code: str) -> bool:
    """True if the paragraph looks like it's already in the target language.
    Checked at both paragraph level (cheap, catches the common case) and
    sentence level (catches a mismatched sentence or two buried inside an
    otherwise-correct paragraph, which whole-paragraph detection can miss
    since langdetect just returns its single best overall guess)."""
    whole = _detect_language(paragraph)
    if whole is not None and whole != target_code:
        return False

    for sentence in _SENTENCE_SPLIT_RE.split(paragraph):
        sentence = sentence.strip()
        if not sentence:
            continue
        lang = _detect_language(sentence)
        if lang is not None and lang != target_code:
            return False

    return True


def _get_llm():
    if config.LLM_PROVIDER != "openai":
        raise NotImplementedError(
            f"LLM_PROVIDER='{config.LLM_PROVIDER}' not wired yet in cleaner.py. "
            "Add a specfically cleaner branch here (e.g. ChatGoogleGenerativeAI, ChatAnthropic) -- LangChain "
            "makes this a drop-in swap since they all implement the same Runnable interface."
        )
    if not config.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set in your environment/.env")

    return ChatOpenAI(
        model=config.LLM_MODEL,
        api_key=config.OPENAI_API_KEY,
        temperature=0.0,  # low temperature: this is correction, not creative writing
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


def _build_language_fix_chain():
    prompt = ChatPromptTemplate.from_messages([
        ("system", LANGUAGE_FIX_SYSTEM_PROMPT),
        ("human", "Paragraph to fix:\n---\n{chunk}\n---"),
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
    #Second Pass: Enforce output language if requested, and fix any remaining mismatches
    if output_language != "mixed" and config.ENFORCE_OUTPUT_LANGUAGE:
        stitched = _enforce_output_language(stitched, output_language)
    #Third Pass: Final safety net to fix any remaining language mismatches
    if output_language != "mixed":
        stitched = _fix_language_mismatches(stitched, output_language)

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


def _fix_language_mismatches(cleaned_text: str, output_language: str) -> str:
    """Final safety net: scan paragraph-by-paragraph (and sentence-by-sentence
    within each) using real language detection, and only send paragraphs that
    don't match output_language through a dedicated fix prompt. Everything
    else is left untouched and never re-sent to the model, which keeps this
    pass cheap in the common case where the first two passes already did
    their job.

    Works for any mismatch -- leftover Hindi, stray English in an Urdu
    lecture, misplaced Arabic, etc -- not just one hardcoded script."""
    target_code = LANGDETECT_CODE_MAP.get(output_language)
    if target_code is None:
        logger.warning(
            f"No langdetect code mapped for output_language='{output_language}' -- "
            "skipping language-mismatch fix pass"
        )
        return cleaned_text

    paragraphs = cleaned_text.split("\n\n")
    flagged = [
        (i, _detect_language(p) or "unknown")
        for i, p in enumerate(paragraphs)
        if not _paragraph_matches_language(p, target_code)
    ]

    if not flagged:
        logger.info(f"No language mismatches detected against target='{output_language}'")
        return cleaned_text

    logger.info(
        f"Language mismatch detected in {len(flagged)}/{len(paragraphs)} "
        f"paragraph(s) against target='{output_language}' -- running targeted fix pass"
    )
    fix_chain = _build_language_fix_chain()

    for i, detected_language in flagged:
        fixed = fix_chain.invoke({
            "output_language": output_language,
            "detected_language": detected_language,
            "chunk": paragraphs[i],
        }).strip()

        if not _paragraph_matches_language(fixed, target_code):
            # Don't loop retrying indefinitely -- flag it clearly so a human
            # can check this paragraph, but don't drop or mangle the content.
            logger.warning(
                f"Paragraph {i} still doesn't match target='{output_language}' "
                "after fix pass -- leaving as returned for manual review"
            )

        paragraphs[i] = fixed

    return "\n\n".join(paragraphs)


def save_clean_transcript(cleaned_text: str, lecture_id: str) -> "Path":
    from pathlib import Path
    output_path = config.CLEAN_TRANSCRIPT_DIR / f"{lecture_id}.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(cleaned_text)
    logger.info(f"Clean transcript saved: {output_path}")
    return output_path