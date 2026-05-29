# CCA-F Style Notes — Examiner Guidance

These notes are injected into the Examiner agent's context alongside the `pack` descriptor.
They tell the Examiner what "good CCA-F questions" look like so generated questions match
the actual exam's style — without inventing facts or copying real exam questions.

## Exam style: scenario-based

CCA-F tests **applied judgment in realistic production situations**, not memorization of definitions.
Every question should describe a specific scenario (a system, a decision, a bug) and ask
the candidate to choose the correct action, diagnose a problem, or compare trade-offs.

## Question stem guidelines

- Set the scene concisely: describe the system, the constraint, the problem.
- Use language an engineer would use: "An agent is built with…", "A team is designing…", "A developer notices that…"
- Avoid academic phrasing ("Which of the following defines…"). Prefer operational phrasing ("A production agent is…")
- The correct answer should not be obvious from the stem alone — require reasoning.

## Distractor (wrong answer) guidelines

Wrong answers should represent realistic mistakes that a partially-informed candidate would make:
- **Anti-patterns**: things that seem right but are actually problematic in production.
- **Confusions**: plausible misapplication of a related concept.
- **Outdated practices**: approaches that worked in older patterns but are superseded.
- **Scope errors**: answers that would be correct for a different scenario or context.

Avoid distractors that are clearly nonsensical — every wrong answer should be defensible by someone who partially understands the topic.

## Domain D1 specific guidance

- Questions test understanding of the **agentic loop** (tool_use → tool_result round-trips), not just that tools exist.
- Orchestrator-subagent questions should involve realistic decisions: when to parallelize, how to isolate context, how to handle failures.
- Trust boundary questions should surface security-relevant mistakes (e.g., prompt injection via tool results, unchecked subagent outputs).
- Avoid questions that can be answered from the term definition alone — require the candidate to reason about a production consequence.

## Difficulty calibration

- **conceptual**: tests one precise mechanism with single-mechanism distractors. Stem can be short.
- **scenario**: describes a multi-step situation. Stem is longer. The correct answer requires reasoning about the full system, not just a single fact.

Start MVP with conceptual difficulty on D1 to validate retrieval quality before enabling scenario questions.
