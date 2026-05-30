"""
AI Tutor UI — V1.2 (design overhaul)

Design direction: "Focused Learner" — warm academic SaaS aesthetic.
Palette: stone/cream base · amber accent · IBM Plex Mono for exam content.

Changes from V1.1:
- Custom CSS system (typography, colors, cards, pills, sidebar)
- Generator functions: immediate loading feedback during 15-30s LLM calls
- Tab auto-switch: clicking Start navigates to Practice automatically
- elem_id on every key component for precise CSS targeting
- Color-coded feedback panels (green/red border + background)
- Styled answer options as exam choice pills
- Guided empty states instead of grey italic text
"""

import json
import os
from pathlib import Path

import gradio as gr
from loguru import logger

from ai_tutor.config import settings
from ai_tutor.graph.tutor_graph import run_dashboard, run_grade, run_practice, run_qna
from ai_tutor.models import Pack
from ai_tutor.packs.loader import load_pack

# ── LangSmith (suppress SSL noise) ───────────────────────────────────────────
_langsmith_enabled = (
    bool(settings.langsmith_api_key)
    and not settings.langsmith_api_key.startswith("your-")
    and str(settings.langsmith_tracing).lower() == "true"
)
os.environ["LANGSMITH_TRACING"] = "true" if _langsmith_enabled else "false"
os.environ.setdefault("LANGSMITH_PROJECT", settings.langsmith_project)
if settings.langsmith_api_key:
    os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)
import logging as _logging
_logging.getLogger("langsmith").setLevel(_logging.CRITICAL)

# ── Data loaded once at startup ───────────────────────────────────────────────
_pack: Pack = load_pack(settings.default_pack_id)
_DOMAIN_CHOICES = [(f"{d.id} — {d.name} ({d.weight:.0%})", d.id) for d in _pack.domains]
_DOMAIN_MAP = {d.id: d for d in _pack.domains}
_ALL_CONCEPTS = {d.id: [c for c in _pack.concepts if c.domain == d.id] for d in _pack.domains}


def _load_manifest() -> dict:
    for pat in [
        f"data/manifests/{settings.default_pack_id}_all_{_pack.corpus_version}.json",
        *[str(p) for p in Path("data/manifests").glob(f"{settings.default_pack_id}_*.json")],
    ]:
        p = Path(pat)
        if p.exists():
            return json.loads(p.read_text())
    return {}


_manifest = _load_manifest()

