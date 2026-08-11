"""
Quiz generation: turn a lecture's indexed chunks into MCQs, short-answer,
and long-answer questions for revision (spec Step 5 -- Note Generation:
MCQ / Short Questions / Long Questions sections).

Source data: the lecture's VECTOR STORE chunks (same chunks chat.py
retrieves from), not the raw clean transcript file. This means quiz
generation reuses whatever's already been ingested by main.py's pipeline --
one source of truth for "what a chunk is" across chat and quiz, and no
separate re-chunking pass needed.

Long lectures produce more chunks than fit in a single LLM call, so
generation runs in BATCHES: chunks are grouped by a character budget
(config.QUIZ_BATCH_CHAR_SIZE), each batch is asked for a small quota of
questions, and all batches' output is merged into the final quiz. This
mirrors the batching pattern already used in cleaner.py, for the same
reason (long input, one LLM call can't hold it all).

Every question carries the chunk_index/indices it was generated from, so
answers stay traceable back to the lecture (spec: "Every generated answer
should be traceable back to the lecture").
"""
import json
import math
from pathlib import Path
from typing import TypedDict

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from loguru import logger

import config
import vectorstore

DIFFICULTIES = ("easy", "medium", "hard")

SYSTEM_PROMPT = """You are a university teaching assistant writing quiz questions from a \
lecture transcript excerpt, to help a student revise.

RULES -- follow these exactly:
1. Base every question and answer ONLY on the excerpt given. Do not invent facts, examples, \
or details not present in the excerpt. If the excerpt is too thin to support the requested \
number of questions, return fewer questions rather than inventing content.
2. The lecture may mix Urdu, English, and Arabic. Write questions and answers in the same \
language/mix the excerpt uses, EXCEPT keep technical terms (e.g. "Inheritance", "API", \
"Docker") in their original Latin script, and keep Arabic religious/quoted phrases exactly \
as given, un-translated.
3. MCQs: exactly 4 options, exactly one correct, plausible-but-wrong distractors (not \
obviously silly), plus a short explanation of why the correct answer is correct.
4. Difficulty guide for MCQs -- "easy": direct recall of a definition/fact stated plainly; \
"medium": requires connecting two things said in the excerpt; "hard": requires applying or \
distinguishing a concept, or a subtle distinction the lecture made.
5. Short-answer questions: answerable in 1-3 sentences from the excerpt.
6. Long-answer questions: require explaining a concept in more depth, drawing on 2+ points \
made in the excerpt; provide brief answer guidance (what a good answer should cover), not a \
full model essay.
7. Output ONLY valid JSON matching the schema below. No markdown fences, no preamble, no \
commentary, no trailing text after the closing brace.

Schema:
{{
  "mcqs": [
    {{"question": str, "options": [str, str, str, str], "correct_index": int (0-3),
      "explanation": str, "difficulty": "easy" | "medium" | "hard"}}
  ],
  "short_questions": [
    {{"question": str, "answer": str}}
  ],
  "long_questions": [
    {{"question": str, "answer_guidance": str}}
  ]
}}
"""

USER_PROMPT = """Generate approximately {num_mcq} MCQs (roughly evenly split across \
easy/medium/hard), {num_short} short-answer questions, and {num_long} long-answer questions \
from this lecture excerpt. If a category's requested count is 0, return an empty list for it.

Lecture excerpt:
---
{excerpt}
---
"""


class QuizItem(TypedDict, total=False):
    question: str
    options: list[str]
    correct_index: int
    explanation: str
    difficulty: str
    answer: str
    answer_guidance: str
    chunk_indices: list


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
        temperature=0.4,  # low temperature: this is correction, not creative writing
    )


def _build_chain():
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", USER_PROMPT),
    ])
    return prompt | _get_llm() | StrOutputParser()


def _parse_quiz_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[-1] if "\n" in raw else raw
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {
                "mcqs": parsed.get("mcqs", []) or [],
                "short_questions": parsed.get("short_questions", []) or [],
                "long_questions": parsed.get("long_questions", []) or [],
            }
    except (json.JSONDecodeError, TypeError):
        pass
    logger.warning(f"Could not parse quiz JSON from a batch response (first 150 chars): '{raw[:150]}'")
    return {"mcqs": [], "short_questions": [], "long_questions": []}


