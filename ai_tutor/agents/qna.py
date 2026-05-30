"""
Q&A Agent — answers free-form student questions grounded in the active Pack's corpus.

Scoped to the Pack's domains (rejects off-topic questions politely).
Every factual claim is cited with a bracketed [1] reference and a citations block.
"""

from pathlib import Path

import anthropic
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_fixed

from ai_tutor.config import settings
from ai_tutor.models import Chunk, Pack

_PROMPT_PATH = Path(__file__).parent / "prompts" / "qna.md"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text()

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), reraise=True)
def _call_qna(user_message: str) -> str:
    response = _client.messages.create(
        model=settings.model_primary,
        max_tokens=1500,
        system=[{"type": "text", "text": _SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


def answer_question(
    question: str,
    retrieved_chunks: list[Chunk],
    pack: Pack,
) -> str:
    """
    Answer a free-form student question with grounded citations.
    Returns markdown text including a JSON citations block at the end.
    """
    chunks_text = "\n\n---\n\n".join(
        f"[{i+1}] Source: {c.source_url}\nTitle: {c.source_title}\n{c.content}"
        for i, c in enumerate(retrieved_chunks[:5])
    )

    domain_names = ", ".join(f"{d.id}: {d.name}" for d in pack.domains)

    user_message = f"""
pack.name: {pack.name}
pack.domains: {domain_names}

student_question: {question}

retrieved_chunks:
{chunks_text}

Answer the question now. Include inline citations [1],[2] and end with
a ```json citations block.
"""
    answer = _call_qna(user_message)
    logger.info(f"Q&A answered: '{question[:60]}...' with {len(retrieved_chunks)} chunks")
    return answer