# ══════════════════════════════════════════════════════════════════════════════
# CUSTOM CSS  — Warm Academic / Professional SaaS
# ══════════════════════════════════════════════════════════════════════════════
_CSS = """
/* ── Foundation ─────────────────────────────────────────────────────────── */
.gradio-container {
  background: #fafaf9 !important;
  font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif !important;
  max-width: 1280px !important;
  margin: 0 auto !important;
}

footer, .built-with, footer.svelte-1ax1toq { display: none !important; }

/* ── Tab Navigation — dark bar with amber active ─────────────────────────── */
.tab-nav {
  background: #1c1917 !important;
  padding: 6px 8px !important;
  border-radius: 0 !important;
  border: none !important;
  gap: 2px !important;
  flex-wrap: wrap !important;
}
.tab-nav button {
  background: transparent !important;
  color: #a8a29e !important;
  border: none !important;
  border-radius: 6px !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  padding: 7px 14px !important;
  transition: all 0.15s !important;
  letter-spacing: 0.01em !important;
}
.tab-nav button:hover { background: rgba(255,255,255,0.08) !important; color: #e7e5e4 !important; }
.tab-nav button.selected { background: #f59e0b !important; color: #1c1917 !important; font-weight: 700 !important; }

/* ── Primary / Secondary buttons ─────────────────────────────────────────── */
button.primary { background: #1c1917 !important; color: #fafaf9 !important; border: none !important;
  border-radius: 8px !important; font-weight: 600 !important; font-size: 14px !important;
  padding: 10px 22px !important; transition: background 0.15s !important; letter-spacing: 0.01em !important; }
button.primary:hover { background: #292524 !important; }
button.primary:disabled { background: #a8a29e !important; cursor: not-allowed !important; }
button.secondary { background: #ffffff !important; color: #1c1917 !important;
  border: 1.5px solid #e7e5e4 !important; border-radius: 8px !important; font-weight: 500 !important;
  font-size: 14px !important; padding: 9px 20px !important; transition: all 0.15s !important; }
button.secondary:hover { border-color: #78716c !important; background: #fafaf9 !important; }

/* ── Question card — left amber border, mono font ────────────────────────── */
#question-card > .block, #question-card {
  background: #ffffff !important;
  border: 1px solid #e7e5e4 !important;
  border-left: 4px solid #f59e0b !important;
  border-radius: 12px !important;
  padding: 24px 28px !important;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
}
#question-card .prose, #question-card .prose p {
  font-family: 'IBM Plex Mono','Fira Code','Courier New', monospace !important;
  font-size: 14.5px !important;
  line-height: 1.75 !important;
  color: #1c1917 !important;
}
#question-card .prose em { color: #78716c !important; font-style: normal !important; font-size: 12px !important; font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important; }

/* ── Answer option pills ─────────────────────────────────────────────────── */
#answer-options .block, #answer-options { background: transparent !important; border: none !important; box-shadow: none !important; }
#answer-options .wrap { gap: 8px !important; flex-direction: column !important; }
#answer-options label {
  background: #ffffff !important;
  border: 1.5px solid #e7e5e4 !important;
  border-radius: 10px !important;
  padding: 14px 18px !important;
  cursor: pointer !important;
  transition: all 0.12s !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  color: #1c1917 !important;
  width: 100% !important;
  margin: 0 !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
  display: flex !important;
  align-items: flex-start !important;
  gap: 12px !important;
  line-height: 1.5 !important;
}
#answer-options label:hover { border-color: #f59e0b !important; background: #fffbeb !important; transform: translateY(-1px) !important; box-shadow: 0 3px 8px rgba(245,158,11,0.12) !important; }
#answer-options label:has(input:checked) { border-color: #f59e0b !important; background: #fef3c7 !important; font-weight: 600 !important; }
#answer-options input[type="radio"] { accent-color: #f59e0b !important; width: 16px !important; height: 16px !important; flex-shrink: 0 !important; margin-top: 2px !important; }

/* ── Feedback panel ──────────────────────────────────────────────────────── */
#feedback-panel > .block, #feedback-panel {
  border-radius: 12px !important;
  border: 1.5px solid #e7e5e4 !important;
  background: #ffffff !important;
  padding: 20px 24px !important;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05) !important;
}
#feedback-panel .prose h2 { margin-top: 0 !important; }

/* ── Sidebar — dark terminal panel ──────────────────────────────────────── */
#agent-sidebar > .block, #agent-sidebar {
  background: #1c1917 !important;
  border-radius: 10px !important;
  border: none !important;
  padding: 14px 16px !important;
  min-height: 80px !important;
}
#agent-sidebar .prose { color: #a8a29e !important; font-size: 12px !important; font-family: 'IBM Plex Mono','Fira Code',monospace !important; line-height: 1.6 !important; }
#agent-sidebar .prose strong { color: #f59e0b !important; font-weight: 600 !important; }
#agent-sidebar .prose code { color: #86efac !important; background: transparent !important; padding: 0 !important; font-size: 11px !important; }
#agent-sidebar .prose li { color: #a8a29e !important; font-size: 11.5px !important; }

/* ── General prose ───────────────────────────────────────────────────────── */
.prose { font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important; color: #1c1917 !important; line-height: 1.65 !important; }
.prose h2 { font-size: 18px !important; font-weight: 700 !important; margin-bottom: 10px !important; color: #1c1917 !important; }
.prose h3 { font-size: 15px !important; font-weight: 600 !important; margin-bottom: 8px !important; color: #292524 !important; }
.prose table { font-size: 13px !important; border-collapse: collapse !important; width: 100% !important; }
.prose th { background: #f5f5f4 !important; padding: 8px 12px !important; text-align: left !important;
  font-weight: 600 !important; font-size: 11px !important; text-transform: uppercase !important;
  letter-spacing: 0.06em !important; color: #78716c !important; border: 1px solid #e7e5e4 !important; }
.prose td { padding: 10px 12px !important; border: 1px solid #e7e5e4 !important; vertical-align: top !important; font-size: 13px !important; }
.prose tr:hover td { background: #fafaf9 !important; }
.prose code { background: #f5f5f4 !important; padding: 2px 6px !important; border-radius: 4px !important;
  font-family: 'IBM Plex Mono',monospace !important; font-size: 12.5px !important; color: #1c1917 !important; }
.prose pre { background: #1c1917 !important; color: #e7e5e4 !important; padding: 16px 20px !important;
  border-radius: 8px !important; font-size: 12.5px !important; overflow-x: auto !important; line-height: 1.6 !important; }
.prose pre code { background: transparent !important; color: #e7e5e4 !important; padding: 0 !important; }
.prose a { color: #2563eb !important; }
.prose hr { border-color: #e7e5e4 !important; margin: 16px 0 !important; }
.prose ul { padding-left: 18px !important; }
.prose li { margin-bottom: 4px !important; }
.prose strong { color: #1c1917 !important; }

/* ── Inputs ──────────────────────────────────────────────────────────────── */
textarea, input[type="text"], input[type="search"] {
  border: 1.5px solid #e7e5e4 !important; border-radius: 8px !important;
  font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important;
  font-size: 14px !important; padding: 10px 14px !important;
  background: #ffffff !important; color: #1c1917 !important;
  transition: border-color 0.15s, box-shadow 0.15s !important;
}
textarea:focus, input[type="text"]:focus {
  border-color: #f59e0b !important; outline: none !important;
  box-shadow: 0 0 0 3px rgba(245,158,11,0.15) !important;
}

/* ── Chatbot ─────────────────────────────────────────────────────────────── */
.chatbot .message-wrap { padding: 6px 0 !important; }
.chatbot .message.user { background: #f5f5f4 !important; border-radius: 10px 10px 2px 10px !important; }
.chatbot .message.bot { background: #fefce8 !important; border: 1px solid #fde68a !important; border-radius: 10px 10px 10px 2px !important; }

/* ── Blocks — remove noisy default borders ───────────────────────────────── */
.block { border: none !important; box-shadow: none !important; background: transparent !important; }
.gap { gap: 12px !important; }

/* ── Loading pulse animation ─────────────────────────────────────────────── */
@keyframes ai-pulse { 0%,100%{opacity:1} 50%{opacity:.45} }
.loading-msg { animation: ai-pulse 1.4s ease-in-out infinite; color: #78716c; font-size: 14px; }

/* ── Error state — red-tinted card ──────────────────────────────────────── */
#feedback-panel .prose p:first-child:has(⚠),
.error-msg {
  background: #fef2f2 !important;
  border: 1.5px solid #fca5a5 !important;
  border-radius: 8px !important;
  padding: 12px 16px !important;
  color: #991b1b !important;
}

/* ── Empty state in Progress ─────────────────────────────────────────────── */
#progress-empty { color: #78716c; font-size: 14px; padding: 24px 0; text-align: center; }

/* ── Topics return hint ──────────────────────────────────────────────────── */
#topics-hint .prose, #topics-hint .prose p {
  font-size: 12.5px !important; color: #78716c !important; margin-top: 6px !important;
}

/* ── Concept list arrows ─────────────────────────────────────────────────── */
#concept-list .prose li::marker { color: #f59e0b; }
#concept-list .prose code { font-size: 11.5px !important; }

/* ── Step guide table — step number in amber mono ────────────────────────── */
#step-guide .prose td:first-child { font-family: 'IBM Plex Mono',monospace !important;
  font-weight: 700 !important; color: #d97706 !important; white-space: nowrap !important; }

/* ── Progress mastery bars ───────────────────────────────────────────────── */
#mastery-panel .prose code { font-size: 10.5px !important; letter-spacing: -0.5px !important; }

/* ── Header strip ────────────────────────────────────────────────────────── */
#app-header > .block { background: transparent !important; padding: 0 !important; }

/* ── Responsive ──────────────────────────────────────────────────────────── */
@media (max-width: 768px) {
  .tab-nav button { padding: 6px 10px !important; font-size: 11.5px !important; }
  #question-card > .block, #question-card { padding: 16px 18px !important; }
  #answer-options label { padding: 12px 14px !important; font-size: 13.5px !important; }
  .gradio-container { max-width: 100% !important; }
}
"""

