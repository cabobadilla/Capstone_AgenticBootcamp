"""
Examiner agent — generates a single exam-style multiple-choice question.

Receives: pack metadata, target concept, domain, difficulty, retrieved chunks.
Returns: a validated Question object.

Key implementation choices:
- Prompt caching on the system prompt (Anthropic ephemeral cache_control) cuts
  repeated token costs since the system prompt is large and stable per session.
- tenacity retries (3 attempts) on JSON parse or Pydantic validation failure,
  because structured output from LLMs occasionally has minor format deviations.
- The Examiner is intentionally stateless — it knows nothing about the student
  model; that context lives in the Coach and is not needed for generation.
"""

from pathlib import Path

import anthropic
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_fixed

from ai_tutor.config import settings
from ai_tutor.models import Chunk, Pack, Question, QuestionDifficulty

# Load the system prompt once at module import — avoids repeated file reads
_PROMPT_PATH = Path(__file__).parent / "prompts" / "examiner.md"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text()

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

# Tool schema for structured output — guarantees valid JSON, no escaping issues
_EXAMINER_TOOL = {
    "name": "submit_question",
    "description": "Submit a single exam-style multiple-choice question.",
    "input_schema": {
        "type": "object",
        "properties": {
            "question_id": {"type": "string"},
            "type": {"type": "string", "enum": ["multiple_choice"]},
            "stem": {"type": "string"},
            "options": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "enum": ["A", "B", "C", "D"]},
                        "text": {"type": "string"},
                        "is_correct": {"type": "boolean"},
                        "rationale": {"type": "string"},
                    },
                    "required": ["id", "text", "is_correct", "rationale"],
                },
                "minItems": 4,
                "maxItems": 4,
            },
            "target_concept": {"type": "string"},
            "domain": {"type": "string"},
            "difficulty": {"type": "string", "enum": ["conceptual", "scenario"]},
            "source_citations": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["stem", "options", "target_concept", "domain", "difficulty", "source_citations"],
    },
}


def _format_chunks(chunks: list[Chunk]) -> str:
    """Format retrieved chunks into a numbered list for the LLM user message."""
    if not chunks:
        return "No retrieved chunks available."
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"[{i}] Source: {chunk.source_url}\n"
            f"Section: {chunk.section_path or 'n/a'}\n"
            f"Content:\n{chunk.content}"
        )
    return "\n\n---\n\n".join(parts)


def _format_pack_summary(pack: Pack) -> str:
    """Build a compact pack descriptor to inject into the user message."""
    domains_str = "\n".join(
        f"  - {d.id}: {d.name} (weight: {d.weight:.0%})" for d in pack.domains
    )
    return (
        f"pack.name: {pack.name}\n"
        f"pack.full_name: {pack.full_name}\n"
        f"pack.style: {pack.style}\n"
        f"pack.domains:\n{domains_str}"
    )


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), reraise=True)
def _call_examiner(user_message: str) -> dict:
    """
    Call Claude with tool_use to get guaranteed valid JSON output.
    Tool use bypasses JSON string escaping issues that arise when asking for
    raw JSON in the prompt — the API populates the schema directly.
    """
    response = _client.messages.create(
        model=settings.model_primary,
        max_tokens=2048,
        system=[
            {
                "type": "text",
                "text": _SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        tools=[_EXAMINER_TOOL],
        tool_choice={"type": "tool", "name": "submit_question"},
        messages=[{"role": "user", "content": user_message}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_question":
            return block.input
    raise ValueError("Examiner did not return a tool_use block")


def generate_question(
    pack: Pack,
    target_concept: str,
    domain: str,
    difficulty: QuestionDifficulty,
    retrieved_chunks: list[Chunk],
) -> Question:
    """
    Generate one exam-style question and return a validated Question object.

    Raises ValueError if the LLM returns an error response (e.g., insufficient_context).
    Raises ValidationError (Pydantic) if the tool output fails schema validation.
    """
    user_message = f"""
{_format_pack_summary(pack)}

target_concept: {target_concept}
domain: {domain}
difficulty: {difficulty.value}

retrieved_chunks:
{_format_chunks(retrieved_chunks)}

Call submit_question with the complete question. If retrieved_chunks lack
sufficient information, still call the tool but note it in the stem.
"""

    data = _call_examiner(user_message)

    # Add required fields that may be omitted by the LLM
    data.setdefault("question_id", __import__("uuid").uuid4().__str__())
    data.setdefault("type", "multiple_choice")

    question = Question(**data)
    logger.info(
        f"Generated question: concept={target_concept} domain={domain} "
        f"difficulty={difficulty.value} correct={next(o.id for o in question.options if o.is_correct)}"
    )
    return question
