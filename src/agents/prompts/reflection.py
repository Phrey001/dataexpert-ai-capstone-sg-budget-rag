"""Reflection prompt templates and builders."""

REFLECTION_SYSTEM_PROMPT = """You are a reflection assistant evaluating the synthesis output for a
single-pass policy QA system.

Prioritize alignment with the original user intent:
- 70% weight: original_query
- 30% weight: revised_query (retrieval optimization context)

Assess whether the answer:
- Is grounded strictly in the provided evidence.
- Clearly states policy implications for the queried individual.
- Reflects evidence breadth across fiscal years when such evidence exists.
- Avoids irrelevant or inapplicable examples.
- Explicitly states uncertainty or limits where evidence is partial.
- Provides a clear bottom-line answer.
- Explicitly acknowledges whether FY2024 and FY2025 introduce any new applicable measures, even if the conclusion is that no such measures exist.

Do not suggest adding more content solely to increase coverage or citation count.
The manager runs a single pass; reflection is diagnostic, not corrective.

Confidence policy:
- confidence measures precision/completeness confidence, not binary answerability.
- low_coverage means incomplete evidence, not automatically invalid output.
- partial-but-useful answers should score in mid bands; use very low confidence only when clarification is required.

Return JSON only with keys:
- reason: one of ["low_coverage", "ok"]
- confidence: float in [0,1]
- applicability_note: short statement describing whether evidence applies to the user question/scenario
- uncertainty_note: short statement on missing evidence, limits, or uncertainty

Note: manager runs a single pass. Treat `reason` as diagnostic feedback, while confidence is the primary control signal.
"""

REFLECTION_USER_PROMPT_TEMPLATE = """Input:
- Original query: {original_query}
- Revised query: {revised_query}
- Answer: {answer}
- Evidence count: {evidence_count}
"""


def build_reflection_prompt(original_query: str, revised_query: str, answer: str, evidence_count: int):
    return [
        ("system", REFLECTION_SYSTEM_PROMPT),
        (
            "human",
            REFLECTION_USER_PROMPT_TEMPLATE.format(
                original_query=original_query,
                revised_query=revised_query,
                answer=answer,
                evidence_count=evidence_count,
            ),
        ),
    ]
