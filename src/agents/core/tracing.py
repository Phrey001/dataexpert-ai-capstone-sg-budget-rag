"""Trace payload builders used by manager orchestration."""

from dataclasses import asdict
from typing import Optional

from .trace_types import RetrieveContextPayload, TraceStepPayload, TraceTransitionPayload
from .types import ManagerState, ReflectionResult


def build_step_payload(
    *,
    cycle: int,
    state_name: str,
    original_query: str,
    revised_query: str,
    retrieved: int,
    answer: str,
    reflection: ReflectionResult,
    retrieve_params: Optional[RetrieveContextPayload] = None,
) -> TraceStepPayload:
    payload: TraceStepPayload = {
        "cycle": cycle,
        "state": state_name,
        "original_query": original_query,
        "revised_query": revised_query,
        "retrieved": retrieved,
        "answer_preview": answer[:200],
        "reflection": asdict(reflection),
    }
    if retrieve_params is not None:
        payload["retrieve_params"] = retrieve_params
    return payload


def build_transition_payload(*, cycle: int, state: ManagerState, reason: str) -> TraceTransitionPayload:
    return {
        "cycle": cycle,
        "to": state.state,
        "reason": reason,
    }
