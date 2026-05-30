# AI Tutor — Project Plan

> Last updated: 2026-05-29

---

## What We Built

An **adaptive, agentic AI Tutor** for the Claude Certified Architect — Foundations (CCA-F) exam.

### Platform (generic)
- **LangGraph orchestration** with 11 nodes: load_pack → route_intent → practice / Q&A / explain / dashboard branches
- **RAG pipeline**: fetch → markdown-header-aware chunking (A2) → OpenAI embeddings → ChromaDB (cosine similarity)
- **6 agents**: Examiner, Grader, Coach, Explainer, Q&A Agent, Student Model Updater
- **Persistent Student Model** (B2 schema, forward-compatible with B3): per-domain mastery scores, misconception tracking, session history
- **Certification Pack system**: zero-code extensibility via YAML files — agents are fully Pack-agnostic

### CCA-F Pack (demo)
- 5 exam domains (D1–D5) with 31 concepts and prerequisite graph
- 429 indexed chunks from 33 official Anthropic + MCP sources
- Corpus version: v1

### UI (Gradio 6)
- 6 tabs: Home · Topics · Practice · Progress · Architecture · Q&A
- Custom CSS — warm academic palette (stone/amber), IBM Plex Mono for exam content, Plus Jakarta Sans body
- Generator functions for 15-30s LLM calls (loading spinner, tab auto-switch to Practice)
- Styled answer pills, color-coded feedback panels, live agent trace sidebar

### Tests
- 18 pytest tests across 5 files (unit + live integration)
- All agents validated via `tool_use` structured output (schema-safe JSON, no escaping issues)

---

## What We Improved

### Architectural decisions closed during build
| Decision | Choice | Reason |
|---|---|---|
| Structured output | Anthropic `tool_use` (not JSON prompt) | LLM generates literal newlines inside JSON strings; tool_use bypasses this |
| Student Model schema | B2 (domain-grouped) | Trivial dashboard rendering; B3 fields reserved as `None` for V2 additive extension |
| Embeddings | OpenAI `text-embedding-3-small` | Key already available; marginal quality difference vs Voyage |
| First domain | D1 (27% weight) | Maximum exam-prep ROI despite being harder to ground than D4 |
| Chunking | A2 (markdown header-aware) | Anthropic docs have consistent `#/##/###` structure; semantic chunk boundaries improve D1 retrieval |

### UI design improvements (Ralph Loop — 2026-05-29)
| Round | Changes |
|---|---|
| Round 1 | Full CSS system (9,900+ chars): dark tab nav (amber active), question card (left amber border + mono font), answer pills (hover lift + amber selected), dark terminal sidebar, loading pulse animation, Google Fonts injection via `launch(head=...)` |
| Round 1 | Generator functions: `start_practice`, `submit_answer`, `next_question` — yield loading state immediately, then LLM result. Eliminates silent 15-30s waits. |
| Round 1 | Tab auto-switch: clicking **Start** yields `gr.update(selected="practice")` to navigate user automatically |
| Round 2 | Error state CSS (red-tinted cards), meaningful Progress empty states with task-specific guidance, Topics return-hint copy, Architecture tab `>` blockquote for platform claim |
| Round 2 | All Gradio 6 API compatibility issues fixed (removed `show_copy_button` kwarg) |

### Bugs fixed during development
- `KeyError: target_concept` in `run_grade` shortcut — fixed with `.get()` default
- JSON truncation in Grader (max_tokens=2048 wasn't enough for verbose markdown explanations) — fixed by switching to `tool_use`
- LangSmith SSL errors blocking Gradio response cycle — suppressed with `logging.CRITICAL` level + auto-disable on corporate SSL
- Gradio 6 `visible=True/False` toggle regression inside tabs — fixed by always-visible components + value-based toggling
- `build-with-claude/agents` page returning 160 chars (React SPA) — replaced with GitHub raw equivalents

---

## Future Roadmap (V2 — post-bootcamp)

### Feature backlog (by priority)
1. **Exam readiness score** — `sum(domain.aggregate_mastery × domain.weight)` for all domains → 0–5 score displayed in Progress tab header
2. **Adaptive study plan** — 7-day plan generated from current mastery gaps using Plan Generator agent; emits ordered concept list by (1-mastery)×weight
3. **Curriculum graph traversal** — use `prerequisites`/`leads_to` in curriculum.yaml to enforce concept ordering (don't test D1 advanced concepts until fundamentals are solid)
4. **Learning style hints** — infer `prefers_examples`, `absorbs_code_fast` from session history patterns; B3 `learning_style_hints` field already reserved in schema
5. **Second Certification Pack** — AWS Cloud Practitioner (or GCP ACE) stub to demonstrate platform genericity on-stage at capstone
6. **Readiness score in UI** — Progress tab header `Readiness: 3.2/5.0 · Estimated ready: Jun 14`

### Technical debt
- LangSmith SSL: install corporate CA or set `REQUESTS_CA_BUNDLE` for clean traces
- `src/` → `ai_tutor/` rename left `__pycache__` dirs from old package; safe to delete
- D1 concept names (not IDs) returned by Coach — Coach prompt should be more explicit about using concept IDs from curriculum
- Corpus: 6/39 URLs failed (React SPA or 404); add Playwright fallback for JS-rendered pages in ingestion
- `scripts/create_pack_skeleton.py` referenced in spec §14 but not yet implemented
- `tests/test_integration.py::test_student_model_persists_across_invocations` is slow (2 full LLM round-trips) — add a mock/fixture mode

### UX improvements
- Mobile: Practice tab answer pills wrap awkwardly below 480px — add `flex-direction: column` media query fix
- Q&A: Add a "suggested questions" chip list on first load to guide new users
- Progress: Visual mastery ring or gauge per domain (not just text bars) in Gradio BarPlot
- Architecture tab: Add a Mermaid diagram via `gr.HTML()` for the LangGraph flow
