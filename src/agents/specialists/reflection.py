"""Reflection helper for structured answer quality evaluation."""

import json
from typing import Callable, Sequence

from ..core.types import ReflectionResult, RetrievalHit
from ..prompts import reflection as reflection_prompts


def _parse_json(raw_text: str) -> dict:
    raw = raw_text.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.removeprefix("json").strip()
    return json.loads(raw)


def reflect_answer(
    *,
    model,
    original_query: str,
    revised_query: str,
    answer: str,
    hits: Sequence[RetrievalHit],
    guard_output: Callable[[str, str], str],
) -> ReflectionResult:
    prompt = reflection_prompts.build_reflection_prompt(
        original_query=original_query,
        revised_query=revised_query,
        answer=answer,
        evidence_count=len(hits),
    )
    response = model.invoke(prompt)
    raw = str(getattr(response, "content", "")).strip()
    raw = guard_output(raw, "reflect")
    payload = _parse_json(raw)
    reason = str(payload.get("reason", "ok"))
    if reason not in {"low_coverage", "ok"}:
        reason = "low_coverage"
    confidence = float(payload.get("confidence", 0.0))
    applicability_note = str(payload.get("applicability_note", "")).strip()
    uncertainty_note = str(payload.get("uncertainty_note", "")).strip()
    if not applicability_note:
        applicability_note = "Applicability is unclear from available evidence."
    if not uncertainty_note:
        uncertainty_note = "Evidence is incomplete; verify scope and year details."
    comments = f"{applicability_note} {uncertainty_note}".strip()
    return ReflectionResult(
        reason=reason,
        confidence=max(0.0, min(confidence, 1.0)),
        comments=comments,
        applicability_note=applicability_note,
        uncertainty_note=uncertainty_note,
    )
