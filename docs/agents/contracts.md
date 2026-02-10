# Orchestration Contracts

## State Machine (`Manager`)

States:
- `execute_plan`
- `success`
- `fail`

Rules:
- manager executes a single deterministic pass (retrieve → rerank → synthesize → reflect).
- confidence bands determine terminal behavior for coherent queries:
  - `>= 0.80` -> success (`confidence_high`)
  - `0.70 - 0.80` -> success with caveat (`confidence_medium_caveated`)
  - `0.50 - 0.70` -> success with partial limitation (`confidence_low_partial`)
  - `< 0.50` -> success with strong clarification notes (`confidence_too_low_clarify`)
- `confidence` and `final_reason` remain metadata outputs (not duplicated as structured fields in answer text).
- final reflection also provides structured UI metadata: `applicability_note`, `uncertainty_note`.
- Band thresholds are internal constants in `Manager` and not exposed as API/CLI toggles.
- `low_coverage` is a diagnostic reason; manager terminal decision is confidence-band based.
- guardrail block returns safe reply and keeps terminal `fail`.
- planner incoherent queries still terminal `fail`.

## Tracing

- LangSmith tracing remains available via the `@traceable` spans.
- There is no custom trace payload in `OrchestrationResult`.

## Planner Contract

`ExecutionPlan` always carries:
- `original_query`
- `revised_query`
- `coherence` (`coherent|incoherent`)
- `coherence_reason` (optional)

Reflection evaluates answer quality using both queries with default weighting:
- primary intent anchor: `original_query` (70%)
- supporting retrieval context: `revised_query` (30%)
- reflection model defaults to strict temperature via `AGENT_REFLECTION_TEMPERATURE=0.0`.
- final synthesis produces answer+citation text; final reflection produces applicability/uncertainty metadata for UI.

Manager early reject rule:
- if planner marks `coherence="incoherent"`, manager returns immediate polite failure response.
- no specialist retrieval/rerank/synthesis/reflect calls are executed for that query.

Retrieve step metadata includes:
- `year_mode` (`explicit|none`)
- `requested_years`
- `recent_year_window`

Retrieval/rerank behavior:
- retrieval builds hybrid candidates from both `dense_vector` and `sparse_vector` (BM25-encoded query).
- candidate lists are merged with `rrf` and deduped by `chunk_id`.
- reranking uses cross-encoder scores on merged candidates and applies a small recency boost (`AGENT_RERANK_RECENCY_BOOST`) after normalization.

Year intent source:
- year selection comes from UI `requested_years`.
- if no years are selected, year mode defaults to `none` (no filter).

Scoring details:
- see `docs/agents/scoring.md` for the full scoring/ranking breakdown.

## Guardrail Contract

Guardrail violations raise `GuardrailsViolationError(stage, reason, safe_reply)`.
Manager converts this into terminal failure with:
- final safe reply answer.
