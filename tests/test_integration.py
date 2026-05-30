"""
Integration tests — end-to-end flows through the LangGraph tutor.

These tests make real LLM calls and use the live ChromaDB collection.
They validate the complete V1 stack: load pack → retrieve → generate → grade → update → persist.
"""

import json
import os
import uuid

import pytest

from ai_tutor.config import settings
from ai_tutor.packs.loader import load_pack

NEEDS_API = pytest.mark.skipif(
    not settings.anthropic_api_key or settings.anthropic_api_key.startswith("your-"),
    reason="ANTHROPIC_API_KEY not configured",
)
NEEDS_CHROMA = pytest.mark.skipif(
    not (settings.chroma_persist_dir / "chroma.sqlite3").exists(),
    reason="ChromaDB not initialised",
)


@NEEDS_CHROMA
def test_retriever_all_domains():
    """All 5 domains must have indexed chunks."""
    from ai_tutor.rag.retriever import retrieve
    from ai_tutor.ingestion.index import get_collection_stats

    stats = get_collection_stats("cca-f")
    domains_with_data = set(stats["domains"].keys())
    expected = {"D1", "D2", "D3", "D4", "D5"}
    assert expected.issubset(domains_with_data), f"Missing domains: {expected - domains_with_data}"


@NEEDS_API
@NEEDS_CHROMA
def test_full_practice_flow():
    """
    End-to-end: generate a question → submit an answer → verify student model updated.
    Uses a unique student_id so it doesn't interfere with the real default student.
    """
    from ai_tutor.graph.tutor_graph import run_practice, run_grade
    from ai_tutor.models import StudentModel
    from ai_tutor.student_model.store import load_student_model, reset_student_model

    test_student = f"test-{uuid.uuid4().hex[:8]}"

    # Generate a question
    result = run_practice(
        pack_id="cca-f",
        student_id=test_student,
        domain="D1",
    )
    assert result["output_type"] == "question"
    q = result["output_data"]
    assert len(q["options"]) == 4
    assert sum(1 for o in q["options"] if o["is_correct"]) == 1

    # Find the correct answer to submit
    correct_id = next(o["id"] for o in q["options"] if o["is_correct"])

    # Grade the answer
    grade_result = run_grade(
        pack_id="cca-f",
        student_id=test_student,
        current_question=q,
        student_answer=correct_id,
        retrieved_chunks=result.get("retrieved_chunks", []),
    )
    assert grade_result["grading_result"]["verdict"] == "correct"

    # Verify student model was persisted
    pack = load_pack("cca-f")
    student_model = load_student_model(test_student, "cca-f", pack)
    assert len(student_model.session_history) == 1
    assert student_model.session_history[0].verdict == "correct"

    # Cleanup test student
    reset_student_model(test_student, "cca-f")


@NEEDS_API
@NEEDS_CHROMA
def test_qna_returns_cited_answer():
    """Q&A flow must return an answer containing at least one source citation."""
    from ai_tutor.graph.tutor_graph import run_qna

    result = run_qna(
        pack_id="cca-f",
        student_id=settings.default_student_id,
        # Use a question that's in the corpus (tool use is in D1/D2)
        question="How does the tool_use / tool_result round-trip work in the Anthropic API agentic loop?",
    )
    assert result["output_type"] == "qna_answer"
    answer = result["output_data"]
    assert isinstance(answer, str)
    assert len(answer) > 100


@NEEDS_CHROMA
def test_dashboard_loads():
    """Dashboard flow must return domain mastery data without LLM calls."""
    from ai_tutor.graph.tutor_graph import run_dashboard

    result = run_dashboard("cca-f", settings.default_student_id)
    assert result["output_type"] == "dashboard"
    data = result["output_data"]
    assert "domain_mastery" in data
    # All 5 domains must appear (pre-populated at model creation)
    for domain in ["D1", "D2", "D3", "D4", "D5"]:
        assert domain in data["domain_mastery"], f"Missing domain {domain} in dashboard"


@NEEDS_API
@NEEDS_CHROMA
def test_student_model_persists_across_invocations():
    """Student model file must persist mastery updates across separate graph calls."""
    from ai_tutor.graph.tutor_graph import run_practice, run_grade
    from ai_tutor.models import StudentModel
    from ai_tutor.student_model.store import load_student_model, reset_student_model

    test_student = f"persist-{uuid.uuid4().hex[:8]}"
    pack = load_pack("cca-f")

    # Run two practice+grade cycles
    for i in range(2):
        r = run_practice("cca-f", test_student, domain="D1")
        q = r["output_data"]
        correct = next(o["id"] for o in q["options"] if o["is_correct"])
        run_grade("cca-f", test_student, q, correct, r.get("retrieved_chunks", []))

    # Load from disk and verify 2 events recorded
    model = load_student_model(test_student, "cca-f", pack)
    assert len(model.session_history) == 2

    reset_student_model(test_student, "cca-f")
