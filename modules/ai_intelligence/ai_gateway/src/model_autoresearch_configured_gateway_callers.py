"""Exact configured model-call adapters for AutoResearch evaluation.

These adapters preserve one admitted provider/model route.  They do not own
campaign reservation, fallback selection, server startup, or promotion.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from typing import Any, Callable, Mapping, Protocol

from modules.infrastructure.shared_utilities.local_llm_resolver import (
    require_lm_studio_backend,
)

from .model_autoresearch_configured_gateway_evidence import (
    MAX_RESPONSE_BYTES,
    bounded_non_negative_float,
    bounded_non_negative_int,
    bounded_positive_int,
    exact_model_id,
    exact_provider,
)


class GatewayModelCaller(Protocol):
    def call_model(
        self,
        *,
        provider: str,
        model: str,
        prompt: str,
        task_type: str,
        max_completion_tokens: int,
        reasoning_effort: str,
    ) -> "GatewayModelCallResult":
        """Call exactly one configured route."""


@dataclass(frozen=True)
class GatewayModelCallResult:
    success: bool
    provider: str
    model: str
    response_text: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    cost_estimate_usd: float

    def normalized(self) -> "GatewayModelCallResult":
        if type(self.success) is not bool:
            raise ValueError("invalid_gateway_model_call_success")
        if not isinstance(self.response_text, str):
            raise ValueError("invalid_gateway_model_call_response_text")
        if len(self.response_text.encode("utf-8")) > MAX_RESPONSE_BYTES:
            raise ValueError("invalid_gateway_model_call_response_text")
        return GatewayModelCallResult(
            success=self.success,
            provider=exact_provider(self.provider),
            model=exact_model_id("model", self.model),
            response_text=self.response_text,
            latency_ms=bounded_non_negative_int("latency_ms", self.latency_ms),
            input_tokens=bounded_non_negative_int("input_tokens", self.input_tokens),
            output_tokens=bounded_non_negative_int("output_tokens", self.output_tokens),
            cost_estimate_usd=bounded_non_negative_float(
                "cost_estimate_usd", self.cost_estimate_usd
            ),
        )


@dataclass(frozen=True)
class AIGatewayConfiguredModelCaller:
    gateway: object

    def call_model(self, **inputs: Any) -> GatewayModelCallResult:
        provider = exact_provider(inputs.get("provider"))
        model = exact_model_id("model", inputs.get("model"))
        completion_cap = bounded_positive_int(
            "max_completion_tokens", inputs.get("max_completion_tokens")
        )
        try:
            effort = exact_model_id("reasoning_effort", inputs.get("reasoning_effort"))
        except ValueError:
            raise ValueError("invalid_reasoning_tokens_control") from None
        task_type = exact_model_id("task_type", inputs.get("task_type"))
        prompt = inputs.get("prompt")
        if not isinstance(prompt, str):
            raise ValueError("configured_gateway_runner_prompt_invalid")
        provider_config = _provider_config(self.gateway, provider)
        routed = replace(
            provider_config,
            models={task_type: model, "quick": model},
        )
        call_provider = getattr(self.gateway, "_call_provider", None)
        if not callable(call_provider):
            raise ValueError("configured_gateway_runner_call_provider_missing")
        started = time.monotonic()
        response = call_provider(
            routed,
            prompt,
            task_type,
            max_completion_tokens=completion_cap,
            reasoning_effort=effort,
        )
        return _call_result(response, provider, model, prompt, started)


@dataclass(frozen=True)
class LMStudioConfiguredModelCaller:
    """Exact already-loaded LM Studio route; never launches or falls back."""

    backend_factory: Callable[[str], Any] = require_lm_studio_backend

    def call_model(self, **inputs: Any) -> GatewayModelCallResult:
        if exact_provider(inputs.get("provider")) != "lm_studio_local":
            raise ValueError("configured_gateway_runner_lm_studio_provider_mismatch")
        if exact_model_id("reasoning_effort", inputs.get("reasoning_effort")) != "off":
            raise ValueError(
                "configured_gateway_runner_lm_studio_reasoning_control_unsupported"
            )
        model = exact_model_id("model", inputs.get("model"))
        prompt = inputs.get("prompt")
        if not isinstance(prompt, str):
            raise ValueError("configured_gateway_runner_prompt_invalid")
        completion_cap = bounded_positive_int(
            "max_completion_tokens", inputs.get("max_completion_tokens")
        )
        started = time.monotonic()
        backend = self.backend_factory(model)
        response = backend.generate_response(prompt, max_tokens=completion_cap)
        return _call_result(response, "lm_studio_local", model, prompt, started)


@dataclass(frozen=True)
class RoutedConfiguredModelCaller:
    """Route only by the admitted provider; no fallback between callers."""

    gateway_caller: GatewayModelCaller
    lm_studio_caller: GatewayModelCaller

    def call_model(self, **inputs: Any) -> GatewayModelCallResult:
        caller = (
            self.lm_studio_caller
            if exact_provider(inputs.get("provider")) == "lm_studio_local"
            else self.gateway_caller
        )
        return caller.call_model(**inputs)


def _call_result(
    response: object,
    provider: str,
    model: str,
    prompt: str,
    started: float,
) -> GatewayModelCallResult:
    if not isinstance(response, str):
        raise ValueError("configured_gateway_runner_call_response_invalid")
    return GatewayModelCallResult(
        success=bool(response.strip()),
        provider=provider,
        model=model,
        response_text=response,
        latency_ms=int(round((time.monotonic() - started) * 1000)),
        input_tokens=_token_count(prompt),
        output_tokens=_token_count(response),
        cost_estimate_usd=0.0,
    ).normalized()


def _provider_config(gateway: object, provider: str) -> Any:
    providers = getattr(gateway, "providers", None)
    if not isinstance(providers, Mapping):
        raise ValueError("configured_gateway_runner_provider_registry_missing")
    config = providers.get(provider)
    if config is None or not getattr(config, "api_key", None):
        raise ValueError("configured_gateway_runner_provider_unavailable")
    return config


def _token_count(text: str) -> int:
    return len(text.split())


__all__ = [
    "AIGatewayConfiguredModelCaller",
    "GatewayModelCallResult",
    "GatewayModelCaller",
    "LMStudioConfiguredModelCaller",
    "RoutedConfiguredModelCaller",
]
