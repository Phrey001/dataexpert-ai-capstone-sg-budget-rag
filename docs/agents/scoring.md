# Scoring & Ranking Notes

This system uses **two distinct scoring stages**:

## 1) Retrieval merge (RRF)
Retrieval produces two ranked lists:
- dense_vector search
- sparse/BM25 search

They are merged with **Reciprocal Rank Fusion (RRF)**:

```
score_rrf = sum(1 / (k + rank))
```

- `rank` is 1-based position in each list.
- `k` is `AGENT_HYBRID_RRF_K` (default: 60).
- Output is **not normalized**; it is a relative merge score only.

Result: each hit gets a `merged_score` in metadata.

### Why rerank can see more than `top_k` hits
Hybrid retrieval runs **two lists** (dense + sparse). Each list is capped by
`top_k`, then merged and deduped. The merged set can therefore exceed `top_k`
before reranking (up to roughly `2 * top_k` minus duplicates). Rerank then
trims to `top_n` (and `AGENT_RERANK_CANDIDATE_LIMIT` can further cap it).

## 2) Retrieval recency bias (RRF stage)
Recency is applied at the **retrieval merge** stage (after RRF) to bias candidate
selection toward recent fiscal years without excluding older evidence.

```
score_rrf = sum(1 / (k + rank))
boost_tier = (window - (current_year - fy)) / window
score_rrf = score_rrf + retrieve_recency_boost * boost_tier
```

Why:
- Budget policies evolve; recent statements are usually more relevant for policy
  explanation unless the user explicitly asks for history/trends.
- Boosting is softer than hard filtering, so older evidence can still surface if
  the merged score is strong.

How:
- `retrieve_recency_boost` is `AGENT_RETRIEVE_RECENCY_BOOST` (default: 0.20).
- Recent window is `AGENT_RECENT_YEAR_WINDOW` (default: 5 years).
- Latest FY is `AGENT_CORPUS_LATEST_FY` (default: 2025) and is treated as the
  corpus “current year” for recency tiering.
- For hits inside the recent window:
  `boost_tier` scales from 1.0 (most recent FY) down to >0 as FY gets older.

Example (window = 5, base boost = 0.20, latest FY = 2025):
- FY2025: delta=0 → tier=1.0 → boost=0.20
- FY2024: delta=1 → tier=0.8 → boost=0.16
- FY2023: delta=2 → tier=0.6 → boost=0.12
- FY2022: delta=3 → tier=0.4 → boost=0.08
- FY2021: delta=4 → tier=0.2 → boost=0.04

## 3) Rerank (cross-encoder + normalized recency boost)
Merged candidates are reranked by a cross-encoder model:

```
score_ce = cross_encoder.predict(query, hit.text)
score_norm = (score_ce - min) / (max - min)
score_final = score_norm + rerank_recency_boost (if hit is in recent window)
```

### Cross-encoder
A cross-encoder scores **query + passage pairs** directly. A “pair” means:
- the **query** text, and
- one **passage** (a candidate chunk of evidence).

The model reads both together and outputs a relevance score for that specific pair.
This typically improves precision over embedding similarity because it can attend
to fine-grained wording and entailment. We use the cross-encoder score as the primary
rerank signal.

### Notes on scale
Cross-encoder scores are **normalized per query** (min-max) before the rerank
recency boost is applied. The boost is material only when it is comparable to the
typical gap between normalized scores. If the boost is too large, it can override
relevance; if too small, it only breaks near-ties.

### Interpreting cross-encoder scores (including negatives)
Cross-encoder outputs are **raw model scores**, not probabilities. Depending on
model architecture and training, scores can be:
- negative or positive,
- on a narrow or wide scale,
- not comparable across different queries.

How to interpret:
- **Ordering is what matters** for rerank. Absolute values are not meaningful.
- Negative scores are normal and simply mean “less relevant” than higher scores.
- Use score **gaps** (e.g., how far the top scores are from the tail) as a rough
  signal of separation, not a calibrated confidence.

Result: the final hit `score` equals `score_final`.

## Important notes
- RRF is used **only** for retrieval merging.
- Cross-encoder rerank is separate and **does not** use RRF.
- Recency boosts are additive at both stages:
  - retrieval merge: `AGENT_RETRIEVE_RECENCY_BOOST`
  - rerank: `AGENT_RERANK_RECENCY_BOOST` (applied after normalization)

## Related config
- `AGENT_HYBRID_RRF_K`
- `AGENT_RECENT_YEAR_WINDOW`
- `AGENT_RETRIEVE_RECENCY_BOOST`
- `AGENT_RERANK_RECENCY_BOOST`
- `AGENT_CROSS_ENCODER_MODEL`
