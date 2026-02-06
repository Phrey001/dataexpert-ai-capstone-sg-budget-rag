"""Environment-backed configuration for agent orchestration."""

import os

from pydantic import BaseModel, Field, field_validator

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    class SettingsConfigDict(dict):
        pass

    class BaseSettings(BaseModel):
        def __init__(self, **data):
            env_data = {}
            for field_name, field_info in self.__class__.model_fields.items():
                alias = field_info.alias or field_name
                if alias in os.environ:
                    env_data[field_name] = os.environ[alias]
            env_data.update(data)
            super().__init__(**env_data)


class AgentConfig(BaseSettings):
    """Environment-backed configuration for agent orchestration.

    Config usage map (selected):
    - top_k/top_n/rerank_candidate_limit: specialists/retrieval.py, specialists/rerank.py, core/manager.py
    - recent_year_window: planner/service.py, specialists/retrieval.py, specialists/rerank.py
    - corpus_latest_fy: specialists/retrieval.py, specialists/rerank.py
    - retrieve_recency_boost: specialists/retrieval.py
    - rerank_recency_boost: specialists/rerank.py
    - confidence_*: core/manager.py
    - max_cycles: core/manager.py
    - planner_model/temperature: planner/service.py
    - synthesis_model/temperature: specialists/service.py, specialists/synthesis.py
    - reflection_model/temperature: specialists/service.py, specialists/reflection.py
    - embedding_model: specialists/retrieval.py
    - cross_encoder_model: specialists/rerank.py
    - hybrid_merge_strategy/hybrid_rrf_k: specialists/retrieval.py
    - mcp_*: specialists/service.py, mcp/tools.py
    - guardrails_*: guardrails/service.py
    - langsmith_*: tracing in runtime and langsmith hooks
    """
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False, populate_by_name=True)

    # Frequently tuned (retrieval/rerank/behavior)
    top_k: int = Field(default=200, alias="AGENT_TOP_K")
    top_n: int = Field(default=100, alias="AGENT_TOP_N")  # return top_n from each list, so return 2*top_n
    rerank_candidate_limit: int = Field(default=100, alias="AGENT_RERANK_CANDIDATE_LIMIT")  # keep limit after rerank
    recent_year_window: int = Field(default=5, alias="AGENT_RECENT_YEAR_WINDOW")
    corpus_latest_fy: int = Field(default=2025, alias="AGENT_CORPUS_LATEST_FY")
    retrieve_recency_boost: float = Field(default=0.8, alias="AGENT_RETRIEVE_RECENCY_BOOST")
    rerank_recency_boost: float = Field(default=0.8, alias="AGENT_RERANK_RECENCY_BOOST")
    confidence_strong: float = Field(default=0.80, alias="AGENT_CONFIDENCE_STRONG")
    confidence_medium: float = Field(default=0.70, alias="AGENT_CONFIDENCE_MEDIUM")
    confidence_low: float = Field(default=0.50, alias="AGENT_CONFIDENCE_LOW")
    confidence_very_low: float = Field(default=0.30, alias="AGENT_CONFIDENCE_VERY_LOW")
    max_cycles: int = Field(default=3, alias="AGENT_MAX_CYCLES")

    # Model knobs (tuned occasionally)
    openai_model: str = Field(default="gpt-4o-mini", alias="AGENT_OPENAI_MODEL")
    synthesis_model: str = Field(default="gpt-4o-mini", alias="AGENT_SYNTHESIS_MODEL")
    synthesis_temperature: float = Field(default=0.2, alias="AGENT_SYNTHESIS_TEMPERATURE")
    reflection_model: str = Field(default="gpt-4o-mini", alias="AGENT_REFLECTION_MODEL")
    reflection_temperature: float = Field(default=0.0, alias="AGENT_REFLECTION_TEMPERATURE")
    planner_model: str = Field(default="gpt-4o-mini", alias="AGENT_PLANNER_MODEL")
    planner_temperature: float = Field(default=0.0, alias="AGENT_PLANNER_TEMPERATURE")
    embedding_model: str = Field(default="BAAI/bge-base-en-v1.5", alias="AGENT_EMBEDDING_MODEL")
    cross_encoder_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2", alias="AGENT_CROSS_ENCODER_MODEL"
    )

    # Less frequently tuned (infra/behavioral defaults)
    milvus_collection: str = Field(default="sg_budget_evidence", alias="AGENT_MILVUS_COLLECTION")
    mcp_enabled: bool = Field(default=True, alias="AGENT_MCP_ENABLED")
    mcp_strict: bool = Field(default=True, alias="AGENT_MCP_STRICT")
    mcp_timeout_seconds: int = Field(default=60, alias="AGENT_MCP_TIMEOUT_SECONDS")
    mcp_retrieve_tool: str = Field(default="retrieve", alias="AGENT_MCP_RETRIEVE_TOOL")
    mcp_rerank_tool: str = Field(default="rerank", alias="AGENT_MCP_RERANK_TOOL")
    mcp_synthesize_tool: str = Field(default="synthesize", alias="AGENT_MCP_SYNTHESIZE_TOOL")
    mcp_reflect_tool: str = Field(default="reflect", alias="AGENT_MCP_REFLECT_TOOL")
    hybrid_merge_strategy: str = Field(default="rrf", alias="AGENT_HYBRID_MERGE_STRATEGY")
    hybrid_rrf_k: int = Field(default=60, alias="AGENT_HYBRID_RRF_K")
    fy_filtering_enabled: bool = Field(default=True, alias="AGENT_FY_FILTERING_ENABLED")
    guardrails_enabled: bool = Field(default=True, alias="AGENT_GUARDRAILS_ENABLED")
    guardrails_input_policy: str = Field(default="block_safe_reply", alias="AGENT_GUARDRAILS_INPUT_POLICY")
    guardrails_output_policy: str = Field(default="block_safe_reply", alias="AGENT_GUARDRAILS_OUTPUT_POLICY")
    langsmith_tracing: bool = Field(default=False, alias="LANGCHAIN_TRACING_V2")
    langsmith_project: str = Field(default="sg-budget-rag", alias="LANGCHAIN_PROJECT")

    @field_validator(
        "top_k",
        "top_n",
        "max_cycles",
        "mcp_timeout_seconds",
        "recent_year_window",
        "corpus_latest_fy",
        "rerank_candidate_limit",
        "hybrid_rrf_k",
    )
    @classmethod
    def _strictly_positive_ints(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be > 0")
        return value

    @field_validator("hybrid_merge_strategy")
    @classmethod
    def _valid_merge_strategy(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"rrf"}:
            raise ValueError("must be 'rrf'")
        return normalized

    @field_validator(
        "confidence_strong",
        "confidence_medium",
        "confidence_low",
        "confidence_very_low",
        "retrieve_recency_boost",
        "rerank_recency_boost",
    )
    @classmethod
    def _valid_threshold(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("must be in [0, 1]")
        return value

    @field_validator("planner_temperature", "synthesis_temperature", "reflection_temperature")
    @classmethod
    def _valid_temperature(cls, value: float) -> float:
        if value < 0 or value > 2:
            raise ValueError("must be in [0, 2]")
        return value

    @classmethod
    def from_env(cls) -> "AgentConfig":
        return cls()
