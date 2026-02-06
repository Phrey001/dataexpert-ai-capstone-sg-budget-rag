# `tests/test_agents.py` Notes

## Scope

This test module covers:
- config parsing/validation
- planner revision + year-intent metadata
- manager transitions and terminal fallback behavior
- specialists hybrid retrieval (dense+sparse merge), cross-encoder rerank/fallback, and readiness behavior
- runtime startup fail-fast path

## Run

Default isolated run:

```bash
python -m unittest tests.test_agents tests.test_api
```

Module-only runs:

```bash
python -m unittest -v tests.test_agents
python -m unittest -v tests.test_api
```

## Key Contracts Checked

- trace top-level keys remain stable:
  - `query_chain`, `transitions`, `steps`, `final_state`, `final_reason`
- planner fails fast on invalid revised query
- manager deterministic two-pass synthesis/reflection and confidence-band terminal semantics (high/caveated/partial/clarify)
- coherent low-confidence outputs still return synthesis answer; applicability/uncertainty are surfaced via reflection metadata
- startup readiness failure returns exit code `2`
