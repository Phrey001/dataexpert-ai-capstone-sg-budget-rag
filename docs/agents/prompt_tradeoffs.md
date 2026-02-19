# Prompt Tradeoffs

Goal: evidence‑grounded, policy‑relevant answers with clear limits and citations.
Tradeoff: higher reliability and auditability, less narrative depth.

- **Synthesis (answer writer):** forces evidence, a policy implication, and a bottom‑line sentence; may reduce nuance.
- **Reflection (reviewer):** produces applicability/uncertainty notes; confidence is diagnostic, so weaker answers can still surface.
- **Planner (query rewriter):** single LLM call to revise query + judge coherence; fast, but relies on prompt strictness to avoid drift.
