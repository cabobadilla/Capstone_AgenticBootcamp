"""
Grader agent tests — validates verdict, citations, and diagnostic signal.
"""

import json
from pathlib import Path

import pytest

from ai_tutor.config import settings
from ai_tutor.models import AnswerChoice, Chunk, GradingResult, Question

FIXTURES_DIR = Path(__file__).parent / "fixtures"
NEEDS_API = pytest.mark.skipif(
    not settings.anthropic_api_key or settings.anthropic_api_key.startswith("your-"),
    reason="ANTHROPIC_API_KEY not configured",
)


def load_fixture_chunks() -> list[Chunk]:
    with (FIXTURES_DIR / "sample_chunks.json").open() as f:
        return [Chunk(**c) for c in json.load(f)]


def make_fixture_question() -> Question:
    """Build a minimal valid Question fixture without calling the Examiner."""
    return Question(
        question_id="fixture-q-001",
        stem=(
            "An agent built with the Anthropic SDK receives a tool_use block "
            "in the assistant message. What must the agent return in the next "
            "human turn to continue the agentic loop correctly?"
        ),
        options=[
            {"id": "A", "text": "A new user message with role='tool'", "is_correct": False, "rationale": "Incorrect role name."},
            {"id": "B", "text": "A message with role='user' containing a tool_result block", "is_correct": True, "rationale": "Correct — tool results go back as user messages."},
            {"id": "C", "text": "Call the API again with the same messages list", "is_correct": False, "rationale": "Would not advance the loop."},
            {"id": "D", "text": "Set stop_reason='tool_use' in the next request", "is_correct": False, "rationale": "stop_reason is output, not input."},
        ],
        target_concept="tool_use_execution_loop",
        domain="D1",
        difficulty="conceptual",
        source_citations=["https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview"],
    )


@NEEDS_API
def test_grader_correct_answer():
    """Grader returns verdict=correct when the student picks the right option."""
    from ai_tutor.agents.grader import grade_answer

    question = make_fixture_question()
    chunks = load_fixture_chunks()
    result = grade_answer(question, student_answer=AnswerChoice.B, retrieved_chunks=chunks)

    assert result.verdict == "correct"
    assert result.correct_option == AnswerChoice.B
    assert result.explanation  # non-empty markdown
    assert len(result.citations) >= 1
    # Confidence must be capped at 0.6 (spec v2 §8.2)
    assert result.concept_signal.confidence <= 0.6


@NEEDS_API
def test_grader_incorrect_answer_has_misconception():
    """Grader identifies a misconception when the student picks a wrong option."""
    from ai_tutor.agents.grader import grade_answer

    question = make_fixture_question()
    chunks = load_fixture_chunks()
    result = grade_answer(question, student_answer=AnswerChoice.A, retrieved_chunks=chunks)

    assert result.verdict == "incorrect"
    assert result.correct_option == AnswerChoice.B
    # Misconception should be identified for wrong answers
    assert result.identified_misconception is not None
    assert result.concept_signal.evidence in ("partial", "missing")


@NEEDS_API
def test_grader_citations_are_real_urls(load_fixture_chunks=load_fixture_chunks):
    """Every citation URL in the grader output must appear in the retrieved chunks."""
    from ai_tutor.agents.grader import grade_answer

    question = make_fixture_question()
    chunks = load_fixture_chunks()
    valid_urls = {c.source_url for c in chunks}

    result = grade_answer(question, student_answer=AnswerChoice.C, retrieved_chunks=chunks)
    for citation in result.citations:
        assert citation.url in valid_urls, f"Citation URL '{citation.url}' not in chunks"
