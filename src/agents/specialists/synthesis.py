"""Synthesis helper for evidence-grounded answer generation."""

import json
from typing import Callable, Optional, Sequence

from ..core.types import RetrievalHit
from ..prompts import synthesis as synthesis_prompts


def synthesize_answer(
    *,
    model,
    original_query: str,
    revised_query: str,
    hits: Sequence[RetrievalHit],
    guard_output: Callable[[str, str], str],
) -> str:
    evidence = [{"source_path": hit.source_path, "text": hit.text, "score": hit.score} for hit in hits[:8]]
    prompt = synthesis_prompts.build_synthesis_prompt(
        original_query=original_query,
        revised_query=revised_query,
        evidence_json=json.dumps(evidence),
    )
    response = model.invoke(prompt)
    content = getattr(response, "content", "")
    if isinstance(content, list):
        content = "\n".join(str(item) for item in content)
    text = str(content).strip()
    if not text:
        raise RuntimeError("Synthesis tool returned empty response.")
    return guard_output(text, "synthesize")
