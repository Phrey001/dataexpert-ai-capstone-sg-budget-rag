# dataexpert-ai-capstone-sg-budget-rag

> This should read like an operational manual for developers.

## Start Here (Developer + Operator Guide)

1. [`docs/agents/README.md`](docs/agents/README.md) - module map, call flow, and where to edit.
2. [`docs/agents/runtime.md`](docs/agents/runtime.md) - CLI runbook, env vars, and failure modes.
3. [`docs/agents/contracts.md`](docs/agents/contracts.md) - manager state machine and trace contracts.
4. [`docs/tests/README.md`](docs/tests/README.md) - tests overview (unit + integration).
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

## API + Frontend

One-command local mode:

```bash
uvicorn src.api.app:app --reload --port 8000
```

If strict mode is enabled, install Guardrails hub validators (see [`docs/api/README.md`](docs/api/README.md)).
API `/ask` also includes default-on prompt-injection screening (details in [`docs/api/README.md`](docs/api/README.md)).

More details: [`docs/api/README.md`](docs/api/README.md)

## Docker / Cloud Run (Backend)

Local build/run:

```bash
docker build -t sg-budget-rag-backend .
docker run --rm -p 8080:8080 sg-budget-rag-backend
```

Cloud Run note:
- Use this Dockerfile for backend deployment.
- Frontend can be deployed separately (e.g., Vercel).

## Capstone Write-Up

### System/AI Agent diagram
- `docs/system_architecture.pptx` (export slide(s) to `screenshots/` as needed)

### UI + example queries screenshots
- `screenshots/` (add UI screenshots here)

### Business problem
- [Add 2–3 sentences on the user problem and why this system matters.]

### Expected outputs
- [Add 2–3 bullets on what answers/insights the app should produce.]

### Dataset + tech choices (with justification)
- [Add short bullets: data sources, why Milvus, why hybrid retrieval, why rerank, etc.]

### Steps + challenges
- [Add brief notes on ingestion, indexing, prompt iteration, issues encountered.]

### Future enhancements
- [Add 3–5 bullets: better OCR, richer metadata, eval harness, etc.]

## Deployment

- Live app: [ADD_DEPLOYED_URL_HERE]
- Deployment plan: [`docs/deployment.md`](docs/deployment.md)
