# Developer Review Guide

Use this as a developer-friendly top‑down path for understanding and reviewing the codebase.

## 1) Start Here (entrypoints)
- API + UI: `src/api/app.py`
- CLI (no API/UI): `src/agents/runtime.py`

## 2) Orchestration flow
- Manager: `src/agents/core/manager.py`
- Planner: `src/agents/planner/service.py`
- Specialists facade: `src/agents/specialists/service.py`

## 3) Specialist internals (by step)
- Retrieval: `src/agents/specialists/retrieval.py`
- Rerank: `src/agents/specialists/rerank.py`
- Synthesis: `src/agents/specialists/synthesis.py`
- Reflection: `src/agents/specialists/reflection.py`
- Guardrails: `src/agents/guardrails/service.py`

## 4) Contracts + config
- Contracts: `src/agents/core/types.py`
- Config defaults: `src/agents/core/config.py`
- API schema: `src/api/schemas.py`

## 5) Data & scoring references
- Ingestion: `docs/load_data.md`
- Scoring details: `docs/agents/scoring.md`
- Sparse/BM25 math: `docs/vector_db/math.md`

## 6) Tests (what matters)
- Unit tests: `docs/tests/unit_tests.md`
- Integration tests: `docs/tests/integration_tests.md`