# ── Google Fonts injection ────────────────────────────────────────────────────
_FONT_HEAD = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600'
    '&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">'
)


# ══════════════════════════════════════════════════════════════════════════════
# STATIC CONTENT
# ══════════════════════════════════════════════════════════════════════════════

def _build_corpus_md() -> str:
    if not _manifest:
        return "_No manifest found. Run `python scripts/ingest_pack.py --pack cca-f`._"
    stats = _manifest.get("collection_stats", {}).get("domains", {})
    total = _manifest.get("chunks_indexed", 0)
    urls = _manifest.get("urls", [])
    by_domain: dict[str, dict] = {}
    for e in urls:
        d, t, ok = e.get("domain", "?"), e.get("tier", 1), e.get("ok", False)
        by_domain.setdefault(d, {"tier1": [], "tier2": []})
        by_domain[d][f"tier{t}"].append((e["url"], ok))
    lines = [
        f"**{total} indexed chunks** across {len(by_domain)} domains — citations link back to source.\n",
        "| Domain | Chunks | Tier 1 sources (authoritative) | Tier 2 sources (supplementary) |",
        "|---|---|---|---|",
    ]
    for d in _pack.domains:
        did = d.id
        t1 = by_domain.get(did, {}).get("tier1", [])
        t2 = by_domain.get(did, {}).get("tier2", [])
        def links(lst): return " · ".join(f"[{'✓' if ok else '✗'} `{url.split('/')[-1][:28]}`]({url})" for url, ok in lst)
        lines.append(f"| **{did}** — {d.name[:24]} | {stats.get(did, 0)} | {links(t1) or '—'} | {links(t2) or '—'} |")
    lines.append("\n_✓ fetched successfully · ✗ URL unavailable (may have moved)_")
    return "\n".join(lines)


