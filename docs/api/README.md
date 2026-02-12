# API + Frontend Runbook

This project uses a single Cloud Run service to host both the API and the frontend UI.

## Local Run

One-command mode (FastAPI serves API + frontend):

```bash
uvicorn src.api.app:app --reload --port 8000
```

Open:
- Frontend UI: `http://localhost:8000/`
- API health: `http://localhost:8000/health`

## API Endpoints

- `GET /health`
- `POST /ask`
  - body: `{"query":"...","top_k":...,"top_n":...,"requested_years":[2024,2025]}`
  - response fields: `answer`, `confidence`, `state_history`, `final_reason`, `applicability_note`, `uncertainty_note`

Note: final answer text (with evidence citations) comes from synthesis. Applicability and uncertainty notes are surfaced as separate API/UI metadata from final reflection.

## Frontend Backend URL

Frontend uses same-origin by default in `frontend/app.js`.
For production, point `API_BASE_URL` to your hosted backend URL (for example, Cloud Run).
The UI also shows a static scope disclaimer describing document boundaries (FY2016-FY2025 budget statements + round-up speeches only).

## Guardrails Validators (Required by default)

Guardrails are enabled by default. You must install the hub validator packages for strict startup.

Install validators:

```bash
source .venv/bin/activate
guardrails hub install hub://guardrails/toxic_language

```

Verify:
- run API/runtime again and confirm readiness no longer fails on validator lookup.

Local unblock options (if needed):
- `AGENT_GUARDRAILS_ENABLED=false` (disable guardrails)
- `AGENT_MCP_STRICT=false` (avoid strict startup blocking)

## Prompt Injection Defense (Default-On)

The API applies a lightweight prompt-injection screen on every `/ask` query before orchestration runs.

- Suspicious input is blocked with a polite safe response.
- `final_reason` is set to `prompt_injection_detected`.
- No config flag is required in this phase (always on).

To tune false positives, edit rules in `src/api/security.py`.
