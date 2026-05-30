"""
LangGraph state definition for the AI Tutor graph.

TutorGraphState is a TypedDict used by LangGraph nodes. It intentionally
mirrors the TutorState Pydantic model in models.py but uses TypedDict because
LangGraph requires that for its state schema.

All fields are Optional with None as default so each node only touches the
fields it's responsible for — other fields pass through unchanged.
"""

from typing import Any, Optional
from typing_extensions import TypedDict


class TutorGraphState(TypedDict, total=False):
    # ── Session context ────────────────────────────────────────────────────────
    pack_id: str
    student_id: str

    # ── Routing ───────────────────────────────────────────────────────────────
    intent: str           # "practice" | "qna" | "explain" | "dashboard" | "end_session"
    user_input: str       # raw user text (for Q&A and Explain flows)

    # ── Practice flow ─────────────────────────────────────────────────────────
    target_concept: Optional[str]
    target_domain: Optional[str]
    difficulty: Optional[str]
    current_question: Optional[dict]    # Question.model_dump()
    student_answer: Optional[str]       # "A" | "B" | "C" | "D"
    grading_result: Optional[dict]      # GradingResult.model_dump()
    retrieved_chunks: list[dict]        # Chunk.model_dump() list

    # ── Student state (loaded from disk, updated by Updater node) ─────────────
    student_model: Optional[dict]       # StudentModel.model_dump()

    # ── Output to the UI ──────────────────────────────────────────────────────
    # Each node writes its result here; the UI reads it after graph completion.
    output_type: str      # "question" | "grading" | "qna_answer" | "explanation" | "dashboard" | "error"
    output_data: Any      # payload specific to output_type

    # ── Live sidebar data (shown in V1 sidebar) ────────────────────────────────
    active_node: str          # name of the currently executing node
    sidebar_log: list[str]    # timestamped log lines for the sidebar panel
