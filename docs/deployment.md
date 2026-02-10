# Deployment Plan (Cloud Run + Vercel)

This is a simple, low‑ops deployment flow. Use Cloud Run for the backend API and Vercel for the frontend.

## Prerequisites / sign‑ups

- **Google Cloud (Cloud Run)**: requires a GCP account and a billing‑enabled project.
- **Vercel**: sign in with GitHub or email (free tier is fine).
- **Milvus (Zilliz Cloud)**: this project uses `MILVUS_URI` + `MILVUS_TOKEN` (already required for local).  
- **OpenAI**: `OPENAI_API_KEY` for LLM calls.

## Backend: Cloud Run

1) **Create a GCP project** and enable billing.  
2) **Enable Cloud Run** in the GCP console.  
3) **Build and push** the container (use your preferred workflow):

```bash
docker build -t sg-budget-rag-backend .
```

4) **Deploy to Cloud Run** (via console or CLI).  
5) **Set env vars** in Cloud Run:

- `OPENAI_API_KEY`
- `MILVUS_URI`
- `MILVUS_TOKEN`
- `MILVUS_DB` (optional)

6) **Confirm the service URL** (you’ll use this for the frontend API base URL).

## Frontend: Vercel

1) **Import the repo** into Vercel.  
2) **Set environment variables**:
   - `VITE_API_URL` (or the API base URL used in `frontend/app.js`) pointing to Cloud Run.  
3) **Deploy** and confirm the live URL.

## Notes

- Cloud Run and Vercel can be deployed independently.
- Backend and frontend are intentionally separated for easier ops.
- **Cost note:** Cloud Run is pay‑as‑you‑go (not free by default). It can be low‑cost for light traffic, but you should expect some billing once usage exceeds free quotas.