def _build_concept_md(domain_id: str) -> str:
    concepts = _ALL_CONCEPTS.get(domain_id, [])
    d = _DOMAIN_MAP.get(domain_id)
    if not concepts or not d:
        return "_No concepts defined for this domain yet._"
    lines = [f"**{d.id} — {d.name}** · {d.weight:.0%} of exam · {len(concepts)} testable concepts\n"]
    for c in concepts:
        pre = f" ← `{'`, `'.join(c.prerequisites)}`" if c.prerequisites else ""
        lines.append(f"- **`{c.id}`** &nbsp; {c.name}{pre}")
    return "\n".join(lines)


_ARCH_MD = """\
## System Architecture

> **Platform model** — AI Tutor is certification-agnostic. The same agents and RAG pipeline
> work for any exam. A new certification is added by dropping YAML files into `packs/<id>/`
> and running ingestion. **Zero code changes required.**

---

### Agent inventory

| Agent | Model | Role |
|---|---|---|
| **Examiner** | Sonnet 4.6 | Generates one scenario-based MCQ grounded in retrieved chunks. Uses Anthropic `tool_use` for schema-safe JSON output. |
| **Grader** | Sonnet 4.6 | Evaluates student answer; explains each option; identifies misconception. Uses `tool_use`. |
| **Coach** | Sonnet 4.6 | Selects the next target concept — lowest mastery × highest domain weight. |
| **Explainer** | Sonnet 4.6 | Mastery-calibrated deep-dive (0–5 scale): first-principles at 0, edge-cases at 4+. |
| **Q&A Agent** | Sonnet 4.6 | Answers free-form questions grounded in corpus. Refuses to invent. |
| **Updater** | Rule-based + Haiku 4.5 | Applies deterministic mastery deltas; Haiku matches fuzzy misconception IDs. |

---

### Practice session — data flow

```
[Start Practice]
  ↓ LangGraph: load_pack → route_intent → select_concept
    Coach → lowest-mastery concept in highest-weight domain
  ↓ LangGraph: generate_question
    RAG → top-5 chunks from ChromaDB (cosine similarity, OpenAI embeddings)
    Examiner → 4-option MCQ with rationale + citations
  → UI displays question + answer pills

[Submit Answer]
  ↓ LangGraph: grade_answer
    Grader → verdict + explanation + concept_signal {evidence, confidence}
  ↓ LangGraph: update_student
    Updater → mastery delta → domain aggregate updated
    Student model saved → data/students/default_cca-f.json
  → UI shows feedback panel (green ✅ / red ❌)
```

### Q&A — data flow

```
[User question]
  ↓ LangGraph: retrieve_for_qna → top-5 chunks (cross-domain)
  ↓ LangGraph: answer_qna → grounded answer with [1],[2] citations
  → Chatbot appends (question, answer)
```

---

### Knowledge base

| Property | Value |
|---|---|
| Vector store | ChromaDB (local persistent · `data/chroma/`) |
| Collection | `pack_cca-f` — one per Certification Pack |
| Embeddings | OpenAI `text-embedding-3-small` (1536-dim, cosine) |
| Chunking | A2: `MarkdownHeaderTextSplitter` → `RecursiveCharacterTextSplitter` (≤1000 tokens, 100 overlap) |
| Corpus size | 429 chunks · 5 domains · 33/39 URLs fetched |

---

### Student model (B2 schema)

```
data/students/default_cca-f.json
├── domains
│   ├── D1 { weight, aggregate_mastery, concepts: { id: { mastery, confidence, last_seen } } }
│   └── D2 … D5
├── misconceptions { id: { count, last_seen, status } }
├── session_history [ { question_id, verdict, concept, domain, timestamp } ]
└── (V2) concepts, learning_style_hints  ← reserved null fields
```

Mastery rules: `demonstrated` +0.3×conf · `missing` −0.2×conf · `partial` no change, −0.1 conf.
Clamped [0.0, 5.0]. Misconception status = "active" when count ≥ 2.

---

### Adding a new Certification Pack

```
packs/<id>/
  pack.yaml         ← domains, weights, exam format, style
  corpus_urls.yaml  ← URLs by domain and tier
  curriculum.yaml   ← concept list with prerequisite graph
  style_notes.md    ← Examiner style guidance

python scripts/ingest_pack.py --pack <id>
```
"""

