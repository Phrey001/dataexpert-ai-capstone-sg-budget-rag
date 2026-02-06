"""Lightweight prompt-injection assessment for API boundary checks."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class InjectionAssessment:
    blocked: bool
    reason_code: str | None
    matched_rules: list[str]


_HIGH_SIGNAL_RULES: dict[str, tuple[str, ...]] = {
    "override_instructions": (
        "ignore previous instructions",
        "ignore system prompt",
        "disregard developer message",
    ),
    "prompt_exfiltration": (
        "reveal system prompt",
        "show hidden prompt",
        "print your instructions",
    ),
    "secret_or_tool_abuse": (
        "show api key",
        "reveal token",
        "print env",
        "bypass guardrails",
        "run shell command",
        "call tool directly",
    ),
}

_BASE64_BLOB_PATTERN = re.compile(r"(?:[A-Za-z0-9+/]{120,}={0,2})")


def assess_prompt_injection(query: str) -> InjectionAssessment:
    text = (query or "").strip().lower()
    matched_rules: list[str] = []

    for rule_name, patterns in _HIGH_SIGNAL_RULES.items():
        if any(pattern in text for pattern in patterns):
            matched_rules.append(rule_name)

    if _BASE64_BLOB_PATTERN.search(text):
        matched_rules.append("encoded_payload")

    if matched_rules:
        return InjectionAssessment(
            blocked=True,
            reason_code="prompt_injection_detected",
            matched_rules=sorted(set(matched_rules)),
        )

    return InjectionAssessment(blocked=False, reason_code=None, matched_rules=[])

