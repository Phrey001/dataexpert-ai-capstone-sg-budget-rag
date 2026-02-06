"""Retrieval helpers for hybrid Milvus search and year-aware filtering."""

from datetime import UTC, datetime
from typing import Any, Optional

from ..core.trace_types import RetrieveContextPayload
from ..core.types import RetrievalHit
from ..mcp.client import search_collection_dense, search_collection_sparse


def build_year_filter_expr(
    retrieve_context: RetrieveContextPayload,
    *,
    fy_filtering_enabled: bool,
    recent_year_window: int,
) -> Optional[str]:
    if not fy_filtering_enabled:
        return None

    year_mode = str(retrieve_context.get("year_mode", "none"))
    requested_years = [int(year) for year in retrieve_context.get("requested_years", []) if str(year).isdigit()]
    allow_broad_horizon = bool(retrieve_context.get("allow_broad_horizon", False))
    window = max(1, int(retrieve_context.get("recent_year_window", recent_year_window)))
    current_year = datetime.now(UTC).year

    if year_mode == "explicit" and requested_years:
        years = sorted(set(requested_years))
        return f"financial_year in [{', '.join(str(year) for year in years)}]"

    if year_mode == "range" and len(requested_years) >= 2:
        start, end = min(requested_years), max(requested_years)
        return f"financial_year >= {start} and financial_year <= {end}"

    if year_mode == "recent":
        if allow_broad_horizon:
            return None
        years = [current_year - idx for idx in range(window)]
        return f"financial_year in [{', '.join(str(year) for year in years)}]"

    return None


def run_retrieve(
    *,
    query: str,
    top_k: int,
    retrieve_context: RetrieveContextPayload,
    collection,
    embedder,
    bm25_encoder,
    retrieve_tool_name: str,
    fy_filtering_enabled: bool,
    recent_year_window: int,
    corpus_latest_fy: int,
    retrieve_recency_boost: float,
    merge_strategy: str,
    rrf_k: int,
) -> list[RetrievalHit]:
    query_vector = embedder.encode([query], normalize_embeddings=True)[0].astype("float32").tolist()
    sparse_query_vector = bm25_encoder.encode_queries([query])[0] if bm25_encoder is not None else {}
    year_expr = build_year_filter_expr(
        retrieve_context,
        fy_filtering_enabled=fy_filtering_enabled,
        recent_year_window=recent_year_window,
    )

    dense_limit = max(1, int(top_k))
    sparse_limit = max(1, int(top_k))
    dense_results = search_collection_dense(collection, query_vector=query_vector, top_k=dense_limit, year_expr=year_expr)
    sparse_results = (
        search_collection_sparse(
            collection,
            sparse_query_vector=sparse_query_vector,
            top_k=sparse_limit,
            year_expr=year_expr,
        )
        if sparse_query_vector
        else [[]]
    )
    return _merge_hits(
        dense_results=dense_results,
        sparse_results=sparse_results,
        year_expr=year_expr,
        retrieve_tool_name=retrieve_tool_name,
        merge_strategy=merge_strategy,
        rrf_k=rrf_k,
        recent_year_window=recent_year_window,
        corpus_latest_fy=corpus_latest_fy,
        retrieve_recency_boost=retrieve_recency_boost,
    )


def _merge_hits(
    *,
    dense_results,
    sparse_results,
    year_expr: Optional[str],
    retrieve_tool_name: str,
    merge_strategy: str,
    rrf_k: int,
    recent_year_window: int,
    corpus_latest_fy: int,
    retrieve_recency_boost: float,
) -> list[RetrievalHit]:
    if merge_strategy != "rrf":
        raise ValueError(f"Unsupported merge_strategy: {merge_strategy}")

    merged: dict[str, dict[str, Any]] = {}
    _accumulate_source(merged, dense_results[0] if dense_results else [], "dense", rrf_k)
    _accumulate_source(merged, sparse_results[0] if sparse_results else [], "sparse", rrf_k)

    current_year = int(corpus_latest_fy or datetime.now(UTC).year)
    window = max(1, int(recent_year_window))
    boost = max(0.0, min(1.0, float(retrieve_recency_boost)))

    for row in merged.values():
        fy = row["entity"].get("financial_year")
        if isinstance(fy, int):
            delta = max(0, current_year - fy)
            if delta < window:
                tier = (window - delta) / window
                row["merged_score"] += boost * tier

    ranked = sorted(merged.values(), key=lambda row: row["merged_score"], reverse=True)
    hits: list[RetrievalHit] = []
    for row in ranked:
        entity = row["entity"]
        hits.append(
            RetrievalHit(
                chunk_id=entity.get("chunk_id", ""),
                source_path=entity.get("source_path", ""),
                text=entity.get("text", ""),
                score=float(row["merged_score"]),
                metadata={
                    "provider": "mcp-local",
                    "tool": retrieve_tool_name,
                    "doc_type": entity.get("doc_type"),
                    "financial_year": entity.get("financial_year"),
                    "year_expr": year_expr,
                    "retrieval_sources": sorted(row["sources"]),
                    "dense_rank": row.get("dense_rank"),
                    "dense_score": row.get("dense_score"),
                    "sparse_rank": row.get("sparse_rank"),
                    "sparse_score": row.get("sparse_score"),
                    "merged_score": row["merged_score"],
                },
            )
        )
    return hits


def _accumulate_source(merged: dict[str, dict[str, Any]], source_results, source_name: str, rrf_k: int) -> None:
    for rank_idx, item in enumerate(source_results, start=1):
        entity = item.entity
        chunk_id = entity.get("chunk_id", "")
        if not chunk_id:
            continue
        source_score = float(getattr(item, "score", 0.0))
        row = merged.setdefault(
            chunk_id,
            {
                "entity": entity,
                "merged_score": 0.0,
                "sources": set(),
            },
        )
        row["sources"].add(source_name)
        row[f"{source_name}_rank"] = rank_idx
        row[f"{source_name}_score"] = source_score
        row["merged_score"] += 1.0 / (rrf_k + rank_idx)
