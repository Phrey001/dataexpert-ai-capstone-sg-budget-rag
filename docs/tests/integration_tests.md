# Integration Smoke Test

## File
- `scripts/run_rag_integration_queries.sh`

## Purpose
End-to-end wiring check (API → retrieval → rerank → synthesis → reflection). It verifies the system responds, not answer quality.

## Requirements
- Running API (`uvicorn src.api.app:app --reload --port 8000`)
- Populated Milvus collection (run `src/vector_db/load_data.py` first)

## Run

```bash
./scripts/run_rag_integration_queries.sh
```
