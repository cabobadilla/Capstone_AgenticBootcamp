"""
Student Model Updater tests — validates deterministic mastery delta rules.
No LLM calls in these tests (pure rule-based logic).
"""

import pytest

from ai_tutor.models import (
    AnswerChoice, ConceptMastery, DomainStats, EvidenceLevel, GradingResult,
    ConceptSignal, Citation, MasteryStatus, Misconception, Pack, StudentModel,
)
from ai_tutor.packs.loader import load_pack


def make_student_model(pack: Pack, concept: str = "agentic_loop_basics",
                       initial_mastery: float = 2.0) -> StudentModel:
    model = StudentModel(
        student_id="test-student",
        pack_id="cca-f",
        domains={
            "D1": DomainStats(
                weight=0.27,
                aggregate_mastery=initial_mastery,
                concepts={concept: ConceptMastery(mastery=initial_mastery, confidence=0.5)},
            )
        },
    )
    return model


def make_grading_result(verdict: str, evidence: str, confidence: float,
                        misconception: str | None = None) -> GradingResult:
    return GradingResult(
        verdict=verdict,
        selected_option=AnswerChoice.A,
        correct_option=AnswerChoice.A if verdict == "correct" else AnswerChoice.B,
        explanation="Test explanation.",
        citations=[Citation(id=1, url="https://docs.anthropic.com/test", title="Test")],
        identified_misconception=misconception,
        concept_signal=ConceptSignal(
            concept="agentic_loop_basics",
            evidence=EvidenceLevel(evidence),
            confidence=confidence,
        ),
    )


@pytest.fixture
def pack():
    return load_pack("cca-f")


def test_demonstrated_increases_mastery(pack):
    from ai_tutor.agents.updater import apply_grading_result
    model = make_student_model(pack, initial_mastery=2.0)
    result = make_grading_result("correct", "demonstrated", confidence=0.5)
    updated = apply_grading_result(result, model, pack, question_id="q1")

    concept = updated.domains["D1"].concepts["agentic_loop_basics"]
    assert concept.mastery > 2.0, "Mastery should increase on demonstrated"
    assert concept.mastery == pytest.approx(2.0 + 0.3 * 0.5, abs=0.001)


def test_missing_decreases_mastery(pack):
    from ai_tutor.agents.updater import apply_grading_result
    model = make_student_model(pack, initial_mastery=2.0)
    result = make_grading_result("incorrect", "missing", confidence=0.5)
    updated = apply_grading_result(result, model, pack, question_id="q1")

    concept = updated.domains["D1"].concepts["agentic_loop_basics"]
    assert concept.mastery < 2.0, "Mastery should decrease on missing"


def test_mastery_clamped_to_zero(pack):
    from ai_tutor.agents.updater import apply_grading_result
    model = make_student_model(pack, initial_mastery=0.1)
    result = make_grading_result("incorrect", "missing", confidence=1.0)
    updated = apply_grading_result(result, model, pack, question_id="q1")

    concept = updated.domains["D1"].concepts["agentic_loop_basics"]
    assert concept.mastery >= 0.0, "Mastery must not go below 0"


def test_mastery_clamped_to_five(pack):
    from ai_tutor.agents.updater import apply_grading_result
    model = make_student_model(pack, initial_mastery=4.95)
    result = make_grading_result("correct", "demonstrated", confidence=1.0)
    updated = apply_grading_result(result, model, pack, question_id="q1")

    concept = updated.domains["D1"].concepts["agentic_loop_basics"]
    assert concept.mastery <= 5.0, "Mastery must not exceed 5"


def test_misconception_increments(pack):
    from ai_tutor.agents.updater import apply_grading_result
    model = make_student_model(pack, initial_mastery=2.0)
    result = make_grading_result("incorrect", "missing", confidence=0.5,
                                 misconception="confuses tool_use with function_call")
    updated = apply_grading_result(result, model, pack, question_id="q1")
    assert len(updated.misconceptions) == 1
    m = list(updated.misconceptions.values())[0]
    assert m.count == 1


def test_misconception_active_after_two(pack):
    from ai_tutor.agents.updater import apply_grading_result
    model = make_student_model(pack, initial_mastery=2.0)
    result = make_grading_result("incorrect", "missing", confidence=0.5,
                                 misconception="confuses tool_use with function_call")
    updated = apply_grading_result(result, model, pack, question_id="q1")
    updated2 = apply_grading_result(result, updated, pack, question_id="q2")

    m = list(updated2.misconceptions.values())[0]
    assert m.count == 2
    assert m.status == MasteryStatus.active


def test_session_history_appended(pack):
    from ai_tutor.agents.updater import apply_grading_result
    model = make_student_model(pack, initial_mastery=2.0)
    result = make_grading_result("correct", "demonstrated", confidence=0.5)
    updated = apply_grading_result(result, model, pack, question_id="test-q-123")
    assert len(updated.session_history) == 1
    assert updated.session_history[0].question_id == "test-q-123"
