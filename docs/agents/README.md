# Agents Module Map

## Purpose
`src/agents` is the RAG orchestration layer: planner → retrieval/rerank → synthesis → reflection, with guardrails and MCP seams.

## Key modules
- `runtime.py` - CLI entrypoint and startup wiring.
- `core/` - config + datatypes + manager state machine.
- `planner/` - query rewrite + coherence check.
- `specialists/` - retrieval, rerank, synthesis, reflection.
- `guardrails/` - GuardrailsAI policy wrapper.
- `mcp/` - MCP tool naming/contracts/client seam.
- `prompts/` - prompt templates used by planner/synthesis/reflection.

## Call flow (happy path)
`runtime.py` → `Manager.run(...)` → `PlannerAI.build_plan(...)` → `Specialists` (retrieve → rerank → synthesize → reflect)

## Where to edit (most common)
- Manager transitions/fallbacks: `src/agents/core/manager.py`
- Config defaults + env knobs: `src/agents/core/config.py`
- Planner behavior: `src/agents/planner/service.py`
- Retrieval/rerank: `src/agents/specialists/retrieval.py`, `src/agents/specialists/rerank.py`
- Synthesis/reflection prompts: `src/agents/prompts/`, `src/agents/specialists/synthesis.py`, `src/agents/specialists/reflection.py`
- Guardrail policy: `src/agents/guardrails/service.py`

## Related docs
- Demo queries: `scripts/demo_queries.md`
- Data ingestion: `docs/vector_db/load_data.md`
