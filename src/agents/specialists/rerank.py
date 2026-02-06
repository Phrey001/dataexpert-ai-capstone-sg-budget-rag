"""Reranking helpers for retrieval hits."""

from datetime import UTC, datetime
from typing import Sequence

from ..core.types import RetrievalHit


def _cross_encoder_rerank(query: str, hits: Sequence[RetrievalHit], cross_encoder, candidate_limit: int) -> list[tuple[RetrievalHit, float]]:
    candidates = list(hits[: max(1, candidate_limit)])
    if not candidates:
        return []
    pairs = [(query, item.text) for item in candidates]
    raw_scores = cross_encoder.predict(pairs)
    scores = [float(score) for score in raw_scores]
    ranked = sorted(zip(candidates, scores), key=lambda row: row[1], reverse=True)
    return ranked


def rerank_hits(
    query: str,
    hits: Sequence[RetrievalHit],
    top_n: int,
    rerank_tool_name: str,
    cross_encoder,
    candidate_limit: int = 100,
    recent_year_window: int = 5,
    corpus_latest_fy: int = 2025,
    rerank_recency_boost: float = 0.05,
) -> list[RetrievalHit]:
    if cross_encoder is None:
        raise RuntimeError("Cross-encoder is required for reranking and could not be loaded.")
    ranked = _cross_encoder_rerank(
        query=query,
        hits=hits,
        cross_encoder=cross_encoder,
        candidate_limit=candidate_limit,
    )
    if not ranked:
        return []
    raw_scores = [score for _, score in ranked]
    min_score = min(raw_scores)
    max_score = max(raw_scores)
    span = max_score - min_score
    if span <= 1e-6:
        normalized = {item.chunk_id: 0.5 for item, _ in ranked}
    else:
        normalized = {item.chunk_id: (score - min_score) / span for item, score in ranked}

    current_year = int(corpus_latest_fy or datetime.now(UTC).year)
    window = max(1, int(recent_year_window))
    recent_years = {current_year - idx for idx in range(window)}
    boost = max(0.0, min(1.0, float(rerank_recency_boost)))

    score_map = {}
    for item, score in ranked:
        norm = normalized.get(item.chunk_id, 0.0)
        fy = item.metadata.get("financial_year")
        if isinstance(fy, int) and fy in recent_years:
            norm += boost
        score_map[item.chunk_id] = norm
    reranked = sorted([item for item, _ in ranked], key=lambda item: score_map.get(item.chunk_id, 0.0), reverse=True)

    return [
        RetrievalHit(
            chunk_id=item.chunk_id,
            source_path=item.source_path,
            text=item.text,
            score=float(score_map.get(item.chunk_id, item.score)),
            metadata={**item.metadata, "tool": rerank_tool_name},
        )
        for item in reranked[:top_n]
    ]
