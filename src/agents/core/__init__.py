"""Core orchestration contracts and manager state machine."""

from .config import AgentConfig
from .manager import Manager
from .types import (
    ExecutionPlan,
    OrchestrationResult,
    PlanStep,
    ReflectionResult,
    RetrievalHit,
    UserQuery,
)

ManagerAI = Manager

__all__ = [
    "AgentConfig",
    "ExecutionPlan",
    "Manager",
    "ManagerAI",
    "OrchestrationResult",
    "PlanStep",
    "ReflectionResult",
    "RetrievalHit",
    "UserQuery",
]
