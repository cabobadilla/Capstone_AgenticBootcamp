# AI Tutor — Functional & Technical Specification (v2)

> **Version**: v2.1 — **POST-BUILD revision (2026-05-29)**. MVP and V1 shipped end-to-end. Document now reflects actual implementation: 6-tab Gradio UI, `tool_use` structured output, Coach ID normalization, "Chalk & Coral" design system. Build outcomes, bugs found, and decisions made during development are captured in **Appendix E — Build Log**. The originally agreed v2 contract (Appendix C decisions log, A2 chunking, B2 schema) was honoured in full.
>
> **Original v2 framing**: closes open decisions from v1 (chunking, student model schema, embeddings provider, observability), reframes scope for a 2-3 week capstone window, and replaces the open implementation roadmap (§20) with a week-by-week schedule. See **Appendix C** for the full decisions log and **Appendix D** for explicit out-of-scope V2 deferrals.
>
> **Purpose of this document**: Build specification for a **generic multi-agent AI Tutor platform** that adapts to any certification or learning challenge. The platform is domain-agnostic: it ingests a curated corpus, models a curriculum, and runs an adaptive tutoring loop powered by specialist agents.
>
> **First validation dataset (demo)**: Anthropic's **Claude Certified Architect — Foundations (CCA-F)** exam. CCA-F serves as the proof-of-value scenario to demonstrate the platform end-to-end: a real, official certification with public curriculum, official documentation as ground truth, and well-defined exam domains.
>
> **Why this framing matters**: The capstone presents not a single-purpose tutor but a **reusable platform**. The same agents, RAG plumbing, and student model work for AWS, Azure, Kubernetes, PMP, or any other certification — only the corpus and the curriculum descriptor change. CCA-F is the demonstration; the platform is the deliverable.
>
> **Target environment**: macOS, Python 3.11+, controlled virtual environment.
>
> **Scope tightening (v2)**: MVP+V1 are the bootcamp deliverable. V2 (adaptive plan, learning style detection, exam readiness score, curriculum graph) is **post-bootcamp** future work. The schema (§11) is forward-compatible so V2 is an additive extension, not a rewrite.

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

**v2 closure**: The slice order is **MVP → V1 → V2 incrementally**, with each slice fully demoable before the next begins. V2 is deferred to **post-bootcamp** (see Appendix D); the 2-3 week capstone window targets MVP + V1.

All slices use the CCA-F Certification Pack as the validation dataset. The platform genericity is preserved at every slice level — no slice introduces certification-specific code.

### Slice 1 — MVP: Targeted Practice (single domain)

