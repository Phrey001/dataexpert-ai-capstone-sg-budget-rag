# dataexpert-ai-capstone-sg-budget-rag

> This should read like an operational manual for developers.


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

