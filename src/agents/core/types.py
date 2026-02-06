"""Shared dataclasses and literals for planner-manager-specialist contracts."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


PlanStepName = Literal["retrieve", "rerank", "synthesize", "reflect"]
ManagerStateName = Literal["execute_plan", "success", "fail"]
ReflectionReason = Literal["low_coverage", "ok"]
YearMode = Literal["explicit", "recent", "range", "none"]
CoherenceLabel = Literal["coherent", "incoherent"]


@dataclass
class UserQuery:
    query: str
    context: Optional[Dict[str, Any]] = None


@dataclass
class PlanContext:
    cycle_index: int = 0
    previous_answer: Optional[str] = None
    reflection_reason: Optional[ReflectionReason] = None
    reflection_confidence: Optional[float] = None
    reflection_comments: Optional[str] = None
    prior_hit_paths: List[str] = field(default_factory=list)
    prior_state_history: List[str] = field(default_factory=list)
    requested_years: List[int] = field(default_factory=list)
    requested_year_mode: YearMode = "none"
    allow_broad_horizon: bool = False


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
    plan_context: PlanContext = field(default_factory=PlanContext)


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
