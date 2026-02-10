# Scoring & Ranking Notes

TL;DR:
- **Retrieval merge** uses RRF to combine dense + sparse lists, then adds a small recency boost.
- **Rerank** uses a cross-encoder, normalizes scores per query, then adds a small recency boost.
- Absolute scores don’t matter; ordering does.

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
- `k` is `AGENT_HYBRID_RRF_K` (default: 60). Higher `k` flattens rank influence; lower `k` makes top ranks dominate.
- Output is **not normalized**; it is a relative merge score only.

Result: each hit gets a `merged_score` in metadata.

Example (merge two lists):
- Dense rank = 3 → 1/(60+3) = 0.0159
- Sparse rank = 9 → 1/(60+9) = 0.0145
- Merged RRF score = 0.0159 + 0.0145 = 0.0304
- If FY2025 with boost_tier=1.0 and retrieve_recency_boost=0.80:
  score_rrf = 0.0304 * (1 + 0.80) = 0.0547

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
boost_tier = (window - (latest_year - doc_fy)) / window
score_rrf = score_rrf * (1 + retrieve_recency_boost * boost_tier)
```

Why:
- Budget policies evolve; recent statements are usually more relevant for policy
  explanation unless the user explicitly asks for history/trends.
- Boosting is softer than hard filtering, so older evidence can still surface if
  the merged score is strong.

How:
- `retrieve_recency_boost` is `AGENT_RETRIEVE_RECENCY_BOOST` (default: 0.80).
- Recent window is `AGENT_RECENT_YEAR_WINDOW` (default: 5 years).
- Latest FY is `AGENT_CORPUS_LATEST_FY` (default: 2025) and is treated as the
  corpus “current year” for recency tiering.
- For hits inside the recent window:
  `boost_tier` scales from 1.0 (most recent FY) down to >0 as FY gets older.

Example (window = 5, base boost = 0.80, latest FY = 2025; delta = latest FY - doc FY):
- FY2025: delta=0 → tier=1.0 → boost=0.80
- FY2024: delta=1 → tier=0.8 → boost=0.64
- FY2023: delta=2 → tier=0.6 → boost=0.48
- FY2022: delta=3 → tier=0.4 → boost=0.32
- FY2021: delta=4 → tier=0.2 → boost=0.16

Interpretation (retrieval stage):
- RRF merge scores are small (typically ~0.01–0.03 per list at top ranks with `k=60`).
- Scale depends on **RRF k and rank**, not `top_k`:
  - rank 1 → 1/(60+1) ≈ 0.016
  - rank 10 → 1/(60+10) ≈ 0.014
  - rank 50 → 1/(60+50) ≈ 0.009
- If a chunk appears in both dense + sparse lists, the contributions add (so a strong item can reach ~0.02–0.03).
- Multiplicative boost keeps recency proportional to relevance, but a large boost (like 0.80) still meaningfully lifts recent FYs relative to older ones.


## 3) Rerank (cross-encoder + normalized recency boost)
Merged candidates are reranked by a cross-encoder model:

```
score_ce = cross_encoder.predict(query, hit.text)
score_norm = (score_ce - min) / (max - min)
score_final = score_norm * (1 + rerank_recency_boost * boost_tier) (if hit is in recent window)
```

The **same tiered recency calculation** used in retrieval merge applies here.
See the retrieval example above for the tier values.
`rerank_recency_boost` is `AGENT_RERANK_RECENCY_BOOST` (default: 0.80).

Example (rerank with normalization):
- Raw cross-encoder scores for a query: min= -2.0, max= 3.0
- A hit with score=1.0 → score_norm = (1 - (-2)) / (3 - (-2)) = 0.6
- If FY2025 and boost_tier=1.0 with boost=0.80:
  score_final = 0.6 * (1 + 0.80) = 1.08

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
recency boost is applied. Multiplicative boosts scale the normalized score,
so recency does not dominate weak matches.

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
- Recency boosts are multiplicative at both stages:
  - retrieval merge: `AGENT_RETRIEVE_RECENCY_BOOST`
  - rerank: `AGENT_RERANK_RECENCY_BOOST` (applied after normalization)

## Related config
- `AGENT_HYBRID_RRF_K`
- `AGENT_RECENT_YEAR_WINDOW`
- `AGENT_RETRIEVE_RECENCY_BOOST`
- `AGENT_RERANK_RECENCY_BOOST`
- `AGENT_CROSS_ENCODER_MODEL`
