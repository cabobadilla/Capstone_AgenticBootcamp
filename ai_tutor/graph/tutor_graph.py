"""
LangGraph orchestration — wires all agents into a stateful tutoring graph.

Graph topology (spec v2 §7.4):
  entry → load_pack → route_intent →
    practice: select_concept → generate_question → [await user answer] → grade_answer → update_student → output
    qna:      retrieve_for_qna → answer_qna → output
    explain:  retrieve_for_explain → explain_concept → output
    dashboard: render_dashboard → output

The graph is invoked once per user action (question generation, answer submission,
Q&A query). It is NOT a streaming long-running process — each invocation is a
discrete request/response cycle that returns an updated state.
"""

import random
from datetime import datetime, timezone

from langgraph.graph import END, StateGraph
from loguru import logger

from ai_tutor.agents.coach import decide_next_action
from ai_tutor.agents.examiner import generate_question
from ai_tutor.agents.explainer import explain_concept
from ai_tutor.agents.grader import grade_answer
from ai_tutor.agents.qna import answer_question
from ai_tutor.agents.updater import apply_grading_result
from ai_tutor.config import settings
from ai_tutor.graph.state import TutorGraphState
from ai_tutor.models import AnswerChoice, Pack, Question, QuestionDifficulty, StudentModel
from ai_tutor.packs.loader import load_pack
from ai_tutor.rag.retriever import retrieve, retrieve_for_concept
from ai_tutor.student_model.store import load_student_model, save_student_model


def _log(state: TutorGraphState, msg: str) -> list[str]:
    """Append a timestamped message to the sidebar log."""
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    existing = state.get("sidebar_log", [])
    return existing + [entry]


# ── Node functions ────────────────────────────────────────────────────────────

def node_load_pack(state: TutorGraphState) -> TutorGraphState:
    """Load the active Pack and Student Model from disk."""
    pack_id = state.get("pack_id", settings.default_pack_id)
    student_id = state.get("student_id", settings.default_student_id)

    pack = load_pack(pack_id)
    student_model = load_student_model(student_id, pack_id, pack)

    return {
        **state,
        "pack_id": pack_id,
        "student_id": student_id,
        "active_node": "load_pack",
        "sidebar_log": _log(state, f"Pack loaded: {pack.name} | Student: {student_id}"),
        # Serialize to dict for state storage (LangGraph state must be JSON-serializable)
        "student_model": student_model.model_dump(mode="json"),
    }


def node_route_intent(state: TutorGraphState) -> TutorGraphState:
    """
    Classify the intent from the current user input.
    For UI-driven flows, intent is set directly by the UI (no Coach call needed).
    For free-text flows (Q&A), the Coach classifies.
    """
    intent = state.get("intent", "practice")
    return {
        **state,
        "active_node": "route_intent",
        "sidebar_log": _log(state, f"Intent: {intent}"),
    }


