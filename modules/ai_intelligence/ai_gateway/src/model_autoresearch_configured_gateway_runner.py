"""Configured gateway runner for model AutoResearch benchmarks.

This module adapts a configured model-caller seam into the existing
``BenchmarkRunner`` contract. It verifies held-out prompt digests before any
model call and returns only digest-bound output receipts to the benchmark
harness.

It does not choose candidates, verify answers, promote models, mutate catalogs,
write PatternMemory, re-index HoloIndex, execute commands, mutate the repo, or
bind RedDog runtime defaults.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass, replace
from typing import Callable, Mapping, Protocol, Sequence

from .model_combination_benchmark_harness import (
    BenchmarkRunner,
    ModelBenchmarkCandidate,
    ModelBenchmarkTask,
    ModelBenchmarkTaskOutput,
    build_model_benchmark_candidate,
)
from .model_intelligence_outcomes import ModelOutcomeMetrics


CONFIGURED_GATEWAY_RUNNER_SCHEMA_VERSION = "model_autoresearch_configured_gateway_runner.v1"


class GatewayModelCaller(Protocol):
    """Minimal callable seam for one explicit provider/model call."""

    def call_model(
        self,
        *,
        provider: str,
        model: str,
        prompt: str,
        task_type: str,
    ) -> "GatewayModelCallResult":
        """Call one configured provider/model pair."""


class PromptSource(Protocol):
    """Digest-bound source for held-out benchmark prompt bodies."""

    def prompt_for_task(self, task: ModelBenchmarkTask) -> str:
        """Return the prompt body for ``task``."""


@dataclass(frozen=True)
class GatewayModelCallResult:
    """Digest-safe result for one provider/model call."""

    success: bool
    provider: str
    model: str
    response_text: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    cost_estimate_usd: float

    def normalized(self) -> "GatewayModelCallResult":
        return GatewayModelCallResult(
            success=bool(self.success),
            provider=_clean_required("provider", self.provider),
            model=_clean_required("model", self.model),
            response_text=str(self.response_text or ""),
            latency_ms=_non_negative_int(self.latency_ms),
            input_tokens=_non_negative_int(self.input_tokens),
            output_tokens=_non_negative_int(self.output_tokens),
            cost_estimate_usd=_non_negative_float(self.cost_estimate_usd),
        )


@dataclass(frozen=True)
class ConfiguredGatewayRunnerPolicy:
    """Bounded policy for configured AutoResearch benchmark calls."""

    allowed_providers: tuple[str, ...]
    max_prompt_chars: int = 20000
    max_calls_per_sample: int = 4
    max_cost_estimate_usd_per_sample: float = 1.0
    task_type: str = "model_autoresearch"
    allow_panel_candidates: bool = True
    schema_version: str = CONFIGURED_GATEWAY_RUNNER_SCHEMA_VERSION

    def normalized(self) -> "ConfiguredGatewayRunnerPolicy":
        providers = tuple(
            dict.fromkeys(_clean_token(item) for item in self.allowed_providers if str(item).strip())
        )
        if not providers:
            raise ValueError("configured_gateway_runner_allowed_providers_required")
        max_prompt_chars = _positive_int("max_prompt_chars", self.max_prompt_chars)
        max_calls = _positive_int("max_calls_per_sample", self.max_calls_per_sample)
        max_cost = _positive_float(
            "max_cost_estimate_usd_per_sample",
            self.max_cost_estimate_usd_per_sample,
        )
        return ConfiguredGatewayRunnerPolicy(
            allowed_providers=providers,
            max_prompt_chars=max_prompt_chars,
            max_calls_per_sample=max_calls,
            max_cost_estimate_usd_per_sample=max_cost,
            task_type=_clean_token(self.task_type or "model_autoresearch"),
            allow_panel_candidates=bool(self.allow_panel_candidates),
        )

    def to_dict(self) -> dict[str, object]:
        policy = self.normalized()
        return {
            "schema_version": policy.schema_version,
            "allowed_providers": list(policy.allowed_providers),
            "max_prompt_chars": policy.max_prompt_chars,
            "max_calls_per_sample": policy.max_calls_per_sample,
            "max_cost_estimate_usd_per_sample": policy.max_cost_estimate_usd_per_sample,
            "task_type": policy.task_type,
            "allow_panel_candidates": policy.allow_panel_candidates,
        }


@dataclass(frozen=True)
class MappingPromptSource:
    """In-memory prompt source for tests and bounded runtime adapters."""

    prompts_by_task_id: Mapping[str, str]

    def prompt_for_task(self, task: ModelBenchmarkTask) -> str:
        task_id = _clean_required("task_id", task.task_id)
        if task_id not in self.prompts_by_task_id:
            raise ValueError("configured_gateway_runner_prompt_missing")
        return str(self.prompts_by_task_id[task_id])


@dataclass(frozen=True)
class AIGatewayConfiguredModelCaller:
    """Adapter for the existing ``AIGateway`` provider registry.

    The adapter targets the exact provider/model role assignment supplied by the
    benchmark candidate. It reuses ``AIGateway._call_provider`` rather than
    importing provider SDKs or networking libraries here.
    """

    gateway: object

    def call_model(
        self,
        *,
        provider: str,
        model: str,
        prompt: str,
        task_type: str,
    ) -> GatewayModelCallResult:
        provider_name = _clean_token(provider)
        model_name = _clean_required("model", model)
        task_name = _clean_token(task_type or "model_autoresearch")
        providers = getattr(self.gateway, "providers", None)
        if not isinstance(providers, Mapping):
            raise ValueError("configured_gateway_runner_provider_registry_missing")
        provider_config = providers.get(provider_name)
        if provider_config is None or not getattr(provider_config, "api_key", None):
            raise ValueError("configured_gateway_runner_provider_unavailable")
        call_provider = getattr(self.gateway, "_call_provider", None)
        if not callable(call_provider):
            raise ValueError("configured_gateway_runner_call_provider_missing")
        routed_config = replace(
            provider_config,
            models={task_name: model_name, "quick": model_name},
        )
        started = time.monotonic()
        response = str(call_provider(routed_config, prompt, task_name) or "")
        latency_ms = int(round((time.monotonic() - started) * 1000))
        return GatewayModelCallResult(
            success=bool(response.strip()),
            provider=provider_name,
            model=model_name,
            response_text=response,
            latency_ms=latency_ms,
            input_tokens=_token_count(prompt),
            output_tokens=_token_count(response),
            cost_estimate_usd=float(_token_count(prompt)) * float(getattr(provider_config, "cost_per_token", 0.0)),
        ).normalized()


def build_configured_gateway_benchmark_runner(
    *,
    caller: GatewayModelCaller,
    prompt_source: PromptSource,
    policy: ConfiguredGatewayRunnerPolicy,
) -> BenchmarkRunner:
    """Build a ``BenchmarkRunner`` backed by an explicit configured gateway."""

    normalized_policy = policy.normalized()

    def _runner(
        task: ModelBenchmarkTask,
        candidate: ModelBenchmarkCandidate,
    ) -> ModelBenchmarkTaskOutput:
        normalized_task = task.normalized()
        prompt = str(prompt_source.prompt_for_task(normalized_task))
        _verify_prompt_digest(normalized_task.prompt_digest, prompt)
        if len(prompt) > normalized_policy.max_prompt_chars:
            raise ValueError("configured_gateway_runner_prompt_too_large")
        assignments = tuple(item.normalized() for item in candidate.role_assignments)
        if not assignments:
            raise ValueError("configured_gateway_runner_missing_role_assignments")
        expected_candidate = build_model_benchmark_candidate(assignments)
        if (
            expected_candidate.candidate_id != candidate.candidate_id
            or expected_candidate.topology_digest != candidate.topology_digest
        ):
            raise ValueError("configured_gateway_runner_candidate_mismatch")
        if len(assignments) > normalized_policy.max_calls_per_sample:
            raise ValueError("configured_gateway_runner_call_budget_exceeded")
        if len(assignments) > 1 and not normalized_policy.allow_panel_candidates:
            raise ValueError("configured_gateway_runner_panel_disabled")

        call_records: list[dict[str, object]] = []
        total_latency_ms = 0
        total_input_tokens = 0
        total_output_tokens = 0
        total_cost = 0.0
        for assignment in assignments:
            provider = _clean_token(assignment.provider)
            if provider not in normalized_policy.allowed_providers:
                raise ValueError("configured_gateway_runner_provider_not_allowed")
            model_name = _model_name_for_provider(assignment.model_id, provider)
            call_prompt = _role_prompt(
                base_prompt=prompt,
                role=assignment.role,
                candidate_id=candidate.candidate_id,
                task_id=normalized_task.task_id,
            )
            result = caller.call_model(
                provider=provider,
                model=model_name,
                prompt=call_prompt,
                task_type=normalized_policy.task_type,
            ).normalized()
            if not result.success or not result.response_text.strip():
                raise ValueError("configured_gateway_runner_call_failed")
            if result.provider != provider or result.model != model_name:
                raise ValueError("configured_gateway_runner_call_route_mismatch")
            response_digest = _content_digest(result.response_text)
            call_records.append(
                {
                    "role": assignment.role,
                    "provider": result.provider,
                    "model": result.model,
                    "response_digest": response_digest,
                    "latency_ms": result.latency_ms,
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                    "cost_estimate_usd": result.cost_estimate_usd,
                }
            )
            total_latency_ms += result.latency_ms
            total_input_tokens += result.input_tokens
            total_output_tokens += result.output_tokens
            total_cost += result.cost_estimate_usd
        if total_cost > normalized_policy.max_cost_estimate_usd_per_sample:
            raise ValueError("configured_gateway_runner_cost_budget_exceeded")
        runner_body = {
            "schema_version": CONFIGURED_GATEWAY_RUNNER_SCHEMA_VERSION,
            "task_id": normalized_task.task_id,
            "prompt_digest": normalized_task.prompt_digest,
            "candidate_id": candidate.candidate_id,
            "candidate_topology_digest": candidate.topology_digest,
            "policy_digest": _policy_digest(normalized_policy),
            "calls": call_records,
        }
        return ModelBenchmarkTaskOutput(
            output_digest=_digest_prefixed("configured_gateway_benchmark_output", runner_body),
            runner_receipt_id=_digest_prefixed("configured_gateway_benchmark_runner", runner_body),
            metrics=ModelOutcomeMetrics(
                latency_ms=total_latency_ms,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                cost_estimate_usd=round(total_cost, 8),
            ),
        ).normalized()

    return _runner


def _role_prompt(*, base_prompt: str, role: str, candidate_id: str, task_id: str) -> str:
    return (
        f"Task: {task_id}\n"
        f"Candidate: {candidate_id}\n"
        f"Role: {_clean_token(role)}\n"
        "Return only the benchmark answer for this role.\n\n"
        f"{base_prompt}"
    )


def _verify_prompt_digest(expected_digest: str, prompt: str) -> None:
    expected = _clean_required("prompt_digest", expected_digest)
    actual = _content_digest(prompt)
    if not hmac.compare_digest(expected, actual):
        raise ValueError("configured_gateway_runner_prompt_digest_mismatch")


def _model_name_for_provider(model_id: str, provider: str) -> str:
    raw = _clean_required("model_id", model_id)
    prefix = f"{provider}/"
    if raw.startswith(prefix):
        raw = raw[len(prefix) :]
    return _clean_required("model", raw)


def _policy_digest(policy: ConfiguredGatewayRunnerPolicy) -> str:
    return _digest_prefixed("configured_gateway_runner_policy", policy.to_dict())


def _content_digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _digest_prefixed(prefix: str, value: Mapping[str, object]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"


def _clean_required(name: str, value: object) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"missing_{name}")
    return text


def _clean_token(value: object) -> str:
    text = _clean_required("token", value)
    return "".join(ch if ch.isalnum() or ch in {"_", "-", ".", "/"} else "_" for ch in text)


def _positive_int(name: str, value: object) -> int:
    try:
        result = int(value)
    except Exception as exc:
        raise ValueError(f"invalid_{name}") from exc
    if result <= 0:
        raise ValueError(f"invalid_{name}")
    return result


def _non_negative_int(value: object) -> int:
    try:
        result = int(value)
    except Exception as exc:
        raise ValueError("invalid_non_negative_int") from exc
    if result < 0:
        raise ValueError("invalid_non_negative_int")
    return result


def _positive_float(name: str, value: object) -> float:
    try:
        result = float(value)
    except Exception as exc:
        raise ValueError(f"invalid_{name}") from exc
    if result <= 0.0:
        raise ValueError(f"invalid_{name}")
    return result


def _non_negative_float(value: object) -> float:
    try:
        result = float(value)
    except Exception as exc:
        raise ValueError("invalid_non_negative_float") from exc
    if result < 0.0:
        raise ValueError("invalid_non_negative_float")
    return result


def _token_count(text: str) -> int:
    return len(str(text).split())


__all__ = [
    "AIGatewayConfiguredModelCaller",
    "CONFIGURED_GATEWAY_RUNNER_SCHEMA_VERSION",
    "ConfiguredGatewayRunnerPolicy",
    "GatewayModelCallResult",
    "GatewayModelCaller",
    "MappingPromptSource",
    "PromptSource",
    "build_configured_gateway_benchmark_runner",
]
