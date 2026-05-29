"""
Gradio Blocks UI — MVP (Slice 1).

Three tabs:
  1. Home — pack indicator, domain selector, start button.
  2. Practice — question display, answer radio, feedback panel with citations.
  3. Progress — session stats (MVP: questions attempted, correct rate, domain).

State management:
  - session_state (gr.State): tracks current_question, chunks, correct_count, total_count.
  - pack_state (gr.State): active pack descriptor and pack_id.

LangSmith tracing is enabled via env vars (LANGSMITH_TRACING=true, LANGSMITH_PROJECT=ai-tutor).
No explicit wrapping needed — langsmith auto-detects the Anthropic client when env vars are set.

V1 additions (not in this file yet): Q&A tab, persistent student model, live agent sidebar.
"""

import os

import gradio as gr
from loguru import logger

from ai_tutor.agents.examiner import generate_question
from ai_tutor.agents.grader import grade_answer
from ai_tutor.config import settings
from ai_tutor.models import AnswerChoice, QuestionDifficulty
from ai_tutor.packs.loader import load_pack
from ai_tutor.rag.retriever import retrieve_for_concept

# Set LangSmith env vars before any LLM calls (read from pydantic settings)
os.environ.setdefault("LANGSMITH_TRACING", str(settings.langsmith_tracing).lower())
os.environ.setdefault("LANGSMITH_PROJECT", settings.langsmith_project)
if settings.langsmith_api_key:
    os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)

# Load pack once at startup — pack files are static during a session
_pack = load_pack(settings.default_pack_id)
_D1_CONCEPTS = [c.id for c in _pack.concepts if c.domain == "D1"]
_DOMAIN_CHOICES = [(d.name, d.id) for d in _pack.domains if d.id == "D1"]  # MVP: D1 only


# ── Event handlers ────────────────────────────────────────────────────────────

