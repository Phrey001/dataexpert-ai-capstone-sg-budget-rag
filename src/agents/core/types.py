"""Shared dataclasses and literals for planner-manager-specialist contracts."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


PlanStepName = Literal["retrieve", "rerank", "synthesize", "reflect"]
ManagerStateName = Literal["execute_plan", "success", "fail"]
ReflectionReason = Literal["low_coverage", "ok"]
YearMode = Literal["explicit", "none"]
CoherenceLabel = Literal["coherent", "incoherent"]


@dataclass
class UserQuery:
    query: str
    context: Optional[Dict[str, Any]] = None


@dataclass
class PlanStep:
    name: PlanStepName
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    steps: List[PlanStep]
    top_k: int
    top_n: int
    original_query: str
    revised_query: str
    coherence: CoherenceLabel = "coherent"
    coherence_reason: Optional[str] = None


@dataclass
class RetrievalHit:
    chunk_id: str
    source_path: str
    text: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReflectionResult:
    reason: ReflectionReason
    confidence: float
    comments: str
    applicability_note: str = ""
    uncertainty_note: str = ""


@dataclass
class ManagerState:
    state: ManagerStateName


@dataclass
class OrchestrationResult:
    answer: str
    confidence: float
    state_history: List[str]
    trace: Dict[str, Any]
