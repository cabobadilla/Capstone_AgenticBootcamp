# AI Tutor — Functional & Technical Specification

> **Purpose of this document**: Build specification for a **generic multi-agent AI Tutor platform** that adapts to any certification or learning challenge. The platform is domain-agnostic: it ingests a curated corpus, models a curriculum, and runs an adaptive tutoring loop powered by specialist agents.
>
> **First validation dataset (demo)**: Anthropic's **Claude Certified Architect — Foundations (CCA-F)** exam. CCA-F serves as the proof-of-value scenario to demonstrate the platform end-to-end: a real, official certification with public curriculum, official documentation as ground truth, and well-defined exam domains.
>
> **Why this framing matters**: The capstone presents not a single-purpose tutor but a **reusable platform**. The same agents, RAG plumbing, and student model work for AWS, Azure, Kubernetes, PMP, or any other certification — only the corpus and the curriculum descriptor change. CCA-F is the demonstration; the platform is the deliverable.
>
> **Target environment**: macOS, Python 3.11+, controlled virtual environment.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Platform vs. Demo: Separation of Concerns](#2-platform-vs-demo-separation-of-concerns)
3. [Scope: MVPs / Slices](#3-scope-mvps--slices)
4. [Functional Specification](#4-functional-specification)
5. [UI Specification](#5-ui-specification)
6. [Frontend Framework — Gradio](#6-frontend-framework--gradio)
7. [Technical Architecture](#7-technical-architecture)
8. [Agent Specifications (with full prompts)](#8-agent-specifications-with-full-prompts)
9. [RAG Corpus Specification](#9-rag-corpus-specification)
10. [Open Decision A — Chunking Strategy](#10-open-decision-a--chunking-strategy)
11. [Open Decision B — Student Model Schema](#11-open-decision-b--student-model-schema)
12. [Certification Pack Specification](#12-certification-pack-specification)
13. [Tech Stack (closed decisions)](#13-tech-stack-closed-decisions)
14. [Project Structure](#14-project-structure)
15. [Setup Instructions (macOS)](#15-setup-instructions-macos)
16. [Testing Strategy](#16-testing-strategy)
17. [Cost Estimation](#17-cost-estimation)
18. [Observability](#18-observability)
19. [Deployment Notes](#19-deployment-notes)
20. [Implementation Roadmap](#20-implementation-roadmap)

---

## 1. Project Overview

### Product name

**AI Tutor** — a personalized, agentic tutoring platform that adapts to any certification or structured learning challenge.

### Problem statement

Candidates preparing for technical certifications face three universal challenges: (1) modern exams test applied judgment via scenarios, not memorization; (2) official material is distributed across many sources (docs, whitepapers, FAQs, courses); and (3) traditional study tools (linear courses, static question banks) don't adapt to the learner's specific knowledge gaps. This is true for AWS, Azure, GCP, Kubernetes, PMP, CCA-F, and most modern certifications.

AI Tutor addresses this with a **generic, certification-agnostic platform**: ingest official material once, model the curriculum, and run adaptive practice sessions grounded in authoritative sources with continuous diagnostic feedback.

### Value proposition

A tutoring platform that combines:

- **Official-material RAG**: citations to authoritative sources, no hallucinations.
- **Continuous student diagnosis**: per-concept knowledge tracking.
- **Dynamic scenario question generation**: targeted at the learner's weak areas.
- **Adaptive coaching**: study plans that evolve session to session.
- **Plug-in certifications**: a new certification is added by providing a Certification Pack (corpus + curriculum descriptor) — no code changes.

### First validation: CCA-F

The first Certification Pack built into the platform is **CCA-F**, chosen because:

- It is a real, official Anthropic certification (launched March 2026).
- Curriculum is public: 5 domains with published weights.
- Official corpus is freely accessible (Anthropic docs, MCP spec, cookbook).
- It is scenario-based (the hardest tutoring challenge to solve well — proving the platform on CCA-F proves it generally).
- It is timely and relevant to the bootcamp audience.

The CCA-F exam structure used as the reference dataset:

| # | Domain | Weight |
|---|---|---|
| D1 | Agentic Architecture & Orchestration | 27% |
| D2 | Tool Design & MCP Integration | 18% |
| D3 | Claude Code Configuration & Workflows | 20% |
| D4 | Prompt Engineering & Structured Output | 20% |
| D5 | Context Management & Reliability | 15% |

60 multiple-choice questions, 120 minutes, passing score 720/1000, scenario-based.

### Out of scope

- Replacement for hands-on practice; the system explicitly recommends real projects.
- Cheating aid; no copies of official questions, only generated ones.
- Real-time content drift handling; corpus is versioned and re-ingested manually.

---

## 2. Platform vs. Demo: Separation of Concerns

A core design principle: **what is generic vs. what is certification-specific** must be cleanly separated. This is what makes the capstone defensible as a platform, not just a CCA-F tool.

### Generic (the platform)

These components have no knowledge of any specific certification:

- All six agents (Examiner, Grader, Coach, Explainer, Q&A, Updater).
- The LangGraph orchestration.
- The RAG retrieval and indexing layer.
- The Student Model storage and update logic.
- The frontend (Gradio).
- The ingestion pipeline (fetch, extract, chunk, embed).
- All telemetry and observability.

### Certification-specific (the Certification Pack)

These are external, declarative artifacts loaded at runtime:

- **Corpus URL list**: which sources to ingest.
- **Curriculum descriptor**: domains, weights, concept list, prerequisites.
- **Exam metadata**: format, duration, passing score, style guidance for the Examiner.
- **Style hints**: e.g., "questions should be scenario-based" or "trivia is acceptable".

### Implication for the demo

The capstone demo presents the **same UI and same agents** working against the CCA-F Certification Pack. A second Pack (even a minimal one — e.g., a small "AWS Cloud Practitioner" stub with 10 documents) would dramatically reinforce the platform claim. Whether to include a second Pack is a stretch goal, not a requirement.

---

## 3. Scope: MVPs / Slices

The product is built as three vertical slices. Each slice is end-to-end functional and demonstrable on its own. **The slice to start with will be decided during Claude Code sessions.**

All slices use the CCA-F Certification Pack as the validation dataset. The platform genericity is preserved at every slice level — no slice introduces certification-specific code.

### Slice 1 — MVP: Targeted Practice (single domain)

- **One exam domain** of the loaded Pack indexed in the RAG (suggested starting domain for CCA-F: **D4 Prompt Engineering & Structured Output** — most stable material, most verifiable answers).
- **Two agents**: Examiner (generates questions) + Grader (evaluates answers, diagnoses misconceptions).
- **Session-only memory** (no persistence across sessions).
- **UI**: practice flow + minimal progress view for the session.
- **Question types**: conceptual + simple scenarios (escalable prompt structure).
- **Estimated effort**: ~35% of total project.

### Slice 2 — V1: Adaptive Tutor with Persistent Student Model

- **All domains** of the loaded Pack indexed in the RAG.
- **Additional agents**: Coach (orchestrator), Explainer, Q&A Agent, Student Model Updater.
- **Persistent Student Model** in JSON file storage (across sessions).
- **UI**: practice flow + free Q&A + persistent progress dashboard.
- **Question types**: full conceptual + scenario coverage.
- **Estimated effort**: +35% (~70% cumulative).

### Slice 3 — V2: Complete Tutor with Adaptive Curriculum

- **Curriculum Graph** (concept-level dependency map from the Pack).
- **Adaptive study plan generation** (regenerated each session based on gaps and exam-date proximity).
- **Learning Style detection** (the system infers and adapts to how the student learns).
- **Exam readiness score** with confidence intervals.
- **UI**: full dashboard with study plan, readiness, projected exam date.
- **(Stretch)**: second Certification Pack loaded to demonstrate platform genericity.
- **Estimated effort**: +30% (100% cumulative).

### Slice progression rule

Each slice must be fully demonstrable end-to-end before moving to the next. No "partial slice" handoffs.

---

## 4. Functional Specification

### 4.1 Core user flows (across slices)

#### Flow A — Practice session (MVP onwards)

1. Student opens the application; selects an active Certification Pack (CCA-F by default).
2. System presents a question generated by the Examiner. Question is targeted at a domain (MVP) or weak concept (V1+).
3. Student selects an answer from multiple-choice options.
4. Grader evaluates the answer. Output includes:
   - Correct / incorrect verdict.
   - Pedagogical explanation of the correct answer with citations to official material.
   - For incorrect answers: identification of the likely misconception.
5. Student can request next question or end session.
6. Student Model is updated (V1+).

#### Flow B — Free Q&A (V1 onwards)

1. Student types a natural-language question about a topic within the active Pack.
2. Q&A Agent retrieves relevant chunks from the RAG (scoped to the active Pack).
3. Q&A Agent composes an answer with explicit citations to source URLs.
4. Optional: the answer can include a follow-up suggestion ("want to practice this concept?").

#### Flow D — Progress dashboard (MVP minimal, V1 enriched, V2 full)

- **MVP**: shows session stats only — questions attempted, correct rate, domain covered.
- **V1**: shows persistent Concept Mastery Map across all domains of the active Pack, last-seen concepts, identified misconceptions.
- **V2**: adds adaptive study plan, readiness score, projected exam-date alignment, learning-style hints.

### 4.2 Functional requirements summary

| ID | Requirement | Slice |
|---|---|---|
| F-01 | Generate scenario-based questions from RAG content of the active Pack | MVP |
| F-02 | Evaluate answer with pedagogical feedback and citations | MVP |
| F-03 | Maintain session history | MVP |
| F-04 | Display session stats | MVP |
| F-05 | Persist Student Model across sessions | V1 |
| F-06 | Free Q&A with citations | V1 |
| F-07 | Targeted question generation based on weak concepts | V1 |
| F-08 | Misconception tracking across sessions | V1 |
| F-09 | Persistent progress dashboard with per-domain mastery | V1 |
| F-10 | Adaptive study plan generation | V2 |
| F-11 | Learning style detection and adaptation | V2 |
| F-12 | Exam readiness score | V2 |
| F-13 | Multiple Certification Packs can be loaded; user selects active Pack | V2 (stretch) |

### 4.3 Non-functional requirements

| ID | Requirement |
|---|---|
| NF-01 | Latency: question generation < 8s, answer grading < 12s, Q&A < 10s (typical) |
| NF-02 | All factual claims in answers must cite at least one source URL from the active Pack's RAG |
| NF-03 | No agent may invent exam-relevant facts; if unsure, must say so |
| NF-04 | Student Model file must be human-readable JSON |
| NF-05 | System must run locally on macOS without external services beyond LLM API and ChromaDB |
| NF-06 | Total per-session cost should remain under USD 0.50 in typical usage |
| NF-07 | Adding a new Certification Pack must require zero code changes (configuration + corpus only) |

---

## 5. UI Specification

### 5.1 General UI principles

- **Minimal cognitive load**: one primary action visible at any time.
- **Citations always visible**: every grader explanation and Q&A response shows source URLs.
- **Progress always accessible**: a tab or panel for the dashboard at any moment.
- **Pack identity present but not intrusive**: a small header element shows the active Certification Pack ("Studying: CCA-F").
- **No animations or distractions**: this is a study tool.

### 5.2 Screens / views

#### View 1 — Home / Session start

- App title and short description.
- Active Pack indicator (default: CCA-F; V2 stretch: selectable).
- Domain selector (MVP: single domain; V1+: all domains of the active Pack, default to weakest).
- Button: "Start practice session".
- Button: "Free Q&A" (V1+).
- Button: "View progress" (opens dashboard).

#### View 2 — Practice session

- Question text area (top).
- Multiple-choice options.
- After selection:
  - Verdict banner (correct/incorrect).
  - Explanation panel with:
    - Why the correct answer is correct.
    - Why each distractor is wrong (especially valuable for scenario-based exams like CCA-F where wrong answers represent anti-patterns).
    - Source citations as clickable URLs.
  - For incorrect answers: identified misconception (V1+).
- Footer buttons: "Next question", "Explain in more depth" (V1+), "End session".

#### View 3 — Free Q&A (V1+)

- Chat-style interface (single thread per session).
- User input box at the bottom.
- Agent responses include citations inline (e.g., `[1]`) with a sources panel showing full URLs.
- Optional: "Practice this concept" button after each response.

#### View 4 — Progress dashboard

- **MVP**: simple list of session stats (questions seen, correct rate, domain).
- **V1**:
  - Per-domain mastery bars (0–5 scale) showing Concept Mastery Map aggregated by domain (domain names come from the active Pack).
  - List of top-tracked misconceptions with frequency.
  - "Last 20 questions" history with verdicts.
- **V2**:
  - All of V1, plus:
  - Adaptive study plan view (week-by-week or topic-by-topic).
  - Exam readiness score with confidence band.
  - Learning style profile summary.

### 5.3 Cross-view elements

- Header with app name, active Pack name, and a tiny mastery indicator (e.g., "CCA-F • D4: 3.2/5").
- Footer with corpus version of the active Pack and a "report wrong answer" link (for future correction loops).
- Light theme by default.

---

## 6. Frontend Framework — Gradio

### 6.1 Decision

The frontend is built with **Gradio**. Rationale:

- Fastest to set up: a working app in under 100 lines.
- Native chat, multiple-choice, and dashboard components.
- Strong Python-only integration; no separate frontend toolchain.
- Clean default look suitable for capstone demo.
- Easy to ship as a single `python -m src.ui.app` command.

### 6.2 Gradio implementation guidelines

- Use **Gradio Blocks API** (not Interface) — needed for multi-view, conditional rendering, and state management.
- Each view is a `gr.Tab` inside `gr.Blocks`:
  - Tab 1: Home/Start.
  - Tab 2: Practice Session.
  - Tab 3: Free Q&A (V1+).
  - Tab 4: Dashboard.
- Use `gr.State` to hold the current session state (current question, last verdict, session_id).
- Use `gr.update(...)` returned from event handlers to swap visible elements (e.g., reveal feedback panel after grading).
- Render citations as Markdown with bracketed numeric links pointing to real URLs.
- For the dashboard, use `gr.BarPlot` or `gr.LinePlot` for mastery bars; fall back to Markdown tables if simpler.
- Avoid `gr.ChatInterface` for the practice flow (too rigid); use it only for the Q&A view.

### 6.3 Layout sketch (pseudo-code)

```python
import gradio as gr

with gr.Blocks(title="AI Tutor") as app:
    session_state = gr.State({})
    pack_state = gr.State({"active_pack": "cca-f"})

    gr.Markdown("# AI Tutor")
    gr.Markdown("Studying: **CCA-F** • Corpus version: v1")  # dynamic

    with gr.Tab("Home"):
        domain = gr.Dropdown(choices=[...], label="Domain")
        start_btn = gr.Button("Start practice")

    with gr.Tab("Practice"):
        question_md = gr.Markdown()
        options = gr.Radio(choices=[], label="Your answer")
        submit_btn = gr.Button("Submit")
        feedback = gr.Markdown(visible=False)
        next_btn = gr.Button("Next question", visible=False)

    with gr.Tab("Q&A"):  # V1+
        chatbot = gr.Chatbot()
        msg = gr.Textbox()
        msg.submit(qna_fn, [msg, chatbot, pack_state], [chatbot])

    with gr.Tab("Progress"):
        refresh_btn = gr.Button("Refresh")
        mastery_chart = gr.BarPlot(...)
        misconceptions_md = gr.Markdown()

    # event wiring
    start_btn.click(start_session_fn, [domain, pack_state], [question_md, options, session_state])
    submit_btn.click(grade_fn, [options, session_state, pack_state], [feedback, next_btn])
    next_btn.click(next_question_fn, [session_state, pack_state], [question_md, options, feedback, next_btn])

app.launch()
```

### 6.4 Gradio-specific risks to manage

- State must flow explicitly through `gr.State` — avoid module-level mutable globals.
- Event chains can become hard to follow; keep each handler small and pure.
- For long-running agent calls, use `yield`-based generators to stream intermediate updates ("Generating question...", "Retrieving sources...", "Composing question...").

---

## 7. Technical Architecture

### 7.1 Architecture overview

The system uses an **Orchestrator + Specialists** pattern with shared state. Three planes:

- **Knowledge Plane**: RAG over the active Pack's corpus, plus (V2) a Curriculum Graph.
- **Student State Plane**: Concept Mastery Map, Misconception Tracker, Session History.
- **Agent Plane**: Coach (orchestrator) and specialist agents.

### 7.2 Component diagram

```
                            ┌──────────────────────────┐
                            │     Frontend UI          │
                            │       (Gradio)           │
                            └────────────┬─────────────┘
                                         │
                            ┌────────────▼─────────────┐
                            │   Coach (Orchestrator)   │
                            │   LangGraph state graph  │
                            └────┬───────┬───────┬─────┘
                                 │       │       │
                  ┌──────────────┘       │       └──────────────┐
                  │                      │                      │
        ┌─────────▼──────┐    ┌──────────▼─────┐    ┌──────────▼─────┐
        │   Examiner     │    │     Grader     │    │   Explainer    │
        │  (generates)   │    │   (evaluates)  │    │   (teaches)    │
        └────────┬───────┘    └────────┬───────┘    └────────┬───────┘
                 │                     │                     │
                 │            ┌────────▼────────┐            │
                 │            │   Q&A Agent     │            │
                 │            │  (free queries) │            │
                 │            └────────┬────────┘            │
                 │                     │                     │
                 └─────────────────────┼─────────────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
     ┌────────▼─────────┐    ┌─────────▼─────────┐    ┌────────▼─────────┐
     │   RAG: ChromaDB  │    │   Student Model   │    │   Active Pack    │
     │ (active Pack)    │    │   (JSON file)     │    │   Descriptor     │
     └──────────────────┘    └───────────────────┘    └──────────────────┘
              ▲
              │
     ┌────────┴─────────┐
     │  Student Model   │
     │     Updater      │ (tool-like, not conversational)
     └──────────────────┘
```

### 7.3 Agent inventory across slices

| Agent | MVP | V1 | V2 | Role |
|---|:-:|:-:|:-:|---|
| Examiner | ✓ | ✓ | ✓ | Generates scenario-based questions targeted at concepts |
| Grader | ✓ | ✓ | ✓ | Evaluates answers with pedagogical feedback |
| Coach (Orchestrator) | — | ✓ | ✓ | Decides session flow, selects target concepts |
| Explainer | — | ✓ | ✓ | Provides deeper explanations of concepts |
| Q&A Agent | — | ✓ | ✓ | Answers free-form questions with citations |
| Student Model Updater | — | ✓ | ✓ | Translates interactions into state updates |
| Plan Generator | — | — | ✓ | Generates adaptive study plans |

### 7.4 LangGraph flow (Slice 2/V1 example)

State schema (illustrative — full schema in Section 8):

```
TutorState = {
  active_pack_id: str,
  pack_descriptor: dict,
  current_input: str,
  intent: "practice" | "qna" | "explain" | "dashboard",
  target_concept: str | None,
  current_question: dict | None,
  student_answer: str | None,
  grading_result: dict | None,
  student_model: dict,
  retrieved_chunks: list[dict],
  final_output: str,
}
```

Node graph (simplified):

```
[entry]
  │
  ▼
[load_pack_descriptor]
  │
  ▼
[classify_intent]  ── intent ──┐
                               │
  ┌─ practice ────────────┐    │
  │                       ▼    │
  │              [select_concept]
  │                       │    │
  │                       ▼    │
  │              [examiner_generate]
  │                       │    │
  │                       ▼    │
  │                  [present_to_user]
  │                       │    │
  │                       ▼ (user answers)
  │              [grader_evaluate]
  │                       │    │
  │                       ▼    │
  │              [updater_apply]
  │                       │    │
  │                       ▼    │
  │                    [output]
  │                            │
  ├─ qna ──── [qna_retrieve] → [qna_answer] → [output]
  │
  ├─ explain ── [explainer_respond] → [output]
  │
  └─ dashboard ── [render_dashboard] → [output]
```

### 7.5 Multi-agent pattern justification

The chosen pattern is **Orchestrator + Specialists with Shared Memory**, implemented via LangGraph. This is justified by the use case because:

- Different reasoning modes are required (generation vs. evaluation vs. explanation vs. retrieval).
- The Student Model is shared, long-lived state — naturally fits a graph state.
- Conditional flows (intent classification, slice-conditional features) are first-class in LangGraph.
- The Updater is best modeled as a structured-output node, not as a conversational agent.

---

## 8. Agent Specifications (with full prompts)

Each agent is specified by its functional role, inputs, outputs, model recommendation, and **complete system prompt**. Prompts are written in English and parameterized for any Certification Pack — they reference the active Pack's metadata rather than hardcoded certification facts.

### 8.1 Examiner

**Role**: Generates a single exam-style question targeted at a specific concept from the active Pack, grounded in retrieved RAG content.

**Input**: `{pack: dict, target_concept: str, domain: str, difficulty: "conceptual"|"scenario", retrieved_chunks: list[str]}`

**Output (structured JSON)**:
```json
{
  "question_id": "uuid",
  "type": "multiple_choice",
  "stem": "string",
  "options": [
    {"id": "A", "text": "string", "is_correct": true|false, "rationale": "string"},
    {"id": "B", ...},
    {"id": "C", ...},
    {"id": "D", ...}
  ],
  "target_concept": "string",
  "domain": "string",
  "difficulty": "conceptual|scenario",
  "source_citations": ["url1", "url2"]
}
```

**Model**: Claude Sonnet 4.6 (Opus 4.5 if budget allows for scenario depth).

**System prompt**:

```
You are an expert exam-question author for a certification specified by the
active Certification Pack. Your task is to author ONE high-quality
multiple-choice question on a specific concept.

YOU WILL RECEIVE:
- pack: a descriptor with these fields:
  - pack.name: e.g., "CCA-F"
  - pack.full_name: e.g., "Claude Certified Architect — Foundations"
  - pack.style: e.g., "scenario-based" | "conceptual" | "mixed"
  - pack.style_notes: free-form guidance about question style for this cert
  - pack.domains: list of {id, name, weight}
- target_concept: the specific concept to test
- domain: the id of the domain (must match one in pack.domains)
- difficulty: "conceptual" or "scenario"
- retrieved_chunks: authoritative excerpts from the official material —
  use ONLY these as the source of truth

GENERAL RULES:
- Questions must reflect the pack's style. If pack.style is "scenario-based",
  prefer realistic production scenarios. If "conceptual", prefer precise
  single-mechanism questions. If "mixed", follow the difficulty parameter.
- Wrong answers are not random; they should represent realistic mistakes:
  anti-patterns, common misunderstandings, or outdated practices.
- Conceptual questions test precise understanding of a single mechanism with
  realistic distractors.
- Scenario questions describe a concrete situation (a broken system, a
  decision with trade-offs) and ask the candidate to make the correct call.

REQUIREMENTS:
1. The question stem must be self-contained and unambiguous.
2. Provide exactly four options: A, B, C, D.
3. Exactly one option must be correct.
4. Each wrong option must represent a realistic mistake.
5. For each option, provide a brief rationale referencing the
   retrieved_chunks. Do not invent facts.
6. If retrieved_chunks do not contain enough information to author a
   defensible question, return {"error": "insufficient_context", "reason": "..."}.
7. Output strictly as JSON matching the provided schema. No text outside
   the JSON object.

CITATIONS:
- source_citations must contain only URLs present in the metadata of the
  retrieved_chunks. Do not fabricate URLs.

Produce the JSON now.
```

### 8.2 Grader

**Role**: Evaluates a student's answer, produces pedagogical feedback, identifies misconceptions, and outputs structured grading data for the Student Model Updater.

**Input**: `{question: dict, student_answer: "A"|"B"|"C"|"D", retrieved_chunks: list[str]}`

**Output (structured JSON)**:
```json
{
  "verdict": "correct|incorrect",
  "selected_option": "A|B|C|D",
  "correct_option": "A|B|C|D",
  "explanation": "markdown string with citations as [1], [2]",
  "citations": [{"id": 1, "url": "..."}],
  "identified_misconception": "string|null",
  "concept_signal": {
    "concept": "string",
    "evidence": "demonstrated|partial|missing",
    "confidence": 0.0
  }
}
```

**Model**: Claude Sonnet 4.6.

**System prompt**:

```
You are a senior tutor and grader. You receive a question, the student's
selected answer, and authoritative source material from the active
Certification Pack. Your job is to (a) determine correctness, (b) explain
the result pedagogically, and (c) extract a diagnostic signal about the
student's understanding.

PEDAGOGICAL PRINCIPLES:
- Never shame the student.
- Always explain WHY the correct answer is correct AND why each plausible
  distractor is wrong. The "why wrong" matters more than "why right" for
  scenario-based exams.
- Cite the official material using bracketed numeric citations like [1],
  [2]. Map each citation to a URL in the citations array.
- Identify the most likely misconception that led to an incorrect answer
  (e.g., "confuses concept X with concept Y").

DIAGNOSTIC SIGNAL RULES:
- evidence="demonstrated": correct answer AND the option required
  understanding (not guessable).
- evidence="partial": incorrect but reflects partial understanding (right
  domain, wrong specific mechanism).
- evidence="missing": fundamental misunderstanding.
- confidence reflects strength of this signal (0.0–1.0). A single question
  is weak evidence — do not exceed 0.6 from one observation.

OUTPUT FORMAT:
- Strictly JSON matching the provided schema.
- "explanation" is markdown formatted for the UI.
- No text outside the JSON object.

GROUNDING:
- All factual claims must be traceable to the retrieved_chunks.
- If retrieved_chunks contradict the question's premises, set
  identified_misconception="QUESTION_QUALITY_ISSUE" and explain.

Begin grading now.
```

### 8.3 Coach (Orchestrator)

**Role**: Decides what happens next in a session. Classifies user intent, selects target concepts for practice based on Student Model gaps and the active Pack's curriculum.

**Input**: `{user_input: str|None, student_model: dict, pack: dict, session_history: list, last_event: dict|None}`

**Output (structured JSON)**:
```json
{
  "action": "ask_question|answer_qna|explain_concept|show_dashboard|end_session",
  "target_concept": "string|null",
  "target_domain": "string|null",
  "difficulty": "conceptual|scenario|null",
  "rationale": "string (for logging/debugging, not shown to user)"
}
```

**Model**: Claude Sonnet 4.6.

**System prompt**:

```
You are the Coach — the orchestrator of a tutoring session. You decide
what the system does next based on (a) the user's input or click event,
(b) the current Student Model, and (c) the active Certification Pack's
curriculum.

DECISION FRAMEWORK:
- Free-form question in Q&A view → action=answer_qna.
- User requests dashboard → action=show_dashboard.
- User clicks "Next question" / "Start practice" → action=ask_question
  and you must choose target_concept and target_domain from
  pack.domains and the concepts the Pack defines.
- User clicks "Explain more" → action=explain_concept and
  target_concept=last question's concept.
- User clicks "End session" → action=end_session.

SELECTING TARGET CONCEPT FOR PRACTICE:
- Read student_model.concept_mastery_map.
- Use pack.domains[*].weight as exam weight.
- Identify concepts with lowest mastery AND highest exam weight.
- Weighting: 60% lowest mastery, 30% domain weight, 10% recency variety
  (avoid repeating the same concept three times in a row).
- If a misconception has count >= 2 in student_model.misconceptions,
  prioritize the concept tied to it.
- For first 2-3 questions of a new student (low mastery confidence),
  favor conceptual difficulty. After that, follow pack.style or scenario.

OUTPUT:
- Strictly JSON.
- rationale is for internal logging only.

If required input is missing, use safe defaults (highest-weight domain,
conceptual difficulty).
```

### 8.4 Explainer

**Role**: Produces an in-depth explanation of a specific concept from the active Pack, calibrated to the student's current mastery, with citations.

**Input**: `{concept: str, current_mastery: float, retrieved_chunks: list[str], context_hint: str|None}`

**Output**: Markdown text with inline citations.

**Model**: Claude Sonnet 4.6.

**System prompt**:

```
You are the Explainer — a patient, precise tutor. You produce a focused
explanation of a single concept from the active Certification Pack,
calibrated to the student's current mastery (0.0–5.0).

CALIBRATION:
- 0.0–1.5: assume new to this concept. Start from first principles, use
  concrete analogies, avoid undefined jargon.
- 1.5–3.0: assume the student has seen it but doesn't fully grasp it.
  Focus on the precise mechanism, common misunderstandings, one short
  example.
- 3.0–4.5: assume the student knows the basics. Focus on edge cases,
  anti-patterns, production trade-offs.
- 4.5+: assume the student knows it. Provide a terse refresher with one
  nuanced caveat.

REQUIREMENTS:
- Length: 150–400 words depending on calibration.
- Every factual claim must include a citation [1], [2], etc.
- Citations array (JSON in a code block at the end) maps numbers to URLs
  from retrieved_chunks metadata.
- Do not invent URLs.
- Markdown formatting: short paragraphs, occasional bullets, code blocks
  for code examples.
- End with one sentence: "Want a practice question on this?"

GROUNDING:
- Use only the retrieved_chunks as source of truth.
- If a key aspect is not covered, say so explicitly: "The official
  material does not specify X, so do not infer it for the exam."
```

### 8.5 Q&A Agent

**Role**: Answers free-form student questions about topics within the active Pack with citations.

**Input**: `{question: str, retrieved_chunks: list[str], student_model: dict, pack: dict}`

**Output**: Markdown text with inline citations and a citations block.

**Model**: Claude Sonnet 4.6.

**System prompt**:

```
You are the Q&A Agent for the AI Tutor. You answer student questions
about topics within the active Certification Pack, grounded strictly in
the official material provided as retrieved_chunks.

SCOPE:
- Only answer questions relevant to the active Pack's domains (you will
  receive pack.domains as context).
- If off-topic, redirect politely: "That topic isn't part of {pack.name}.
  Want to practice a relevant concept instead?"
- If in-scope but the retrieved material doesn't cover it, say so. Do
  NOT invent.

ANSWER STRUCTURE:
- Start with a direct one-sentence answer.
- Follow with a short explanation (2–4 paragraphs).
- Use bracketed numeric citations [1], [2] throughout. Every factual
  statement must be cited.
- End with the citations block as JSON in a code block:
  ```json
  {"citations": [{"id": 1, "url": "...", "title": "..."}, ...]}
  ```
- If relevant, suggest a related practice concept the student could try.

STYLE:
- Concise. Precise. No marketing language. No filler.
- Match the official documentation's terminology exactly.
- If the student appears to have a misconception, address it gently and
  directly.
```

### 8.6 Student Model Updater

**Role**: NOT a conversational agent. Takes the output of the Grader and applies updates to the Student Model JSON. Implemented as a deterministic function with optional LLM assistance for ambiguous misconception tagging.

**Input**: `{grading_result: dict, current_student_model: dict}`

**Output**: Updated `student_model` dict.

**Model**: Claude Haiku 4.5 (only for ambiguous misconception matching).

**System prompt (for the LLM-assisted ambiguous case)**:

```
You are the Student Model Updater. You receive a grading_result and the
current student_model. Your job is ONLY to determine the correct update
to apply to the model — not to converse, not to teach.

UPDATE RULES (apply deterministically in code; this prompt is used only
when a fuzzy match on misconception ID is needed):

1. concept_mastery_map[concept]:
   - evidence="demonstrated": mastery += 0.3 * confidence.
   - evidence="partial": no change; mastery_confidence -= 0.1.
   - evidence="missing": mastery -= 0.2 * confidence.
   - Clamp mastery to [0.0, 5.0].
2. misconceptions[misconception_id]:
   - If identified_misconception is non-null and non-error:
     - Increment count.
     - Set last_seen to current timestamp.
     - If count >= 2, set status="active".
3. session_history: append question_id, verdict, timestamp.

For ambiguous misconception text:
- If the new text closely matches an existing misconception_id, return
  the existing id with is_new=false.
- Otherwise create a new kebab-case id with is_new=true.

Return JSON: {"matched_misconception_id": "...", "is_new": true|false}
```

---

## 9. RAG Corpus Specification

### 9.1 Corpus is loaded from the active Pack

The platform itself defines no corpus URLs. Each Certification Pack provides:

- A list of URLs to ingest (Tier 1 = authoritative, Tier 2 = supplementary).
- Optional manual chunks (e.g., locally-written summaries).
- Metadata mappings (which URL → which domain).

When the user selects a Pack, the platform either uses the already-ingested ChromaDB collection (if present) or triggers ingestion for that Pack. Each Pack gets its own ChromaDB collection named `pack_<pack_id>`.

### 9.2 Corpus tier policy

Trust tiers stored in ChromaDB metadata. Citations may only reference Tier 1 sources.

- **Tier 1 — Official Authoritative**: First-party publications by the certification authority.
- **Tier 2 — Official Supplementary**: First-party blog posts, cookbooks, example repos.

### 9.3 CCA-F Pack — URLs to ingest (the validation Pack)

This is the corpus for the demo, exposed as a `cca-f` Certification Pack:

#### Domain D1 — Agentic Architecture & Orchestration (27%)

- https://docs.claude.com/en/api/agent-sdk/overview
- https://docs.claude.com/en/docs/claude-code/sdk/sdk-overview
- https://docs.claude.com/en/docs/agent-sdk/subagents
- https://docs.claude.com/en/api/agent-sdk/python
- https://docs.claude.com/en/api/agent-sdk/typescript
- https://docs.claude.com/en/docs/agents-and-tools/tool-use/overview
- https://docs.claude.com/en/docs/claude-code/sdk/migration-guide

#### Domain D2 — Tool Design & MCP Integration (18%)

- https://docs.claude.com/en/docs/agents-and-tools/tool-use/overview
- https://docs.claude.com/en/api/agent-sdk/custom-tools
- https://modelcontextprotocol.io/specification/2025-11-25
- https://modelcontextprotocol.io/specification/2025-11-25/basic
- https://modelcontextprotocol.io/specification/2025-06-18

#### Domain D3 — Claude Code Configuration & Workflows (20%)

- https://docs.claude.com/en/docs/claude-code/overview
- https://docs.claude.com/en/docs/claude-code/hooks
- https://docs.claude.com/en/docs/claude-code/hooks-guide
- https://docs.claude.com/en/docs/claude-code/slash-commands
- https://docs.claude.com/en/docs/claude-code/sdk/sdk-slash-commands
- https://docs.claude.com/en/api/agent-sdk/slash-commands
- https://docs.claude.com/en/release-notes/claude-code

#### Domain D4 — Prompt Engineering & Structured Output (20%)

- https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/overview
- https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices
- https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/chain-of-thought
- https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/system-prompts
- https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/prefill-claudes-response
- https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/prompt-templates-and-variables
- https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/prompt-improver
- https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/prompt-generator
- https://docs.claude.com/en/docs/build-with-claude/structured-outputs
- https://docs.claude.com/en/docs/agent-sdk/structured-outputs
- https://docs.claude.com/en/docs/test-and-evaluate/strengthen-guardrails/increase-consistency

#### Domain D5 — Context Management & Reliability (15%)

- https://docs.claude.com/en/release-notes/overview (context editing, prompt caching)
- https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/prompt-improver
- (Additional URLs for: context windows, prompt caching, extended thinking — to be located during ingestion)

#### Tier 2 — Supplementary

- https://github.com/anthropics/anthropic-cookbook
- https://github.com/anthropics/anthropic-cookbook/tree/main/patterns/agents
- https://github.com/anthropics/anthropic-cookbook/blob/main/patterns/agents/README.md
- https://github.com/anthropics/anthropic-cookbook/blob/main/patterns/agents/prompts/research_lead_agent.md
- https://github.com/anthropics/anthropic-cookbook/blob/main/patterns/agents/prompts/research_subagent.md
- https://github.com/anthropics/anthropic-cookbook/blob/main/tool_evaluation/tool_evaluation.ipynb

### 9.4 Ingestion pipeline (functional description)

The ingestion pipeline is **generic** — it works with any Certification Pack:

**Step 1 — Load Pack descriptor** (see Section 12 for format)

**Step 2 — Fetch**
- For each URL: fetch HTML via `requests` (respectful delay, ~1s between requests).
- For GitHub: fetch raw content from `raw.githubusercontent.com`; for notebooks, fetch `.ipynb` JSON and extract cell content.

**Step 3 — Extract**
- HTML: convert to clean Markdown using `trafilatura`. Strip navigation, headers, footers.
- Notebooks: concatenate markdown + code cells (code fenced as ` ```python `).

**Step 4 — Chunk** (see Section 10 for strategy options)

**Step 5 — Embed**
- Voyage AI `voyage-3` (preferred) or OpenAI `text-embedding-3-small` (fallback). One choice per corpus.

**Step 6 — Index in ChromaDB**
- Collection name: `pack_<pack_id>` (e.g., `pack_cca-f`).
- Each chunk persisted with metadata:
  ```
  {
    "pack_id": "cca-f",
    "source_url": str,
    "source_title": str,
    "tier": 1 | 2,
    "domain": str,           // domain id from the Pack
    "domain_weight": float,
    "concept_tags": [str],
    "content_type": "concept" | "code_example" | "pattern" | "anti_pattern" | "reference",
    "ingested_at": ISO8601,
    "corpus_version": "v1"
  }
  ```

**Step 7 — Verify**
- Generate `ingestion_manifest.json` per Pack listing all URLs, chunk counts per source, per domain.
- Manual spot check: 5 random chunks per domain.

### 9.5 Re-ingestion policy

- Each Pack is versioned independently (`corpus_version`).
- A full re-ingest is triggered when: official material is updated, exam scope changes, or schema changes.
- The UI shows the active Pack's corpus version.

---

## 10. Open Decision A — Chunking Strategy

To be closed in a Claude Code session.

### Option A1 — **Fixed-size with overlap (RecursiveCharacterTextSplitter)**

- Chunk size: 800 tokens, overlap 100 tokens.
- Splits on paragraph → sentence → character boundaries.
- **Pros**: predictable, simple, well-tested, LangChain native.
- **Cons**: can split mid-concept; code blocks may be broken.

### Option A2 — **Markdown header-aware (MarkdownHeaderTextSplitter then size-bounded)**

- First split by markdown headers (`#`, `##`, `###`) preserving the header hierarchy in metadata.
- Then size-bound each section to max 1000 tokens (split further if needed).
- **Pros**: respects document structure; each chunk carries semantic context (section title) in metadata; matches how docs are organized.
- **Cons**: requires consistent markdown structure; chunks vary in size.

### Option A3 — **Semantic chunking (embedding-distance based)**

- Use a semantic chunker (e.g., `SemanticChunker` from LangChain experimental) that splits when consecutive sentence embeddings diverge beyond a threshold.
- **Pros**: chunks align with topic boundaries naturally.
- **Cons**: slower, more expensive at ingest time, less deterministic, harder to debug.

### Decision criteria to apply in Claude Code

- Is the official material consistently structured with markdown headers? (Favors A2)
- How important is reproducibility vs. semantic quality? (A1 most reproducible; A3 most semantic)
- Build-time budget vs. retrieval quality? (A1 fastest; A3 highest quality but slowest)

---

## 11. Open Decision B — Student Model Schema

To be closed in a Claude Code session.

The Student Model is **Pack-agnostic** at the schema level — concept and domain identifiers come from whatever Pack is active. The three options below differ in structural richness.

### Option B1 — **Flat concept list**

```json
{
  "student_id": "string",
  "pack_id": "string",
  "created_at": "iso8601",
  "updated_at": "iso8601",
  "concept_mastery": {
    "concept_id_1": {"mastery": 2.4, "confidence": 0.6, "last_seen": "..."},
    "concept_id_2": {"mastery": 1.8, "confidence": 0.4, "last_seen": "..."}
  },
  "misconceptions": {
    "misconception_id_1": {"count": 3, "last_seen": "...", "status": "active"}
  },
  "session_history": [
    {"question_id": "...", "verdict": "correct", "timestamp": "..."}
  ]
}
```

- **Pros**: simplest, fast lookups, easy to inspect by hand, ideal for MVP/V1.
- **Cons**: no domain aggregation, no concept relationships, no learning-style data.

### Option B2 — **Domain-grouped with aggregation**

```json
{
  "student_id": "string",
  "pack_id": "string",
  "domains": {
    "D1": {
      "weight": 0.27,
      "aggregate_mastery": 2.6,
      "concepts": {
        "concept_id_1": {"mastery": 2.4, "confidence": 0.6, "last_seen": "..."}
      }
    },
    "D2": {...}
  },
  "misconceptions": {...},
  "session_history": [...]
}
```

- **Pros**: dashboard rendering is trivial (per-domain bars); aggregate_mastery computed on update.
- **Cons**: slightly more complex updates; domain reassignment is painful if it ever happens.

### Option B3 — **Graph-based with concept relationships (V2-ready)**

```json
{
  "student_id": "string",
  "pack_id": "string",
  "domains": {...},
  "concepts": {
    "concept_id_1": {
      "mastery": 2.4,
      "confidence": 0.6,
      "domain": "D1",
      "prerequisites": ["concept_id_0"],
      "leads_to": ["concept_id_5"],
      "last_seen": "..."
    }
  },
  "misconceptions": {...},
  "session_history": [...],
  "learning_style_hints": {
    "prefers_examples": 0.7,
    "prefers_analogies": 0.3,
    "absorbs_code_fast": 0.8
  }
}
```

- **Pros**: full curriculum graph; supports V2 adaptive plan generation; learning style ready.
- **Cons**: more complex to build initially; some fields unused until V2.

### Decision criteria to apply in Claude Code

- How early is a polished dashboard needed? (Favors B2)
- How likely is the project to reach V2? (Favors B3)
- How much complexity can the MVP tolerate? (Favors B1)

---

## 12. Certification Pack Specification

A Certification Pack is the declarative artifact that makes the platform generic. Adding a new certification requires authoring a Pack — no code changes.

### 12.1 Pack file structure

```
packs/
  cca-f/
    pack.yaml             # the descriptor (see schema below)
    corpus_urls.yaml      # URLs to ingest, grouped by domain and tier
    curriculum.yaml       # concepts list per domain
    style_notes.md        # free-form Examiner guidance for this cert
    sample_questions.md   # optional, for prompt few-shot examples
```

### 12.2 `pack.yaml` schema (illustrative)

```yaml
id: cca-f
name: CCA-F
full_name: Claude Certified Architect — Foundations
authority: Anthropic
exam_format: multiple_choice
question_count: 60
duration_minutes: 120
passing_score: 720
scoring_scale: [100, 1000]
style: scenario-based         # one of: scenario-based | conceptual | mixed
language: en
corpus_version: v1
domains:
  - id: D1
    name: Agentic Architecture & Orchestration
    weight: 0.27
  - id: D2
    name: Tool Design & MCP Integration
    weight: 0.18
  - id: D3
    name: Claude Code Configuration & Workflows
    weight: 0.20
  - id: D4
    name: Prompt Engineering & Structured Output
    weight: 0.20
  - id: D5
    name: Context Management & Reliability
    weight: 0.15
```

### 12.3 `curriculum.yaml` schema (illustrative)

```yaml
concepts:
  - id: agentic_loop_stop_reason
    name: Agentic Loop and stop_reason semantics
    domain: D1
    prerequisites: []
    leads_to: [hub_and_spoke_orchestration]
  - id: hub_and_spoke_orchestration
    name: Hub-and-spoke multi-agent orchestration
    domain: D1
    prerequisites: [agentic_loop_stop_reason]
    leads_to: [subagent_context_isolation]
  # ... and so on
```

### 12.4 Loading a Pack

At app startup (or when the user switches packs):

1. Read `pack.yaml` → load into `pack_state`.
2. Check if a ChromaDB collection `pack_<id>` exists. If not, run ingestion using `corpus_urls.yaml`.
3. Load `curriculum.yaml` into the Curriculum Graph (V2 uses prerequisites/leads_to; V1 only uses concept list).
4. Initialize a new Student Model for this student × Pack combination if one doesn't exist.

### 12.5 Demo strategy

For the capstone:

- The **CCA-F Pack is the primary deliverable**, fully populated.
- During the demo, the platform claim is reinforced by showing the Pack files and explaining that the same agents would work with any other Pack.
- **Stretch goal**: a minimal "second Pack" (e.g., 10 documents from an AWS Cloud Practitioner free study guide, just enough to demonstrate Pack switching works).

---

## 13. Tech Stack (closed decisions)

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.11+ | Required for LangGraph features |
| Environment | Virtualenv via `uv` or `venv` | macOS controlled environment |
| Agent framework | **LangGraph** | State graph + conditional flows |
| LLM provider | **Anthropic** (Claude Sonnet 4.6 primary, Haiku 4.5 for lightweight tasks) | Mix is OK per per-agent recommendations |
| Vector store | **ChromaDB** (local persistent) | Zero-setup; per-Pack collections |
| Embeddings | Voyage AI `voyage-3` (preferred) or OpenAI `text-embedding-3-small` (fallback) | One choice per corpus |
| Student Model storage | **JSON files** on local disk | One file per student_id × pack_id |
| Frontend | **Gradio** | Closed decision; see Section 6 |
| Pack files | YAML + Markdown | Human-readable, version-controllable |
| Document parsing | `trafilatura` for HTML → Markdown; `nbformat` for notebooks | |
| Observability | **LangSmith** | Optional but recommended for demo |
| Testing | `pytest` | |
| Config management | `pydantic-settings` with `.env` file | |
| Logging | `loguru` or stdlib `logging` | |

### Required environment variables

```
ANTHROPIC_API_KEY=...
VOYAGE_API_KEY=...
OPENAI_API_KEY=...                    # fallback embeddings
LANGSMITH_API_KEY=...                 # optional
LANGSMITH_PROJECT=ai-tutor            # optional
CHROMA_PERSIST_DIR=./data/chroma
STUDENT_MODELS_DIR=./data/students
PACKS_DIR=./packs
DEFAULT_PACK_ID=cca-f
```

---

## 14. Project Structure

```
ai-tutor/
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
│
├── packs/                          # Certification Packs (declarative)
│   └── cca-f/
│       ├── pack.yaml
│       ├── corpus_urls.yaml
│       ├── curriculum.yaml
│       ├── style_notes.md
│       └── sample_questions.md     # optional
│
├── data/
│   ├── chroma/                     # ChromaDB persistence (per-Pack collections)
│   ├── students/                   # student JSON files (per student × pack)
│   ├── raw/                        # raw fetched documents (cache)
│   └── manifests/                  # ingestion manifests per Pack
│
├── src/
│   ├── __init__.py
│   ├── config.py                   # pydantic settings
│   ├── models.py                   # pydantic models for structured data
│   │
│   ├── packs/
│   │   ├── __init__.py
│   │   ├── loader.py               # load pack.yaml, curriculum.yaml
│   │   └── registry.py             # active Pack management
│   │
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── fetch.py
│   │   ├── extract.py
│   │   ├── chunk.py                # decision A applies here
│   │   ├── embed.py
│   │   └── index.py                # ChromaDB indexing per Pack
│   │
│   ├── rag/
│   │   ├── __init__.py
│   │   └── retriever.py            # per-Pack retrieval with domain filtering
│   │
│   ├── student_model/
│   │   ├── __init__.py
│   │   ├── schema.py               # decision B applies here
│   │   ├── store.py                # JSON file persistence
│   │   └── updater.py              # rule-based + LLM-assisted updates
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── examiner.py
│   │   ├── grader.py
│   │   ├── coach.py
│   │   ├── explainer.py
│   │   ├── qna.py
│   │   └── prompts/                # system prompts as separate .md files
│   │       ├── examiner.md
│   │       ├── grader.md
│   │       ├── coach.md
│   │       ├── explainer.md
│   │       ├── qna.md
│   │       └── updater.md
│   │
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── state.py                # TutorState definition
│   │   └── tutor_graph.py          # LangGraph wiring
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   └── app.py                  # Gradio entry point
│   │
│   └── curriculum/
│       ├── __init__.py
│       └── graph.py                # Curriculum Graph helpers (V2)
│
├── scripts/
│   ├── ingest_pack.py              # ingest a specific Pack
│   ├── inspect_chroma.py
│   ├── reset_student.py
│   └── create_pack_skeleton.py     # bootstrap a new Pack
│
└── tests/
    ├── test_packs.py
    ├── test_ingestion.py
    ├── test_retriever.py
    ├── test_examiner.py
    ├── test_grader.py
    ├── test_updater.py
    └── fixtures/
        └── sample_chunks.json
```

---

## 15. Setup Instructions (macOS)

### 15.1 Prerequisites

- macOS 13+ (Ventura or newer).
- Python 3.11 or 3.12 (`brew install python@3.12`).
- An Anthropic API key (https://console.anthropic.com).
- An embeddings API key (Voyage AI or OpenAI).
- Git.

### 15.2 Initial setup

```bash
# Clone the repo
git clone <repo-url> ai-tutor && cd ai-tutor

# Create a virtualenv
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env and fill API keys

# Create data directories
mkdir -p data/chroma data/students data/raw data/manifests

# Ingest the CCA-F Pack (one-time, ~10-20 minutes)
python scripts/ingest_pack.py --pack cca-f

# Inspect what was ingested
python scripts/inspect_chroma.py --pack cca-f

# Launch the UI
python -m src.ui.app
```

### 15.3 Suggested dependency list (initial draft)

- `anthropic>=0.40.0`
- `langgraph>=0.2.0`
- `langchain-core>=0.3.0`
- `langchain-anthropic>=0.3.0`
- `chromadb>=0.5.0`
- `voyageai` or `openai`
- `trafilatura`
- `nbformat`
- `pyyaml`
- `pydantic>=2.0`
- `pydantic-settings`
- `loguru`
- `pytest`
- `gradio`

---

## 16. Testing Strategy

### 16.1 Unit tests

- **Pack loading**: malformed Pack files raise; valid Packs load with all expected fields.
- **Ingestion**: fetch (mocked), extraction (fixture HTML → expected MD), chunking (deterministic).
- **Retriever**: domain and Pack filtering, top-k, citation metadata presence.
- **Updater**: mastery transitions, misconception increment.
- **Agents**: output schema conformance using Pydantic validation.

### 16.2 Integration tests

- End-to-end practice flow with a fixture Pack: load Pack → ingest small corpus → run session → assert valid grading output.
- Q&A flow with citation verification: every claim references a URL present in retrieved chunks' metadata.
- Pack switching test (V2): switch from CCA-F to a fixture Pack and verify Student Model is per-Pack.

### 16.3 LLM output testing

- Use **LLM-as-judge** sparingly for subjective outputs (e.g., "is this question scenario-style?").
- For schema conformance: use Pydantic `model_validate` and fail fast.

### 16.4 Manual evaluation

- Periodically review 10 random generated questions for quality, scoring on:
  - Faithfulness to source (no hallucinations).
  - Style match to the Pack (e.g., CCA-F → scenario-based, not trivia).
  - Distractor quality (anti-patterns or random?).
  - Cite-ability (citations are real, retrievable URLs).

---

## 17. Cost Estimation

**Assumptions** (typical capstone usage with CCA-F Pack):

- ~50 practice sessions during development + ~10 demo sessions.
- Each session: 10 questions + grading + 2-3 explanations + 5 Q&A queries.

### Per-component cost

| Component | Calls/session | Tokens/call (in/out) | Cost/session |
|---|---|---|---|
| Examiner (Sonnet 4.6) | 10 | 3000 / 600 | ~$0.10 |
| Grader (Sonnet 4.6) | 10 | 2000 / 500 | ~$0.07 |
| Explainer (Sonnet 4.6) | 2-3 | 1500 / 400 | ~$0.02 |
| Q&A (Sonnet 4.6) | 5 | 2000 / 500 | ~$0.04 |
| Coach (Sonnet 4.6) | 20 | 800 / 200 | ~$0.03 |
| Updater (Haiku 4.5, partial) | 10 | 500 / 100 | ~$0.005 |
| Embeddings (queries) | 30 | n/a | <$0.01 |
| **Total per session** | | | **~$0.28** |

### One-time corpus ingestion (CCA-F Pack)

- ~600 chunks × embedding cost = ~$0.10 (Voyage) or ~$0.20 (OpenAI).

### Project total estimate

- ~60 sessions × $0.28 + ingestion = **~$17-25 USD**.
- Adding a second Pack for demo: + ~$0.05-0.10 ingestion.

### Cost controls to implement

- Use prompt caching for system prompts (significant savings).
- Cap context size per retrieval (top-5 chunks, not top-20).
- Use Haiku for non-reasoning tasks.
- Add a per-session token budget log; warn if a session exceeds 50K tokens.

---

## 18. Observability

### 18.1 LangSmith (recommended)

- Set `LANGSMITH_API_KEY` and `LANGSMITH_PROJECT=ai-tutor`.
- LangGraph auto-traces all nodes and agent calls.
- Useful for: debugging Coach decisions, verifying retrieved chunks per query, inspecting agent prompts.

### 18.2 Local logging

- Use `loguru` with two outputs:
  - INFO+ to stdout (concise).
  - DEBUG+ to a rotating file `./logs/tutor.log`.
- Log structured events: pack_id loaded, question_id generated, verdict, mastery delta, retrieval queries.

### 18.3 Demo-time visualization

- For the capstone demo, consider a Gradio sidebar showing live: current agent thinking, retrieved chunks, mastery delta after each grade. This is often the difference between a forgettable and a memorable demo.

---

## 19. Deployment Notes

Out of scope for the capstone, but documented:

- The app runs entirely locally for the capstone.
- For future remote deployment: containerize with Docker, persist ChromaDB to a volume, migrate Student Models to Postgres (replacing JSON), reverse proxy in front.
- Anthropic API keys must never be shipped client-side; the frontend always goes through the local backend.
- A SaaS evolution would expose Pack authoring as a self-service feature.

---

## 20. Implementation Roadmap

### Suggested order (within whichever slice is chosen first)

1. **Repository scaffolding** — `pyproject.toml`, `.env.example`, folder structure, README.
2. **Config & models** — `src/config.py`, `src/models.py`.
3. **Pack loader** — `src/packs/loader.py`. Author the CCA-F Pack files in `packs/cca-f/`.
4. **Ingestion pipeline** — fetch → extract → chunk → embed → index. Per-Pack collection.
5. **Retriever** — Pack-scoped, domain-filtered queries.
6. **Examiner agent** — implement and test with sample chunks and a target concept.
7. **Grader agent** — implement and test with sample questions and answers.
8. **Minimal Gradio UI** — practice flow only, single Pack (CCA-F).
9. **End-to-end test** — load Pack → generate question → answer → grade → display. Closes MVP.
10. **(V1) Coach + LangGraph wiring** — intent classification, state graph.
11. **(V1) Student Model store and Updater** — per-Pack persistence.
12. **(V1) Explainer + Q&A agents**.
13. **(V1) Dashboard tab** in Gradio.
14. **(V2) Curriculum Graph** loaded from Pack.
15. **(V2) Plan Generator**.
16. **(V2) Learning style detection**.
17. **(V2) Readiness scoring**.
18. **(V2 stretch) Second Pack** to demonstrate platform genericity.

### Definition of "done" for the MVP

- CCA-F Pack files authored (`pack.yaml`, `corpus_urls.yaml`, `curriculum.yaml`).
- Corpus for one domain ingested into a `pack_cca-f` ChromaDB collection.
- A user can run a session of 10 questions, answer each, receive correct/incorrect verdict with explanation and citations.
- All citations resolve to real URLs from the ingested corpus.
- The application runs with `python -m src.ui.app` on macOS.

### Definition of "done" for V1

- All five CCA-F domains ingested.
- Student Model persists across sessions (per student × Pack).
- Dashboard shows per-domain mastery and active misconceptions.
- Q&A flow works with grounded citations.

### Definition of "done" for V2

- Adaptive study plan generated and updated each session.
- Readiness score computed and displayed.
- Learning style hints inferred over 3+ sessions.
- (Stretch) A second Pack loads cleanly and Pack switching works.

---

## Appendix A — Glossary

- **AI Tutor**: the generic tutoring platform.
- **Certification Pack** (Pack): a declarative bundle of corpus URLs + curriculum + exam metadata + style notes that turns the platform into a tutor for a specific certification.
- **CCA-F**: Claude Certified Architect — Foundations, the first validation Pack used to demo the platform.
- **Concept mastery**: a 0–5 score representing the system's estimate of the learner's understanding of a specific concept within the active Pack.
- **Misconception**: a specific, recurring incorrect mental model the learner exhibits.

## Appendix B — Out-of-scope risks to acknowledge

- **Corpus drift**: certification material changes; Packs need periodic re-ingestion.
- **Exam content drift**: certification authorities update their exams; curriculum files need revision.
- **Sample question scarcity**: most certs publish few official samples. The platform relies on the Examiner to generate. Examiner quality is the single biggest determinant of value — invest disproportionate effort there.
- **Pack quality variance**: a poorly authored Pack produces a poor tutor. The platform is only as good as the Pack — clear authoring guidelines are essential for any future expansion beyond CCA-F.