def start_session(domain_id: str, session_state: dict) -> tuple:
    """
    Generate the first question for a new session.
    Called when the user clicks 'Start practice session'.
    Returns updated UI components + new session state.
    """
    if not _D1_CONCEPTS:
        return (
            gr.update(value="⚠️ No concepts found for D1. Re-run ingestion."),
            gr.update(choices=[], visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            {"error": True},
        )

    import random
    concept = random.choice(_D1_CONCEPTS)
    chunks = retrieve_for_concept(settings.default_pack_id, concept, domain=domain_id)

    if not chunks:
        return (
            gr.update(value=f"⚠️ No chunks found for concept '{concept}'. Check ingestion."),
            gr.update(choices=[], visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            {"error": True},
        )

    logger.info(f"Starting session: domain={domain_id} concept={concept}")
    question = generate_question(
        pack=_pack,
        target_concept=concept,
        domain=domain_id,
        difficulty=QuestionDifficulty.conceptual,
        retrieved_chunks=chunks,
    )

    new_state = {
        "question": question.model_dump(),
        "chunks": [c.model_dump() for c in chunks],
        "domain": domain_id,
        "correct_count": 0,
        "total_count": 0,
    }

    option_labels = [f"{o.id}) {o.text}" for o in question.options]
    question_md = f"**{question.stem}**\n\n*Concept: {question.target_concept} | Difficulty: {question.difficulty.value}*"

    return (
        gr.update(value=question_md),
        gr.update(choices=option_labels, value=None, visible=True),
        gr.update(visible=True),   # submit button
        gr.update(value="", visible=False),  # feedback — hidden until graded
        gr.update(visible=False),  # next button — hidden until graded
        new_state,
    )


def submit_answer(selected_label: str | None, session_state: dict) -> tuple:
    """
    Grade the student's selected answer.
    Called when the user clicks 'Submit'.
    """
    if not selected_label or session_state.get("error"):
        return (
            gr.update(value="⚠️ Please select an answer first.", visible=True),
            gr.update(visible=False),
        )

    # Extract option ID (A/B/C/D) from the label "A) ..."
    answer_id = selected_label[0]
    student_answer = AnswerChoice(answer_id)

    from ai_tutor.models import Chunk, Question
    question = Question(**session_state["question"])
    chunks = [Chunk(**c) for c in session_state["chunks"]]

    result = grade_answer(question, student_answer, chunks)

    # Update session stats
    session_state["total_count"] += 1
    if result.verdict == "correct":
        session_state["correct_count"] += 1

    # Format feedback markdown
    verdict_icon = "✅" if result.verdict == "correct" else "❌"
    correct_text = next(o.text for o in question.options if o.id == result.correct_option)

    feedback_md = (
        f"## {verdict_icon} {'Correct!' if result.verdict == 'correct' else 'Incorrect'}\n\n"
        f"**Correct answer:** {result.correct_option}) {correct_text}\n\n"
        f"---\n\n"
        f"{result.explanation}\n\n"
    )

    if result.identified_misconception:
        feedback_md += f"\n\n⚠️ **Watch out for:** {result.identified_misconception}"

    if result.citations:
        sources = "\n".join(f"- [{c.id}] {c.url}" for c in result.citations)
        feedback_md += f"\n\n**Sources:**\n{sources}"

    return (
        gr.update(value=feedback_md, visible=True),
        gr.update(visible=True),  # next button
    )


def next_question(session_state: dict) -> tuple:
    """Generate the next question. Reuses start_session logic with current domain."""
    domain_id = session_state.get("domain", "D1")
    return start_session(domain_id, session_state)


def refresh_progress(session_state: dict) -> str:
    """Render session stats for the Progress tab."""
    total = session_state.get("total_count", 0)
    correct = session_state.get("correct_count", 0)
    domain = session_state.get("domain", "—")

    if total == 0:
        return "No questions answered yet. Start a practice session first."

    pct = int(100 * correct / total)
    return (
        f"## Session Progress\n\n"
        f"| Metric | Value |\n"
        f"|---|---|\n"
        f"| Domain | {domain} |\n"
        f"| Questions attempted | {total} |\n"
        f"| Correct | {correct} ({pct}%) |\n"
        f"| Incorrect | {total - correct} |\n\n"
        f"*Progress resets when you start a new session.*"
    )


# ── Layout ────────────────────────────────────────────────────────────────────

with gr.Blocks(title="AI Tutor") as app:
    # Shared state — flows through all event handlers
    session_state = gr.State({})

    gr.Markdown(
        f"# 🎓 AI Tutor\n"
        f"Studying: **{_pack.name}** — {_pack.full_name} | "
        f"Corpus version: `{_pack.corpus_version}`"
    )

    with gr.Tab("🏠 Home"):
        gr.Markdown("Select a domain and start a practice session.")
        domain_dropdown = gr.Dropdown(
            choices=_DOMAIN_CHOICES,
            value="D1",
            label="Domain (MVP: D1 only)",
            interactive=True,
        )
        start_btn = gr.Button("▶ Start practice session", variant="primary")

    with gr.Tab("📝 Practice"):
        question_md = gr.Markdown("Click **Start practice session** on the Home tab to begin.")
        answer_radio = gr.Radio(choices=[], label="Your answer", visible=False, interactive=True)
        submit_btn = gr.Button("Submit answer", variant="primary", visible=False)
        feedback_md = gr.Markdown(visible=False)
        next_btn = gr.Button("Next question →", visible=False)

    with gr.Tab("📊 Progress"):
        refresh_btn = gr.Button("Refresh stats")
        progress_md = gr.Markdown("No session data yet.")

    # ── Event wiring ──────────────────────────────────────────────────────────
    start_btn.click(
        fn=start_session,
        inputs=[domain_dropdown, session_state],
        outputs=[question_md, answer_radio, submit_btn, feedback_md, next_btn, session_state],
    )

    submit_btn.click(
        fn=submit_answer,
        inputs=[answer_radio, session_state],
        outputs=[feedback_md, next_btn],
    )

    next_btn.click(
        fn=next_question,
        inputs=[session_state],
        outputs=[question_md, answer_radio, submit_btn, feedback_md, next_btn, session_state],
    )

    refresh_btn.click(
        fn=refresh_progress,
        inputs=[session_state],
        outputs=[progress_md],
    )


def main() -> None:
    logger.info(f"Launching AI Tutor UI — pack={settings.default_pack_id}")
    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        show_error=True,
        theme=gr.themes.Default(),
    )


if __name__ == "__main__":
    main()
