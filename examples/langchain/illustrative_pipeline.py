"""
Illustrative example only.

This file is not used by the application runtime.
It shows a simpler deterministic orchestration style that still keeps
the control flow explicit for this repo's planner/retrieval/rerank/
synthesis/reflection pipeline.
"""

from dataclasses import dataclass

from langchain_openai import ChatOpenAI


@dataclass
class PipelineResult:
    answer: str
    confidence: float
    final_reason: str


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


def retrieve_hits(revised_query: str) -> list[str]:
    """Placeholder for dense + sparse retrieval."""
    return [f"evidence for: {revised_query}"]


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


def run_pipeline(user_query: str) -> PipelineResult:
    """
    Example deterministic flow:
    1. plan query
    2. retrieve hits
    3. rerank hits
    4. synthesize answer
    5. reflect on answer

    This keeps the execution order explicit but avoids some of the wrapper
    layers used by the current repo.
    """
    planner_model = build_planner_model()
    answer_model = build_answer_model()
    reflection_model = build_reflection_model()

    revised_query = plan_query(planner_model, user_query)
    hits = retrieve_hits(revised_query)
    reranked_hits = rerank_hits(revised_query, hits)
    answer = synthesize_answer(answer_model, user_query, revised_query, reranked_hits)
    confidence, final_reason = reflect_answer(reflection_model, answer)

    return PipelineResult(
        answer=answer,
        confidence=confidence,
        final_reason=final_reason,
    )
