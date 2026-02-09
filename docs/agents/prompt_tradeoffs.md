# Prompt Tradeoffs (Executive Summary)

Our prompts are designed to produce **evidence‑grounded, policy‑relevant answers** with
clear limits and citations. This improves reliability and auditability, at the cost of
shorter, more conservative responses.

**Synthesis (answer writer)**  
Prioritizes evidence, forces a direct policy implication and a bottom‑line sentence,
and avoids irrelevant examples. This keeps answers on‑scope and actionable, but reduces
nuance and narrative depth. It also requires multiple citations when evidence exists.

**Reflection (reviewer)**  
Produces structured applicability/uncertainty notes for the UI and treats confidence as
diagnostic rather than a refusal trigger. This keeps outputs usable but can allow weaker
answers to show. Coherence is LLM‑judged, so odd queries may still pass.

**Planner (query rewriter)**  
Uses a single LLM call to revise the query and judge coherence. This is fast and simple,
but relies on prompt strictness to avoid intent drift.
