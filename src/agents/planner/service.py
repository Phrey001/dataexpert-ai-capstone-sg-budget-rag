"""Planner implementation for query revision and execution-plan construction."""

import json
from typing import Any, Dict, List

from langsmith.run_helpers import traceable

from ..core.config import AgentConfig
from ..prompts import planner as planner_prompts
from ..core.types import CoherenceLabel, ExecutionPlan, PlanStep, UserQuery


class PlannerAI:
    """Interprets query intent and builds execution payloads for manager orchestration."""

    def __init__(self, config: AgentConfig):
        """Initialize the planner with configuration and lazy model cache."""
        self.config = config
        self._planner_model = None

    @traceable(name="planner.build_plan", run_type="chain")
    def build_plan(self, user_query: UserQuery) -> ExecutionPlan:
        """Create an ExecutionPlan with retrieval, rerank, synthesis, and reflection steps."""
        context = user_query.context or {}
        original_query = str(context.get("original_query") or user_query.query).strip()
        planner_output = self._generate_planner_output(original_query=original_query, context=context)
        revised_query = planner_output["revised_query"].strip()
        coherence = planner_output["coherence"]
        coherence_reason = planner_output["coherence_reason"]
        if not revised_query and coherence == "coherent":
            raise RuntimeError("Planner generated an empty revised_query.")
        if not revised_query and coherence == "incoherent":
            revised_query = original_query

        requested_years = [int(year) for year in context.get("requested_years", []) if str(year).isdigit()]
        year_mode = "explicit" if requested_years else "none"

        retrieve_params: Dict[str, Any] = {
            "original_query": original_query,
            "revised_query": revised_query,
            "year_mode": year_mode,
            "requested_years": requested_years,
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
        )

    def _generate_planner_output(self, original_query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Call the planner LLM and parse revised_query + coherence fields."""
        model = self._get_planner_model()
        payload = {
            "original_query": original_query,
            "current_revised_query": context.get("revised_query") or original_query,
        }
        prompt = planner_prompts.build_planner_prompt(payload_json=json.dumps(payload))
        response = model.invoke(prompt)
        raw = str(getattr(response, "content", "")).strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            raw = raw.removeprefix("json").strip()
        parsed = json.loads(raw)
        coherence = str(parsed.get("coherence", "")).strip().lower()
        coherence = "incoherent" if coherence == "incoherent" else "coherent"
        coherence_reason = str(parsed.get("coherence_reason", "")).strip() or None
        revised_query = str(parsed.get("revised_query", "")).strip()
        if not revised_query and coherence == "coherent":
            raise RuntimeError("Planner LLM returned empty revised_query.")
        return {
            "revised_query": revised_query,
            "coherence": coherence,
            "coherence_reason": coherence_reason,
        }

    def _get_planner_model(self):
        """Lazily construct the planner chat model."""
        if self._planner_model is not None:
            return self._planner_model

        from langchain_openai import ChatOpenAI

        self._planner_model = ChatOpenAI(model=self.config.planner_model, temperature=self.config.planner_temperature)
        return self._planner_model
