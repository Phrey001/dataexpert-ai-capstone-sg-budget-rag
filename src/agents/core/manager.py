"""Manager state machine orchestration for planner and specialist execution."""

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Optional

from langsmith.run_helpers import traceable

from .config import AgentConfig
from ..planner.service import PlannerAI
from ..specialists.service import GuardrailsViolationError, Specialists
from .trace_types import RetrieveContextPayload, TracePayload
from .tracing import build_step_payload, build_transition_payload
from .types import ManagerState, OrchestrationResult, ReflectionResult, RetrievalHit, UserQuery


@dataclass
class RunContext:
    latest_answer: str = ""
    latest_confidence: float = 0.0
    latest_hits: list[RetrievalHit] = field(default_factory=list)
    latest_reflection: ReflectionResult = field(
        default_factory=lambda: ReflectionResult(reason="low_coverage", confidence=0.0, comments="not_started")
    )
    state_history: list[str] = field(default_factory=list)
    revised_query: str = ""


class Manager:
    """State-machine manager that executes a single deterministic plan pass."""

    def __init__(self, config: AgentConfig):
        self.config = config

    @traceable(name="manager.run", run_type="chain")
    def run(self, user_query: UserQuery, planner: PlannerAI, specialists: Specialists) -> OrchestrationResult:
        plan = planner.build_plan(user_query)
        if plan.coherence == "incoherent":
            return self._build_incoherent_reject(plan)
        state = ManagerState(state="execute_plan")
        ctx = RunContext(state_history=[state.state], revised_query=plan.revised_query)
        original_query = plan.original_query
        trace: TracePayload = {
            "plan": asdict(plan),
            "transitions": [],
            "steps": [],
            "query_chain": [{"cycle": 0, "original_query": original_query, "revised_query": plan.revised_query}],
            "final_state": None,
            "final_reason": None,
        }

        try:
            if state.state == "execute_plan":
                transition_reason = self._handle_execute(ctx, state, plan, original_query, specialists, trace)
            else:
                state.state = "fail"
                transition_reason = "unknown_state"
        except GuardrailsViolationError as exc:
            ctx.latest_answer = exc.safe_reply
            ctx.latest_confidence = 0.0
            ctx.latest_reflection = ReflectionResult(reason="low_coverage", confidence=0.0, comments=exc.reason)
            state.state = "fail"
            transition_reason = "guardrail_block"
            trace["guardrail_event"] = {"stage": exc.stage, "reason": exc.reason}

        trace["transitions"].append(build_transition_payload(cycle=1, state=state, reason=transition_reason))
        ctx.state_history.append(state.state)

        trace["final_state"] = state.state
        trace["final_reason"] = trace["transitions"][-1]["reason"] if trace["transitions"] else None
        ctx.latest_answer = self._apply_terminal_fallback(
            answer=ctx.latest_answer,
            state=state,
            trace=trace,
            reflection=ctx.latest_reflection,
        )

        return OrchestrationResult(
            answer=ctx.latest_answer,
            confidence=ctx.latest_confidence,
            state_history=ctx.state_history,
            trace=trace,
        )

    def _build_incoherent_reject(self, plan) -> OrchestrationResult:
        trace: TracePayload = {
            "plan": asdict(plan),
            "transitions": [],
            "steps": [],
            "query_chain": [],
            "final_state": "fail",
            "final_reason": "incoherent_query",
            "coherence": {"label": "incoherent", "reason": plan.coherence_reason},
        }
        answer = (
            "Sorry, I couldn’t interpret the query clearly. "
            "Please restate your goal and include a financial year scope "
            "(for example: 'Summarize FY2025 productivity measures for SMEs')."
        )
        return OrchestrationResult(
            answer=answer,
            confidence=0.0,
            state_history=["fail"],
            trace=trace,
        )

    def _handle_execute(
        self,
        ctx: RunContext,
        state: ManagerState,
        plan,
        original_query: str,
        specialists: Specialists,
        trace: TracePayload,
    ) -> str:
        retrieve_params = self._step_params(plan, "retrieve")
        ctx.latest_hits = specialists.retrieve(ctx.revised_query, plan.top_k, retrieve_context=retrieve_params)
        reranked_hits = specialists.rerank(ctx.revised_query, ctx.latest_hits, plan.top_n)
        ctx.latest_answer, ctx.latest_reflection, ctx.latest_confidence = self._run_synthesis_reflection(
            specialists=specialists,
            original_query=original_query,
            revised_query=ctx.revised_query,
            hits=reranked_hits,
        )
        trace["steps"].append(
            build_step_payload(
                cycle=1,
                state_name=state.state,
                original_query=original_query,
                revised_query=plan.revised_query,
                retrieved=len(reranked_hits),
                answer=ctx.latest_answer,
                reflection=ctx.latest_reflection,
                retrieve_params=retrieve_params,
            )
        )
        state, transition_reason, _ = self._transition(state, ctx.latest_reflection)
        return transition_reason

    def _run_synthesis_reflection(
        self,
        *,
        specialists: Specialists,
        original_query: str,
        revised_query: str,
        hits: list[RetrievalHit],
    ) -> tuple[str, ReflectionResult, float]:
        answer = specialists.synthesize(
            original_query=original_query,
            revised_query=revised_query,
            hits=hits,
        )
        reflection = specialists.reflect(original_query, revised_query, answer, hits)
        return answer, reflection, reflection.confidence

    def _apply_terminal_fallback(
        self,
        answer: str,
        state: ManagerState,
        trace: TracePayload,
        reflection: ReflectionResult,
    ) -> str:
        if trace.get("guardrail_event"):
            return answer
        final_reason = trace.get("final_reason")
        if state.state == "fail":
            return self._build_polite_fallback(final_reason, reflection)
        return answer

    def _transition(
        self,
        state: ManagerState,
        reflection: ReflectionResult,
    ) -> tuple[ManagerState, str, Optional[str]]:
        band = self._confidence_band(reflection.confidence)
        if band == "high":
            state.state = "success"
            return state, "confidence_high", None
        if band == "medium":
            state.state = "success"
            return state, "confidence_medium_caveated", reflection.comments
        if band == "low":
            state.state = "success"
            return state, "confidence_low_partial", reflection.comments
        state.state = "success"
        return state, "confidence_too_low_clarify", reflection.comments

    def _step_params(self, plan, step_name: str) -> RetrieveContextPayload:
        for step in plan.steps:
            if step.name == step_name:
                return dict(step.params)
        return {}

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
