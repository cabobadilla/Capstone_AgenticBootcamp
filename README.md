# AI Tutor

Generic multi-agent AI Tutor platform built on Anthropic Claude + LangGraph + ChromaDB + Gradio. First validation Certification Pack: **CCA-F** (Claude Certified Architect — Foundations).

See `ai-tutor-spec.md` for the full functional and technical specification.

## Quickstart (macOS)

```bash
# 1. Create and activate the virtualenv (Python 3.11)
python3.11 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install --upgrade pip
pip install -e ".[dev]"

# 3. Configure environment
cp .env.example .env
# Edit .env and fill in API keys (ANTHROPIC_API_KEY, VOYAGE_API_KEY or OPENAI_API_KEY)

# 4. Ingest the CCA-F Pack (one-time)
python scripts/ingest_pack.py --pack cca-f

# 5. Launch the UI
python -m src.ui.app
```

## Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| Agent framework | LangGraph |
| LLM provider | Anthropic (Claude Sonnet 4.6 / Haiku 4.5) |
| Vector store | ChromaDB (local persistent) |
| Embeddings | Voyage AI `voyage-3` (preferred) or OpenAI `text-embedding-3-small` |
| Student Model storage | JSON files on local disk |
| Frontend | Gradio |
| Pack files | YAML + Markdown |
| Observability | LangSmith (optional) |
| Testing | pytest |

## Project layout

See Section 14 of `ai-tutor-spec.md`.
