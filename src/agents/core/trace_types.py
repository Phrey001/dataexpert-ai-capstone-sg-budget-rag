"""TypedDict payload shapes for trace and retrieval context objects."""

from typing import Any, NotRequired, TypedDict

from .types import YearMode


class RetrieveContextPayload(TypedDict, total=False):
    original_query: str
    revised_query: str
    year_mode: YearMode
    requested_years: list[int]
    recent_year_window: int


class TraceStepPayload(TypedDict):
    cycle: int
    state: str
    original_query: str
    revised_query: str
    retrieved: int
    answer_preview: str
    reflection: dict[str, Any]
    retrieve_params: NotRequired[RetrieveContextPayload]


class TraceTransitionPayload(TypedDict):
    cycle: int
    to: str
    reason: str


class GuardrailEventPayload(TypedDict):
    stage: str
    reason: str


class CoherencePayload(TypedDict):
    label: str
    reason: str | None


class QueryChainPayload(TypedDict, total=False):
    cycle: int
    original_query: str
    revised_query: str
    source: str


class TracePayload(TypedDict, total=False):
    plan: dict[str, Any]
    transitions: list[TraceTransitionPayload]
    steps: list[TraceStepPayload]
    query_chain: list[QueryChainPayload]
    final_state: str | None
    final_reason: str | None
    guardrail_event: GuardrailEventPayload
    coherence: CoherencePayload

