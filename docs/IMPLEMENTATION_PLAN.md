# AI Tutor — Implementation Plan

> Companion to [`ai-tutor-spec-v2.md`](../ai-tutor-spec-v2.md). Master version lives at `~/.claude/plans/context-i-want-to-frolicking-dove.md`. This in-project copy is what you and Claude Code work from day-to-day.

## Goal

Ship MVP + V1 of the AI Tutor in a 2-3 week capstone window, then take the CCA-F exam.

## Locked-in decisions (closed in Q&A, see spec v2 Appendix C)

| Decision | Choice |
|---|---|
| Slice strategy | MVP → V1 → V2 incremental |
| First domain (MVP) | D1 — Agentic Architecture & Orchestration (27%) |
| Chunking (Decision A) | A2 — markdown header-aware, ≤1000 token sections |
| Student Model (Decision B) | B2 — domain-grouped, B3-compat reserves |
| Embeddings | OpenAI `text-embedding-3-small` |
| Observability | LangSmith ON from MVP |
| Live agent sidebar | V1 only (skip in MVP) |
| Pack scope | CCA-F only; second Pack = post-bootcamp |

## Pre-week 0 (DONE)

- ✅ Repo scaffolded: `src/`, `data/`, `packs/`, `tests/`
- ✅ `pyproject.toml`, `.env.example`, `.gitignore`, `README.md`
- ✅ `.venv` created (Python 3.11.15), `pip install -e ".[dev]"` succeeded
- ✅ All deps import (anthropic 0.105.2, langgraph 1.2.2, chromadb 1.5.9, gradio 6.15.2)
- ⚠️ Pending fix: `pyproject.toml:45` `include = ["src*"]` → rename `src/` → `ai_tutor/` and update to `["ai_tutor*"]`

## Week 1 — Ship MVP (Slice 1)

### Day 1 — Foundation

- [ ] Rename `src/` → `ai_tutor/`; update `pyproject.toml` (`include = ["ai_tutor*"]`); re-run `pip install -e ".[dev]"` to refresh editable install.
- [ ] `cp .env.example .env`; populate `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT=ai-tutor`, `LANGSMITH_TRACING=true`.
- [ ] Implement `ai_tutor/config.py` using `pydantic-settings` to load `.env`. Fields per spec v2 §13.
- [ ] Implement `ai_tutor/models.py` — Pydantic models: `Pack`, `Domain`, `Concept`, `Question`, `GradingResult`, `Citation`, `StudentModel` (B2 schema), `TutorState`.
- [ ] Verify: `python -c "from ai_tutor.config import settings; print(settings.anthropic_api_key[:10])"` prints first 10 chars without error.

### Day 2 — Pack files + ingestion pipeline (D1 only)

- [ ] Author `packs/cca-f/pack.yaml` per spec v2 §12.2.
- [ ] Author `packs/cca-f/corpus_urls.yaml` — D1 URLs from spec v2 §9.3 (7 URLs) + 2-3 Tier 2 supplementary (Anthropic cookbook agent patterns).
- [ ] Author `packs/cca-f/curriculum.yaml` — D1 concepts (5-8 entries: `agentic_loop_stop_reason`, `hub_and_spoke_orchestration`, `subagent_context_isolation`, `tool_use_loop`, etc.).
- [ ] Author `packs/cca-f/style_notes.md` — scenario-based, single-mechanism wrong answers, no trivia.
- [ ] Implement `ai_tutor/packs/loader.py` — `load_pack(pack_id) -> Pack`; validates YAML against Pydantic.
- [ ] Implement `ai_tutor/ingestion/fetch.py` — HTTP with 1s delay; `raw.githubusercontent.com` for GitHub URLs; nbformat for `.ipynb`.
- [ ] Implement `ai_tutor/ingestion/extract.py` — `trafilatura` HTML → markdown; notebook concat (markdown + code cells fenced).
- [ ] Implement `ai_tutor/ingestion/chunk.py` — `MarkdownHeaderTextSplitter` → `RecursiveCharacterTextSplitter(1000, 100)`; store `section_path` in metadata.
- [ ] Implement `ai_tutor/ingestion/embed.py` — OpenAI `text-embedding-3-small`; batch 50; `tenacity` retry exp backoff.
- [ ] Implement `ai_tutor/ingestion/index.py` — ChromaDB persistent client; collection `pack_cca-f`; metadata per spec v2 §9.4.
- [ ] Implement `scripts/ingest_pack.py --pack cca-f --domain D1` — orchestrates fetch → extract → chunk → embed → index.
- [ ] Run: `python scripts/ingest_pack.py --pack cca-f --domain D1`. Expected: ~80-150 chunks, manifest written to `data/manifests/cca-f_D1_v1.json`.

### Day 3 — RAG retriever + Examiner agent

