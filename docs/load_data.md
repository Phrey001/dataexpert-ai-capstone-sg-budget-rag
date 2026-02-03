# Load Data Pipeline

## Purpose and scope

`src/vector_db/load_data.py` ingests local budget-related PDFs from the repository `data/` directory into a Milvus collection for hybrid retrieval.

This pipeline:
- recursively discovers PDFs under `data/`
- extracts and chunks PDF text
- tags each chunk with `doc_type` and `financial_year`
- generates dense vectors locally (no LLM API usage)
- generates sparse vectors using the custom BM25 encoder

## Directory conventions

The loader expects files under this pattern:

`data/<doc_type>/.../*.pdf`

Examples:
- `data/budgets_statements/fy2024_budget_statement.pdf`
- `data/round_up_speech/fy2020/2_fy2020_supplementary_budget_debate_round_up_speech.pdf`

## Metadata rules

### `doc_type`

`doc_type` is derived from the first subfolder under `data/`.

Example:
- `data/budgets_statements/...` -> `doc_type = "budgets_statements"`
- `data/round_up_speech/...` -> `doc_type = "round_up_speech"`

### `financial_year`

`financial_year` is derived from filename only using regex:

`fy(\d{4})`

Example:
- `fy2025_budget_statement.pdf` -> `financial_year = 2025`

If `fyYYYY` is missing in filename, the run fails immediately.

## Chunking strategy

Text is chunked by words with overlap:
- `chunk_size` default: `400`
- `chunk_overlap` default: `80`

Each chunk stores:
- `chunk_start` and `chunk_end` word offsets
- raw `text`

`chunk_id` is deterministic from relative file path + chunk index.

## Embedding strategy

### Dense vectors

Dense vectors are generated locally with:
- library: `sentence-transformers`
- model: `BAAI/bge-base-en-v1.5`
- device: CPU
- normalization: enabled

Expected dense vector dimension is `768`.

### Sparse vectors

Sparse vectors are generated with the project-local `BM25SparseEncoder`:
- source: `src/vector_db/sparse.py`
- output format: `Dict[int, float]` compatible with Milvus sparse vector field

## Milvus schema

The collection stores:
- `chunk_id` (`VARCHAR`, primary key)
- `doc_id` (`VARCHAR`)
- `source_path` (`VARCHAR`)
- `doc_type` (`VARCHAR`)
- `financial_year` (`INT64`)
- `chunk_start` (`INT64`)
- `chunk_end` (`INT64`)
- `text` (`VARCHAR`)
- `dense_vector` (`FLOAT_VECTOR`, dim from embedding model)
- `sparse_vector` (`SPARSE_FLOAT_VECTOR`)

Indexes:
- dense: `HNSW` with `IP`
- sparse: `SPARSE_INVERTED_INDEX` with `IP`

## Failure policy

The loader is fail-fast:
- missing required env vars -> fail
- invalid `data_root` -> fail
- no PDFs found -> fail
- missing `doc_type` path segment -> fail
- missing `fyYYYY` in filename -> fail
- unreadable/empty PDF text -> fail
- vector count mismatch -> fail
- existing collection dense dimension mismatch -> fail

## Usage

Example commands:


Minimal commands demo run with strong idempotency (defaults + full rebuild by drop collection):
```bash
python3 -m src.vector_db.load_data --recreate-collection
```

Sample demo run with explicit flags (defaults + incremental refresh)
```bash
python3 -m src.vector_db.load_data \
  --data-root data \
  --collection sg_budget_evidence \
  --embedding-model BAAI/bge-base-en-v1.5 \
  --chunk-size 400 \
  --chunk-overlap 80 \
  --reset-docs
```

Flag precedence:
- `--recreate-collection`: drops existing collection and recreates it; ignores `--reset-docs`
- `--reset-docs`: incremental mode; deletes existing chunks by `doc_id` before insert

Required environment variables:
- `MILVUS_URI`
- `MILVUS_TOKEN`

Optional:
- `MILVUS_DB` (defaults to Milvus `default` database when unset)

Expected consol outputs on runtime include:
- number of PDFs discovered
- number of chunk records built
- dense embedding dimension
- number of inserted chunks

## Known limitations for implementation approach

- No OCR fallback for scanned PDFs.
- Metadata field `financial_year` is inferred from filenames only.
- Metadata field `doc_type` depends strictly on folder structure under `data/`
  (limited to `data/budget_statements` and `data/round_up_speech` in project scope).
- BM25 model is persisted to `artifacts/bm25_model.pkl` without explicit versioning metadata, as project scope favors full rebuilds for deterministic runs.