# Orchestration Contracts

## Manager behavior
- States: `execute_plan` → `success|fail`
- Single deterministic pass: retrieve → rerank → synthesize → reflect
- Plan steps kept as an extension point; current control flow is fixed
- Confidence bands set `final_reason` only (defaults in `src/agents/core/config.py`):
  - `>= 0.80` → `confidence_high`
  - `0.70–0.80` → `confidence_medium_caveated`
  - `0.50–0.70` → `confidence_low_partial`
  - `< 0.50` → `confidence_too_low_clarify`
- Guardrail block or incoherent query → terminal `fail`; all other cases return `success`
- Reflection adds UI metadata: `applicability_note`, `uncertainty_note`

## Planner contract
- `ExecutionPlan` includes: `original_query`, `revised_query`, `coherence`, `coherence_reason?`
- Reflection weights: `original_query` 70% + `revised_query` 30%
- Synthesis returns answer+citation text; reflection returns UI metadata

## Retrieval + rerank contract
- Hybrid retrieval uses dense + BM25 vectors, merged by RRF and deduped by `chunk_id`
- Rerank uses a cross-encoder + recency boost (`AGENT_RERANK_RECENCY_BOOST`)
- Retrieve metadata: `year_mode` (`explicit|none`), `requested_years`, `recent_year_window`
- Scoring details: `docs/agents/scoring.md`

## Tracing + guardrails
- LangSmith spans via `@traceable`; no custom trace payload in `OrchestrationResult`
- `GuardrailsViolationError(stage, reason, safe_reply)` → terminal `fail` with safe reply
