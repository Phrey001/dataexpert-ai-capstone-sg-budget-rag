"""Specialist facade for retrieval, rerank, synthesis, and reflection."""

import os
import pickle
from pathlib import Path
from typing import Optional, Sequence

from langsmith.run_helpers import traceable

from ..core.config import AgentConfig
from ..core.types import ReflectionResult, RetrievalHit, RetrieveContextPayload
from ..guardrails.service import GuardrailsService, GuardrailsViolationError
from ..mcp.tools import missing_tool_names, resolve_tool_names
from .reflection import reflect_answer
from .rerank import rerank_hits
from .retrieval import run_retrieve
from .synthesis import synthesize_answer


class MCPReadinessError(RuntimeError):
    pass


class Specialists:
    """Concrete specialists implementation backed by MCP-style dependencies."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self._tool_names = resolve_tool_names(config)
        self._collection = None
        self._embedder = None
        self._bm25_encoder = None
        self._cross_encoder = None
        self._synthesis_model = None
        self._reflection_model = None
        self._guardrails = GuardrailsService(config)
        self.validate_ready()

    def validate_ready(self) -> None:
        if not self.config.mcp_enabled:
            raise MCPReadinessError("MCP is disabled (AGENT_MCP_ENABLED=false).")

        required_env = ["OPENAI_API_KEY", "MILVUS_URI", "MILVUS_TOKEN"]
        missing_env = [name for name in required_env if not os.getenv(name)]
        if missing_env:
            raise MCPReadinessError(f"Missing required env vars: {', '.join(missing_env)}")

        missing_tools = missing_tool_names(self._tool_names)
        if missing_tools:
            raise MCPReadinessError(f"Missing MCP tool mapping for: {', '.join(missing_tools)}")

        try:
            import pymilvus  # noqa: F401
            import sentence_transformers  # noqa: F401
            import langchain_openai  # noqa: F401
            self._guardrails.validate_imports()
        except Exception as exc:
            raise MCPReadinessError(f"Dependency import failed: {exc}") from exc

        if self.config.mcp_strict:
            try:
                self._get_collection()
                self._get_embedder()
                self._get_bm25_encoder()
                self._get_cross_encoder()
                self._get_synthesis_model()
                self._get_reflection_model()
                self._guardrails.warm_up()
            except Exception as exc:
                raise MCPReadinessError(f"Strict readiness check failed: {exc}") from exc

    @traceable(name="specialists.mcp.retrieve", run_type="tool")
    def retrieve(self, query: str, top_k: int, retrieve_context: Optional[RetrieveContextPayload] = None) -> list[RetrievalHit]:
        guarded_query = self._guardrails.guard_input(query)
        return run_retrieve(
            query=guarded_query,
            top_k=top_k,
            retrieve_context=retrieve_context or {},
            collection=self._get_collection(),
            embedder=self._get_embedder(),
            bm25_encoder=self._get_bm25_encoder(),
            retrieve_tool_name=self._tool_names["retrieve"],
            fy_filtering_enabled=self.config.fy_filtering_enabled,
            recent_year_window=self.config.recent_year_window,
            corpus_latest_fy=self.config.corpus_latest_fy,
            retrieve_recency_boost=self.config.retrieve_recency_boost,
            merge_strategy=self.config.hybrid_merge_strategy,
            rrf_k=self.config.hybrid_rrf_k,
        )

    @traceable(name="specialists.mcp.rerank", run_type="tool")
    def rerank(self, query: str, hits: Sequence[RetrievalHit], top_n: int) -> list[RetrievalHit]:
        cross_encoder = self._get_cross_encoder()
        return rerank_hits(
            query=query,
            hits=hits,
            top_n=top_n,
            rerank_tool_name=self._tool_names["rerank"],
            cross_encoder=cross_encoder,
            candidate_limit=self.config.rerank_candidate_limit,
            recent_year_window=self.config.recent_year_window,
            corpus_latest_fy=self.config.corpus_latest_fy,
            rerank_recency_boost=self.config.rerank_recency_boost,
        )

    @traceable(name="specialists.mcp.synthesize", run_type="llm")
    def synthesize(
        self,
        original_query: str,
        revised_query: str,
        hits: Sequence[RetrievalHit],
    ) -> str:
        model = self._get_synthesis_model()
        return synthesize_answer(
            model=model,
            original_query=original_query,
            revised_query=revised_query,
            hits=hits,
            guard_output=self._guardrails.guard_output,
        )

    @traceable(name="specialists.mcp.reflect", run_type="llm")
    def reflect(self, original_query: str, revised_query: str, answer: str, hits: Sequence[RetrievalHit]) -> ReflectionResult:
        model = self._get_reflection_model()
        return reflect_answer(
            model=model,
            original_query=original_query,
            revised_query=revised_query,
            answer=answer,
            hits=hits,
            guard_output=self._guardrails.guard_output,
        )

    def _get_collection(self):
        if self._collection is not None:
            return self._collection

        from pymilvus import Collection, connections

        connections.connect(uri=os.getenv("MILVUS_URI"), token=os.getenv("MILVUS_TOKEN"))
        collection = Collection(self.config.milvus_collection)
        collection.load()
        self._collection = collection
        return self._collection

    def _get_embedder(self):
        if self._embedder is not None:
            return self._embedder

        from sentence_transformers import SentenceTransformer

        self._embedder = SentenceTransformer(self.config.embedding_model, device="cpu")
        return self._embedder

    def _get_bm25_encoder(self):
        if self._bm25_encoder is not None:
            return self._bm25_encoder

        artifact_path = Path("artifacts") / "bm25_model.pkl"
        if not artifact_path.exists():
            raise RuntimeError(f"Missing BM25 artifact: {artifact_path}")
        with artifact_path.open("rb") as handle:
            self._bm25_encoder = pickle.load(handle)
        return self._bm25_encoder

    def _get_cross_encoder(self):
        if self._cross_encoder is not None:
            return self._cross_encoder

        from sentence_transformers import CrossEncoder

        self._cross_encoder = CrossEncoder(self.config.cross_encoder_model, device="cpu")
        return self._cross_encoder

    def _get_synthesis_model(self):
        if self._synthesis_model is not None:
            return self._synthesis_model

        from langchain_openai import ChatOpenAI

        self._synthesis_model = ChatOpenAI(
            model=self.config.synthesis_model,
            temperature=self.config.synthesis_temperature,
        )
        return self._synthesis_model

    def _get_reflection_model(self):
        if self._reflection_model is not None:
            return self._reflection_model

        from langchain_openai import ChatOpenAI

        self._reflection_model = ChatOpenAI(
            model=self.config.reflection_model,
            temperature=self.config.reflection_temperature,
        )
        return self._reflection_model
