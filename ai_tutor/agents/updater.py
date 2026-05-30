"""
Student Model Updater — applies grading results to the persistent student state.

Mostly deterministic rule-based logic (spec v2 §8.6). The LLM (Haiku) is only
invoked in one case: when an identified_misconception string fuzzy-matches an
existing misconception_id in the student model. This avoids creating duplicate
misconception entries for the same underlying concept gap.
"""

from datetime import datetime, timezone
from pathlib import Path

import anthropic
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_fixed

from ai_tutor.config import settings
from ai_tutor.models import (
    ConceptMastery,
    DomainStats,
    GradingResult,
    Misconception,
    MasteryStatus,
    Pack,
    SessionEvent,
    StudentModel,
)

_PROMPT_PATH = Path(__file__).parent / "prompts" / "updater.md"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text()

_haiku_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

# Mastery delta rules (spec v2 §8.6)
_MASTERY_DELTA = {
    "demonstrated": +0.3,
    "missing": -0.2,
    "partial": 0.0,   # no mastery change on partial; confidence drops instead
}
_CONFIDENCE_PARTIAL_PENALTY = -0.1


@retry(stop=stop_after_attempt(2), wait=wait_fixed(1), reraise=False)
def _fuzzy_match_misconception(new_text: str, existing_ids: list[str]) -> dict | None:
    """
    Use Claude Haiku to check if a new misconception string maps to an existing ID.
    Returns {"matched_misconception_id": str, "is_new": bool} or None on failure.
    Called only when there are existing misconceptions to compare against.
    """
    if not existing_ids:
        return None

    response = _haiku_client.messages.create(
        model=settings.model_lightweight,
        max_tokens=128,
        system=_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f"New misconception text: \"{new_text}\"\n"
                f"Existing misconception IDs: {existing_ids}\n"
                "Return JSON: {{\"matched_misconception_id\": \"...\", \"is_new\": true|false}}"
            ),
        }],
    )

    import json
    raw = response.content[0].text.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
    return json.loads(raw)


def _to_kebab(text: str) -> str:
    """Convert free-form misconception text to a kebab-case ID."""
    import re
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text[:60]  # cap length


def apply_grading_result(
    grading_result: GradingResult,
    student_model: StudentModel,
    pack: Pack,
    question_id: str,
) -> StudentModel:
    """
    Apply a grading result to the student model and return the updated model.

    Deterministic mastery updates + optional Haiku-assisted misconception matching.
    Does NOT mutate in place — returns a new StudentModel with updated_at timestamp.
    """
    now = datetime.now(timezone.utc)
    signal = grading_result.concept_signal
    concept = signal.concept
    evidence = signal.evidence.value
    confidence = signal.confidence

    # ── 1. Resolve concept → canonical ID + domain ────────────────────────────
    # Coach occasionally returns concept names (e.g. "Orchestrator and subagent roles…")
    # instead of IDs ("orchestrator_subagent_pattern"). Normalise before any writes.
    canonical_concept = concept
    domain_id = None

    # First try: exact ID match
    for c in pack.concepts:
        if c.id == concept:
            canonical_concept = c.id
            domain_id = c.domain
            break

    # Second try: case-insensitive name match (Coach returned a name not an ID)
    if not domain_id:
        for c in pack.concepts:
            if c.name.lower() == concept.lower():
                canonical_concept = c.id
                domain_id = c.domain
                logger.debug(f"Updater: normalised concept name '{concept}' → id '{canonical_concept}'")
                break

    # Last resort: default to D1
    if not domain_id:
        logger.warning(f"Updater: unknown concept '{concept}', defaulting to D1")
        domain_id = "D1"
        canonical_concept = concept  # keep as-is (orphan key, but won't break)

    concept = canonical_concept  # use normalised ID from here on

    # Find domain weight from pack
    domain_weight = next((d.weight for d in pack.domains if d.id == domain_id), 0.0)

    if domain_id not in student_model.domains:
        student_model.domains[domain_id] = DomainStats(weight=domain_weight)

    domain_stats = student_model.domains[domain_id]

    # ── 2. Apply mastery delta ─────────────────────────────────────────────────
    if concept not in domain_stats.concepts:
        domain_stats.concepts[concept] = ConceptMastery()

    concept_mastery = domain_stats.concepts[concept]
    delta = _MASTERY_DELTA[evidence] * confidence
    new_mastery = max(0.0, min(5.0, concept_mastery.mastery + delta))
    concept_mastery.mastery = round(new_mastery, 3)
    concept_mastery.last_seen = now

    # Partial evidence reduces confidence (we're less certain of what we know)
    if evidence == "partial":
        concept_mastery.confidence = max(0.0, concept_mastery.confidence + _CONFIDENCE_PARTIAL_PENALTY)
    elif evidence == "demonstrated":
        concept_mastery.confidence = min(1.0, concept_mastery.confidence + confidence * 0.2)

    # ── 3. Update domain aggregate mastery ────────────────────────────────────
    if domain_stats.concepts:
        avg = sum(c.mastery for c in domain_stats.concepts.values()) / len(domain_stats.concepts)
        domain_stats.aggregate_mastery = round(avg, 3)

    # ── 4. Process misconception ───────────────────────────────────────────────
    raw_misconception = grading_result.identified_misconception
    if raw_misconception and raw_misconception != "QUESTION_QUALITY_ISSUE":
        existing_ids = list(student_model.misconceptions.keys())

        # Try fuzzy match if there are existing misconceptions
        matched_id = None
        if existing_ids:
            match_result = _fuzzy_match_misconception(raw_misconception, existing_ids)
            if match_result and not match_result.get("is_new", True):
                matched_id = match_result.get("matched_misconception_id")

        misconception_id = matched_id or _to_kebab(raw_misconception)

        if misconception_id not in student_model.misconceptions:
            student_model.misconceptions[misconception_id] = Misconception()

        m = student_model.misconceptions[misconception_id]
        m.count += 1
        m.last_seen = now
        if m.count >= 2:
            m.status = MasteryStatus.active

        logger.debug(f"Misconception '{misconception_id}' count={m.count}")

    # ── 5. Append to session history ──────────────────────────────────────────
    student_model.session_history.append(SessionEvent(
        question_id=question_id,
        verdict=grading_result.verdict,
        concept=concept,
        domain=domain_id,
        timestamp=now,
    ))

    # Keep only last 100 events to avoid unbounded growth
    if len(student_model.session_history) > 100:
        student_model.session_history = student_model.session_history[-100:]

    student_model.updated_at = now
    logger.info(
        f"Updated student model: concept={concept} mastery={concept_mastery.mastery:.2f} "
        f"domain={domain_id} aggregate={domain_stats.aggregate_mastery:.2f}"
    )
    return student_model
