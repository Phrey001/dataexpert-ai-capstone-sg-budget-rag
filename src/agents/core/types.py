"""Shared dataclasses and literals for planner-manager-specialist contracts."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, TypedDict


PlanStepName = Literal["retrieve", "rerank", "synthesize", "reflect"]
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


class RetrieveContextPayload(TypedDict, total=False):
    original_query: str
    revised_query: str
    year_mode: YearMode
    requested_years: list[int]
    recent_year_window: int




@dataclass
class OrchestrationResult:
    answer: str
    confidence: float
    state_history: List[str]
    final_reason: Optional[str] = None
    reflection: Optional[ReflectionResult] = None
    guardrail_event: Optional[Dict[str, Any]] = None
    coherence: Optional[Dict[str, Any]] = None
