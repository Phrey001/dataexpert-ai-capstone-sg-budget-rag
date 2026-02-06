# Math Notes

This document centralizes math references and shows where each formula is implemented in code.

## BM25 Sparse Retrieval

**Formula**

score(t, d) = idf(t) * (tf(t, d) * (k1 + 1)) / (tf(t, d) + k1 * (1 - b + b * |d| / avgdl))

idf(t) = log(1 + (N - df(t) + 0.5) / (df(t) + 0.5))

**Reference (plain English)**
- BM25 explained (GeeksforGeeks) - https://www.geeksforgeeks.org/what-is-bm25-best-matching-25-algorithm/

**Code**
- `src/vector_db/sparse.py` (BM25SparseEncoder)
  - `fit(...)` builds `idf`, `avgdl`, and `vocab`.
  - `_encode(..., use_bm25=True)` applies the BM25 scoring formula.
  - `_encode(..., use_bm25=False)` applies an IDF-weighted TF for query vectors.

**Artifact**
- `artifacts/bm25_model.pkl` stores the fitted vocabulary/IDF so query-time BM25 vectors match ingested document vectors.

---

## Reciprocal Rank Fusion (RRF)

**Formula**

RRF(d) = sum over lists i of 1 / (k + rank_i(d))

**Reference (plain English)**
- RRF explained in 4 mins (Veso AI blog) - https://veso.ai/blog/reciprocal-rank-fusion/

**Code**
- `src/vector_db/main.py`
  - `rrf_merge(...)` implements RRF to combine dense + sparse hit lists.
  - RRF is used to fuse dense + sparse retrieval in the evidence store API.
