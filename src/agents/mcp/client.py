"""Lightweight MCP/Milvus client wrappers used by specialist services."""

from typing import Any, Optional


def _search_kwargs(anns_field: str, data: list[object], top_k: int, year_expr: Optional[str]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "data": data,
        "anns_field": anns_field,
        "param": {"metric_type": "IP", "params": {"ef": 64}},
        "limit": top_k,
        "output_fields": ["chunk_id", "source_path", "text", "doc_type", "financial_year"],
    }
    if year_expr:
        kwargs["expr"] = year_expr
    return kwargs


def search_collection_dense(collection, query_vector: list[float], top_k: int, year_expr: Optional[str]):
    kwargs = _search_kwargs(anns_field="dense_vector", data=[query_vector], top_k=top_k, year_expr=year_expr)
    return collection.search(**kwargs)


def search_collection_sparse(collection, sparse_query_vector: dict[int, float], top_k: int, year_expr: Optional[str]):
    kwargs = _search_kwargs(anns_field="sparse_vector", data=[sparse_query_vector], top_k=top_k, year_expr=year_expr)
    return collection.search(**kwargs)