_HOME_INTRO = f"""\
## What is AI Tutor?

An adaptive exam-prep companion for the **{_pack.full_name} ({_pack.name})** certification —
a real Anthropic exam with 60 scenario-based questions, 120-minute time limit, and a 720/1000 passing score.

The app generates practice questions grounded in official Anthropic documentation,
grades your answers with pedagogical feedback citing real sources, tracks your
knowledge gaps across all five exam domains, and adapts future questions toward
your weakest areas session after session.

---

## How to use — step by step

| Step | Action | Tab |
|---|---|---|
| **1** | Pick an exam domain and click **▶ Start practice session** | Topics |
| **2** | Read the question, select an answer, click **Submit** | Practice |
| **3** | Read the explanation and source citations | Practice |
| **4** | Click **→ Next question** or pick a different domain | Practice / Topics |
| **5** | Check **Progress** to see mastery per domain and gaps | Progress |
| **6** | Ask follow-up questions in plain English | Q&A |

> **Suggested study order:** Start with **D1 Agentic Architecture (27%)** — highest exam weight.
> Once D1 mastery reaches 3.0+, move to D3 Claude Code (20%) and D4 Prompt Engineering (20%).

---

## Exam domains covered

| Domain | Name | Exam weight |
|---|---|---|
| D1 | Agentic Architecture & Orchestration | **27%** |
| D2 | Tool Design & MCP Integration | 18% |
| D3 | Claude Code Configuration & Workflows | **20%** |
| D4 | Prompt Engineering & Structured Output | **20%** |
| D5 | Context Management & Reliability | 15% |

---

### Reference corpus
"""

_HOME_CORPUS_MD = _HOME_INTRO + _build_corpus_md()
_INITIAL_CONCEPT_MD = _build_concept_md("D1")


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _sidebar(log: list[str], node: str = "") -> str:
    node_line = f"**node:** `{node}`\n\n" if node else ""
    lines = "\n".join(f"- {l}" for l in (log or [])[-8:])
    return f"{node_line}{lines or '_waiting…_'}"


def _loading_question() -> str:
    return (
        "<div class='loading-msg'>⏳ Generating question…"
        "<br><small style='color:#a8a29e'>Selecting concept · retrieving relevant passages · authoring question (15–20 s)</small></div>"
    )


def _loading_grade() -> str:
    return (
        "<div class='loading-msg'>⏳ Grading your answer…"
        "<br><small style='color:#a8a29e'>Analysing against official documentation (10–15 s)</small></div>"
    )


# ══════════════════════════════════════════════════════════════════════════════
# EVENT HANDLERS  (generators → immediate loading feedback)
# ══════════════════════════════════════════════════════════════════════════════

def on_domain_change(domain_id: str) -> str:
    return _build_concept_md(domain_id)


