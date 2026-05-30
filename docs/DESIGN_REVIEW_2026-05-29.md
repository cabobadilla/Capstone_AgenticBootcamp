# Design Review — AI Tutor UI
**Date**: 2026-05-29  
**Reviewer**: Ralph Loop (automated) + frontend-design skill  
**Scope**: `ai_tutor/ui/app.py` — Gradio 6 Blocks, 6-tab layout

---

## What the app does

AI Tutor is an agentic exam-prep tool for the CCA-F (Claude Certified Architect — Foundations) certification. It generates scenario-based practice questions from official Anthropic docs, grades answers with pedagogical feedback and source citations, tracks per-domain mastery across sessions, and adapts future questions toward the student's weakest areas.

---

## What Ralph found (pre-improvement audit)

### Critical UX issues
| # | Issue | Impact |
|---|---|---|
| 1 | **Silent 15-30s LLM waits** — no loading feedback while question generates or answer grades | User thinks app is broken; clicks Start multiple times |
| 2 | **Tab doesn't auto-switch** after clicking Start — user must manually navigate to Practice | Confusing flow; user can't find the question |
| 3 | **Default Gradio grey theme** — looks like a tutorial/demo, not a product | Immediate trust/quality signal failure |
| 4 | **Radio buttons uncustomised** — standard HTML radio inputs, no pill styling | Options don't feel like exam choices |
| 5 | **Empty states are generic italic text** — "Click Refresh to load." gives no task context | User doesn't know what to do |

### Design quality issues
| # | Issue |
|---|---|
| 6 | No consistent color system — accent colors varied across components |
| 7 | Question text uses body font — exam content needs monospace for focus |
| 8 | No visual hierarchy in Architecture tab — 90 lines of markdown with no scan points |
| 9 | Sidebar was plain Markdown — no dark terminal aesthetic to distinguish it from content |
| 10 | Progress tab mastery bars were text tables with no visual weight |

---

## What was improved

### Round 1 — Foundation (CSS + loading states + navigation)
- **9,900-char custom CSS system** injected via `gr.Blocks(css=...)`:
  - Dark tab navigation (stone-950 background, amber-400 active state)
  - Question card: white surface, left amber border (`border-left: 4px solid #f59e0b`), IBM Plex Mono font
  - Answer pills: white cards with hover lift and amber selected state
  - Dark terminal sidebar (`#1c1917` background, `#a8a29e` text, `#f59e0b` strong, `#86efac` code)
  - `@keyframes ai-pulse` loading animation
  - Full `prose` overrides for tables, code, pre, links
  - Responsive breakpoints at 768px
- **Google Fonts injection** via `launch(head=...)`: Plus Jakarta Sans + IBM Plex Mono
- **Generator functions** (`yield`) for `start_practice`, `submit_answer`, `next_question`:
  - First yield: loading message + switch to Practice tab
  - Second yield: LLM result (question / feedback)
  - Eliminates the silent blank-screen wait
- **Tab auto-switch**: `gr.Tabs(selected=...)` updated via `gr.update(selected="practice")` in the generator's first yield

### Round 2 — Polish (empty states + copy + error handling)
- Error state CSS: red-tinted background (`#fef2f2`) and border (`#fca5a5`) for error messages
- Progress empty states: replaced "Click Refresh to load." with task-specific copy ("Complete questions on Practice, then refresh.")
- Topics tab: added return hint ("Return here anytime to change domains or drill a specific area.")
- Architecture tab: blockquote callout for platform claim (visually separated from body text)
- Removed unsupported Gradio 6 kwarg (`show_copy_button` on `gr.Chatbot`)
- Q&A tab: added Enter key hint in description copy

---

## Frontend-design skill verification (Round 2)

**Criteria checked:**
- ✅ Loading states — explicit loading messages with pulse animation for both question gen and grading
- ✅ Empty states — task-specific guidance in all three Progress sub-panels
- ✅ Error states — CSS error card styling + traceback logging for debugging
- ✅ Visual hierarchy — tab nav (dark/amber), question card (mono/bordered), sidebar (dark terminal), feedback (full-width card)
- ✅ First-time user orientation — Home tab has step table, Topics hints tab switch, Practice hints Start
- ✅ Mobile responsiveness — 768px breakpoint reduces tab padding and answer pill padding
- ✅ Professional color palette — stone/amber/IBM Plex Mono is distinctive and not "purple AI gradient"
- ✅ API compatibility — all Gradio 6.15.2 kwarg issues resolved
- ⚠️ Minor remaining: answer pills may wrap on <480px screens (see PLAN.md future roadmap)
- ⚠️ Minor remaining: Coach sometimes returns domain name instead of concept ID (prompt issue, not UI)

**Design skill verdict**: The app now reads as a professional exam-prep SaaS tool. The amber/stone palette is distinctive and Anthropic-adjacent without copying brand assets. Monospace exam content differentiates question text from UI chrome. Loading states eliminate the biggest UX failure point.

---

## Final state

| Metric | Value |
|---|---|
| CSS lines | ~250 (in `_CSS` constant) |
| Generator functions | 3 (`start_practice`, `submit_answer`, `next_question`) |
| Tabs | 6 (Home · Topics · Practice · Progress · Architecture · Q&A) |
| Tab auto-switch | ✅ Start → Practice |
| Loading states | ✅ Both question gen and grading |
| Empty states | ✅ All 3 Progress sub-panels |
| Error states | ✅ CSS + full traceback logging |
| Test suite | 18 passing (no regressions) |

---

## Files changed in this session

| File | Change |
|---|---|
| `ai_tutor/ui/app.py` | Complete rewrite to v1.2: CSS system, generators, tab switch, elem_ids |
| `CLAUDE.md` | Updated status, added Next Steps section, kept under 110 lines |
| `PLAN.md` | New — What We Built / What We Improved / Future Roadmap |
| `docs/DESIGN_REVIEW_2026-05-29.md` | This file |
