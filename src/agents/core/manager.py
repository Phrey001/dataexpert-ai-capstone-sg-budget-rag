"""Manager state machine orchestration for planner and specialist execution."""

from typing import Dict, Literal, Optional

from langsmith.run_helpers import traceable

from .config import AgentConfig
from ..planner.service import PlannerAI
from ..specialists.service import GuardrailsViolationError, Specialists
from .types import OrchestrationResult, ReflectionResult, RetrievalHit, RetrieveContextPayload, UserQuery


class Manager:
    """State-machine manager that executes a single deterministic plan pass."""

    def __init__(self, config: AgentConfig):
        self.config = config

    @traceable(name="manager.run", run_type="chain")
    def run(self, user_query: UserQuery, planner: PlannerAI, specialists: Specialists) -> OrchestrationResult:
        plan = planner.build_plan(user_query)
        if plan.coherence == "incoherent":
            return self._build_incoherent_reject(plan)
        state = "execute_plan"
        state_history = [state]
        revised_query = plan.revised_query
        latest_answer = ""
        latest_confidence = 0.0
        latest_reflection = ReflectionResult(reason="low_coverage", confidence=0.0, comments="not_started")
        original_query = plan.original_query
        try:
            if state == "execute_plan":
                retrieve_params = next((dict(step.params) for step in plan.steps if step.name == "retrieve"), {})
                hits = specialists.retrieve(revised_query, plan.top_k, retrieve_context=retrieve_params)
                reranked_hits = specialists.rerank(revised_query, hits, plan.top_n)
                latest_answer = specialists.synthesize(
                    original_query=original_query,
                    revised_query=revised_query,
                    hits=reranked_hits,
                )
                latest_reflection = specialists.reflect(original_query, revised_query, latest_answer, reranked_hits)
                latest_confidence = latest_reflection.confidence
                transition_reason = self._transition_reason(latest_reflection)
                state = "success"
            else:
                state = "fail"
                transition_reason = "unknown_state"
        except GuardrailsViolationError as exc:
            latest_answer = exc.safe_reply
            latest_confidence = 0.0
            latest_reflection = ReflectionResult(reason="low_coverage", confidence=0.0, comments=exc.reason)
            state = "fail"
            transition_reason = "guardrail_block"
            guardrail_event = {"stage": exc.stage, "reason": exc.reason}
        else:
            guardrail_event = None
        state_history.append(state)

        final_reason = transition_reason
        if not guardrail_event and state == "fail":
            latest_answer = self._build_polite_fallback(final_reason, latest_reflection)

        return OrchestrationResult(
            answer=latest_answer,
            confidence=latest_confidence,
            state_history=state_history,
            final_reason=final_reason,
            reflection=latest_reflection,
            guardrail_event=guardrail_event,
        )

    def _build_incoherent_reject(self, plan) -> OrchestrationResult:
        answer = (
            "Sorry, I couldn’t interpret the query clearly. "
            "Please restate your goal and include a financial year scope "
            "(for example: 'Summarize FY2025 productivity measures for SMEs')."
        )
        return OrchestrationResult(
            answer=answer,
            confidence=0.0,
            state_history=["fail"],
            final_reason="incoherent_query",
            coherence={"label": "incoherent", "reason": plan.coherence_reason},
        )

    def _transition_reason(self, reflection: ReflectionResult) -> str:
        band = self._confidence_band(reflection.confidence)
        if band == "high":
            return "confidence_high"
        if band == "medium":
            return "confidence_medium_caveated"
        if band == "low":
            return "confidence_low_partial"
        return "confidence_too_low_clarify"

    def _build_polite_fallback(self, final_reason: Optional[str], reflection: ReflectionResult) -> str:
        reason = final_reason or reflection.reason or "insufficient_confidence"
        return (
            "Sorry, I can’t answer this confidently yet. "
            f"Reason: {reason}. "
            "Please clarify the objective and narrow the financial year scope "
            "(for example: 'FY2025 productivity support for SMEs')."
        )

    def _confidence_band(self, confidence: float) -> Literal["high", "medium", "low", "very_low"]:
        if confidence >= self.config.confidence_strong:
            return "high"
        if confidence >= self.config.confidence_medium:
            return "medium"
        if confidence >= self.config.confidence_low:
            return "low"
        if confidence >= self.config.confidence_very_low:
            return "very_low"
        return "very_low"