def _batch_chunks(chunks: list, char_budget: int) -> list[list]:
    """Group consecutive chunks (already in chunk_index order) into batches
    that fit under char_budget, so each LLM call gets a coherent, bounded
    slice of the lecture rather than the whole transcript at once."""
    batches = []
    current, current_len = [], 0
    for doc in chunks:
        doc_len = len(doc.page_content)
        if current and current_len + doc_len > char_budget:
            batches.append(current)
            current, current_len = [], 0
        current.append(doc)
        current_len += doc_len
    if current:
        batches.append(current)
    return batches


def _trim_balanced_by_difficulty(mcqs: list[dict], target: int) -> list[dict]:
    """Trim to `target` MCQs while keeping a roughly even easy/medium/hard
    split, instead of naively truncating (which could leave an all-easy or
    all-hard quiz depending on batch order)."""
    if not target or len(mcqs) <= target:
        return mcqs
    by_diff = {d: [m for m in mcqs if m.get("difficulty") == d] for d in DIFFICULTIES}
    per_diff = target // len(DIFFICULTIES)
    result = []
    for d in DIFFICULTIES:
        result.extend(by_diff[d][:per_diff])
    remaining = [m for m in mcqs if m not in result]
    while len(result) < target and remaining:
        result.append(remaining.pop(0))
    return result[:target]


def generate_quiz(
    lecture_id: str,
    num_mcq: int | None = None,
    num_short: int | None = None,
    num_long: int | None = None,
) -> dict:
    """
    Generate a quiz (MCQs + short-answer + long-answer questions) for a
    lecture, sourced from its already-ingested vector store chunks.

    Args:
        lecture_id: which lecture's vector store collection to draw from
        num_mcq / num_short / num_long: target counts; pass 0 to skip a
            category entirely. Defaults come from config.QUIZ_DEFAULT_*.

    Returns:
        {
            "lecture_id": str,
            "mcqs": [QuizItem, ...],
            "short_questions": [QuizItem, ...],
            "long_questions": [QuizItem, ...],
        }
    """
    num_mcq = config.QUIZ_DEFAULT_NUM_MCQ if num_mcq is None else num_mcq
    num_short = config.QUIZ_DEFAULT_NUM_SHORT if num_short is None else num_short
    num_long = config.QUIZ_DEFAULT_NUM_LONG if num_long is None else num_long

    chunks = vectorstore.get_all_chunks(lecture_id)
    if not chunks:
        raise ValueError(
            f"No chunks found for lecture_id='{lecture_id}' -- has it been ingested? "
            "Run main.py's pipeline first."
        )

    batches = _batch_chunks(chunks, config.QUIZ_BATCH_CHAR_SIZE)
    logger.info(f"Generating quiz for '{lecture_id}' from {len(chunks)} chunk(s) in {len(batches)} batch(es)")

    # split requested totals roughly evenly across batches so each batch
    # gets a small, achievable quota instead of one batch being asked for
    # everything (and running out of source material) while others get none
    per_batch_mcq = max(1, math.ceil(num_mcq / len(batches))) if num_mcq else 0
    per_batch_short = max(1, math.ceil(num_short / len(batches))) if num_short else 0
    per_batch_long = max(1, math.ceil(num_long / len(batches))) if num_long else 0

    chain = _build_chain()
    all_mcqs, all_short, all_long = [], [], []

    for i, batch in enumerate(batches):
        excerpt = "\n\n".join(doc.page_content for doc in batch)
        chunk_indices = [doc.metadata.get("chunk_index", "?") for doc in batch]
        logger.info(f"Quiz batch {i + 1}/{len(batches)} (chunks {chunk_indices}, {len(excerpt)} chars)")

        raw = chain.invoke({
            "num_mcq": per_batch_mcq,
            "num_short": per_batch_short,
            "num_long": per_batch_long,
            "excerpt": excerpt,
        })
        parsed = _parse_quiz_json(raw)

        for item in parsed["mcqs"]:
            item["chunk_indices"] = chunk_indices
            all_mcqs.append(item)
        for item in parsed["short_questions"]:
            item["chunk_indices"] = chunk_indices
            all_short.append(item)
        for item in parsed["long_questions"]:
            item["chunk_indices"] = chunk_indices
            all_long.append(item)

    # batches can slightly overshoot due to per-batch rounding up -- trim
    # back down to the requested totals (MCQs trimmed to keep difficulty
    # balance rather than a plain truncation)
    all_mcqs = _trim_balanced_by_difficulty(all_mcqs, num_mcq)
    all_short = all_short[:num_short] if num_short else []
    all_long = all_long[:num_long] if num_long else []

    logger.info(
        f"Quiz generated for '{lecture_id}': {len(all_mcqs)} MCQs, "
        f"{len(all_short)} short, {len(all_long)} long question(s)"
    )

    return {
        "lecture_id": lecture_id,
        "mcqs": all_mcqs,
        "short_questions": all_short,
        "long_questions": all_long,
    }