def start_practice(domain_id: str, session_state: dict):
    """Generator: yield loading state instantly, then LLM result."""
    # ── Immediate yield: switch to Practice tab, show spinner ────────────────
    yield (
        gr.update(value=_loading_question()),
        gr.update(choices=[], value=None),
        gr.update(),
        gr.update(value=""),
        gr.update(value=""),
        session_state,
        gr.update(value="**Generating…**\n\n- selecting concept\n- retrieving chunks"),
        gr.update(selected="practice"),
    )

    try:
        result = run_practice(
            pack_id=settings.default_pack_id,
            student_id=settings.default_student_id,
            domain=domain_id,
        )
        q = result.get("output_data", {})
        option_labels = [f"{o['id']})  {o['text']}" for o in q.get("options", [])]
        q_md = (
            f"**{q.get('stem', 'Error generating question')}**\n\n"
            f"*`{q.get('target_concept', '')}` &nbsp;·&nbsp; "
            f"{q.get('domain', '')} &nbsp;·&nbsp; {q.get('difficulty', '')}*"
        )
        new_state = {
            **session_state,
            "question": q,
            "chunks": result.get("retrieved_chunks", []),
            "student_model": result.get("student_model"),
            "domain": domain_id,
            "correct_count": session_state.get("correct_count", 0),
            "total_count": session_state.get("total_count", 0),
        }
        yield (
            gr.update(value=q_md),
            gr.update(choices=option_labels, value=None),
            gr.update(),
            gr.update(value=""),
            gr.update(value=""),
            new_state,
            gr.update(value=_sidebar(result.get("sidebar_log", []), result.get("active_node", ""))),
            gr.update(),
        )
    except Exception as e:
        import traceback
        logger.error(f"start_practice: {e}\n{traceback.format_exc()}")
        yield (
            gr.update(value=f"⚠️ **Error generating question**\n\n`{e}`\n\nTry again or check the logs."),
            gr.update(choices=[]),
            gr.update(),
            gr.update(value=""),
            gr.update(value=""),
            session_state,
            gr.update(value=f"Error: {e}"),
            gr.update(),
        )


def submit_answer(selected_label: str | None, session_state: dict):
    """Generator: yield loading state instantly, then grading result."""
    if not selected_label:
        yield (gr.update(value="⚠️ **Please select an answer before submitting.**"), gr.update(value=""), gr.update(), session_state)
        return

    answer_id = selected_label[0]

    # ── Immediate: show grading spinner ─────────────────────────────────────
    yield (gr.update(value=_loading_grade()), gr.update(value=""), gr.update(), session_state)

    try:
        result = run_grade(
            pack_id=settings.default_pack_id,
            student_id=settings.default_student_id,
            current_question=session_state["question"],
            student_answer=answer_id,
            retrieved_chunks=session_state.get("chunks", []),
        )
        gr_result = result.get("grading_result", {})
        verdict = gr_result.get("verdict", "unknown")
        logger.info(f"UI grading: verdict={verdict}")

        correct_id = gr_result.get("correct_option")
        correct_text = next(
            (o["text"] for o in session_state["question"].get("options", []) if o["id"] == correct_id), "—"
        )

        icon = "✅" if verdict == "correct" else "❌"
        label = "Correct!" if verdict == "correct" else "Incorrect"

        feedback = (
            f"## {icon} {label}\n\n"
            f"**Correct answer:** {correct_id})  {correct_text}\n\n---\n\n"
            f"{gr_result.get('explanation', '')}"
        )
        if gr_result.get("identified_misconception"):
            feedback += f"\n\n> ⚠️ **Watch out for:** {gr_result['identified_misconception']}"
        if gr_result.get("citations"):
            sources = "\n".join(f"- [{c['id']}] [{c['url']}]({c['url']})" for c in gr_result["citations"])
            feedback += f"\n\n**Sources:**\n{sources}"

        new_state = {
            **session_state,
            "student_model": result.get("student_model"),
            "grading_result": gr_result,
            "total_count": session_state.get("total_count", 0) + 1,
            "correct_count": session_state.get("correct_count", 0) + (1 if verdict == "correct" else 0),
        }
        yield (
            gr.update(value=feedback),
            gr.update(value="→ Next question"),
            gr.update(value=_sidebar(result.get("sidebar_log", []), result.get("active_node", ""))),
            new_state,
        )
    except Exception as e:
        import traceback
        logger.error(f"submit_answer: {e}\n{traceback.format_exc()}")
        yield (
            gr.update(value=f"⚠️ **Grading error**\n\n`{e}`"),
            gr.update(value=""),
            gr.update(),
            session_state,
        )


def next_question(session_state: dict):
    yield from start_practice(session_state.get("domain", "D1"), session_state)


def qna_respond(user_msg: str, history: list, session_state: dict):
    if not user_msg.strip():
        return history, "", gr.update()
    try:
        result = run_qna(
            pack_id=settings.default_pack_id,
            student_id=settings.default_student_id,
            question=user_msg,
        )
        answer = result.get("output_data", "No answer generated.")
        return history + [(user_msg, answer)], "", gr.update(value=_sidebar(result.get("sidebar_log", []), result.get("active_node", "")))
    except Exception as e:
        return history + [(user_msg, f"⚠️ Error: {e}")], "", gr.update()


