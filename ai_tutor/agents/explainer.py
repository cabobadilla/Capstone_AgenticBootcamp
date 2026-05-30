"""
Explainer agent — produces calibrated in-depth explanations of concepts.

Unlike the Examiner and Grader, the Explainer returns free-form Markdown text
(not structured JSON), since its output is purely educational prose. It uses
tool_use only for the citations block at the end.
"""

from pathlib import Path

import anthropic
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_fixed

from ai_tutor.config import settings
from ai_tutor.models import Chunk

_PROMPT_PATH = Path(__file__).parent / "prompts" / "explainer.md"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text()

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), reraise=True)
def _call_explainer(user_message: str) -> str:
    response = _client.messages.create(
        model=settings.model_primary,
        max_tokens=1024,
        system=[{"type": "text", "text": _SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


def explain_concept(
    concept: str,
    current_mastery: float,
    retrieved_chunks: list[Chunk],
    context_hint: str | None = None,
) -> str:
    """
    Produce a mastery-calibrated explanation of a concept.
    Returns markdown text with inline [1],[2] citations.
    """
    chunks_text = "\n\n---\n\n".join(
        f"[{i+1}] Source: {c.source_url}\n{c.content}"
        for i, c in enumerate(retrieved_chunks[:4])
    )

    user_message = f"""
concept: {concept}
current_mastery: {current_mastery:.1f}/5.0
context_hint: {context_hint or 'none'}

retrieved_chunks:
{chunks_text}

Produce the explanation now (150-400 words, markdown, end with "Want a practice question on this?").
"""
    explanation = _call_explainer(user_message)
    logger.info(f"Explained concept={concept} mastery={current_mastery:.1f}")
    return explanation