# ── Export ────────────────────────────────────────────────

def save_quiz_markdown(quiz: dict) -> Path:
    """Write the quiz to work/quizzes/<lecture_id>.md (spec: Markdown export)."""
    lecture_id = quiz["lecture_id"]
    lines = [f"# Quiz -- {lecture_id}\n"]

    if quiz["mcqs"]:
        lines.append("## Multiple Choice Questions\n")
        for i, q in enumerate(quiz["mcqs"], 1):
            lines.append(f"**{i}. ({q.get('difficulty', '?')})** {q.get('question', '')}")
            for j, opt in enumerate(q.get("options", [])):
                marker = "x" if j == q.get("correct_index") else " "
                lines.append(f"- [{marker}] {opt}")
            if q.get("explanation"):
                lines.append(f"  *Explanation:* {q['explanation']}")
            lines.append("")

    if quiz["short_questions"]:
        lines.append("## Short Answer Questions\n")
        for i, q in enumerate(quiz["short_questions"], 1):
            lines.append(f"**{i}.** {q.get('question', '')}")
            lines.append(f"*Answer:* {q.get('answer', '')}")
            lines.append("")

    if quiz["long_questions"]:
        lines.append("## Long Answer Questions\n")
        for i, q in enumerate(quiz["long_questions"], 1):
            lines.append(f"**{i}.** {q.get('question', '')}")
            lines.append(f"*Answer guidance:* {q.get('answer_guidance', '')}")
            lines.append("")

    output_path = config.QUIZ_DIR / f"{lecture_id}.md"
    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Quiz saved: {output_path}")
    return output_path


def save_quiz_json(quiz: dict) -> Path:
    """Write the quiz to work/quizzes/<lecture_id>.json (structured -- for a future frontend)."""
    output_path = config.QUIZ_DIR / f"{quiz['lecture_id']}.json"
    output_path.write_text(json.dumps(quiz, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Quiz JSON saved: {output_path}")
    return output_path


# ── CLI ───────────────────────────────────────────────────

def _ask_int(prompt_text: str, default: int) -> int:
    raw = input(f"{prompt_text} (Enter for {default}): ").strip()
    return int(raw) if raw.isdigit() else default


def main():
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

    num_mcq = _ask_int("Number of MCQs", config.QUIZ_DEFAULT_NUM_MCQ)
    num_short = _ask_int("Number of short-answer questions", config.QUIZ_DEFAULT_NUM_SHORT)
    num_long = _ask_int("Number of long-answer questions", config.QUIZ_DEFAULT_NUM_LONG)

    try:
        quiz = generate_quiz(lecture_id, num_mcq=num_mcq, num_short=num_short, num_long=num_long)
    except Exception as e:
        logger.error(f"Quiz generation failed: {e}")
        return

    md_path = save_quiz_markdown(quiz)
    save_quiz_json(quiz)
    print(f"\nQuiz saved to: {md_path}")


if __name__ == "__main__":
    main()