- [ ] Implement `ai_tutor/rag/retriever.py` — `retrieve(pack_id, domain, concept=None, k=5) -> list[Chunk]`; metadata filtering on `pack_id` + `domain`.
- [ ] Implement `ai_tutor/agents/prompts/examiner.md` — verbatim from spec v2 §8.1 system prompt.
- [ ] Implement `ai_tutor/agents/examiner.py`:
  - Load prompt from file at module import.
  - Anthropic SDK `claude-sonnet-4-6`.
  - Use prompt caching on the system prompt (ephemeral cache_control).
  - Output is a Pydantic-validated `Question`.
  - `tenacity` retry (3 attempts) on schema validation failure.
- [ ] Write `tests/test_examiner.py` — 3 questions on D1 concepts using fixture chunks; assert schema valid, 4 options, exactly one correct, citations all resolve to URLs in fixture metadata.
- [ ] **Manual quality gate**: generate 10 D1 questions, review for (a) faithfulness, (b) scenario quality, (c) distractor anti-patterns. If <7/10 acceptable → fall back to D4 (rerun day 2 for D4, ~3 hours).

### Day 4 — Grader agent + CLI end-to-end

- [ ] Implement `ai_tutor/agents/prompts/grader.md` — verbatim from spec v2 §8.2.
- [ ] Implement `ai_tutor/agents/grader.py` — same patterns as Examiner; output is Pydantic `GradingResult`.
- [ ] Write `tests/test_grader.py` — grade 3 correct + 3 incorrect answers; assert misconception identified on incorrect, citations present, verdict matches.
- [ ] Implement `scripts/practice_cli.py` — terminal loop: prompt for concept → Examiner → display question → read input A/B/C/D → Grader → display explanation + citations → repeat until quit.
- [ ] Verify: `python scripts/practice_cli.py` runs a 3-question session end-to-end in terminal.

### Day 5 — Gradio UI MVP

- [ ] Implement `ai_tutor/ui/app.py` per spec v2 §6.3:
  - `gr.Blocks(title="AI Tutor")`.
  - Header: `Studying: CCA-F • Domain: D1 • Corpus v1`.
  - Tab "Home": domain dropdown (D1 only for MVP) + "Start practice session".
  - Tab "Practice": question markdown + radio (A/B/C/D) + submit + feedback markdown + "Next question".
  - Tab "Progress": session stats (questions seen, correct rate, current domain).
  - `gr.State` holds `session_state` (question_id, answers, correct_count) and `pack_state`.
- [ ] LangSmith env vars wired (`LANGSMITH_TRACING=true`, project=`ai-tutor`).
- [ ] Verify: `python -m ai_tutor.ui.app` launches on `http://127.0.0.1:7860`. Run 5-question session end-to-end, click every citation URL.
- [ ] **MVP DONE**: D1 only, session-only memory, demoable end-to-end.

## Week 2 — Ship V1 (Slice 2)

### Day 6-7 — Full corpus ingestion + remaining agents

- [ ] Add D2, D3, D4, D5 URLs to `packs/cca-f/corpus_urls.yaml` (from spec v2 §9.3).
- [ ] Add D2-D5 concepts to `packs/cca-f/curriculum.yaml` (~5-8 each, ~30 total).
- [ ] Run full ingest: `python scripts/ingest_pack.py --pack cca-f` (no `--domain` flag → all). Expected: ~600 chunks.
- [ ] Implement `ai_tutor/agents/{coach,explainer,qna,updater}.py` with prompts from spec v2 §8.3, §8.4, §8.5, §8.6 verbatim.
- [ ] Updater is rule-based deterministic (mastery deltas + misconception increment); Haiku 4.5 only invoked for ambiguous misconception ID matching.

### Day 8 — Student Model + LangGraph orchestration

- [ ] Implement `ai_tutor/student_model/schema.py` — Pydantic B2 schema with B3-compat reserves:
  ```python
  class DomainStats(BaseModel):
      weight: float
      aggregate_mastery: float = 0.0
      concepts: dict[str, ConceptMastery] = {}

  class StudentModel(BaseModel):
      student_id: str
      pack_id: str
      domains: dict[str, DomainStats]
      misconceptions: dict[str, Misconception] = {}
      session_history: list[SessionEvent] = []
      # B3-compat reserves (None in V1; populated post-bootcamp)
      concepts: dict | None = None
      learning_style_hints: dict | None = None
  ```
- [ ] Implement `ai_tutor/student_model/store.py` — `load(student_id, pack_id)`, `save(model)` → JSON file at `data/students/{student_id}_{pack_id}.json`. Atomic write (write to tmp then rename).
- [ ] Implement `ai_tutor/student_model/updater.py` — `apply(grading_result, student_model) -> StudentModel`. Implements deterministic rules from §8.6; LLM-assisted misconception ID matching as fallback only.
- [ ] Implement `ai_tutor/graph/state.py` — `TutorState` TypedDict per spec v2 §7.4.
- [ ] Implement `ai_tutor/graph/tutor_graph.py` — LangGraph wiring of nodes: `load_pack_descriptor` → `classify_intent` → branches (practice/qna/explain/dashboard) → `output`.

