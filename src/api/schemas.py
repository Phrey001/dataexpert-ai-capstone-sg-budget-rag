"""Request/response models for the FastAPI layer."""

from typing import Literal

from pydantic import BaseModel


class AskRequest(BaseModel):
    query: str
    top_k: int | None = None
    top_n: int | None = None
    requested_years: list[int] | None = None


class AskResponse(BaseModel):
    answer: str
    confidence: float
    state_history: list[str]
    final_reason: str | None = None
    applicability_note: str | None = None
    uncertainty_note: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    mcp_ready: bool
    message: str