def node_select_concept(state: TutorGraphState) -> TutorGraphState:
    """Use Coach to select target concept + domain based on student model gaps."""
    pack = load_pack(state["pack_id"])
    student_model = StudentModel(**state["student_model"])
    session_history = [e.model_dump(mode="json") for e in student_model.session_history[-10:]]

    # Detect last concept from recent history for variety weighting
    last_concept = None
    if student_model.session_history:
        last_concept = student_model.session_history[-1].concept

    coach_result = decide_next_action(
        user_input=state.get("user_input", "next question"),
        pack=pack,
        student_model=student_model,
        session_history=session_history,
        last_concept=last_concept,
    )

    target_concept = coach_result.get("target_concept")
    target_domain = coach_result.get("target_domain", "D1")

    # Build concept lookup maps for this domain (ID and name → ID)
    domain_concepts = [c for c in pack.concepts if c.domain == target_domain]
    concept_ids = {c.id for c in domain_concepts}
    name_to_id = {c.name.lower(): c.id for c in domain_concepts}

    # Normalize: Coach sometimes returns full concept names instead of IDs.
    # Try ID match first, then name match, then pick the lowest-mastery concept.
    if target_concept and target_concept not in concept_ids:
        matched = name_to_id.get(target_concept.lower())
        if matched:
            logger.debug(f"Normalized Coach concept '{target_concept}' → '{matched}'")
            target_concept = matched
        else:
            logger.warning(f"Coach returned unknown concept '{target_concept}'; falling back to lowest-mastery")
            target_concept = None

    if not target_concept:
        domain_stats = student_model.domains.get(target_domain)
        concept_id_list = [c.id for c in domain_concepts]
        if domain_stats and domain_stats.concepts and concept_id_list:
            # Pick the valid curriculum concept with the lowest tracked mastery
            def _mastery(cid: str) -> float:
                cm = domain_stats.concepts.get(cid)
                return cm.mastery if cm else 0.0
            target_concept = min(concept_id_list, key=_mastery)
        elif concept_id_list:
            target_concept = random.choice(concept_id_list)
        else:
            target_concept = "agentic_loop_basics"

    difficulty = coach_result.get("difficulty") or "conceptual"

    return {
        **state,
        "target_concept": target_concept,
        "target_domain": target_domain,
        "difficulty": difficulty,
        "active_node": "select_concept",
        "sidebar_log": _log(state, f"Target: {target_concept} ({target_domain}, {difficulty})"),
    }


def node_generate_question(state: TutorGraphState) -> TutorGraphState:
    """Call the Examiner to generate a question for the selected concept."""
    pack = load_pack(state["pack_id"])
    concept = state["target_concept"]
    domain = state["target_domain"]
    difficulty = QuestionDifficulty(state.get("difficulty", "conceptual"))

    chunks = retrieve_for_concept(state["pack_id"], concept, domain=domain, difficulty=difficulty.value)
    if not chunks:
        # Broaden search if no domain-specific chunks found
        chunks = retrieve(state["pack_id"], concept, k=5)

    question = generate_question(pack, concept, domain, difficulty, chunks)

    return {
        **state,
        "current_question": question.model_dump(mode="json"),
        "retrieved_chunks": [c.model_dump(mode="json") for c in chunks],
        "output_type": "question",
        "output_data": question.model_dump(mode="json"),
        "active_node": "generate_question",
        "sidebar_log": _log(state, f"Question generated: {question.question_id[:8]}…"),
    }


def node_grade_answer(state: TutorGraphState) -> TutorGraphState:
    """Call the Grader to evaluate the student's answer."""
    from ai_tutor.models import Chunk
    question = Question(**state["current_question"])
    student_answer = AnswerChoice(state["student_answer"])
    chunks = [Chunk(**c) for c in state.get("retrieved_chunks", [])]

    result = grade_answer(question, student_answer, chunks)

    return {
        **state,
        "grading_result": result.model_dump(mode="json"),
        "output_type": "grading",
        "output_data": result.model_dump(mode="json"),
        "active_node": "grade_answer",
        "sidebar_log": _log(state, f"Graded: {result.verdict} | evidence={result.concept_signal.evidence}"),
    }


def node_update_student(state: TutorGraphState) -> TutorGraphState:
    """Apply grading result to student model and persist to disk."""
    from ai_tutor.models import GradingResult
    pack = load_pack(state["pack_id"])
    student_model = StudentModel(**state["student_model"])
    grading_result = GradingResult(**state["grading_result"])
    question_id = state["current_question"]["question_id"]

    updated = apply_grading_result(grading_result, student_model, pack, question_id)
    save_student_model(updated)

    return {
        **state,
        "student_model": updated.model_dump(mode="json"),
        "active_node": "update_student",
        "sidebar_log": _log(state, f"Student model updated: {state.get('target_concept', 'unknown')} mastery saved"),
    }


