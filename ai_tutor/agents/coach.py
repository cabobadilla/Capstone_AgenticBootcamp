"""
Coach agent — session orchestrator that decides what happens next.

The Coach is the only agent that reads the Student Model. It uses mastery
scores and domain weights to select which concept to target next, ensuring
the student's weakest areas get the most practice (spec v2 §8.3).

In V1, the Coach is called by the LangGraph router. It does NOT generate
content — it only routes: which concept, which domain, which action.
"""

from pathlib import Path

import anthropic
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_fixed

from ai_tutor.config import settings
from ai_tutor.models import Pack, StudentModel

_PROMPT_PATH = Path(__file__).parent / "prompts" / "coach.md"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text()

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

_COACH_TOOL = {
    "name": "route_session",
    "description": "Route the session to the next action.",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["ask_question", "answer_qna", "explain_concept", "show_dashboard", "end_session"],
            },
            "target_concept": {"type": ["string", "null"]},
            "target_domain": {"type": ["string", "null"]},
            "difficulty": {"type": ["string", "null"], "enum": ["conceptual", "scenario", None]},
            "rationale": {"type": "string"},
        },
        "required": ["action", "rationale"],
    },
}


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), reraise=True)
def _call_coach(user_message: str) -> dict:
    response = _client.messages.create(
        model=settings.model_primary,
        max_tokens=512,  # Coach output is small — just a routing decision
        system=[{"type": "text", "text": _SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        tools=[_COACH_TOOL],
        tool_choice={"type": "tool", "name": "route_session"},
        messages=[{"role": "user", "content": user_message}],
    )
    for block in response.content:
        if block.type == "tool_use":
            return block.input
    raise ValueError("Coach did not return a tool_use block")


def decide_next_action(
    user_input: str,
    pack: Pack,
    student_model: StudentModel | None,
    session_history: list[dict],
    last_concept: str | None = None,
) -> dict:
    """
    Ask the Coach what to do next given the current session context.

    Returns a dict with keys: action, target_concept, target_domain, difficulty, rationale.
    Falls back to sensible defaults if the LLM call fails.
    """
    # Summarise student mastery for the Coach (keep it short to save tokens)
    mastery_summary = "No mastery data yet."
    if student_model and student_model.domains:
        lines = []
        for domain_id, stats in student_model.domains.items():
            lines.append(f"  {domain_id}: aggregate_mastery={stats.aggregate_mastery:.1f}/5.0")
        mastery_summary = "\n".join(lines)

    # Active misconceptions (count >= 2)
    active_misconceptions = []
    if student_model:
        active_misconceptions = [
            mid for mid, m in student_model.misconceptions.items() if m.count >= 2
        ]

    # Highest-weight domain defaults (used by Coach as fallback)
    sorted_domains = sorted(pack.domains, key=lambda d: d.weight, reverse=True)
    default_domain = sorted_domains[0].id if sorted_domains else "D1"

    # Build per-domain concept ID list for the Coach so it returns valid IDs, not free-text names.
    concept_ids_by_domain = {}
    for domain in pack.domains:
        concept_ids_by_domain[domain.id] = [c.id for c in pack.concepts if c.domain == domain.id]

    user_message = f"""
user_input: {user_input or 'start_practice'}

pack.name: {pack.name}
pack.domains: {[{'id': d.id, 'name': d.name, 'weight': d.weight} for d in pack.domains]}

IMPORTANT: target_concept MUST be one of the concept IDs listed below — not a free-text description.
concept_ids_by_domain:
{concept_ids_by_domain}

student_model.mastery:
{mastery_summary}

active_misconceptions: {active_misconceptions}
last_concept: {last_concept or 'none'}
session_questions_count: {len(session_history)}
default_domain: {default_domain}

Route the session now. Set target_concept to a concept ID from the list above.
"""

    try:
        result = _call_coach(user_message)
        # Apply default domain if Coach didn't specify one
        if not result.get("target_domain"):
            result["target_domain"] = default_domain
        logger.info(f"Coach decision: action={result['action']} concept={result.get('target_concept')} domain={result.get('target_domain')}")
        return result
    except Exception as e:
        logger.warning(f"Coach call failed ({e}), using defaults")
        return {
            "action": "ask_question",
            "target_concept": None,
            "target_domain": default_domain,
            "difficulty": "conceptual",
            "rationale": "fallback",
        }
