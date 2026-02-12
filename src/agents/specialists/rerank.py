"""Reranking helpers for retrieval hits."""

from datetime import UTC, datetime
from typing import Sequence

from ..core.types import RetrievalHit


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
    """Rerank retrieval hits with a cross-encoder and optional recency boost.

    Defaults are fallbacks; production values are passed in from AgentConfig
    (defined in src/agents/core/config.py).
    """
    if cross_encoder is None:
        raise RuntimeError("Cross-encoder is required for reranking and could not be loaded.")
    candidates = list(hits[: max(1, candidate_limit)])
    if not candidates:
        return []
    pairs = [(query, item.text) for item in candidates]
    raw_scores = [float(score) for score in cross_encoder.predict(pairs)]
    ranked = sorted(zip(candidates, raw_scores), key=lambda row: row[1], reverse=True)
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
    boost = max(0.0, min(1.0, float(rerank_recency_boost)))

    score_map = {}
    for item, score in ranked:
        norm = normalized.get(item.chunk_id, 0.0)
        fy = item.metadata.get("financial_year")
        if isinstance(fy, int):
            delta = max(0, current_year - fy)
            if delta < window:
                tier = (window - delta) / window
                norm *= 1.0 + (boost * tier)
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
