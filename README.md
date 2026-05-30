# 🎓 AI Tutor — Adaptive Exam Prep Platform

> A multi-agent, RAG-powered tutoring platform that generates scenario-based practice
> questions, grades answers with pedagogical feedback, and adapts to your knowledge
> gaps session after session. **First validation Pack: CCA-F** (Claude Certified
> Architect — Foundations).

Built with Anthropic Claude · LangGraph · ChromaDB · Gradio. Designed to be
**certification-agnostic**: adding a new exam is YAML files only, zero code.

---

## Table of Contents

- [What it does](#what-it-does)
- [Features](#features)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Quick start](#quick-start)
- [Usage walkthrough](#usage-walkthrough)
- [Project structure](#project-structure)
- [Add a new Certification Pack](#add-a-new-certification-pack)
- [Testing](#testing)
- [Documentation](#documentation)
- [Roadmap](#roadmap)

---

## What it does

Preparing for a modern IT certification has three universal problems:

1. **Exams test applied judgment** in production scenarios, not flashcard memorization.
2. **Official material is scattered** across docs, blog posts, cookbooks, and SDKs.
3. **Static question banks don't adapt** to your specific knowledge gaps.

AI Tutor solves all three:

- **RAG-grounded question generation** from the certification's official documentation.
- **Pedagogical grading** with explanations and citations — every claim links to a source URL.
- **Continuous per-concept mastery tracking** that survives across sessions.
- **Adaptive concept selection** — the Coach picks your weakest area in the highest-weight exam domain.

The CCA-F Pack ships with 31 testable concepts across 5 domains and a 429-chunk
corpus drawn from official Anthropic docs and MCP specifications.

---

## Features

| Feature | Status |
|---|---|
| Scenario-based question generation with citations | ✅ Shipping |
| Pedagogical grading (verdict + misconception identification) | ✅ Shipping |
| Persistent student model (per-domain mastery) | ✅ Shipping |
| Free-form Q&A grounded in corpus | ✅ Shipping |
| Live agent trace sidebar | ✅ Shipping |
| 5-domain corpus (D1–D5) for CCA-F | ✅ Shipping |
| Tab-based UI (Home, Topics, Practice, Progress, Architecture, Q&A) | ✅ Shipping |
| LangSmith tracing | ✅ Optional |
| Adaptive study plan (Plan Generator agent) | 🟡 V2 roadmap |
| Exam readiness score | 🟡 V2 roadmap |
| Learning style detection | 🟡 V2 roadmap |
| Second Certification Pack | 🟡 V2 roadmap |

---

## Architecture

### Agent inventory

| Agent | Model | Role |
|---|---|---|
| **Examiner** | Claude Sonnet 4.6 | Generates one scenario-based MCQ grounded in retrieved chunks (`tool_use` for schema-safe JSON). |
| **Grader** | Claude Sonnet 4.6 | Evaluates the answer, explains each option, identifies the misconception. |
| **Coach** | Claude Sonnet 4.6 | Picks the next concept — lowest mastery × highest exam weight. |
| **Explainer** | Claude Sonnet 4.6 | Mastery-calibrated deep-dive (0–5 scale) on a single concept. |
| **Q&A Agent** | Claude Sonnet 4.6 | Answers free-form questions grounded strictly in the corpus. |
| **Updater** | Rule-based + Haiku 4.5 | Applies deterministic mastery deltas; Haiku for fuzzy misconception matching. |

### Practice session — data flow

```
User clicks "Start practice"
  ▼
LangGraph: load_pack → route_intent → select_concept
            Coach selects lowest-mastery concept in target domain
  ▼
LangGraph: generate_question
            RAG retriever → top-5 chunks from ChromaDB (cosine similarity)
            Examiner → 4-option MCQ with rationale + source citations
  ▼
UI: render question + answer pills

User selects answer → clicks Submit
  ▼
LangGraph: grade_answer
            Grader → verdict + explanation + concept_signal
  ▼
LangGraph: update_student
            Updater → mastery delta → domain aggregate updated
            Student model saved → data/students/{student}_{pack}.json
  ▼
UI: render feedback panel (color-coded, with citations)
```

### Knowledge base

- **Vector store**: ChromaDB (local persistent, `data/chroma/`)
- **Collection naming**: `pack_<pack_id>` (one collection per Certification Pack)
- **Embeddings**: OpenAI `text-embedding-3-small` (1536-dim, cosine similarity)
- **Chunking (A2 strategy)**: `MarkdownHeaderTextSplitter` → `RecursiveCharacterTextSplitter` (≤1000 tokens, 100-token overlap)

### Student model (B2 schema)

Stored as human-readable JSON, one file per `student_id × pack_id`:

```json
{
  "student_id": "default",
  "pack_id": "cca-f",
  "domains": {
    "D1": { "weight": 0.27, "aggregate_mastery": 2.1, "concepts": { ... } },
    "D2": { ... }
  },
  "misconceptions": { "confuses-orchestrator-with-peer-to-peer": { "count": 2, "status": "active" } },
  "session_history": [ { "question_id": "...", "verdict": "correct", "concept": "...", ... } ]
}
```

Mastery deltas (deterministic):
- `demonstrated` → mastery **+= 0.3 × confidence**
- `missing` → mastery **−= 0.2 × confidence**
- `partial` → no mastery change; confidence **−= 0.1**
- Clamped to **[0.0, 5.0]**

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11 | LangGraph + Pydantic v2 baseline |
| Agent orchestration | **LangGraph** | Stateful graph with conditional edges fits the Practice / Q&A / Explain / Dashboard branches |
| LLM provider | **Anthropic** (Claude Sonnet 4.6 + Haiku 4.5) | Mix matched to cost / reasoning depth |
| Structured output | **Anthropic `tool_use`** | Guarantees valid JSON — avoids string escaping failures |
| Vector store | **ChromaDB** (local persistent) | Zero-setup, per-Pack collections |
| Embeddings | **OpenAI `text-embedding-3-small`** | 1536-dim, cosine similarity |
| Frontend | **Gradio 6 Blocks** | Custom CSS · generator-based loading states · tab auto-switching |
| Observability | **LangSmith** (optional) | LangGraph node-by-node trace replay |
| Persistence | **JSON files** + ChromaDB SQLite | Human-readable, easy to inspect |
| Config | **pydantic-settings** | `.env` loading with type validation |
| Logging | **loguru** | One-line setup, structured logs |
| Testing | **pytest** | 18 tests, unit + live integration |

---

## Quick start

### Prerequisites

- macOS 13+ (Ventura or newer) — Linux should work, untested
- Python 3.11 (`brew install python@3.11`)
- Anthropic API key — [console.anthropic.com](https://console.anthropic.com)
- OpenAI API key — [platform.openai.com](https://platform.openai.com)
- LangSmith API key (optional but recommended) — [smith.langchain.com](https://smith.langchain.com)

### Setup

```bash
# 1. Clone and enter the project
git clone <repo-url> Capstone-AIBootcamp && cd Capstone-AIBootcamp

# 2. Create and activate the virtualenv
python3.11 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies (editable mode with dev extras)
pip install --upgrade pip setuptools wheel
pip install -e ".[dev]"

# 4. Configure environment
cp .env.example .env
# Edit .env and fill in:
#   ANTHROPIC_API_KEY=sk-ant-...
#   OPENAI_API_KEY=sk-...
#   LANGSMITH_API_KEY=lsv2_...   (optional)

# 5. Ingest the CCA-F corpus (one-time, ~2 minutes)
python scripts/ingest_pack.py --pack cca-f

# 6. Launch the UI
python -m ai_tutor.ui.app
# → http://127.0.0.1:7860
```

### Smoke test before the UI

```bash
# Quick terminal session — generates and grades 3 questions
python scripts/practice_cli.py --questions 3

# Inspect what was indexed
python scripts/inspect_chroma.py --pack cca-f
```

---

## Usage walkthrough

The Gradio UI has six tabs. The typical study flow:

| Tab | What you do |
|---|---|
| 🏠 **Home** | Read the intro, see the loaded corpus and exam domain weights |
| 📚 **Topics** | Pick an exam domain (D1–D5), see the concept list, click **▶ Start practice session** |
| 📝 **Practice** | Read the question, select A/B/C/D, click Submit, read the explanation with citations |
| 📊 **Progress** | Click Refresh to see per-domain mastery, active misconceptions, and recent history |
| 🏗️ **Architecture** | Technical reference — agents, data flows, knowledge base, schema |
| 💬 **Q&A** | Ask any free-form question; answers are grounded in the corpus only |

**Suggested study path:** Start with **D1 Agentic Architecture (27% weight)** — highest exam value. Once D1 mastery reaches ~3.0, move to D3 Claude Code (20%) and D4 Prompt Engineering (20%).

---

## Project structure

```
Capstone-AIBootcamp/
├── README.md                       ← you are here
├── CLAUDE.md                       ← agent-facing project context (≤200 lines)
├── PLAN.md                         ← What We Built / Improved / Future Roadmap
├── ai-tutor-spec-v2.md             ← full functional + technical spec (closed decisions)
├── pyproject.toml                  ← dependencies + setuptools config
├── .env.example                    ← env var template
│
├── ai_tutor/                       ← main package
│   ├── config.py                   ← pydantic-settings singleton
│   ├── models.py                   ← Pack, Question, GradingResult, StudentModel, TutorState
│   ├── packs/loader.py             ← Pack YAML loading + validation
│   ├── ingestion/                  ← fetch → extract → chunk (A2) → embed → index
│   ├── rag/retriever.py            ← Pack + domain-scoped cosine retrieval
│   ├── agents/                     ← examiner, grader, coach, explainer, qna, updater
│   │   └── prompts/                ← system prompts as Markdown files
│   ├── graph/                      ← LangGraph state + tutor_graph (11 nodes)
│   ├── student_model/              ← atomic JSON store + rule-based updater
│   └── ui/app.py                   ← Gradio 6 Blocks — 6 tabs, custom CSS, generators
│
├── packs/cca-f/                    ← CCA-F Certification Pack (YAML + Markdown)
│   ├── pack.yaml                   ← domains, weights, exam metadata
│   ├── corpus_urls.yaml            ← URLs to ingest, grouped by domain and tier
│   ├── curriculum.yaml             ← 31 concepts with prerequisite graph
│   └── style_notes.md              ← Examiner style guidance
│
├── data/                           ← runtime state (gitignored)
│   ├── chroma/                     ← ChromaDB SQLite + vector files
│   ├── students/                   ← student model JSON per student × pack
│   ├── raw/                        ← cached fetched documents
│   └── manifests/                  ← per-pack ingestion manifests
│
├── scripts/
│   ├── ingest_pack.py              ← orchestrate the full ingestion pipeline
│   ├── practice_cli.py             ← terminal practice loop (smoke test)
│   ├── inspect_chroma.py           ← spot-check indexed chunks
│   └── reset_student.py            ← wipe student progress
│
├── tests/                          ← 18 pytest tests (unit + integration)
└── docs/
    ├── IMPLEMENTATION_PLAN.md      ← day-by-day execution plan
    └── DESIGN_REVIEW_2026-05-29.md ← UI design review report
```

---

## Add a new Certification Pack

The platform is **certification-agnostic** — adding a new exam takes **zero code changes**:

```bash
# 1. Create the Pack directory
mkdir -p packs/aws-saa/

# 2. Author the four YAML/Markdown files
#    - pack.yaml         (domains, weights, exam format)
#    - corpus_urls.yaml  (Tier 1 + Tier 2 URLs by domain)
#    - curriculum.yaml   (concept list with prerequisite graph)
#    - style_notes.md    (Examiner style guidance for this cert)

# 3. Ingest the corpus
python scripts/ingest_pack.py --pack aws-saa

# 4. Switch the default pack in .env
echo "DEFAULT_PACK_ID=aws-saa" >> .env

# 5. Launch — the same agents, RAG pipeline, and UI now teach AWS Solutions Architect
python -m ai_tutor.ui.app
```

The Pack format is documented in [`ai-tutor-spec-v2.md`](./ai-tutor-spec-v2.md) §12.

---

## Testing

```bash
# Fast tests (no LLM calls — runs in ~10s)
pytest tests/test_updater.py tests/test_retriever.py -v

# Full suite including live LLM integration tests (~2 min)
pytest tests/ -v

# Lint
ruff check ai_tutor tests
```

Test inventory:
- `test_packs.py` — Pack YAML validation
- `test_retriever.py` — pack/domain-scoped retrieval (4 tests)
- `test_examiner.py` — Question schema, citation validity (4 tests)
- `test_grader.py` — verdict, misconception, citation grounding (3 tests)
- `test_updater.py` — mastery delta rules, misconception counting (7 tests, no LLM)
- `test_integration.py` — end-to-end LangGraph flows (5 tests)

---

## Documentation

| Document | Purpose |
|---|---|
| [`ai-tutor-spec-v2.md`](./ai-tutor-spec-v2.md) | Full functional + technical specification (~1,580 lines). Closed decisions are marked. |
| [`PLAN.md`](./PLAN.md) | What We Built · What We Improved · Future Roadmap |
| [`CLAUDE.md`](./CLAUDE.md) | Agent-facing project context — stack, conventions, commands (under 200 lines) |
| [`docs/IMPLEMENTATION_PLAN.md`](./docs/IMPLEMENTATION_PLAN.md) | Day-by-day build plan with verification gates |
| [`docs/DESIGN_REVIEW_2026-05-29.md`](./docs/DESIGN_REVIEW_2026-05-29.md) | UI design audit and improvements |

---

## Roadmap

### V2 features (post-bootcamp)

The B2 student model schema reserves `concepts` and `learning_style_hints` fields
specifically so V2 lands as an **additive extension**, not a rewrite.

1. **Exam readiness score** — `sum(domain.aggregate_mastery × domain.weight)` → 0–5 score in Progress tab
2. **Adaptive study plan** — 7-day plan generated from current mastery gaps
3. **Curriculum graph traversal** — enforce prerequisite ordering before testing advanced concepts
4. **Learning style detection** — infer `prefers_examples`, `absorbs_code_fast` from session patterns
5. **Second Certification Pack** — AWS Cloud Practitioner or GCP ACE to demonstrate genericity
6. **LangSmith SSL fix** — install corporate CA for clean traces

### Known limitations

- **6 of 39 corpus URLs failed** during ingestion (React SPA pages). Replace with GitHub raw markdown equivalents for missing content.
- **`partial` evidence = 0 mastery change** by design — a wrong answer with "right domain, wrong mechanism" doesn't reward mastery. This is correct per spec but can look like "nothing happened" in early sessions.
- **Mobile**: answer pills wrap awkwardly below 480px — fix planned via `flex-direction: column` media query.
- **LangSmith SSL errors** on machines with corporate certificates (errors are suppressed; tracing falls back to off).

---

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | All 6 agents |
| `OPENAI_API_KEY` | ✅ | Embeddings (`text-embedding-3-small`) |
| `LANGSMITH_API_KEY` | Optional | LangGraph trace upload |
| `LANGSMITH_PROJECT` | Optional | LangSmith project name (default: `ai-tutor`) |
| `LANGSMITH_TRACING` | Optional | `true` / `false` |
| `CHROMA_PERSIST_DIR` | Default | `./data/chroma` |
| `STUDENT_MODELS_DIR` | Default | `./data/students` |
| `PACKS_DIR` | Default | `./packs` |
| `DEFAULT_PACK_ID` | Default | `cca-f` |
| `DEFAULT_STUDENT_ID` | Default | `default` |
| `MAX_SESSION_TOKENS` | Default | `50000` |

---

## Author

**Christian Bobadilla** — Capstone project for the BCG / Anthropic AI Bootcamp.

Built end-to-end with Claude Code as the development partner. Design direction:
"Chalk & Coral" — crisp white base, jet-black navigation, vivid coral-orange accent.

---

## License

To be determined. Code intended for personal study and capstone demonstration purposes.