def node_retrieve_for_qna(state: TutorGraphState) -> TutorGraphState:
    """Retrieve relevant chunks for a Q&A question."""
    query = state.get("user_input", "")
    chunks = retrieve(state["pack_id"], query, k=5)
    return {
        **state,
        "retrieved_chunks": [c.model_dump(mode="json") for c in chunks],
        "active_node": "retrieve_for_qna",
        "sidebar_log": _log(state, f"Retrieved {len(chunks)} chunks for Q&A"),
    }


def node_answer_qna(state: TutorGraphState) -> TutorGraphState:
    """Call the Q&A agent to answer the student's question."""
    from ai_tutor.models import Chunk
    pack = load_pack(state["pack_id"])
    chunks = [Chunk(**c) for c in state.get("retrieved_chunks", [])]
    answer = answer_question(state.get("user_input", ""), chunks, pack)
    return {
        **state,
        "output_type": "qna_answer",
        "output_data": answer,
        "active_node": "answer_qna",
        "sidebar_log": _log(state, "Q&A answer composed"),
    }


def node_retrieve_for_explain(state: TutorGraphState) -> TutorGraphState:
    """Retrieve chunks for the concept being explained."""
    concept = state.get("target_concept", state.get("user_input", ""))
    domain = state.get("target_domain")
    chunks = retrieve(state["pack_id"], concept, domain=domain, k=4)
    return {
        **state,
        "retrieved_chunks": [c.model_dump(mode="json") for c in chunks],
        "active_node": "retrieve_for_explain",
        "sidebar_log": _log(state, f"Retrieved {len(chunks)} chunks for explanation"),
    }


def node_explain_concept(state: TutorGraphState) -> TutorGraphState:
    """Call the Explainer to produce a calibrated concept explanation."""
    from ai_tutor.models import Chunk
    concept = state.get("target_concept", "")
    student_model = StudentModel(**state["student_model"])
    chunks = [Chunk(**c) for c in state.get("retrieved_chunks", [])]

    # Get current mastery for calibration
    domain = state.get("target_domain", "D1")
    domain_stats = student_model.domains.get(domain)
    current_mastery = 0.0
    if domain_stats and concept in domain_stats.concepts:
        current_mastery = domain_stats.concepts[concept].mastery

    explanation = explain_concept(concept, current_mastery, chunks)
    return {
        **state,
        "output_type": "explanation",
        "output_data": explanation,
        "active_node": "explain_concept",
        "sidebar_log": _log(state, f"Explanation generated for {concept}"),
    }


def node_render_dashboard(state: TutorGraphState) -> TutorGraphState:
    """Compile dashboard data from the student model."""
    student_model = StudentModel(**state["student_model"])

    domain_mastery = {
        domain_id: stats.aggregate_mastery
        for domain_id, stats in student_model.domains.items()
    }
    active_misconceptions = [
        {"id": mid, "count": m.count}
        for mid, m in student_model.misconceptions.items()
        if m.count >= 1
    ]
    recent_history = [
        e.model_dump(mode="json")
        for e in student_model.session_history[-20:]
    ]

    return {
        **state,
        "output_type": "dashboard",
        "output_data": {
            "domain_mastery": domain_mastery,
            "misconceptions": active_misconceptions,
            "recent_history": recent_history,
            "total_questions": len(student_model.session_history),
        },
        "active_node": "render_dashboard",
        "sidebar_log": _log(state, "Dashboard rendered"),
    }


# ── Conditional routing ───────────────────────────────────────────────────────

def route_by_intent(state: TutorGraphState) -> str:
    """Route to the appropriate sub-graph based on intent."""
    intent = state.get("intent", "practice")
    routing = {
        "practice": "select_concept",
        "qna": "retrieve_for_qna",
        "explain": "retrieve_for_explain",
        "dashboard": "render_dashboard",
    }
    return routing.get(intent, "select_concept")


def route_after_grade(state: TutorGraphState) -> str:
    """After grading, always update the student model."""
    return "update_student"