- **One exam domain** of the loaded Pack indexed in the RAG. **Starting domain for CCA-F: D1 — Agentic Architecture & Orchestration (27% weight)** — chosen for maximum exam-prep ROI.
  - **Trade-off (v2)**: D1 is the highest-weight domain but is scenario-heavy and harder to ground questions in cleanly than D4. The v1 spec recommended D4 first for that reason.
  - **Mitigation**: start D1 with **conceptual-difficulty questions only** (per §8.1 Examiner prompt's `difficulty` parameter). Validate retrieval quality with 20 manual chunk inspections before enabling scenario difficulty. If question quality is poor after ~10 manual reviews on day 3, fall back to D4 (3-hour contained pivot).
- **Two agents**: Examiner (generates questions) + Grader (evaluates answers, diagnoses misconceptions).
- **Session-only memory** (no persistence across sessions).
- **UI**: practice flow + minimal progress view for the session.
- **Question types**: conceptual first; scenarios enabled after retrieval validation.
- **Observability (v2)**: LangSmith tracing **enabled from day 1** of MVP (closes §18 optionality).
- **Estimated effort**: ~35% of total project.

### Slice 2 — V1: Adaptive Tutor with Persistent Student Model

- **All domains** of the loaded Pack indexed in the RAG.
- **Additional agents**: Coach (orchestrator), Explainer, Q&A Agent, Student Model Updater.
- **Persistent Student Model** in JSON file storage (across sessions).
- **UI**: practice flow + free Q&A + persistent progress dashboard.
- **Question types**: full conceptual + scenario coverage.
- **Estimated effort**: +35% (~70% cumulative).

### Slice 3 — V2: Complete Tutor with Adaptive Curriculum (POST-BOOTCAMP)

> **v2 scope note**: V2 is **out of scope** for the 2-3 week capstone window (Appendix D). All schema decisions in §11 are forward-compatible so V2 lands as an additive extension when work resumes. The capstone narrative explicitly positions V2 as a post-ship roadmap.

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

### 5.2 Tabs (as shipped)

> **POST-BUILD update (v2.1)**: shipped with **6 tabs** rather than the originally specified 4 views. The original 4 (Home, Practice, Q&A, Dashboard) were split for clarity: Home (intro + corpus) was separated from Topics (domain selector), and Architecture (technical reference) was added so the platform-genericity claim is demonstrable during the capstone demo.

**Tab order (final):**

#### Tab 1 — Home

Onboarding screen — what the app is, how to use it step-by-step, and a full reference table of every document loaded into the knowledge base (Tier 1 authoritative · Tier 2 supplementary).

- App title and short description.
- Active Pack indicator: "Studying: CCA-F · Corpus v1 · 31 concepts · 429 chunks".
- "What is AI Tutor?" intro paragraph.
- "How to use" — 6-step instruction table.
- Exam domains weight table (D1–D5).
- **Reference Documents Loaded** — every URL grouped by domain and tier, with ✓/✗ fetch status, clickable.

#### Tab 2 — Topics

Domain and concept selection — moved here from Home for visual clarity.

- Domain dropdown (D1–D5 with weight).
- Dynamic concept list (updates when domain changes) showing all curriculum concepts for the selected domain.
- Button: "▶ Start practice session" — when clicked, app **auto-switches to the Practice tab** via `gr.Tabs(selected=...)`.

#### Tab 3 — Practice

Question display + grading feedback.

- **Question card** with left amber/coral border accent, IBM Plex Mono font.
- Question stem with concept · domain · difficulty subtitle.
- 4 answer pills (A/B/C/D) styled as cards with hover-lift and selected state.
- "Submit answer" button + "→ Next question" button (text appears after grading).
- Feedback panel: verdict (✅/❌) + explanation + identified misconception + inline `[1],[2]` citations + clickable source URLs.

#### Tab 4 — Progress

Persistent dashboard — mastery + misconceptions + history.

- "🔄 Refresh dashboard" button + this-session correct/total summary.
- Per-domain mastery bars (0–5 scale), one row per domain (block-character `█` bars).
- Active Misconceptions list (count ≥ 1; status="active" when count ≥ 2).
- Recent Questions table (last 15: concept · domain · verdict).

#### Tab 5 — Architecture

Technical reference for the capstone demo — not present in original spec.

- System architecture statement (platform vs Pack separation).
- Agent inventory table (6 agents · model · role).
- Practice session data flow diagram.
- Q&A data flow diagram.
- Knowledge base details (ChromaDB, embeddings, chunking).
- Student Model schema (B2 with B3-compat reserves).
- "Add a new Pack" one-page recipe.

#### Tab 6 — Q&A

Free-form grounded question answering — moved to last position so it doesn't compete with the primary study flow.

- Chat-style interface (`gr.Chatbot`).
- User input box at the bottom.
- Agent responses include inline `[1]` citations + JSON citations block at the end.
- Refuses to answer questions outside the corpus (does not invent facts).

#### Cross-tab — Live agent sidebar

A right-side dark terminal panel (`#111111` background, IBM Plex Mono, amber/coral labels) showing the live LangGraph trace: active node + last 8 timestamped log lines. Visible on every tab.

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

> **POST-BUILD note (v2.1)**: structured output uses Anthropic **`tool_use`**, not raw JSON in the prompt. Asking Claude for JSON in the message body produced literal-newline characters inside string values (`explanation: "## Correct!\n\n..."` with actual `\n` not `\\n`) that broke `json.loads`. Tool use eliminates this — the API populates the input schema directly, guaranteed valid. The system prompt below remains as written; only the call mechanism changed (see `ai_tutor/agents/examiner.py`).

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

> **POST-BUILD note (v2.1)**: same `tool_use` pattern as the Examiner. The Grader's `explanation` field is verbose markdown with line breaks and embedded citations, which made raw-JSON output especially fragile. Tool use is mandatory here. `max_tokens` increased to 4096 to accommodate full explanations of all 4 options.

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

> **POST-BUILD note (v2.1)**: during V1 build the Coach occasionally returned concept **names** (e.g. `"Orchestrator and subagent roles in multi-agent systems"`) instead of concept **IDs** (`orchestrator_subagent_pattern`), causing the Updater to write mastery against orphan keys that never matched the curriculum. Fixed in two layers:
> 1. Coach user message now explicitly lists `concept_ids_by_domain` and the prompt instructs Claude to set `target_concept` to one of those IDs.
> 2. `node_select_concept` in `tutor_graph.py` normalises Coach output via ID match → case-insensitive name match → lowest-mastery fallback.
> 3. `updater.py` does the same name→ID fallback as a final safety net.

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

**Step 4 — Chunk** — **CLOSED (v2)**: use **Strategy A2** (markdown header-aware then size-bound). Implementation: `langchain_text_splitters.MarkdownHeaderTextSplitter` to split on `#`, `##`, `###` headers and preserve the header path in chunk metadata, then `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)` to size-bound any section longer than 1000 tokens. See §10 for the rationale.

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

## 10. Decision A — Chunking Strategy — **CLOSED (v2)**

> **Selected**: **Option A2 — Markdown header-aware then size-bound**.
>
> **Rationale**: The CCA-F corpus (Anthropic docs + MCP spec + cookbook) is consistently structured with markdown headers, so semantic boundaries align with structural boundaries. A2 keeps the header path in metadata, which strengthens retrieval grounding for the scenario-heavy D1 material chosen as the MVP starting domain. A1 was rejected because mid-concept splits would degrade D1 question quality. A3 was rejected as overkill: too slow, non-deterministic, and harder to debug for a 2-3 week capstone.
>
> **Implementation**: `MarkdownHeaderTextSplitter(headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")])` → `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)` for any section longer than 1000 tokens. Header path is stored in chunk metadata as `section_path: "h1 > h2 > h3"`.

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

## 11. Decision B — Student Model Schema — **CLOSED (v2)**

> **Selected**: **Option B2 — Domain-grouped with aggregation**, designed forward-compatible for B3.
>
> **Rationale**: B2 makes the dashboard rendering trivial (per-domain mastery bars from `domains.<id>.aggregate_mastery`) and matches the per-domain weighting in the Coach's `target_concept` selection (§8.3). B1 was rejected because we would migrate to B2 by V1 anyway — wasted work. B3 was rejected as not needed for MVP/V1 (its extra fields — `concepts{}`, `learning_style_hints` — only matter for V2 features that are out of scope).
>
> **Forward-compat for B3**: the V1 Pydantic schema reserves `concepts: dict | None = None` and `learning_style_hints: dict | None = None` as optional fields. V2 enables them additively — no destructive migration. See Appendix D.
>
> **Persisted as**: one JSON file per `student_id × pack_id` at `data/students/{student_id}_{pack_id}.json` (human-readable per NF-04).

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

## 13. Tech Stack (closed decisions · final versions shipped)

> **POST-BUILD note (v2.1)**: pinned versions reflect what's actually running. Structured output uses Anthropic **`tool_use`** (added during V1 build to fix JSON escaping failures). Gradio 6.15.2 introduced breaking class-name changes — `.tab-container` replaced `.tab-nav` (see §6.4 risks).

| Layer | Choice | Shipped version | Notes |
|---|---|---|---|
| Language | Python 3.11 | 3.11.15 | LangGraph + Pydantic v2 baseline |
| Environment | venv | — | `.venv` via `python3.11 -m venv` |
| Agent framework | **LangGraph** | 1.2.2 | 11-node state graph: load_pack → route_intent → practice/qna/explain/dashboard branches |
| LLM provider | **Anthropic** (Claude Sonnet 4.6 + Haiku 4.5) | sdk 0.105.2 | Sonnet for reasoning agents · Haiku for Updater fuzzy misconception matching |
| Structured output | **Anthropic `tool_use`** | — | Closed during V1 build. Replaces "ask for JSON" pattern that failed on multi-line markdown explanations. |
| Vector store | **ChromaDB** (local persistent) | 1.5.9 | Collection naming: `pack_<pack_id>`. Cosine similarity (`hnsw:space=cosine`). |
| Embeddings | **OpenAI `text-embedding-3-small`** | sdk 2.38.0 | 1536-dim. ~$0.20 to ingest full CCA-F corpus. |
| Student Model storage | **JSON files** on local disk | — | Atomic writes via tmp file + rename. One file per `student_id × pack_id`. |
| Frontend | **Gradio Blocks** | 6.15.2 | Custom CSS (10K chars) · generator-based loading states · tab auto-switching via `gr.Tabs(selected=...)`. |
| Pack files | YAML + Markdown | — | `pack.yaml` · `corpus_urls.yaml` · `curriculum.yaml` · `style_notes.md` |
| Document parsing | `trafilatura` + `nbformat` | 2.0.0 / 5.10.4 | HTML → Markdown; `.ipynb` cells concatenated with code fenced as ` ```python `. |
| Observability | **LangSmith** | sdk 0.8.7 | Auto-disabled if API key is placeholder. SSL errors suppressed via `logging.CRITICAL` on `langsmith` logger. |
| Retry policy | `tenacity` | 9.1.4 | 3 attempts · exponential backoff on embed batches and agent calls |
| Testing | `pytest` + `pytest-asyncio` | 9.0.3 / 1.4.0 | 18 tests across 5 files · unit + live integration |
| Config | `pydantic-settings` + `.env` | 2.14.1 | Singleton `settings` imported everywhere |
| Logging | `loguru` | 0.7.3 | One-line setup · structured log levels |
| Lint | `ruff` | 0.15.15 | `target-version = py311` |

### Required environment variables

```
ANTHROPIC_API_KEY=...                 # required
OPENAI_API_KEY=...                    # required — primary embeddings (closed v2)
LANGSMITH_API_KEY=...                 # required from MVP (closed v2)
LANGSMITH_PROJECT=ai-tutor            # required from MVP
LANGSMITH_TRACING=true                # set explicitly to enable
VOYAGE_API_KEY=...                    # optional — not used in v2 closed stack
CHROMA_PERSIST_DIR=./data/chroma
STUDENT_MODELS_DIR=./data/students
PACKS_DIR=./packs
DEFAULT_PACK_ID=cca-f
DEFAULT_STUDENT_ID=default            # for single-user local mode
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

- ~600 chunks × OpenAI `text-embedding-3-small` = **~$0.20** total (closed v2). MVP D1-only ingestion: ~$0.04 (~100 chunks).

### Project total estimate (v2 — capstone window)

- MVP (D1 only) sessions during dev: ~20 × $0.28 = ~$5.60
- V1 (all 5 domains) sessions during dev + demo: ~40 × $0.28 = ~$11.20
- Ingestion: $0.20 (full corpus, run once)
- **Capstone total: ~$17 USD** within NF-06 ($0.50/session) easily.
- (Future) Adding a second Pack: + ~$0.05-0.10 ingestion. **Post-bootcamp** (Appendix D).

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

## 20. Implementation Roadmap — **SHIPPED (v2.1, 2026-05-29)**

> ✅ **All weeks complete.** MVP and V1 demoable end-to-end. UI redesigned with "Chalk & Coral" palette. 18/18 tests passing. See `PLAN.md` and `docs/IMPLEMENTATION_PLAN.md` for the as-built record.

### Pre-week 0 ✅ DONE
- Repo scaffolded (`src/` → renamed to `ai_tutor/`, `data/`, `packs/`, `tests/`, `scripts/`).
- `.venv` created with Python 3.11.15.
- `pip install -e ".[dev]"` succeeded; all 150+ deps verified.
- `pyproject.toml:45` `include = ["ai_tutor*"]` after rename.

### Week 1 — MVP ✅ SHIPPED
- **Day 1**: foundation — `CLAUDE.md`, `config.py`, `models.py` (11 Pydantic models), `.env` populated.
- **Day 2**: CCA-F Pack files (D1 only) + ingestion pipeline + `scripts/ingest_pack.py`. **First D1 ingest: 36 chunks.**
- **Day 3**: RAG retriever + Examiner agent + tests. **Decision: switched to `tool_use` after raw-JSON failures.**
- **Day 4**: Grader agent + tests + `scripts/practice_cli.py`.
- **Day 5**: Gradio UI MVP — Home/Practice/Progress tabs. **MVP demoable end-to-end.**

### Week 2 — V1 ✅ SHIPPED
- **Day 6-7**: D2–D5 ingestion (**429 total chunks · 33/39 URLs fetched**). Coach/Explainer/Q&A/Updater agents.
- **Day 8**: Student Model (B2 + B3 reserves) + atomic JSON store + LangGraph orchestration (11 nodes).
- **Day 9**: Q&A tab, enriched dashboard, live agent sidebar via LangGraph `sidebar_log`.
- **Day 10**: 18 tests passing (unit + integration). **V1 demoable.**

### Week 3 — Polish + design overhaul ✅ SHIPPED
- **Ralph Loop (Day 11-12)**: 3-round UI improvement cycle — custom 10K-char CSS, generator-based loading states, tab auto-switch, color-coded feedback panels.
- **Design Shotgun (Day 13)**: 3 palette variants generated and compared. User selected **"Chalk & Coral"** (light mode · jet-black nav · coral `#ea580c` accent).
- **Bug fixes (Day 13)**: Coach concept-ID normalisation (Coach was returning concept names instead of IDs, breaking mastery accumulation).
- **Documentation pass (Day 14)**: `README.md`, `PLAN.md`, `CLAUDE.md` updated, `docs/DESIGN_REVIEW_2026-05-29.md` written.
- **Day 15**: capstone-ready.

### Definitions of done — unchanged from v1 (§20)

See "MVP done", "V1 done", "V2 done" definitions retained verbatim from v1 below for traceability.

### Definition of "done" for the MVP — ✅ MET

- ✅ CCA-F Pack files authored (`pack.yaml`, `corpus_urls.yaml`, `curriculum.yaml`, `style_notes.md`).
- ✅ Corpus for one domain ingested into a `pack_cca-f` ChromaDB collection.
- ✅ A user can run a session of N questions, answer each, receive correct/incorrect verdict with explanation and citations.
- ✅ All citations resolve to real URLs from the ingested corpus.
- ✅ The application runs with `python -m ai_tutor.ui.app` on macOS (package renamed from `src` during build).

### Definition of "done" for V1 — ✅ MET

- ✅ All five CCA-F domains ingested (429 chunks).
- ✅ Student Model persists across sessions (per student × Pack) at `data/students/{id}_{pack}.json`.
- ✅ Dashboard shows per-domain mastery, active misconceptions, and last 15 questions.
- ✅ Q&A flow works with grounded citations and refuses out-of-corpus topics.

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

---

## Appendix C — Decisions log (v2)

| Date | Decision | Choice | Rationale | Spec ref |
|---|---|---|---|---|
| 2026-05-29 | Slice strategy | MVP → V1 → V2 incrementally | User wants demoable artifact at each gate; ships defensible capstone story | §3 |
| 2026-05-29 | MVP first domain | D1 — Agentic Architecture & Orchestration (27%) | Maximum exam-prep ROI for personal goal; trade-off mitigated by conceptual-first difficulty | §3.1, §9.3 |
| 2026-05-29 | Decision A (chunking) | A2 — markdown header-aware + size-bound (≤1000 tokens) | Anthropic/MCP docs are well-structured with headers; preserves semantic context for scenario-heavy D1 | §10 |
| 2026-05-29 | Decision B (Student Model) | B2 — domain-grouped, B3-compatible reserves | Trivial dashboard render, matches Coach weighting logic, no destructive migration for V2 | §11 |
| 2026-05-29 | Embeddings | OpenAI `text-embedding-3-small` | User has `OPENAI_API_KEY`; marginal quality gap to Voyage doesn't justify extra signup | §13 |
| 2026-05-29 | Observability | LangSmith ON from MVP day 1 | User has `LANGSMITH_API_KEY`; live-trace walkthrough is the capstone "wow" factor | §18 |
| 2026-05-29 | Live agent sidebar | Deferred to V1 (not in MVP) | Protect MVP ship date in tight 2-3 week window | §18.3 |
| 2026-05-29 | Pack scope | CCA-F only; second Pack = post-bootcamp | Insufficient time for a meaningful second Pack; platform genericity demoed via pack files alone | §12.5 |
| 2026-05-29 | V2 scope | Post-bootcamp future work | 2-3 week timeline does not accommodate adaptive plan + learning style + readiness + curriculum graph | §3, App. D |
| 2026-05-29 | Capstone deadline | 2-3 weeks from kickoff | User confirmation | n/a |
| 2026-05-29 | Project use | Personal CCA-F prep + capstone deliverable | User confirmation | §1 |

---

## Appendix D — V2 features explicitly deferred (post-bootcamp)

These features from v1 §3 (Slice 3) and §4.2 (F-10..F-13) are **out of scope** for the capstone delivery window. They remain in the v2 design intentionally so the architecture stays forward-compatible.

| Feature | v1 ref | Re-entry criteria | Architectural enablement preserved |
|---|---|---|---|
| Adaptive study plan (Plan Generator) | F-10, §7.3 | After V1 demoed; ≥3 sessions of student data exist for testing | Student Model B2 schema reads cleanly into a future Plan Generator; no migration |
| Learning style detection | F-11, §11 (B3) | ≥3 sessions of student data; LLM-judge harness for "prefers examples vs analogies" | `learning_style_hints: dict \| None` reserved on the B2 schema |
| Exam readiness score | F-12, §3 (Slice 3) | Plan Generator landed; calibration data from ≥10 sessions | Mastery aggregates already exposed at the domain level in B2 |
| Curriculum graph (prerequisites/leads_to) | §3, §7.3 | Curriculum YAML already includes the fields; only the traversal logic + UI viz is missing | `concepts: dict \| None` reserved on B2; `packs/cca-f/curriculum.yaml` schema already supports prerequisites/leads_to |
| Multiple Certification Packs (second Pack live) | F-13, §12.5 | After capstone ships; pick a target (AWS Cloud Practitioner is the documented suggestion) | All agents, RAG, schema are already Pack-parameterized — no code changes needed to add a Pack |
| Live agent sidebar in MVP | §18.3 | Day 9 of V1 (week 2) per `docs/IMPLEMENTATION_PLAN.md` | LangSmith provides the same observability for MVP demos |

**Capstone narrative for V2**: *"V2 features are architecturally enabled — the B2 schema reserves the B3 fields, the curriculum YAML already encodes prerequisite/leads_to relationships, and the agent layer is fully Pack-parameterized. Resuming work post-bootcamp is additive, not a rewrite."*

---

## Appendix E — Build Log (v2.1 — post-build addendum)

> Captures everything that happened *during* the build that wasn't predicted in the original v2 spec — bugs found, decisions made under pressure, lessons learned. Future readers (including future you) should use this to understand why the code looks the way it does.

### E.1 — Final shipped stats

| Metric | Value |
|---|---|
| Lines of Python | ~3,200 across `ai_tutor/` |
| Custom CSS | ~250 lines (~10 KB) in `_CSS` constant |
| Test suite | 18 tests across 5 files (unit + live integration) — all passing |
| Corpus ingested | 429 chunks across 5 domains (D1=72, D2=57, D3=215, D4=55, D5=30) |
| URLs fetched | 33 of 39 successful (6 React-SPA pages returned <500 chars) |
| Concepts in curriculum | 31 across D1–D5 (7+7+6+6+5) |
| Cost to date | ~$5 USD across development sessions (well under the $17–25 estimate) |

### E.2 — Bugs found and fixed during build

| Bug | Symptom | Root cause | Fix |
|---|---|---|---|
| **JSON-in-string escaping** | Grader returned malformed JSON; `json.loads` raised `Unterminated string` | LLM generated literal newlines (not `\\n`) inside multi-line markdown `explanation` strings | Switched both Examiner and Grader to Anthropic **`tool_use`** — API populates the schema directly, guaranteed valid JSON |
| **`max_tokens` truncation** | Same symptom as above (truncated mid-string) before the `tool_use` switch | Grader explanations exceeded 2048-token budget | Bumped to 4096; ultimately solved by `tool_use` |
| **Coach returns concept names** | Mastery never accumulated; orphan keys with long names in student model | Coach's user message didn't list valid concept IDs; LLM returned free-text concept descriptions instead | Three-layer fix: (1) prompt now includes `concept_ids_by_domain` and instructs use of IDs; (2) `node_select_concept` normalises via ID→name→fallback; (3) Updater does same name→ID lookup as final safety net |
| **`KeyError: target_concept` in `run_grade`** | Stack trace on every submit | `run_grade` shortcut path bypassed `node_select_concept`, so `target_concept` was missing when `node_update_student` referenced it | Use `state.get("target_concept", "unknown")` for non-critical log line |
| **Gradio 6 `visible=True/False` regression** | Feedback panel never rendered after submit, despite handler returning correctly | Gradio 6 changed how visibility toggles propagate inside `gr.Tab` containers | Switched to always-visible components with empty/non-empty value-based toggling |
| **Gradio 6 tab CSS not applied** | Tab nav stayed white instead of jet black after palette change | Gradio 6.15 renames `.tab-nav` → `.tab-container` / `.tab-wrapper` | Updated CSS selectors; kept `.tab-nav` as fallback for future versions |
| **`show_copy_button` unsupported** | `TypeError` on app startup | Removed in Gradio 6 | Removed kwarg |
| **LangSmith SSL errors flood logs** | `SSLCertVerificationError` on every API call, blocking response flow | Corporate SSL cert chain not trusted by Python `requests` on this machine | Suppressed `langsmith` logger to `CRITICAL`; auto-disable tracing when key is placeholder |
| **6 of 39 URLs return 160 chars** | Thin corpus chunks | docs.anthropic.com renders some pages as React SPA — `requests` gets the JS shell only | Replaced SPA URLs with GitHub raw-markdown equivalents from the Anthropic cookbook |
| **`partial` evidence = 0 mastery looks broken** | Users complain that progress doesn't update after a wrong answer | Working as designed: `partial` evidence means "right domain, wrong mechanism" — no mastery change is correct | Add a clearer copy explanation in a future iteration; not a code bug |

### E.3 — Decisions made during build (not in original v2 spec)

| Decision | Why | Where |
|---|---|---|
| **Anthropic `tool_use` for all structured-output agents** | LLM JSON-in-prompt failures with multi-line strings | Examiner, Grader |
| **6 tabs instead of 4 views** | Better separation of onboarding (Home) from action (Topics), plus a dedicated Architecture tab for the capstone demo | UI |
| **Tab auto-switching** via `gr.Tabs(selected=...)` in generator yield | Eliminates the "user clicks Start, nothing happens visibly" UX failure | UI |
| **Generator-based loading states** (`yield` + final `yield`) | 15–30s silent waits on LLM calls are unacceptable; show "Generating…" immediately | `start_practice`, `submit_answer`, `next_question` |
| **Custom CSS via `gr.Blocks(css=...)`** + Google Fonts via `launch(head=...)` | Default Gradio looks like a tutorial demo, not a real product | UI |
| **"Chalk & Coral" palette** (light + jet-black nav + coral `#ea580c` accent) | Selected by user via `/design-shotgun` comparison vs Midnight Scholar and Forest Terminal alternatives | UI |
| **`elem_id` on every key component** | Required to make CSS overrides actually work in Gradio 6 | UI |
| **No `gr.Image` `show_copy_button` kwarg** | Unsupported in 6.15.2 | UI |

### E.4 — What we'd do differently if starting over

1. **Default to `tool_use` from day 1.** Asking the LLM for raw JSON in a prompt is fragile in ways that don't surface until the explanation field gets long. Tool use should be the structured-output default for every agent.
2. **Pass valid concept IDs to Coach in the prompt body, not the system prompt.** The Coach system prompt said "pick a concept" but the user message didn't supply the valid set. The LLM happily made up names that looked plausible.
3. **Inspect Gradio's actual rendered classes early.** We assumed `.tab-nav` worked because the docs said so; turned out 6.15.2 uses `.tab-container`. Five minutes of `browser_evaluate` in the live app would have saved an hour.
4. **Build the architecture tab content from the start.** Writing the data-flow diagrams in markdown forced us to clarify the graph; we should have started there rather than discovering the model through code.
5. **Test with `partial` evidence in mind.** The first wrong answer with `partial` evidence produced mastery=0.00, which looks identical to "broken." A clearer UI explanation would have prevented user confusion.

### E.5 — What still needs work (V2 backlog highlights)

1. **Exam readiness score** in the Progress tab header: `sum(domain.aggregate_mastery × domain.weight)` → 0–5 score.
2. **Plan Generator agent** — 7-day study plan from current mastery gaps.
3. **Curriculum graph traversal** — enforce prerequisite ordering using `prerequisites`/`leads_to` already in `curriculum.yaml`.
4. **Learning style hints** — infer from session_history patterns; B3 field already reserved.
5. **Second Certification Pack** — AWS Cloud Practitioner stub to demonstrate genericity on stage.
6. **Mobile UX** — answer pills wrap awkwardly below 480px; needs `flex-direction: column` media query.
7. **LangSmith SSL** — install corporate CA bundle or configure `REQUESTS_CA_BUNDLE` so traces flush cleanly.

### E.6 — Files produced during build

| Path | Purpose |
|---|---|
| `ai_tutor/` (renamed from `src/`) | Main package — 6 agents · LangGraph · RAG · student model · UI |
| `packs/cca-f/{pack,corpus_urls,curriculum}.yaml + style_notes.md` | The CCA-F Certification Pack |
| `tests/test_{examiner,grader,retriever,updater,integration}.py` | 18 tests |
| `scripts/{ingest_pack,practice_cli,inspect_chroma,reset_student}.py` | CLI utilities |
| `data/manifests/cca-f_all_v1.json` | Ingestion manifest (run record) |
| `README.md` | Public-facing project README with quick start |
| `CLAUDE.md` | Agent-facing project context (≤200 lines) |
| `PLAN.md` | What We Built · What We Improved · Future Roadmap |
| `docs/IMPLEMENTATION_PLAN.md` | Day-by-day execution plan |
| `docs/DESIGN_REVIEW_2026-05-29.md` | UI design audit + Ralph Loop report |
| `ai-tutor-spec-v2.md` | This document — post-build revision |