def refresh_dashboard(session_state: dict):
    try:
        result = run_dashboard(settings.default_pack_id, settings.default_student_id)
        data = result.get("output_data", {})
        domain_mastery = data.get("domain_mastery", {})
        misconceptions = data.get("misconceptions", [])
        recent = data.get("recent_history", [])
        total = data.get("total_questions", 0)

        # Mastery bars (10-char wide)
        mastery_rows = "\n".join(
            f"| **{did}** | `{'█' * int(s * 2)}{' ' * max(0, 10 - int(s * 2))}` | {s:.2f} / 5.0 |"
            for did, s in sorted(domain_mastery.items())
        )
        mastery_md = (
            f"## Domain Mastery\n\n"
            f"| Domain | Progress | Score |\n|---|---|---|\n"
            f"{mastery_rows or '| — | — | No data yet |'}\n\n"
            f"*{total} total questions answered across all sessions*"
        )

        m_rows = "\n".join(
            f"- **{m['id'].replace('-', ' ')}** · seen {m['count']}×"
            for m in sorted(misconceptions, key=lambda x: -x["count"])[:8]
        ) if misconceptions else "_No recurring misconceptions yet — great work!_"
        misc_md = f"## Active Misconceptions\n\n{m_rows}"

        if recent:
            h_rows = "\n".join(
                f"| `{e.get('concept','—')[:32]}` | {e.get('domain','—')} | {'✅' if e.get('verdict') == 'correct' else '❌'} |"
                for e in reversed(recent[-15:])
            )
            hist_md = f"## Recent Questions\n\n| Concept | Domain | Result |\n|---|---|---|\n{h_rows}"
        else:
            hist_md = "## Recent Questions\n\n_No questions answered yet. Start a practice session on the Topics tab._"

        correct = session_state.get("correct_count", 0)
        total_s = session_state.get("total_count", 0)
        pct = f"{int(100*correct/total_s)}%" if total_s else "—"
        session_md = f"**This session:** {correct}/{total_s} correct ({pct})"
        return gr.update(value=mastery_md), gr.update(value=misc_md), gr.update(value=hist_md), gr.update(value=session_md)
    except Exception as e:
        logger.error(f"Dashboard: {e}")
        err = gr.update(value=f"⚠️ {e}")
        return err, err, err, err


# ══════════════════════════════════════════════════════════════════════════════
# LAYOUT
# ══════════════════════════════════════════════════════════════════════════════

