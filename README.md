# dataexpert-ai-capstone-sg-budget-rag

> This should read like an operational manual for developers.

## Start Here (Developer + Operator Guide)

1. [`docs/agents/README.md`](docs/agents/README.md) - module map, call flow, and where to edit.
2. [`docs/agents/runtime.md`](docs/agents/runtime.md) - CLI runbook, env vars, and failure modes.
3. [`docs/agents/contracts.md`](docs/agents/contracts.md) - manager state machine and trace contracts.
4. [`docs/tests/test_agents.md`](docs/tests/test_agents.md) - test scope and commands.
5. [`docs/load_data.md`](docs/load_data.md) - vector DB ingestion/runbook for `src/vector_db/load_data.py`.
6. Continue below in this `README.md` for quickstart and environment setup.
   Defaults for runtime knobs live in `src/agents/core/config.py`.

## Quickstart

### 1) Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment Variables
`.env` files are loaded automatically if present.

Required:
- `OPENAI_API_KEY`
- `MILVUS_URI` (base URL, e.g. `https://<cluster-endpoint>`)
- `MILVUS_TOKEN` (Zilliz Cloud bearer token)

Optional:
- `MILVUS_DB` (can leave it unset as None with no defaults; Milvus should work just fine using "default")

## API + Frontend (Phase 1)

One-command local mode:

```bash
uvicorn src.api.app:app --reload --port 8000
```

If strict mode is enabled, install Guardrails hub validators (see [`docs/api/README.md`](docs/api/README.md)).
API `/ask` also includes default-on prompt-injection screening (details in [`docs/api/README.md`](docs/api/README.md)).

More details: [`docs/api/README.md`](docs/api/README.md)
