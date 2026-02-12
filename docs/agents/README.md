# Agents Module Map

`src/agents` is organized by responsibility:

- `runtime.py` - CLI entrypoint and startup wiring.
- `core/` - shared config, datatypes, manager state machine.
- `planner/` - planner service.
- `specialists/` - specialist facade plus retrieval/rerank/synthesis/reflection helpers.
- `guardrails/` - GuardrailsAI policy wrapper and violation mapping.
- `mcp/` - MCP tool naming/contracts/client seam.
- `prompts/` - prompt templates used by planner/synthesis/reflection.

## Call Flow

1. `runtime.py` builds `AgentConfig`, `PlannerAI`, `Manager`, `Specialists`.
2. `Manager.run(...)` drives state transitions.
3. `PlannerAI.build_plan(...)` returns revised query + plan steps.
4. `Specialists` executes retrieve/rerank/synthesize/reflect.
5. Guardrails and readiness failures surface as terminal manager outcomes.

## Where to Edit

- State transitions/fallbacks: `src/agents/core/manager.py`
- Runtime/env tunables are centralized in `src/agents/core/config.py` (`AgentConfig`); confidence-band thresholds are env-backed in the same config.
- Synthesis/reflection model + temperature knobs are in `src/agents/core/config.py` (internal dev/ops tuning, not user API toggles).
- Planner query revision or year intent: `src/agents/planner/service.py`
- Retrieval filters/rerank behavior: `src/agents/specialists/retrieval.py`, `src/agents/specialists/rerank.py`
- Synthesis/reflection prompting: `src/agents/prompts/`, `src/agents/specialists/synthesis.py`, `src/agents/specialists/reflection.py`
- Guardrail policy behavior: `src/agents/guardrails/service.py`
- Sample/demo queries: `docs/agents/sample_queries.md`
- Data ingestion runbook: `docs/load_data.md`