### Day 9 — Q&A + dashboard + live agent sidebar

- [ ] Add Tab "Q&A" to `ai_tutor/ui/app.py` — `gr.Chatbot()`; submit wired to Q&A agent through LangGraph.
- [ ] Enrich Tab "Progress":
  - `gr.BarPlot` of per-domain mastery (5 bars, 0-5 scale).
  - `gr.Markdown` list of top 5 active misconceptions.
  - `gr.DataFrame` of last 20 questions with verdict.
- [ ] Implement live agent sidebar (right rail) — uses LangGraph `stream()` to surface current node + retrieved chunks + mastery delta after each grade.

### Day 10 — Integration tests + polish

- [ ] Write `tests/test_integration.py` — load Pack → 5-question session via LangGraph → assert student_model.json updated correctly + all citations resolve.
- [ ] Write `tests/test_packs.py`, `test_ingestion.py`, `test_retriever.py`, `test_updater.py`.
- [ ] Manual QA: 20-question session in UI; every citation URL clicks through.
- [ ] **V1 DONE**: all 5 domains, persistent student model, Q&A, dashboard, live sidebar.

## Week 3 — Demo prep + buffer

### Day 11-12 — Capstone demo prep

- [ ] Write 5-minute demo script: launch app → practice session → see citations → switch to Q&A → ask about MCP → view dashboard.
- [ ] Practice live LangSmith trace walkthrough (open most recent session trace, narrate the graph execution).
- [ ] Author `docs/PLATFORM_GENERICITY.md` — step-by-step "how to add a new Pack" with AWS Cloud Practitioner stub as illustrative example.

### Day 13-14 — Stretch / buffer

**If on schedule:**
- [ ] V2 Plan Generator stub — emits 7-day study plan from current mastery (narrative output, not adaptive). Demo value high, code cost low.

**If behind:**
- [ ] Fix P0 bugs surfaced in manual QA.
- [ ] Rewrite README for capstone audience.
- [ ] Polish UI: empty states, error messages, loading spinners.

### Day 15 — Capstone presentation

- [ ] Final dry run (full demo end-to-end).
- [ ] Submit deliverables.

## Verification gates

### After day 5 (MVP)

```bash
source .venv/bin/activate
pytest tests/test_examiner.py tests/test_grader.py -v       # all pass
python scripts/ingest_pack.py --pack cca-f --domain D1      # ~80-150 chunks
python scripts/inspect_chroma.py --pack cca-f               # 5 sample chunks shown
python scripts/practice_cli.py                              # 3-question terminal session
python -m ai_tutor.ui.app                                   # Gradio on http://127.0.0.1:7860
```
LangSmith trace at https://smith.langchain.com/projects/ai-tutor.

### After day 10 (V1)

```bash
pytest tests/ -v                                            # full suite passes
python scripts/ingest_pack.py --pack cca-f                  # ~600 chunks (5 domains)
python -m ai_tutor.ui.app                                   # all 4 tabs working
cat data/students/default_cca-f.json | jq '.domains'        # 5 entries with aggregate_mastery
```

### Capstone demo readiness (day 14)

- Live demo: 10-question session start → finish in <10 minutes.
- Every citation URL resolves to real source.
- LangSmith trace shown live alongside.
- Pack YAML files opened in editor: "this is all you need to add a new cert."
- V2 roadmap shown: reserved schema fields, curriculum YAML graph fields, agent layer Pack-parameterization.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| D1 scenario quality is poor | Day 3 manual review gate. Fall back to D4 (~3hr pivot). |
| MVP slips past day 5 | Q&A + sidebar deferred to V1; MVP Progress tab is session stats only. |
| ChromaDB persistence flake | `scripts/reset_chroma.py` for clean restarts. Document in CLAUDE.md. |
| OpenAI embeddings rate limit | `tenacity` retry exp backoff in `embed.py`. Batch 50. |
| LangSmith free-tier limits | Disable tracing for bulk test runs via env flag. |
| Schema migration B2 → B3 | B2 schema reserves `concepts`, `learning_style_hints` as `None`. Additive only. |
| Cost overrun (>$0.50/session) | Prompt caching on system prompts day 4. Per-session token logger day 9. |

## Out of scope (post-bootcamp)

- V2 features: Plan Generator, learning style detection, readiness score, curriculum graph traversal.
- Second Certification Pack.
- Multi-user / authentication.
- Remote deployment.
- Mobile / responsive UI.
- Corpus drift detection.
