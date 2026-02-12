# Tests Overview

These tests are intended for local or CI use (not on the deployed Cloud Run service).

## Unit / Contract Tests

### Files
- `tests/test_agents.py`
- `tests/test_api.py`

### Purpose
Fast unit/contract tests using mocks. They validate config parsing, planner output, manager flow, and API wiring without requiring Milvus or model downloads.

### Run

```bash
python -m unittest tests.test_agents tests.test_api
```

## Integration Smoke Test

### File
- `scripts/run_rag_integration_queries.py`

### Purpose
End-to-end wiring check (API → retrieval → rerank → synthesis → reflection). It verifies the system responds, not answer quality.

### Requirements
- Running API (`uvicorn src.api.app:app --reload --port 8000`)
- Populated Milvus collection (run `src/vector_db/load_data.py` first)

### Run

```bash
./scripts/run_rag_integration_queries.py
```
