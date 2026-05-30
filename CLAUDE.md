# AI Tutor — Capstone Project

Agentic AI Tutor for the **CCA-F** (Claude Certified Architect — Foundations) exam.
Personal goal: pass CCA-F. Capstone goal: demonstrate a generic, Pack-parameterized tutoring platform.

## Status — 2026-05-29
- **Slice**: V1 complete (MVP + full 5-domain corpus + LangGraph orchestration + Gradio V1.2 UI)
- **Active Pack**: CCA-F · 429 chunks · 5 domains · 31 concepts
- **UI version**: 1.2 — custom CSS system, generator loading states, tab auto-switch, amber/stone palette
- **Spec**: `ai-tutor-spec-v2.md` (all decisions closed)
- **Plan**: `docs/IMPLEMENTATION_PLAN.md`

## Tech stack
- **Python 3.11** (.venv). Activate: `source .venv/bin/activate`
- **LangGraph** — 11-node stateful graph (practice / Q&A / explain / dashboard branches)
- **Anthropic** — Claude Sonnet 4.6 (primary) + Haiku 4.5 (Updater misconception matching)
- **ChromaDB** — local persistent, `data/chroma/`, collection `pack_cca-f`
- **OpenAI `text-embedding-3-small`** — embeddings (closed decision v2)
- **Gradio 6.15** — Blocks UI, 6 tabs, generator functions, custom CSS
- **LangSmith** — tracing (enabled when `LANGSMITH_TRACING=true`, suppressed on SSL error)
- Supporting: `pydantic v2`, `pydantic-settings`, `loguru`, `trafilatura`, `nbformat`, `tenacity`, `pytest`, `ruff`

## Source layout
```
ai_tutor/
  config.py            pydantic-settings singleton
  models.py            Pack, Question, GradingResult, StudentModel (B2+B3 reserves), TutorState, Chunk
  packs/loader.py      load_pack(), load_corpus_urls(), load_style_notes()
  ingestion/           fetch → extract → chunk (A2) → embed → index
  rag/retriever.py     pack+domain-scoped cosine retrieval
  agents/              examiner, grader, coach, explainer, qna, updater + prompts/*.md
  graph/               state.py (TutorGraphState TypedDict), tutor_graph.py (LangGraph)
  student_model/       store.py (atomic JSON), updater.py (rule-based + Haiku)
  ui/app.py            Gradio 6 Blocks — 6 tabs, CSS v1.2, generator loading states
```

## Closed decisions (spec v2 Appendix C)
| Decision | Choice |
|---|---|
| Slice strategy | MVP → V1 → V2 incremental (V2 post-bootcamp) |
| First domain | D1 Agentic Architecture (27% weight) |
| Chunking | A2 — MarkdownHeaderTextSplitter → RecursiveCharacterTextSplitter (≤1000 tokens) |
| Student Model | B2 domain-grouped, B3-compatible reserves (`concepts`, `learning_style_hints` = None) |
| Embeddings | OpenAI `text-embedding-3-small` |
| Structured output | Anthropic `tool_use` (avoids JSON string escaping failures) |
| Observability | LangSmith from MVP (suppressed on SSL error) |

## Conventions
- **Prompts** in `ai_tutor/agents/prompts/*.md` — loaded at module import, never inlined
- **Agent output** via `tool_use` (Examiner + Grader) or text (Explainer, Q&A)
- **Citations** reference only URLs present in retrieved chunk metadata
- **Student model** stored as atomic JSON: `data/students/{student_id}_{pack_id}.json`
- **ChromaDB collection** naming: `pack_<pack_id>` (e.g., `pack_cca-f`)
- **Prompt caching** (Anthropic `ephemeral`) on all system prompts
- **Code comments** on non-obvious WHY (not WHAT): agent patterns, LangGraph wiring, ChromaDB filter syntax, mastery delta rules

## Common commands
```bash
source .venv/bin/activate
pytest tests/ -v                                        # 18 tests (fast + integration)
ruff check ai_tutor tests                               # lint
python scripts/ingest_pack.py --pack cca-f             # full ingestion
python scripts/ingest_pack.py --pack cca-f --domain D1 # single domain
python scripts/inspect_chroma.py --pack cca-f          # spot-check chunks
python scripts/practice_cli.py                         # terminal session
python -m ai_tutor.ui.app                              # Gradio on :7860
python scripts/reset_student.py                        # wipe progress
```

## How to add a new Certification Pack (zero code)
1. `mkdir packs/<id>/` → author `pack.yaml`, `corpus_urls.yaml`, `curriculum.yaml`, `style_notes.md`
2. `python scripts/ingest_pack.py --pack <id>`
3. Set `DEFAULT_PACK_ID=<id>` in `.env` (or UI Pack selector in V2)

## Environment variables (`.env`)
```
ANTHROPIC_API_KEY=...      # required
OPENAI_API_KEY=...         # required (embeddings)
LANGSMITH_API_KEY=...      # required for tracing (set LANGSMITH_TRACING=false to disable)
LANGSMITH_PROJECT=ai-tutor
LANGSMITH_TRACING=true
CHROMA_PERSIST_DIR=./data/chroma
STUDENT_MODELS_DIR=./data/students
PACKS_DIR=./packs
DEFAULT_PACK_ID=cca-f
DEFAULT_STUDENT_ID=default
MAX_SESSION_TOKENS=50000
```

## Non-goals (current scope — V2 is post-bootcamp)
- Adaptive study plan, learning style detection, exam readiness score, curriculum graph
- Multi-user / authentication
- Deployment beyond local macOS
- Real-time corpus drift detection
- Second Certification Pack (design is Pack-parameterized; second Pack = YAML + ingest only)

## Next Steps (V2 roadmap)
1. **Plan Generator** — emits a 7-day study plan from current mastery map (Updater B3 fields are already reserved)
2. **Exam readiness score** — computed from per-domain aggregate_mastery × domain_weight
3. **Learning style hints** — inferred from session_history patterns (prefers_examples, absorbs_code_fast)
4. **Curriculum graph traversal** — use `prerequisites`/`leads_to` in curriculum.yaml for ordered study paths
5. **Second Pack** — AWS Cloud Practitioner or GCP ACE stub to demonstrate platform genericity on stage
6. **LangSmith SSL fix** — install corporate CA or configure `REQUESTS_CA_BUNDLE` for clean traces

## Skill routing (gstack)
Standard routing per `~/.claude/CLAUDE.md`. For this project:
- Bugs/unexpected behaviour → `/investigate`
- UI testing → `/qa` or `/qa-only`
- Pre-merge review → `/review`
- Save session progress → `/context-save` → `/context-restore`
