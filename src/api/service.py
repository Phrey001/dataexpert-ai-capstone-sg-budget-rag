"""Service adapter that maps API requests to the agent orchestration layer."""

from __future__ import annotations

from dotenv import load_dotenv

from src.agents.core.config import AgentConfig
from src.agents.core.manager import Manager
from src.agents.core.types import UserQuery
from src.agents.planner.service import PlannerAI
from src.agents.specialists.service import MCPReadinessError, Specialists

from .schemas import AskRequest, AskResponse, HealthResponse
from .security import assess_prompt_injection


class AgentAPIService:
    """Thin service to keep FastAPI handlers small and testable."""

    def __init__(self):
        load_dotenv()
        self.base_config = AgentConfig.from_env()
        self._specialists: Specialists | None = None
        self._startup_error: str | None = None
        self._initialize_specialists()

    def _initialize_specialists(self) -> None:
        try:
            self._specialists = Specialists(config=self.base_config)
            self._startup_error = None
        except MCPReadinessError as exc:
            self._specialists = None
            self._startup_error = str(exc)

    def health(self) -> HealthResponse:
        if self._specialists is None:
            return HealthResponse(status="degraded", mcp_ready=False, message=self._startup_error or "not ready")
        return HealthResponse(status="ok", mcp_ready=True, message="ready")

    def ask(self, payload: AskRequest) -> AskResponse:
        assessment = assess_prompt_injection(payload.query)
        if assessment.blocked:
            return AskResponse(
                answer=(
                    "Sorry, I can’t process this request because it appears to contain "
                    "instruction or security override patterns. Please rephrase your "
                    "question as a normal budget query."
                ),
                confidence=0.0,
                state_history=["blocked"],
                final_reason="prompt_injection_detected",
            )

        if self._specialists is None:
            raise MCPReadinessError(self._startup_error or "MCP is not ready.")

        config = self._config_with_overrides(payload)
        planner = PlannerAI(config)
        manager = Manager(config)
        context = {}
        if payload.requested_years:
            context["requested_years"] = payload.requested_years
        user_query = UserQuery(query=payload.query, context=context or None)
        result = manager.run(
            user_query=user_query,
            planner=planner,
            specialists=self._specialists,
        )
        reflection = result.reflection or {}
        return AskResponse(
            answer=result.answer,
            confidence=result.confidence,
            state_history=result.state_history,
            final_reason=result.final_reason,
            applicability_note=reflection.get("applicability_note") if isinstance(reflection, dict) else reflection.applicability_note,
            uncertainty_note=reflection.get("uncertainty_note") if isinstance(reflection, dict) else reflection.uncertainty_note,
        )

    def _config_with_overrides(self, payload: AskRequest) -> AgentConfig:
        overrides = {
            key: value
            for key, value in {
                "top_k": payload.top_k,
                "top_n": payload.top_n,
            }.items()
            if value is not None
        }
        return self.base_config.model_copy(update=overrides)