# ── Build graph ───────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    Build and compile the tutor LangGraph.

    Returns a compiled graph ready to invoke with an initial state dict.
    """
    graph = StateGraph(TutorGraphState)

    # Register all nodes
    graph.add_node("load_pack", node_load_pack)
    graph.add_node("route_intent", node_route_intent)
    graph.add_node("select_concept", node_select_concept)
    graph.add_node("generate_question", node_generate_question)
    graph.add_node("grade_answer", node_grade_answer)
    graph.add_node("update_student", node_update_student)
    graph.add_node("retrieve_for_qna", node_retrieve_for_qna)
    graph.add_node("answer_qna", node_answer_qna)
    graph.add_node("retrieve_for_explain", node_retrieve_for_explain)
    graph.add_node("explain_concept", node_explain_concept)
    graph.add_node("render_dashboard", node_render_dashboard)

    # Entry → load pack → route
    graph.set_entry_point("load_pack")
    graph.add_edge("load_pack", "route_intent")

    # Conditional routing after intent classification
    graph.add_conditional_edges("route_intent", route_by_intent, {
        "select_concept": "select_concept",
        "retrieve_for_qna": "retrieve_for_qna",
        "retrieve_for_explain": "retrieve_for_explain",
        "render_dashboard": "render_dashboard",
    })

    # Practice flow
    graph.add_edge("select_concept", "generate_question")
    graph.add_edge("generate_question", END)  # pause: wait for user answer

    # Grade flow (separate invocation after user answers)
    graph.add_edge("grade_answer", "update_student")
    graph.add_edge("update_student", END)

    # Q&A flow
    graph.add_edge("retrieve_for_qna", "answer_qna")
    graph.add_edge("answer_qna", END)

    # Explain flow
    graph.add_edge("retrieve_for_explain", "explain_concept")
    graph.add_edge("explain_concept", END)

    # Dashboard flow
    graph.add_edge("render_dashboard", END)

    return graph.compile()


# Module-level compiled graph — imported by the UI
tutor_graph = build_graph()


def run_practice(pack_id: str = settings.default_pack_id,
                 student_id: str = settings.default_student_id,
                 domain: str | None = None) -> dict:
    """Convenience wrapper: generate a new practice question."""
    state: TutorGraphState = {
        "pack_id": pack_id,
        "student_id": student_id,
        "intent": "practice",
        "target_domain": domain,
        "retrieved_chunks": [],
        "sidebar_log": [],
    }
    return tutor_graph.invoke(state)


def run_grade(pack_id: str, student_id: str,
              current_question: dict, student_answer: str,
              retrieved_chunks: list[dict]) -> dict:
    """Convenience wrapper: grade a student's answer."""
    state: TutorGraphState = {
        "pack_id": pack_id,
        "student_id": student_id,
        "intent": "grade",   # handled manually below (grade_answer is a separate entry)
        "current_question": current_question,
        "student_answer": student_answer,
        "retrieved_chunks": retrieved_chunks,
        "sidebar_log": [],
    }
    # Grade flow enters at grade_answer directly (the graph entry is load_pack for full flows)
    # For grading we need the student model loaded first
    state = node_load_pack(state)
    state = node_grade_answer(state)
    state = node_update_student(state)
    return state


def run_qna(pack_id: str, student_id: str, question: str) -> dict:
    """Convenience wrapper: answer a Q&A question."""
    state: TutorGraphState = {
        "pack_id": pack_id,
        "student_id": student_id,
        "intent": "qna",
        "user_input": question,
        "retrieved_chunks": [],
        "sidebar_log": [],
    }
    return tutor_graph.invoke(state)


def run_dashboard(pack_id: str, student_id: str) -> dict:
    """Convenience wrapper: load dashboard data."""
    state: TutorGraphState = {
        "pack_id": pack_id,
        "student_id": student_id,
        "intent": "dashboard",
        "retrieved_chunks": [],
        "sidebar_log": [],
    }
    return tutor_graph.invoke(state)
