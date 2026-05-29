"""
Shared Pydantic models used across all layers of the AI Tutor platform.

Design principle: all models are Pack-agnostic — domain/concept identifiers
are strings that come from the active Certification Pack, not hardcoded values.
This is what makes the platform generic (spec v2 §2).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ── Enums ─────────────────────────────────────────────────────────────────────

class QuestionDifficulty(str, Enum):
    """Conceptual = tests a single precise mechanism; scenario = realistic prod situation."""
    conceptual = "conceptual"
    scenario = "scenario"


class QuestionType(str, Enum):
    multiple_choice = "multiple_choice"


class AnswerChoice(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class EvidenceLevel(str, Enum):
    """Grader diagnostic signal: how strongly does the answer evidence understanding?"""
    demonstrated = "demonstrated"  # correct + non-guessable option
    partial = "partial"             # right domain, wrong mechanism
    missing = "missing"             # fundamental misunderstanding


class MasteryStatus(str, Enum):
    active = "active"       # recurring misconception (count >= 2)
    resolved = "resolved"


# ── Certification Pack ────────────────────────────────────────────────────────

class Domain(BaseModel):
    """One exam domain in a Certification Pack (e.g., D1 — Agentic Architecture)."""
    id: str                  # e.g., "D1"
    name: str
    weight: float            # fraction of exam score (e.g., 0.27 for 27%)


class Concept(BaseModel):
    """A single testable concept within a domain."""
    id: str                  # kebab-case, e.g., "agentic_loop_stop_reason"
    name: str
    domain: str              # matches Domain.id
    prerequisites: list[str] = Field(default_factory=list)  # other concept ids
    leads_to: list[str] = Field(default_factory=list)        # used by V2 curriculum graph


class Pack(BaseModel):
    """
    Declarative Certification Pack loaded from packs/<id>/pack.yaml.
    Agents receive this at runtime — they have no hardcoded cert knowledge.
    """
    id: str                        # e.g., "cca-f"
    name: str                      # e.g., "CCA-F"
    full_name: str
    authority: str                 # e.g., "Anthropic"
    exam_format: str               # e.g., "multiple_choice"
    question_count: int
    duration_minutes: int
    passing_score: int
    scoring_scale: tuple[int, int] # e.g., (100, 1000)
    style: str                     # "scenario-based" | "conceptual" | "mixed"
    language: str = "en"
    corpus_version: str = "v1"
    domains: list[Domain]
    concepts: list[Concept] = Field(default_factory=list)


# ── Question ──────────────────────────────────────────────────────────────────

class QuestionOption(BaseModel):
    """One answer choice in a multiple-choice question."""
    id: AnswerChoice
    text: str
    is_correct: bool
    # The Examiner always provides rationale for each option (including why wrong ones are wrong)
    rationale: str


class Question(BaseModel):
    """Output of the Examiner agent — a single exam-style multiple-choice question."""
    question_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: QuestionType = QuestionType.multiple_choice
    stem: str                        # the question text
    options: list[QuestionOption]    # exactly 4 (A, B, C, D)
    target_concept: str
    domain: str                      # matches Domain.id in the active Pack
    difficulty: QuestionDifficulty
    source_citations: list[str]      # URLs from retrieved chunk metadata only

    @field_validator("options")
    @classmethod
    def exactly_four_options(cls, v: list[QuestionOption]) -> list[QuestionOption]:
        if len(v) != 4:
            raise ValueError(f"Expected 4 options, got {len(v)}")
        if sum(1 for o in v if o.is_correct) != 1:
            raise ValueError("Exactly one option must be correct")
        return v


# ── Grading ───────────────────────────────────────────────────────────────────

class Citation(BaseModel):
    id: int      # numeric label used inline in Markdown: [1], [2]
    url: str
    title: str = ""


class ConceptSignal(BaseModel):
    """
    Diagnostic signal extracted by the Grader — used by the Updater to
    adjust mastery scores without requiring another LLM call.
    """
    concept: str
    evidence: EvidenceLevel
    # Confidence capped at 0.6 per spec v2 §8.2 — one question is weak signal
    confidence: float = Field(ge=0.0, le=1.0)


class GradingResult(BaseModel):
    """Output of the Grader agent — verdict + pedagogical feedback + diagnostic signal."""
    verdict: str                              # "correct" | "incorrect"
    selected_option: AnswerChoice
    correct_option: AnswerChoice
    explanation: str                          # Markdown with [1], [2] citations
    citations: list[Citation]
    identified_misconception: str | None      # None if correct; "QUESTION_QUALITY_ISSUE" possible
    concept_signal: ConceptSignal


# ── Student Model (B2 — domain-grouped, B3-compatible) ───────────────────────

class ConceptMastery(BaseModel):
    """Per-concept mastery tracking. Score: 0.0 (no knowledge) → 5.0 (expert)."""
    mastery: float = Field(default=0.0, ge=0.0, le=5.0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)  # how certain we are of the mastery score
    last_seen: datetime | None = None


class DomainStats(BaseModel):
    """
    B2 schema: per-domain aggregation makes dashboard rendering trivial
    (one bar per domain, value = aggregate_mastery).
    """
    weight: float                             # from Pack domain weight, e.g. 0.27
    aggregate_mastery: float = 0.0            # weighted average of concept masteries in this domain
    concepts: dict[str, ConceptMastery] = Field(default_factory=dict)


class Misconception(BaseModel):
    count: int = 0
    last_seen: datetime | None = None
    status: MasteryStatus = MasteryStatus.active


class SessionEvent(BaseModel):
    question_id: str
    verdict: str
    concept: str
    domain: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StudentModel(BaseModel):
    """
    Persistent student knowledge state. One JSON file per student_id × pack_id.
    B2 schema with B3-compat reserves: `concepts` and `learning_style_hints` are
    None in V1 and populated post-bootcamp when V2 features land (additive, no migration).
    """
    student_id: str
    pack_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # B2 core: per-domain grouped mastery
    domains: dict[str, DomainStats] = Field(default_factory=dict)
    misconceptions: dict[str, Misconception] = Field(default_factory=dict)
    session_history: list[SessionEvent] = Field(default_factory=list)

    # B3-compat reserves (None in V1 — post-bootcamp V2 will populate these)
    concepts: dict[str, Any] | None = None
    learning_style_hints: dict[str, Any] | None = None


# ── LangGraph State ───────────────────────────────────────────────────────────

class TutorState(BaseModel):
    """
    Shared state that flows through the LangGraph graph.
    Every node reads from and writes into this state — it is the single
    source of truth for a tutoring session. (spec v2 §7.4)
    """
    # Pack context (loaded once at session start)
    active_pack_id: str = ""
    pack_descriptor: Pack | None = None

    # Routing — classified by the Coach node
    current_input: str = ""
    intent: str = ""   # "practice" | "qna" | "explain" | "dashboard" | "end_session"

    # Current question lifecycle
    target_concept: str | None = None
    target_domain: str | None = None
    difficulty: QuestionDifficulty | None = None
    current_question: Question | None = None
    student_answer: AnswerChoice | None = None
    grading_result: GradingResult | None = None

    # Persistent student knowledge
    student_model: StudentModel | None = None

    # RAG: chunks retrieved for the current turn (cleared each turn)
    retrieved_chunks: list[dict] = Field(default_factory=list)

    # Output rendered to the UI
    final_output: str = ""

    # Session-level token counter for cost guard (NF-06)
    session_token_count: int = 0


# ── RAG chunk (internal) ──────────────────────────────────────────────────────

class Chunk(BaseModel):
    """A single document chunk returned by the RAG retriever."""
    content: str
    source_url: str
    source_title: str = ""
    tier: int = 1               # 1 = authoritative, 2 = supplementary (spec v2 §9.2)
    domain: str = ""
    domain_weight: float = 0.0
    section_path: str = ""      # header breadcrumb from A2 chunker: "h1 > h2 > h3"
    concept_tags: list[str] = Field(default_factory=list)
    content_type: str = "concept"   # "concept" | "code_example" | "pattern" | "anti_pattern"
    score: float = 0.0          # cosine similarity from ChromaDB query
