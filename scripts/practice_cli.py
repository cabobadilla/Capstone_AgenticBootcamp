"""
practice_cli.py — terminal practice loop for MVP smoke-testing.

Lets you run a practice session without the Gradio UI.
Useful for quick end-to-end verification and debugging agent output.

Usage:
    python scripts/practice_cli.py
    python scripts/practice_cli.py --concept agentic_loop_basics --questions 5
"""

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from ai_tutor.agents.examiner import generate_question
from ai_tutor.agents.grader import grade_answer
from ai_tutor.models import AnswerChoice, QuestionDifficulty
from ai_tutor.packs.loader import load_pack
from ai_tutor.rag.retriever import retrieve_for_concept

# Silence loguru during CLI — only show user-facing output
logger.remove()


def print_question(question, num: int) -> None:
    print(f"\n{'─' * 60}")
    print(f"  Question {num} | Domain: {question.domain} | Difficulty: {question.difficulty.value}")
    print(f"  Concept: {question.target_concept}")
    print(f"{'─' * 60}")
    print(f"\n{question.stem}\n")
    for opt in question.options:
        print(f"  {opt.id}) {opt.text}")


def print_result(result, question) -> None:
    verdict_symbol = "✓" if result.verdict == "correct" else "✗"
    correct_text = next(o.text for o in question.options if o.id == result.correct_option)
    print(f"\n  {verdict_symbol} {result.verdict.upper()} — Correct answer: {result.correct_option}) {correct_text}")
    print(f"\n{result.explanation}")
    if result.identified_misconception:
        print(f"\n  ⚠️  Likely misconception: {result.identified_misconception}")
    if result.citations:
        print("\n  Sources:")
        for c in result.citations:
            print(f"    [{c.id}] {c.url}")


def run_session(pack_id: str, concept: str | None, num_questions: int) -> None:
    print(f"\n{'═' * 60}")
    print(f"  AI Tutor — Practice Session")
    print(f"  Pack: {pack_id.upper()} | Domain: D1")
    print(f"{'═' * 60}")

    pack = load_pack(pack_id)

    # Pick concepts to cover
    d1_concepts = [c.id for c in pack.concepts if c.domain == "D1"]
    if concept:
        concepts_queue = [concept] * num_questions
    else:
        # Cycle through D1 concepts randomly
        concepts_queue = [random.choice(d1_concepts) for _ in range(num_questions)]

    session_stats = {"correct": 0, "total": 0}

    for i, target_concept in enumerate(concepts_queue, 1):
        # Retrieve relevant chunks for this concept
        chunks = retrieve_for_concept(pack_id, target_concept, domain="D1", difficulty="conceptual")
        if not chunks:
            print(f"\n  ⚠ No chunks found for concept '{target_concept}' — skipping")
            continue

        # Generate question
        print(f"\n  Generating question {i}/{num_questions}...", end="", flush=True)
        try:
            question = generate_question(
                pack=pack,
                target_concept=target_concept,
                domain="D1",
                difficulty=QuestionDifficulty.conceptual,
                retrieved_chunks=chunks,
            )
        except Exception as e:
            print(f" FAILED ({e})")
            continue

        print(" done.")
        print_question(question, i)

        # Get student answer
        while True:
            raw = input("\n  Your answer (A/B/C/D) or Q to quit: ").strip().upper()
            if raw == "Q":
                print("\n  Session ended early.")
                _print_stats(session_stats)
                return
            if raw in ("A", "B", "C", "D"):
                break
            print("  Please enter A, B, C, or D.")

        student_answer = AnswerChoice(raw)

        # Grade
        print("  Grading...", end="", flush=True)
        try:
            result = grade_answer(question, student_answer, chunks)
        except Exception as e:
            print(f" FAILED ({e})")
            continue

        print(" done.")
        print_result(result, question)

        session_stats["total"] += 1
        if result.verdict == "correct":
            session_stats["correct"] += 1

        if i < num_questions:
            input("\n  Press Enter for next question...")

    _print_stats(session_stats)


def _print_stats(stats: dict) -> None:
    total = stats["total"]
    correct = stats["correct"]
    if total == 0:
        return
    pct = int(100 * correct / total)
    print(f"\n{'═' * 60}")
    print(f"  Session complete: {correct}/{total} correct ({pct}%)")
    print(f"{'═' * 60}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Tutor — terminal practice session")
    parser.add_argument("--pack", default="cca-f")
    parser.add_argument("--concept", default=None, help="Fixed concept to drill (optional)")
    parser.add_argument("--questions", type=int, default=3, help="Number of questions (default 3)")
    args = parser.parse_args()

    run_session(args.pack, args.concept, args.questions)


if __name__ == "__main__":
    main()
