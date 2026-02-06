"""GuardrailsAI adapter for input/output safety checks."""

import importlib
from typing import Sequence

from ..core.config import AgentConfig


class GuardrailsViolationError(RuntimeError):
    def __init__(self, stage: str, reason: str, safe_reply: str):
        super().__init__(f"Guardrails blocked at {stage}: {reason}")
        self.stage = stage
        self.reason = reason
        self.safe_reply = safe_reply


class GuardrailsService:
    def __init__(self, config: AgentConfig):
        self.config = config
        self._guardrails_module = None
        self._input_guard = None
        self._output_guard = None

    def validate_imports(self) -> None:
        if self.config.guardrails_enabled:
            import guardrails  # noqa: F401

    def warm_up(self) -> None:
        if not self.config.guardrails_enabled:
            return
        self._build_input_guard()
        self._build_output_guard()

    def guard_input(self, text: str) -> str:
        if not self.config.guardrails_enabled:
            return text
        return self._run_guardrails(text=text, stage="input", policy=self.config.guardrails_input_policy)

    def guard_output(self, text: str, stage: str) -> str:
        if not self.config.guardrails_enabled:
            return text
        return self._run_guardrails(text=text, stage=stage, policy=self.config.guardrails_output_policy)

    def _run_guardrails(self, text: str, stage: str, policy: str) -> str:
        guard = self._build_input_guard() if stage == "input" else self._build_output_guard()
        try:
            result = guard.validate(text)
        except Exception as exc:
            if policy == "block_safe_reply":
                raise GuardrailsViolationError(
                    stage=stage,
                    reason=f"guardrails_validation_failed:{exc}",
                    safe_reply=self._safe_reply_for(stage),
                ) from exc
            return text

        if getattr(result, "validation_passed", True):
            return text
        if policy == "block_safe_reply":
            reason = getattr(result, "error", None) or "guardrails_validation_failed"
            raise GuardrailsViolationError(stage=stage, reason=str(reason), safe_reply=self._safe_reply_for(stage))
        return text

    def _build_input_guard(self):
        if self._input_guard is not None:
            return self._input_guard
        Guard, toxic_validator_cls = self._guardrails_bundle()
        self._input_guard = Guard().use(toxic_validator_cls(on_fail="exception"))
        return self._input_guard

    def _build_output_guard(self):
        if self._output_guard is not None:
            return self._output_guard
        Guard, toxic_validator_cls = self._guardrails_bundle()
        self._output_guard = Guard().use(toxic_validator_cls(on_fail="exception"))
        return self._output_guard

    def _guardrails_bundle(self):
        module = self._get_guardrails_module()
        Guard = getattr(module, "Guard")
        toxicity_validator_cls = self._load_guardrails_validator(
            candidates=(
                ("guardrails.hub", "ToxicLanguage"),
                ("guardrails.hub", "Toxicity"),
                ("guardrails.hub", "ToxicLanguageValidator"),
            )
        )
        return Guard, toxicity_validator_cls

    def _load_guardrails_validator(self, candidates: Sequence[tuple[str, str]]):
        for module_name, class_name in candidates:
            try:
                module = importlib.import_module(module_name)
            except Exception:
                continue
            validator_cls = getattr(module, class_name, None)
            if validator_cls is not None:
                return validator_cls
        joined = ", ".join(f"{module}.{name}" for module, name in candidates)
        raise ImportError(f"No supported Guardrails validator found. Tried: {joined}")

    def _safe_reply_for(self, stage: str) -> str:
        if stage == "input":
            return (
                "Sorry, I can’t process that request as written due to safety checks. "
                "Please remove sensitive personal details or harmful language and try again."
            )
        return "Sorry, I can’t provide that response safely. Please rephrase your request with non-sensitive details."

    def _get_guardrails_module(self):
        if self._guardrails_module is not None:
            return self._guardrails_module
        self._guardrails_module = importlib.import_module("guardrails")
        return self._guardrails_module
