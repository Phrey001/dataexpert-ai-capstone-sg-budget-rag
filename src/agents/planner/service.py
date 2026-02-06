"""Planner implementation for query revision and execution-plan construction."""

import json
from typing import Any, Dict, List

from langsmith.run_helpers import traceable

from ..core.config import AgentConfig
from ..prompts import planner as planner_prompts
from ..core.types import CoherenceLabel, ExecutionPlan, PlanContext, PlanStep, UserQuery
from .year_intent import infer_year_intent, normalize_year_mode


class PlannerAI:
    """Interprets query intent and builds execution payloads for manager orchestration."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self._planner_model = None

    @traceable(name="planner.build_plan", run_type="chain")
    def build_plan(self, user_query: UserQuery) -> ExecutionPlan:
        context = user_query.context or {}
        original_query = str(context.get("original_query") or user_query.query).strip()
        plan_context = self._build_plan_context(context)
        planner_output = self._generate_planner_output(original_query=original_query, context=context, plan_context=plan_context)
        revised_query = planner_output["revised_query"].strip()
        coherence = planner_output["coherence"]
        coherence_reason = planner_output["coherence_reason"]
        if not revised_query and coherence == "coherent":
            raise RuntimeError("Planner generated an empty revised_query.")
        if not revised_query and coherence == "incoherent":
            revised_query = original_query

        year_intent = infer_year_intent(original_query, revised_query, current_year=self.config.corpus_latest_fy)
        plan_context.requested_years = year_intent["requested_years"]
        plan_context.requested_year_mode = year_intent["requested_year_mode"]
        plan_context.allow_broad_horizon = year_intent["allow_broad_horizon"]

        retrieve_params: Dict[str, Any] = {
            "original_query": original_query,
            "revised_query": revised_query,
            "year_mode": year_intent["requested_year_mode"],
            "requested_years": year_intent["requested_years"],
            "allow_broad_horizon": year_intent["allow_broad_horizon"],
            "recent_year_window": self.config.recent_year_window,
        }
        shared_query_params = {"original_query": original_query, "revised_query": revised_query}
        steps: List[PlanStep] = [
            PlanStep(name="retrieve", params=retrieve_params),
            PlanStep(name="rerank", params=shared_query_params),
            PlanStep(name="synthesize", params=shared_query_params),
            PlanStep(name="reflect", params=shared_query_params),
        ]
        return ExecutionPlan(
            steps=steps,
            top_k=self.config.top_k,
            top_n=self.config.top_n,
            original_query=original_query,
            revised_query=revised_query,
            coherence=coherence,
            coherence_reason=coherence_reason,
            plan_context=plan_context,
        )

    def _build_plan_context(self, context: Dict[str, Any]) -> PlanContext:
        state_history = context.get("prior_state_history", [])
        if not isinstance(state_history, list):
            state_history = []
        prior_hit_paths = context.get("prior_hit_paths", [])
        if not isinstance(prior_hit_paths, list):
            prior_hit_paths = []

        return PlanContext(
            cycle_index=int(context.get("cycle_index", 0) or 0),
            previous_answer=context.get("previous_answer"),
            reflection_reason=context.get("reflection_reason"),
            reflection_confidence=context.get("reflection_confidence"),
            reflection_comments=context.get("reflection_comments"),
            prior_hit_paths=[str(path) for path in prior_hit_paths],
            prior_state_history=[str(item) for item in state_history],
            requested_years=[int(year) for year in context.get("requested_years", []) if str(year).isdigit()],
            requested_year_mode=normalize_year_mode(context.get("requested_year_mode")),
            allow_broad_horizon=bool(context.get("allow_broad_horizon", False)),
        )

    def _generate_planner_output(self, original_query: str, context: Dict[str, Any], plan_context: PlanContext) -> Dict[str, Any]:
        model = self._get_planner_model()
        payload = {
            "original_query": original_query,
            "current_revised_query": context.get("revised_query") or original_query,
            "cycle_index": plan_context.cycle_index,
            "previous_answer": plan_context.previous_answer,
            "reflection_reason": plan_context.reflection_reason,
            "reflection_confidence": plan_context.reflection_confidence,
            "reflection_comments": plan_context.reflection_comments,
            "prior_hit_paths": plan_context.prior_hit_paths,
            "prior_state_history": plan_context.prior_state_history,
        }
        prompt = planner_prompts.build_planner_prompt(payload_json=json.dumps(payload))
        response = model.invoke(prompt)
        raw = str(getattr(response, "content", "")).strip()
        parsed = self._parse_json(raw)
        coherence = self._normalize_coherence(parsed.get("coherence"))
        coherence_reason = str(parsed.get("coherence_reason", "")).strip() or None
        revised_query = str(parsed.get("revised_query", "")).strip()
        if not revised_query and coherence == "coherent":
            raise RuntimeError("Planner LLM returned empty revised_query.")
        return {
            "revised_query": revised_query,
            "coherence": coherence,
            "coherence_reason": coherence_reason,
        }

    def _parse_json(self, raw_text: str) -> Dict[str, Any]:
        raw = raw_text.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            raw = raw.removeprefix("json").strip()
        return json.loads(raw)

    def _normalize_coherence(self, value: Any) -> CoherenceLabel:
        raw = str(value or "").strip().lower()
        if raw == "incoherent":
            return "incoherent"
        return "coherent"

    def _get_planner_model(self):
        if self._planner_model is not None:
            return self._planner_model

        from langchain_openai import ChatOpenAI

        self._planner_model = ChatOpenAI(model=self.config.planner_model, temperature=self.config.planner_temperature)
        return self._planner_model
