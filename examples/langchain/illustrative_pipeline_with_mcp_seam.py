"""
Illustrative example only.

This file is not used by the application runtime.
It shows the same explicit deterministic pipeline as illustrative_pipeline.py,
but adds a small MCP-inspired seam with named tools and a client wrapper.
"""

from dataclasses import dataclass
from typing import TypedDict

from langchain_openai import ChatOpenAI


class ToolNames(TypedDict):
    retrieve: str
    rerank: str
    synthesize: str
    reflect: str


DEFAULT_TOOL_NAMES: ToolNames = {
    "retrieve": "retrieve",
    "rerank": "rerank",
    "synthesize": "synthesize",
    "reflect": "reflect",
}


@dataclass
class PipelineResult:
    answer: str
    confidence: float
    final_reason: str
    tool_trace: list[str]


class RetrievalClient:
    """Small client seam that hides retrieval backend details."""

    def retrieve(self, query: str) -> list[str]:
        return [f"evidence for: {query}"]


def build_planner_model():
    return ChatOpenAI(model="gpt-4o-mini", temperature=0.0)


def build_answer_model():
    return ChatOpenAI(model="gpt-4o-mini", temperature=0.2)


def build_reflection_model():
    return ChatOpenAI(model="gpt-4o-mini", temperature=0.0)


def plan_query(model, user_query: str) -> str:
    """Placeholder for planner prompt + invoke + parse."""
    _ = model
    return user_query.strip()


def rerank_hits(revised_query: str, hits: list[str]) -> list[str]:
    """Placeholder for rerank step."""
    _ = revised_query
    return hits[:3]


def synthesize_answer(model, original_query: str, revised_query: str, hits: list[str]) -> str:
    """Placeholder for synthesis prompt + invoke."""
    _ = model
    return (
        f"Answer for '{original_query}' using revised query '{revised_query}' "
        f"and {len(hits)} evidence items."
    )


def reflect_answer(model, answer: str) -> tuple[float, str]:
    """Placeholder for reflection prompt + invoke + parse."""
    _ = model
    if answer:
        return 0.85, "confidence_high"
    return 0.0, "confidence_too_low_clarify"


def run_pipeline(user_query: str, tool_names: ToolNames | None = None) -> PipelineResult:
    """
    Example deterministic flow with an MCP-inspired seam:
    1. planner model revises the query
    2. retrieval client is called through a named tool boundary
    3. rerank/synthesize/reflect keep explicit step order

    Compared with illustrative_pipeline.py, the extra structure here is:
    - named tools
    - a small typed contract for tool names
    - a client wrapper for retrieval
    """
    names = tool_names or DEFAULT_TOOL_NAMES
    tool_trace: list[str] = []

    planner_model = build_planner_model()
    answer_model = build_answer_model()
    reflection_model = build_reflection_model()
    retrieval_client = RetrievalClient()

    revised_query = plan_query(planner_model, user_query)

    tool_trace.append(names["retrieve"])
    hits = retrieval_client.retrieve(revised_query)

    tool_trace.append(names["rerank"])
    reranked_hits = rerank_hits(revised_query, hits)

    tool_trace.append(names["synthesize"])
    answer = synthesize_answer(answer_model, user_query, revised_query, reranked_hits)

    tool_trace.append(names["reflect"])
    confidence, final_reason = reflect_answer(reflection_model, answer)

    return PipelineResult(
        answer=answer,
        confidence=confidence,
        final_reason=final_reason,
        tool_trace=tool_trace,
    )
