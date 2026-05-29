# AI Tutor — Capstone Project

Agentic AI Tutor platform. First validation Pack: **CCA-F** (Anthropic Claude Certified Architect — Foundations).
Personal goal: pass CCA-F. Capstone goal: demonstrate a reusable, Pack-parameterized tutoring platform.

## Status
- Slice: MVP in progress (D1 — Agentic Architecture & Orchestration)
- Capstone deadline: 2-3 weeks from kickoff (bootcamp-driven)
- Spec v2 (closed decisions): [`ai-tutor-spec-v2.md`](./ai-tutor-spec-v2.md)
- Implementation plan (day-by-day): [`docs/IMPLEMENTATION_PLAN.md`](./docs/IMPLEMENTATION_PLAN.md)

## Tech stack
- **Python 3.11.15** in local `.venv`. Activate: `source .venv/bin/activate`.
- **LangGraph** for agent orchestration (Coach + 5 specialists per spec v2 §7).
- **Anthropic Claude** — `claude-sonnet-4-6` for reasoning agents; `claude-haiku-4-5` for the Updater's ambiguous-misconception matching only.
- **ChromaDB** (local persistent at `data/chroma/`). One collection per Pack: `pack_<id>`.
- **OpenAI `text-embedding-3-small`** for embeddings (closed v2 — preferred over Voyage).
- **Gradio Blocks** for the UI (Home / Practice / Q&A / Progress tabs).
- **LangSmith** for tracing — ON from MVP day 1.
- Supporting: `pydantic` v2, `pydantic-settings`, `loguru`, `trafilatura`, `nbformat`, `pyyaml`, `tenacity`, `pytest`, `pytest-asyncio`, `ruff`.

## Source layout
- `ai_tutor/` — main package (rename of original `src/`; update `pyproject.toml:45` to `include = ["ai_tutor*"]`)
  - `config.py` — `pydantic-settings` loading `.env`
  - `models.py` — Pydantic models: `Pack`, `Question`, `GradingResult`, `StudentModel`, `TutorState`
  - `packs/loader.py` — load and validate Pack YAMLs
  - `ingestion/{fetch,extract,chunk,embed,index}.py` — pipeline
  - `rag/retriever.py` — Pack + domain filtered queries
  - `student_model/{schema,store,updater}.py` — B2 schema, JSON store, rule-based updater
  - `agents/{examiner,grader,coach,explainer,qna,updater}.py` + `prompts/*.md`
  - `graph/{state,tutor_graph}.py` — LangGraph wiring
  - `ui/app.py` — Gradio entry point
  - `curriculum/graph.py` — V2 stub (post-bootcamp)
- `packs/cca-f/{pack,corpus_urls,curriculum}.yaml` + `style_notes.md`
- `data/{chroma,students,raw,manifests}/` — runtime state
- `scripts/{ingest_pack,practice_cli,inspect_chroma,reset_student,reset_chroma}.py`
- `tests/test_*.py` + `tests/fixtures/`

## Closed decisions (spec v2 Appendix C)
- Slice strategy: MVP → V1 → V2 incremental (V2 is post-bootcamp)
- First domain (MVP): **D1** (highest exam weight, 27%)
- Chunking (Decision A): **A2** — markdown header-aware → size-bound ≤1000 tokens
- Student Model (Decision B): **B2** — domain-grouped, B3-compatible reserves (`concepts`, `learning_style_hints` reserved as `None`)
- Embeddings: OpenAI `text-embedding-3-small`
- Observability: LangSmith from MVP
- Live agent sidebar: V1 only (deferred from MVP to protect ship date)
- Pack scope: CCA-F only; second Pack is post-bootcamp

## Conventions
- **Prompts live in `ai_tutor/agents/prompts/*.md`** — loaded at module import. Never inline a prompt in Python.
- **Agent outputs are structured JSON**, validated by Pydantic. Use `tenacity` to retry on schema failures (3 attempts max).
- **Citations may only reference URLs present in retrieved chunk metadata.** No invented URLs ever.
- **One student model JSON file per `student_id × pack_id`** at `data/students/{student_id}_{pack_id}.json`. Atomic writes (tmp file + rename).
- **ChromaDB collection naming**: `pack_<pack_id>` (e.g., `pack_cca-f`).
- **Prompt caching ON** for system prompts (Anthropic ephemeral `cache_control`) to keep per-session cost <$0.50 (NF-06).
- **Code comments**: add short inline comments at key decision points — WHY a parameter was chosen, WHY a branch exists, WHY a specific API call pattern is used. Comment the non-obvious; skip the self-explanatory. Focus on: agent invocation patterns, LangGraph node wiring, ChromaDB metadata filter syntax, Pydantic model design rationale, and any workaround or performance optimization.

## Common commands

```bash
# Environment
source .venv/bin/activate

# Quality gates
pytest tests/ -v
ruff check ai_tutor tests

# Pack ingestion
python scripts/ingest_pack.py --pack cca-f --domain D1   # MVP scope
python scripts/ingest_pack.py --pack cca-f               # V1 (all domains)
python scripts/inspect_chroma.py --pack cca-f            # sample 5 chunks

# Run
python scripts/practice_cli.py                            # terminal MVP loop
python -m ai_tutor.ui.app                                 # Gradio on :7860

# Reset
python scripts/reset_student.py --student default --pack cca-f
python scripts/reset_chroma.py --pack cca-f               # drops collection
```

## How to add a new Certification Pack (platform genericity)
1. `mkdir packs/<pack_id>/`
2. Author `pack.yaml`, `corpus_urls.yaml`, `curriculum.yaml`, `style_notes.md` per spec v2 §12.
3. `python scripts/ingest_pack.py --pack <pack_id>`
4. Set `DEFAULT_PACK_ID=<pack_id>` in `.env` (or use the UI Pack selector in V2).
5. **Zero code changes** — agents, RAG, schema are all Pack-parameterized.

## Environment variables (see `.env.example`)
```
ANTHROPIC_API_KEY=...        # required
OPENAI_API_KEY=...           # required (embeddings)
LANGSMITH_API_KEY=...        # required from MVP
LANGSMITH_PROJECT=ai-tutor
LANGSMITH_TRACING=true
CHROMA_PERSIST_DIR=./data/chroma
STUDENT_MODELS_DIR=./data/students
PACKS_DIR=./packs
DEFAULT_PACK_ID=cca-f
DEFAULT_STUDENT_ID=default
```

## Non-goals (current scope)
- V2 features (adaptive plan, learning style, readiness score, curriculum graph) — post-bootcamp.
- Multi-user / authentication.
- Deployment beyond local macOS.
- Real-time corpus drift detection.
- Mobile / responsive UI.

## Skill routing (gstack — defer to global rules)
Standard routing per `~/.claude/CLAUDE.md`. Most relevant for this project:
- New product ideas / scope expansion → `/office-hours` then `/plan-ceo-review`.
- Architecture decisions before coding → `/plan-eng-review`.
- Bugs / errors → `/investigate`.
- Testing the running UI → `/qa` or `/qa-only`.
- Pre-merge code review → `/review`.
- Ship/deploy → `/ship` then `/land-and-deploy`.
- Save progress → `/context-save`. Resume later → `/context-restore`.

## Key references
- Original spec (v1, frozen for reference): `ai-tutor-spec.md`
- Closed spec (v2 — work from this): `ai-tutor-spec-v2.md`
- Day-by-day plan: `docs/IMPLEMENTATION_PLAN.md`
- Master plan (Claude Code plan file): `~/.claude/plans/context-i-want-to-frolicking-dove.md`
