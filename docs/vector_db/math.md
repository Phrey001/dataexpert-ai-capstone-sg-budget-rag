# Math Notes

This document centralizes math references and shows where each formula is implemented in code.

## TF-IDF (Contrast Reference)

**Simple TF-IDF (per term)**
> `tfidf(t, d) = tf(t,d) * idf(t)`

**BM25 vs TF-IDF (at a glance)**
- TF‑IDF: no length normalization, no saturation term.
- BM25: adds length normalization and term‑frequency saturation via `k1` and `b`.

**Why BM25-style preferred over simple TF-IDF**
- It handles repeated terms and uneven chunk sizes better than plain TF‑IDF.
- It fits our vector database workflow, so retrieval stays fast and predictable.

**Note on length normalization in this repo**
- We chunk to a mostly fixed size, so length normalization usually has a small effect.
- It still matters for edge cases such as:
  - The final chunk of a PDF (often shorter than the target chunk size).
  - Pages with unusually sparse text (e.g., tables or blank pages).
  - OCR extraction noise that yields very short or very long chunks.

## BM25-style Sparse Retrieval (Not True BM25)

**Why this is not “true” BM25 (in this repo)**
- In textbook BM25, document and query weights are computed for full score refresh at query time; here we precompute the **document weights** and load into vector DB and later rely on sparse dot-product on query time to combine them, approximating BM25-style for a practical implementation.


**Why simplified queries encoding different from documents encoding**
- Query vectors use a simplified `idf * tf` weighting (no query length normalization or saturation term).
- We assume query expressions are very intentional and high‑signal; long queries add useful constraints, not noise.
- Hence we keep query weights simple (no query length normalization or saturation term) to preserve recall. Rare terms as specified during document encoding are still rewarded via IDF.


**Formula**

Offline Retrieval during query (needs query + document chunks):
> `BM25-style score(q, d) = Document weight * Query weight`

> `Query weight = idf(t) * tf(t,q)`

Online Encoding during chunking and loading into vector db (only document chunks):
> `Document weight = idf(t) * (tf(t,d) * (k1 + 1)) / denominator`

> `denominator = (tf(t,d) + k1 * (1 - b + b * |d| / avgdl))`


Where `Term Frequency tf` (used above):
- q: Query
- d: Document
- tf(t,q): Number of times term t appears in query q
- tf(t,d): Number of times term t appears in document d

Where `Inverse Document Frequency idf(t)` (used above):
> `idf(t) = log(1 + (N - df(t) + 0.5) / (df(t) + 0.5))`
> 
> **IDF note (in this repo):** We treat each chunk as a “document”, so `N` and `df(t)` are computed over chunks. `df(t)` counts how many chunks contain term `t` at least once (not total occurrences).


Where for `Document weight`:
- t: Query term
- d: Document
- tf(t,d): Number of times term t appears in document d
- |d|: Length of document d
- avgdl: Average document length in corpus
- k1: Controls term frequency scaling (saturation)
- b: Controls document length normalization

**Default parameter note (this repo):**
- We use `k1 = 1.5` and `b = 0.75`, which are standard BM25 defaults in many implementations.

Where for `Inverse Document Frequency idf(t)`:
- N: Total number of documents in corpus
- df(t): number of documents containing term t


**Reference (plain English)**
- BM25 explained (GeeksforGeeks) - https://www.geeksforgeeks.org/what-is-bm25-best-matching-25-algorithm/

**Code**
- `src/vector_db/sparse.py` (BM25SparseEncoder)
  - `fit(...)` builds `idf`, `avgdl`, and `vocab`.
  - `_encode(..., use_bm25=True)` applies the BM25 scoring formula.
  - `_encode(..., use_bm25=False)` applies an IDF-weighted TF for query vectors.

**Artifact**
- `artifacts/bm25_model.pkl` stores the fitted vocabulary/IDF so query-time BM25 vectors match ingested document vectors.

**Illustrative example (tiny corpus)**

Assumptions:
| Variable | Value | Meaning |
|---|---:|---|
| N | 3 | total chunks |
| avgdl | 100 | avg chunk length |
| k1 | 1.2 | BM25 term scaling |
| b | 0.75 | length normalization |
| df(t) | 1 | chunks containing term t |
| tf(t,d) | 3 | term count in doc d |
| \|d\| | 120 | length of doc d |

Computation:
| Step | Formula | Value |
|---|---|---:|
| idf(t) | log(1 + (N - df + 0.5)/(df + 0.5)) | ~0.98 |
| denom | tf + k1 * (1 - b + b * |d|/avgdl) | 4.38 |
| score(t,d) | idf * (tf * (k1 + 1)) / denom | ~1.48 |

This is the per-term contribution; multi-term queries sum per-term scores.