with gr.Blocks(title="AI Tutor — CCA-F", css=_CSS) as app:
    session_state = gr.State({})

    # ── Global header ─────────────────────────────────────────────────────────
    with gr.Row(elem_id="app-header"):
        with gr.Column(scale=5):
            gr.Markdown(
                f"# 🎓 AI Tutor &nbsp;·&nbsp; {_pack.name}\n"
                f"*{_pack.full_name}* &nbsp;·&nbsp; "
                f"Corpus `{_pack.corpus_version}` &nbsp;·&nbsp; "
                f"{sum(len(v) for v in _ALL_CONCEPTS.values())} concepts &nbsp;·&nbsp; "
                f"{_manifest.get('chunks_indexed', '?')} chunks"
            )
        with gr.Column(scale=1):
            sidebar_md = gr.Markdown(
                "**Agent trace**\n\n_No action yet._",
                elem_id="agent-sidebar",
            )

    # ─────────────────────────────────────────────────────────────────────────
    with gr.Tabs(selected="home") as main_tabs:

        # ── TAB 1: HOME ───────────────────────────────────────────────────────
        with gr.Tab("🏠 Home", id="home"):
            gr.Markdown(_HOME_CORPUS_MD, elem_id="step-guide")

        # ── TAB 2: TOPICS ─────────────────────────────────────────────────────
        with gr.Tab("📚 Topics", id="topics"):
            gr.Markdown("### Choose a domain to practise")
            gr.Markdown(
                "The tutor automatically targets the concept with the **lowest mastery** "
                "in the selected domain, weighted by exam importance.",
                elem_id="topics-hint",
            )
            with gr.Row():
                with gr.Column(scale=2):
                    domain_dd = gr.Dropdown(
                        choices=_DOMAIN_CHOICES,
                        value="D1",
                        label="Exam domain",
                        interactive=True,
                    )
                    start_btn = gr.Button("▶ Start practice session", variant="primary", size="lg")
                    gr.Markdown(
                        "_After clicking Start, the app switches to **Practice** automatically. "
                        "Return here anytime to change domains or drill a specific area._",
                        elem_id="topics-hint",
                    )
                with gr.Column(scale=3):
                    concept_list_md = gr.Markdown(
                        _INITIAL_CONCEPT_MD,
                        elem_id="concept-list",
                    )

        # ── TAB 3: PRACTICE ───────────────────────────────────────────────────
        with gr.Tab("📝 Practice", id="practice"):
            gr.Markdown(
                "_Questions are generated from official Anthropic documentation and graded with citations._"
            )
            question_md = gr.Markdown(
                "**Start a session on the Topics tab to receive your first question.**\n\n"
                "_The app will automatically navigate here once the question is ready._",
                elem_id="question-card",
            )
            answer_radio = gr.Radio(
                choices=[],
                label="Select your answer",
                interactive=True,
                elem_id="answer-options",
            )
            with gr.Row():
                submit_btn = gr.Button("Submit answer", variant="primary")
                next_btn = gr.Button("", variant="secondary")
            feedback_md = gr.Markdown("", elem_id="feedback-panel")

        # ── TAB 4: PROGRESS ───────────────────────────────────────────────────
        with gr.Tab("📊 Progress", id="progress"):
            gr.Markdown(
                f"Scores persist across sessions · stored in "
                f"`data/students/default_{settings.default_pack_id}.json`"
            )
            with gr.Row():
                refresh_btn = gr.Button("🔄 Refresh dashboard", variant="secondary")
                session_summary = gr.Markdown("_Complete questions on the Practice tab, then refresh._")
            with gr.Row():
                mastery_md = gr.Markdown(
                    "## Domain Mastery\n\n"
                    "_No data yet — answer questions in Practice, then click **Refresh**._",
                    elem_id="mastery-panel",
                )
                misc_md = gr.Markdown(
                    "## Active Misconceptions\n\n"
                    "_Recurring errors surface here after 2+ occurrences._"
                )
            hist_md = gr.Markdown(
                "## Recent Questions\n\n"
                "_Your last 15 questions will appear here. Start a session on the **Topics** tab._"
            )

        # ── TAB 5: ARCHITECTURE ───────────────────────────────────────────────
        with gr.Tab("🏗️ Architecture", id="architecture"):
            gr.Markdown(_ARCH_MD, elem_id="arch-content")

        # ── TAB 6: Q&A ────────────────────────────────────────────────────────
        with gr.Tab("💬 Q&A", id="qna"):
            gr.Markdown(
                "Ask any question about the CCA-F curriculum. "
                "Answers are strictly grounded in the indexed corpus — the agent will not invent facts. "
                "If a topic isn't covered in the loaded documents, it will say so clearly.\n\n"
                "_Press **Enter** or click **Ask** to submit. Scroll up to see the full conversation._"
            )
            chatbot = gr.Chatbot(
                label="CCA-F Knowledge Base",
                height=480,
            )
            with gr.Row():
                qna_input = gr.Textbox(
                    placeholder="e.g. How does the tool_use / tool_result round-trip work in the agentic loop?",
                    show_label=False,
                    scale=5,
                )
                qna_btn = gr.Button("Ask", variant="primary", scale=1)

    # ── Event wiring ──────────────────────────────────────────────────────────
    domain_dd.change(fn=on_domain_change, inputs=[domain_dd], outputs=[concept_list_md])

    _practice_outputs = [question_md, answer_radio, submit_btn, feedback_md, next_btn, session_state, sidebar_md, main_tabs]

    start_btn.click(fn=start_practice, inputs=[domain_dd, session_state], outputs=_practice_outputs)
    next_btn.click(fn=next_question, inputs=[session_state], outputs=_practice_outputs)

    submit_btn.click(
        fn=submit_answer,
        inputs=[answer_radio, session_state],
        outputs=[feedback_md, next_btn, sidebar_md, session_state],
    )
    qna_btn.click(fn=qna_respond, inputs=[qna_input, chatbot, session_state], outputs=[chatbot, qna_input, sidebar_md])
    qna_input.submit(fn=qna_respond, inputs=[qna_input, chatbot, session_state], outputs=[chatbot, qna_input, sidebar_md])
    refresh_btn.click(fn=refresh_dashboard, inputs=[session_state], outputs=[mastery_md, misc_md, hist_md, session_summary])


def main() -> None:
    logger.info(f"Launching AI Tutor v1.2 — pack={settings.default_pack_id}")
    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        show_error=True,
        head=_FONT_HEAD,
    )


if __name__ == "__main__":
    main()
