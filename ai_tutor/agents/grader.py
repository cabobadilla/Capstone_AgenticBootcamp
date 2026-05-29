"""
Grader agent — evaluates a student's answer and produces pedagogical feedback.

The Grader is the most user-visible agent: its output (explanation + citations)
is what the student reads after every question. Quality here directly determines
the value of the tutor.

Key design decisions:
- Same prompt-caching pattern as the Examiner (ephemeral cache on system prompt).
- The Grader also re-receives the retrieved_chunks so its factual claims are
  grounded in the same sources the Examiner used — citations are consistent.
- The concept_signal output feeds directly into the Student Model Updater (V1),
  so the schema here must exactly match what the Updater expects.
"""

from pathlib import Path

import anthropic
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_fixed

from ai_tutor.config import settings
from ai_tutor.models import AnswerChoice, Chunk, GradingResult, Question

_PROMPT_PATH = Path(__file__).parent / "prompts" / "grader.md"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text()

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _format_question_for_grader(question: Question, student_answer: AnswerChoice) -> str:
    """Format the question + student answer as structured input for the Grader."""
    options_str = "\n".join(
        f"  {o.id}. {o.text} {'[SELECTED BY STUDENT]' if o.id == student_answer else ''}"
        for o in question.options
    )
    return (
        f"Question (ID: {question.question_id}):\n"
        f"  Concept: {question.target_concept}\n"
        f"  Domain: {question.domain}\n"
        f"  Difficulty: {question.difficulty.value}\n\n"
        f"Stem:\n{question.stem}\n\n"
        f"Options:\n{options_str}\n\n"
        f"Student selected: {student_answer.value}"
    )


def _format_chunks(chunks: list[Chunk]) -> str:
    if not chunks:
        return "No retrieved chunks available."
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(f"[{i}] Source: {chunk.source_url}\nContent:\n{chunk.content}")
    return "\n\n---\n\n".join(parts)


# Tool schema for structured output — Claude fills this via tool_use which guarantees valid JSON
_GRADER_TOOL = {
    "name": "submit_grading_result",
    "description": "Submit the grading result for a student's answer.",
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {"type": "string", "enum": ["correct", "incorrect"]},
            "selected_option": {"type": "string", "enum": ["A", "B", "C", "D"]},
            "correct_option": {"type": "string", "enum": ["A", "B", "C", "D"]},
            "explanation": {
                "type": "string",
                "description": "Pedagogical explanation in markdown with [1],[2] inline citations."
            },
            "citations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "url": {"type": "string"},
                        "title": {"type": "string"},
                    },
                    "required": ["id", "url"],
                },
            },
            "identified_misconception": {
                "type": ["string", "null"],
                "description": "The likely misconception, or null if the answer was correct.",
            },
            "concept_signal": {
                "type": "object",
                "properties": {
                    "concept": {"type": "string"},
                    "evidence": {"type": "string", "enum": ["demonstrated", "partial", "missing"]},
                    "confidence": {"type": "number"},
                },
                "required": ["concept", "evidence", "confidence"],
            },
        },
        "required": ["verdict", "selected_option", "correct_option", "explanation",
                     "citations", "identified_misconception", "concept_signal"],
    },
}


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), reraise=True)
def _call_grader(user_message: str) -> dict:
    """
    Call Claude with tool_use to get guaranteed valid JSON output.
    Tool use bypasses the JSON-in-string escaping problem — Claude populates
    the tool input schema directly, so no manual JSON parsing needed.
    """
    response = _client.messages.create(
        model=settings.model_primary,
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": _SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        tools=[_GRADER_TOOL],
        # Force Claude to always call the tool (no prose fallback)
        tool_choice={"type": "tool", "name": "submit_grading_result"},
        messages=[{"role": "user", "content": user_message}],
    )
    # Extract the tool_use block input — always valid JSON from the API
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_grading_result":
            return block.input
    raise ValueError("Grader did not return a tool_use block")


def grade_answer(
    question: Question,
    student_answer: AnswerChoice,
    retrieved_chunks: list[Chunk],
) -> GradingResult:
    """
    Grade a student's answer and return structured pedagogical feedback.

    Uses tool_use for structured output — avoids JSON string escaping issues.
    """
    user_message = f"""
{_format_question_for_grader(question, student_answer)}

retrieved_chunks (same sources the question was built from):
{_format_chunks(retrieved_chunks[:3])}

Call submit_grading_result with your complete grading output.
"""

    data = _call_grader(user_message)
    result = GradingResult(**data)

    logger.info(
        f"Graded question {question.question_id}: verdict={result.verdict} "
        f"evidence={result.concept_signal.evidence} misconception={result.identified_misconception}"
    )
    return result
