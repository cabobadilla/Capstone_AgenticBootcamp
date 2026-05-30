"""
Examiner agent tests.

Integration tests that call the real Examiner agent with real fixtures.
Skipped if ANTHROPIC_API_KEY is not set (CI without secrets).

These tests validate the contract:
- Output JSON matches the Question schema
- Exactly 4 options (A, B, C, D)
- Exactly one correct answer
- All source_citations are URLs that appear in the fixture chunk sources
"""

import json
from pathlib import Path

import pytest

from ai_tutor.config import settings
from ai_tutor.models import Chunk, Pack, Domain, Concept, Question, QuestionDifficulty
from ai_tutor.packs.loader import load_pack

FIXTURES_DIR = Path(__file__).parent / "fixtures"
# Use settings (reads .env) rather than os.getenv (reads raw env only)
NEEDS_API = pytest.mark.skipif(
    not settings.anthropic_api_key or settings.anthropic_api_key.startswith("your-"),
    reason="ANTHROPIC_API_KEY not configured",
)


def load_fixture_chunks() -> list[Chunk]:
    """Load saved ChromaDB chunks from the fixture file."""
    with (FIXTURES_DIR / "sample_chunks.json").open() as f:
        raw = json.load(f)
    return [Chunk(**c) for c in raw]


@pytest.fixture
def cca_f_pack() -> Pack:
    return load_pack("cca-f")


@pytest.fixture
def d1_chunks() -> list[Chunk]:
    return load_fixture_chunks()


# ── Schema validation (fast, no LLM call) ────────────────────────────────────

def test_fixture_chunks_load():
    """Fixture chunks file exists and loads into Chunk models."""
    chunks = load_fixture_chunks()
    assert len(chunks) >= 3
    for chunk in chunks:
        assert chunk.source_url.startswith("http")
        assert len(chunk.content) > 50


def test_pack_loads(cca_f_pack):
    """CCA-F pack.yaml loads and validates correctly."""
    pack = cca_f_pack
    assert pack.id == "cca-f"
    assert len(pack.domains) == 5
    domain_ids = {d.id for d in pack.domains}
    assert "D1" in domain_ids
    # Weights must sum to ~1.0
    total_weight = sum(d.weight for d in pack.domains)
    assert abs(total_weight - 1.0) < 0.01, f"Domain weights sum to {total_weight}, expected ~1.0"


# ── Live LLM integration tests ────────────────────────────────────────────────

@NEEDS_API
def test_examiner_generates_valid_question(cca_f_pack, d1_chunks):
    """Examiner produces a schema-valid Question with exactly one correct answer."""
    from ai_tutor.agents.examiner import generate_question

    question = generate_question(
        pack=cca_f_pack,
        target_concept="tool_use_execution_loop",
        domain="D1",
        difficulty=QuestionDifficulty.conceptual,
        retrieved_chunks=d1_chunks[:5],
    )

    # Schema checks
    assert isinstance(question, Question)
    assert len(question.options) == 4
    assert question.domain == "D1"
    # difficulty may differ from requested: CCA-F pack.style="scenario-based" can override
    assert question.difficulty in (QuestionDifficulty.conceptual, QuestionDifficulty.scenario)

    # Exactly one correct answer
    correct_options = [o for o in question.options if o.is_correct]
    assert len(correct_options) == 1, f"Expected 1 correct option, got {len(correct_options)}"

    # All options have rationale
    for opt in question.options:
        assert opt.rationale, f"Option {opt.id} missing rationale"

    # Citations must be URLs from the fixture chunks
    valid_urls = {c.source_url for c in d1_chunks}
    for url in question.source_citations:
        assert url in valid_urls, f"Citation URL '{url}' not in retrieved chunks"


@NEEDS_API
def test_examiner_three_concepts(cca_f_pack, d1_chunks):
    """Generate 3 questions on different D1 concepts — all must be schema-valid."""
    from ai_tutor.agents.examiner import generate_question

    concepts = [
        "agentic_loop_basics",
        "orchestrator_subagent_pattern",
        "multi_agent_trust_boundaries",
    ]
    questions = []
    for concept in concepts:
        q = generate_question(
            pack=cca_f_pack,
            target_concept=concept,
            domain="D1",
            difficulty=QuestionDifficulty.conceptual,
            retrieved_chunks=d1_chunks[:5],
        )
        questions.append(q)

    assert len(questions) == 3
    for q in questions:
        assert len(q.options) == 4
        assert sum(1 for o in q.options if o.is_correct) == 1
