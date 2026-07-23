"""Bounded configured-gateway runner for held-out model AutoResearch."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import threading
import time
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Mapping, Protocol

from .model_autoresearch_configured_gateway_evidence import (
    MAX_RESPONSE_BYTES,
    ConfiguredGatewayModelBudgetEvidence,
    ConfiguredGatewayReasoningControlEvidence,
    ConfiguredGatewayReceiptStore,
    ConfiguredGatewayRunnerCallReceipt,
    PromptGuardApprovalReceipt,
    bounded_non_negative_float,
    bounded_non_negative_int,
    bounded_positive_int,
    build_attempt_receipt,
    build_runner_receipt,
    canonical_decimal,
    digest_payload,
    exact_model_id,
    exact_provider,
    require_sha256,
)
from .model_autoresearch_output_evidence_bundle import (
    ModelAutoResearchOutputEvidenceStore,
    build_model_autoresearch_output_evidence_record,
)
from .model_combination_benchmark_harness import (
    BenchmarkRunner,
    ModelBenchmarkCandidate,
    ModelBenchmarkTask,
    ModelBenchmarkTaskOutput,
    build_model_benchmark_candidate,
)
from .model_intelligence_outcomes import ModelOutcomeMetrics


CONFIGURED_GATEWAY_RUNNER_SCHEMA_VERSION = "model_autoresearch_configured_gateway_runner.v2"


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


class PromptSource(Protocol):
    def prompt_for_task(self, task: ModelBenchmarkTask) -> str:
        """Return one held-out source prompt."""


class PromptGuard(Protocol):
    def __call__(
        self,
        *,
        prompt: str,
        task_id: str,
        source_prompt_digest: str,
    ) -> PromptGuardApprovalReceipt:
        """Approve one fully wrapped egress prompt without changing it."""


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
                "cost_estimate_usd",
                self.cost_estimate_usd,
            ),
        )


@dataclass(frozen=True)
class ConfiguredGatewayRunnerPolicy:
    allowed_providers: tuple[str, ...]
    model_budgets: tuple[ConfiguredGatewayModelBudgetEvidence, ...] = ()
    max_prompt_chars: int = 20000
    max_calls_per_sample: int = 4
    max_total_calls: int = 1
    max_cost_estimate_usd_per_sample: str = "1"
    task_type: str = "model_autoresearch"
    allow_panel_candidates: bool = False
    required_prompt_guard_contract_digest: str = ""
    required_prompt_guard_profile_digest: str = ""
    schema_version: str = CONFIGURED_GATEWAY_RUNNER_SCHEMA_VERSION

    def normalized(self) -> "ConfiguredGatewayRunnerPolicy":
        providers = tuple(exact_provider(item) for item in self.allowed_providers)
        budgets = tuple(item.normalized() for item in self.model_budgets)
        _validate_policy_collections(providers, budgets)
        if type(self.allow_panel_candidates) is not bool:
            raise ValueError("invalid_allow_panel_candidates")
        return ConfiguredGatewayRunnerPolicy(
            allowed_providers=providers,
            model_budgets=budgets,
            max_prompt_chars=bounded_positive_int("max_prompt_chars", self.max_prompt_chars),
            max_calls_per_sample=bounded_positive_int(
                "max_calls_per_sample",
                self.max_calls_per_sample,
            ),
            max_total_calls=bounded_positive_int("max_total_calls", self.max_total_calls),
            max_cost_estimate_usd_per_sample=canonical_decimal(
                "max_cost_estimate_usd_per_sample",
                self.max_cost_estimate_usd_per_sample,
            ),
            task_type=exact_model_id("task_type", self.task_type),
            allow_panel_candidates=self.allow_panel_candidates,
            required_prompt_guard_contract_digest=require_sha256(
                "required_prompt_guard_contract_digest",
                self.required_prompt_guard_contract_digest,
            ),
            required_prompt_guard_profile_digest=require_sha256(
                "required_prompt_guard_profile_digest",
                self.required_prompt_guard_profile_digest,
            ),
        )

    def to_dict(self) -> dict[str, object]:
        item = self.normalized()
        return {
            "schema_version": item.schema_version,
            "allowed_providers": list(item.allowed_providers),
            "model_budgets": [budget.to_dict() for budget in item.model_budgets],
            "max_prompt_chars": item.max_prompt_chars,
            "max_calls_per_sample": item.max_calls_per_sample,
            "max_total_calls": item.max_total_calls,
            "max_cost_estimate_usd_per_sample": item.max_cost_estimate_usd_per_sample,
            "task_type": item.task_type,
            "allow_panel_candidates": item.allow_panel_candidates,
            "required_prompt_guard_contract_digest": (
                item.required_prompt_guard_contract_digest
            ),
            "required_prompt_guard_profile_digest": item.required_prompt_guard_profile_digest,
        }


def _validate_policy_collections(providers, budgets) -> None:
    if not providers or len(set(providers)) != len(providers):
        raise ValueError("configured_gateway_runner_allowed_providers_required")
    if not budgets:
        raise ValueError("configured_gateway_runner_model_budgets_required")
    assignments = [item.assignment_model_id for item in budgets]
    routes = [(item.provider, item.api_model) for item in budgets]
    if len(assignments) != len(set(assignments)):
        raise ValueError("configured_gateway_runner_duplicate_assignment_model_budget")
    if len(routes) != len(set(routes)):
        raise ValueError("configured_gateway_runner_duplicate_route_model_budget")
    if set(providers) != {item.provider for item in budgets}:
        raise ValueError("configured_gateway_runner_model_budget_provider_set_mismatch")


@dataclass(frozen=True)
class MappingPromptSource:
    prompts_by_task_id: Mapping[str, str]

    def prompt_for_task(self, task: ModelBenchmarkTask) -> str:
        if task.task_id not in self.prompts_by_task_id:
            raise ValueError("configured_gateway_runner_prompt_missing")
        prompt = self.prompts_by_task_id[task.task_id]
        if not isinstance(prompt, str):
            raise ValueError("configured_gateway_runner_prompt_invalid")
        return prompt


@dataclass(frozen=True)
class AIGatewayConfiguredModelCaller:
    gateway: object

    def call_model(
        self,
        *,
        provider: str,
        model: str,
        prompt: str,
        task_type: str,
        max_completion_tokens: int,
        reasoning_effort: str,
    ) -> GatewayModelCallResult:
        provider_name = exact_provider(provider)
        model_name = exact_model_id("model", model)
        completion_cap = bounded_positive_int(
            "max_completion_tokens",
            max_completion_tokens,
        )
        try:
            effort = exact_model_id("reasoning_effort", reasoning_effort)
        except ValueError:
            raise ValueError("invalid_reasoning_tokens_control") from None
        provider_config = _provider_config(self.gateway, provider_name)
        routed = replace(
            provider_config,
            models={task_type: model_name, "quick": model_name},
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
        if not isinstance(response, str):
            raise ValueError("configured_gateway_runner_call_response_invalid")
        latency_ms = int(round((time.monotonic() - started) * 1000))
        input_tokens, output_tokens = _token_count(prompt), _token_count(response)
        return GatewayModelCallResult(
            success=bool(response.strip()),
            provider=provider_name,
            model=model_name,
            response_text=response,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_estimate_usd=0.0,
        ).normalized()


def _provider_config(gateway: object, provider: str):
    providers = getattr(gateway, "providers", None)
    if not isinstance(providers, Mapping):
        raise ValueError("configured_gateway_runner_provider_registry_missing")
    config = providers.get(provider)
    if config is None or not getattr(config, "api_key", None):
        raise ValueError("configured_gateway_runner_provider_unavailable")
    return config


@dataclass(frozen=True)
class _PreparedCall:
    role: str
    provider: str
    api_model: str
    prompt: str
    prompt_digest: str
    guard_report_digest: str
    budget: ConfiguredGatewayModelBudgetEvidence
    input_upper_tokens: int
    reserved_cost: Decimal


@dataclass(frozen=True)
class _PreparedRun:
    task: ModelBenchmarkTask
    candidate: ModelBenchmarkCandidate
    calls: tuple[_PreparedCall, ...]
    total_reserved_cost: Decimal


class _CallBudgetLedger:
    def __init__(self, max_total_calls: int) -> None:
        self._max_total_calls = max_total_calls
        self._claimed_calls = 0
        self._lock = threading.Lock()

    def reserve(self, count: int) -> "_RunCallReservation":
        with self._lock:
            if self._claimed_calls + count > self._max_total_calls:
                raise ValueError("configured_gateway_runner_total_call_budget_exceeded")
            self._claimed_calls += count
        return _RunCallReservation(self, count)

    def release(self, count: int) -> None:
        with self._lock:
            if count < 0 or count > self._claimed_calls:
                raise RuntimeError("configured_gateway_runner_call_budget_state_invalid")
            self._claimed_calls -= count


class _RunCallReservation:
    def __init__(self, ledger: _CallBudgetLedger, reserved: int) -> None:
        self._ledger = ledger
        self._reserved = reserved
        self._attempted = 0
        self._released = False
        self._lock = threading.Lock()

    def mark_attempted(self) -> None:
        with self._lock:
            if self._released or self._attempted >= self._reserved:
                raise RuntimeError("configured_gateway_runner_call_budget_state_invalid")
            self._attempted += 1

    def release_unattempted(self) -> None:
        with self._lock:
            if self._released:
                return
            release_count = self._reserved - self._attempted
            self._released = True
        self._ledger.release(release_count)


def build_configured_gateway_benchmark_runner(
    *,
    caller: GatewayModelCaller,
    prompt_source: PromptSource,
    policy: ConfiguredGatewayRunnerPolicy,
    prompt_guard: PromptGuard | None = None,
    output_evidence_store: ModelAutoResearchOutputEvidenceStore | None = None,
    runner_receipt_store: ConfiguredGatewayReceiptStore | None = None,
    call_attempt_receipt_store: ConfiguredGatewayReceiptStore | None = None,
) -> BenchmarkRunner:
    normalized_policy = policy.normalized()
    if prompt_guard is None:
        raise ValueError("configured_gateway_runner_prompt_guard_required")
    policy_digest = digest_payload(normalized_policy.to_dict())
    call_budget = _CallBudgetLedger(normalized_policy.max_total_calls)

    def _runner(task, candidate):
        prepared = _prepare_run(
            task=task,
            candidate=candidate,
            prompt_source=prompt_source,
            prompt_guard=prompt_guard,
            policy=normalized_policy,
        )
        reservation = call_budget.reserve(len(prepared.calls))
        try:
            return _execute_run(
                prepared=prepared,
                caller=caller,
                policy=normalized_policy,
                policy_digest=policy_digest,
                output_evidence_store=output_evidence_store,
                runner_receipt_store=runner_receipt_store,
                call_attempt_receipt_store=call_attempt_receipt_store,
                reservation=reservation,
            )
        finally:
            reservation.release_unattempted()

    return _runner


def _prepare_run(*, task, candidate, prompt_source, prompt_guard, policy) -> _PreparedRun:
    normalized_task = task.normalized()
    source_prompt = prompt_source.prompt_for_task(normalized_task)
    _verify_prompt_digest(normalized_task.prompt_digest, source_prompt)
    if len(source_prompt) > policy.max_prompt_chars:
        raise ValueError("configured_gateway_runner_prompt_too_large")
    assignments = tuple(item.normalized() for item in candidate.role_assignments)
    expected = build_model_benchmark_candidate(assignments)
    if not assignments or expected != candidate:
        raise ValueError("configured_gateway_runner_candidate_mismatch")
    if len(assignments) > policy.max_calls_per_sample:
        raise ValueError("configured_gateway_runner_call_budget_exceeded")
    if len(assignments) > 1 and not policy.allow_panel_candidates:
        raise ValueError("configured_gateway_runner_panel_disabled")
    budget_map = {item.assignment_model_id: item for item in policy.model_budgets}
    prepared = tuple(
        _prepare_call(
            assignment=item,
            budget=budget_map.get(item.model_id),
            source_prompt=source_prompt,
            task=normalized_task,
            candidate=candidate,
            prompt_guard=prompt_guard,
            policy=policy,
        )
        for item in assignments
    )
    total = sum((item.reserved_cost for item in prepared), Decimal(0))
    if total > Decimal(policy.max_cost_estimate_usd_per_sample):
        raise ValueError("configured_gateway_runner_cost_reservation_exceeded")
    return _PreparedRun(normalized_task, candidate, prepared, total)


def _prepare_call(
    *,
    assignment,
    budget,
    source_prompt,
    task,
    candidate,
    prompt_guard,
    policy,
) -> _PreparedCall:
    if assignment.provider not in policy.allowed_providers:
        raise ValueError("configured_gateway_runner_provider_not_allowed")
    if budget is None:
        raise ValueError("configured_gateway_runner_model_not_allowed")
    if assignment.provider != budget.provider:
        raise ValueError("configured_gateway_runner_model_not_allowed")
    prompt = _role_prompt(
        base_prompt=source_prompt,
        role=assignment.role,
        candidate_id=candidate.candidate_id,
        task_id=task.task_id,
    )
    if len(prompt) > policy.max_prompt_chars:
        raise ValueError("configured_gateway_runner_prompt_too_large")
    approval = _guard_prompt(prompt_guard, prompt, task, policy)
    input_upper = len(prompt.encode("utf-8")) + budget.request_overhead_input_tokens
    reserved = (
        Decimal(input_upper) * Decimal(budget.input_cost_per_million)
        + Decimal(budget.max_completion_tokens)
        * Decimal(budget.output_cost_per_million)
    ) / Decimal(1_000_000)
    return _PreparedCall(
        role=assignment.role,
        provider=budget.provider,
        api_model=budget.api_model,
        prompt=prompt,
        prompt_digest=_content_digest(prompt),
        guard_report_digest=approval.report_digest,
        budget=budget,
        input_upper_tokens=input_upper,
        reserved_cost=reserved,
    )


def _guard_prompt(guard, prompt, task, policy) -> PromptGuardApprovalReceipt:
    try:
        result = guard(
            prompt=prompt,
            task_id=task.task_id,
            source_prompt_digest=task.prompt_digest,
        )
        approval = result.normalized()
    except Exception:
        raise ValueError("configured_gateway_runner_prompt_guard_failed") from None
    if not approval.passed:
        raise ValueError("configured_gateway_runner_prompt_guard_blocked")
    if approval.prompt.encode("utf-8") != prompt.encode("utf-8"):
        raise ValueError("configured_gateway_runner_prompt_guard_changed")
    if approval.contract_digest != policy.required_prompt_guard_contract_digest:
        raise ValueError("configured_gateway_runner_prompt_guard_contract_mismatch")
    if approval.profile_digest != policy.required_prompt_guard_profile_digest:
        raise ValueError("configured_gateway_runner_prompt_guard_profile_mismatch")
    return approval


def _execute_run(
    *,
    prepared,
    caller,
    policy,
    policy_digest,
    output_evidence_store,
    runner_receipt_store,
    call_attempt_receipt_store,
    reservation,
) -> ModelBenchmarkTaskOutput:
    call_receipts = []
    for item in prepared.calls:
        call_receipts.append(
            _execute_call(
                prepared=prepared,
                item=item,
                caller=caller,
                policy=policy,
                policy_digest=policy_digest,
                output_evidence_store=output_evidence_store,
                attempt_store=call_attempt_receipt_store,
                reservation=reservation,
            )
        )
    total_text = format(prepared.total_reserved_cost, "f")
    receipt = build_runner_receipt(
        task_id=prepared.task.task_id,
        candidate_id=prepared.candidate.candidate_id,
        source_prompt_digest=prepared.task.prompt_digest,
        policy_digest=policy_digest,
        guard_contract_digest=policy.required_prompt_guard_contract_digest,
        guard_profile_digest=policy.required_prompt_guard_profile_digest,
        total_reserved_cost_usd=total_text,
        calls=call_receipts,
    )
    if runner_receipt_store is not None:
        try:
            stored_id = runner_receipt_store.append(receipt)
        except Exception:
            raise ValueError("configured_gateway_runner_success_receipt_failed") from None
        if stored_id != receipt.receipt_id:
            raise ValueError("configured_gateway_runner_success_receipt_mismatch")
    return _task_output(receipt, prepared.total_reserved_cost)


def _execute_call(
    *,
    prepared,
    item,
    caller,
    policy,
    policy_digest,
    output_evidence_store,
    attempt_store,
    reservation,
) -> ConfiguredGatewayRunnerCallReceipt:
    attempt_group_id = digest_payload(
        {
            "task_id": prepared.task.task_id,
            "candidate_id": prepared.candidate.candidate_id,
            "role": item.role,
            "sent_prompt_digest": item.prompt_digest,
        }
    )
    fields = _attempt_fields(prepared, item)
    _persist_attempt(attempt_store, attempt_group_id, "ATTEMPTED", None, fields)
    reservation.mark_attempted()
    raw_result = _invoke_model_call(
        caller=caller,
        item=item,
        task_type=policy.task_type,
        attempt_store=attempt_store,
        attempt_group_id=attempt_group_id,
        fields=fields,
    )
    return _validate_and_record_result(
        raw_result=raw_result,
        prepared=prepared,
        item=item,
        policy_digest=policy_digest,
        output_evidence_store=output_evidence_store,
        attempt_store=attempt_store,
        attempt_group_id=attempt_group_id,
        fields=fields,
    )


def _invoke_model_call(
    *,
    caller,
    item,
    task_type,
    attempt_store,
    attempt_group_id,
    fields,
):
    try:
        return caller.call_model(
            provider=item.provider,
            model=item.api_model,
            prompt=item.prompt,
            task_type=task_type,
            max_completion_tokens=item.budget.max_completion_tokens,
            reasoning_effort=item.budget.reasoning_control.effort,
        )
    except BaseException as exc:
        status = "CANCELLED" if isinstance(
            exc, (asyncio.CancelledError, KeyboardInterrupt, SystemExit)
        ) else "FAILED"
        try:
            _persist_terminal(attempt_store, attempt_group_id, status, fields)
        except BaseException:
            if not isinstance(exc, Exception):
                raise exc.with_traceback(exc.__traceback__)
            raise
        if isinstance(exc, Exception):
            raise ValueError("configured_gateway_runner_call_failed") from None
        raise


def _validate_and_record_result(
    *,
    raw_result,
    prepared,
    item,
    policy_digest,
    output_evidence_store,
    attempt_store,
    attempt_group_id,
    fields,
):
    try:
        result = raw_result.normalized()
    except Exception:
        _persist_terminal(attempt_store, attempt_group_id, "REJECTED_OUTPUT", fields)
        raise ValueError("configured_gateway_runner_call_result_invalid") from None
    if result.provider != item.provider or result.model != item.api_model:
        _persist_terminal(attempt_store, attempt_group_id, "ROUTE_MISMATCH", fields)
        raise ValueError("configured_gateway_runner_call_route_mismatch")
    if not result.success or not result.response_text.strip():
        _persist_terminal(attempt_store, attempt_group_id, "FAILED", fields)
        raise ValueError("configured_gateway_runner_call_failed")
    if result.output_tokens > item.budget.max_completion_tokens:
        _persist_terminal(attempt_store, attempt_group_id, "REJECTED_OUTPUT", fields)
        raise ValueError("configured_gateway_runner_output_tokens_exceeded")
    if result.input_tokens > item.input_upper_tokens:
        _persist_terminal(attempt_store, attempt_group_id, "REJECTED_OUTPUT", fields)
        raise ValueError("configured_gateway_runner_input_tokens_exceeded")
    try:
        evidence = _build_output_evidence(
            prepared, item, result, policy_digest
        )
    except Exception as exc:
        _persist_terminal(attempt_store, attempt_group_id, "REJECTED_OUTPUT", fields)
        if isinstance(exc, ValueError):
            raise
        raise ValueError("configured_gateway_runner_output_rejected") from None
    evidence_id = None
    if output_evidence_store is not None:
        try:
            evidence_id = output_evidence_store.append(evidence)
        except Exception:
            _persist_terminal(attempt_store, attempt_group_id, "EVIDENCE_FAILED", fields)
            raise ValueError("configured_gateway_runner_output_evidence_failed") from None
        if evidence_id != evidence.record_id:
            _persist_terminal(attempt_store, attempt_group_id, "EVIDENCE_FAILED", fields)
            raise ValueError("configured_gateway_runner_output_evidence_failed")
    _persist_terminal(attempt_store, attempt_group_id, "COMPLETED", fields)
    return _call_receipt(item, result, evidence_id)


def _build_output_evidence(prepared, item, result, policy_digest):
    return build_model_autoresearch_output_evidence_record(
        task_id=prepared.task.task_id,
        prompt_digest=prepared.task.prompt_digest,
        candidate_id=prepared.candidate.candidate_id,
        candidate_topology_digest=prepared.candidate.topology_digest,
        role=item.role,
        provider=result.provider,
        model=result.model,
        policy_digest=policy_digest,
        response_text=result.response_text,
        latency_ms=result.latency_ms,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost_estimate_usd=float(item.reserved_cost),
    )


def _call_receipt(item, result, evidence_id):
    return ConfiguredGatewayRunnerCallReceipt(
        role=item.role,
        provider=result.provider,
        api_model=result.model,
        sent_prompt_digest=item.prompt_digest,
        guard_report_digest=item.guard_report_digest,
        response_digest=_content_digest(result.response_text),
        reserved_cost_usd=format(item.reserved_cost, "f"),
        latency_ms=result.latency_ms,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        output_evidence_record_id=evidence_id,
    )


def _attempt_fields(prepared, item):
    return {
        "task_id": prepared.task.task_id,
        "candidate_id": prepared.candidate.candidate_id,
        "role": item.role,
        "provider": item.provider,
        "api_model": item.api_model,
        "source_prompt_digest": prepared.task.prompt_digest,
        "sent_prompt_digest": item.prompt_digest,
        "reserved_cost_usd": format(item.reserved_cost, "f"),
    }


def _persist_attempt(store, group_id, status, reason, fields) -> None:
    if store is None:
        return
    receipt = build_attempt_receipt(
        attempt_group_id=group_id,
        status=status,
        terminal_reason=reason,
        fields=fields,
    )
    try:
        stored_id = store.append(receipt)
    except Exception:
        if status == "ATTEMPTED":
            raise ValueError("configured_gateway_runner_attempt_evidence_unavailable") from None
        raise ValueError("configured_gateway_runner_attempt_evidence_indeterminate") from None
    if stored_id != receipt.attempt_receipt_id:
        raise ValueError("configured_gateway_runner_attempt_evidence_mismatch")


def _persist_terminal(store, group_id, status, fields) -> None:
    _persist_attempt(store, group_id, status, status.lower(), fields)


def _task_output(receipt, total_cost):
    body = receipt.to_dict()
    total_latency = sum(item.latency_ms for item in receipt.calls)
    total_input = sum(item.input_tokens for item in receipt.calls)
    total_output = sum(item.output_tokens for item in receipt.calls)
    return ModelBenchmarkTaskOutput(
        output_digest="configured_gateway_benchmark_output:" + digest_payload(body)[7:],
        runner_receipt_id=receipt.receipt_id,
        metrics=ModelOutcomeMetrics(
            latency_ms=total_latency,
            input_tokens=total_input,
            output_tokens=total_output,
            cost_estimate_usd=float(total_cost),
        ),
    ).normalized()


def _role_prompt(*, base_prompt: str, role: str, candidate_id: str, task_id: str) -> str:
    return (
        f"Task: {task_id}\n"
        f"Candidate: {candidate_id}\n"
        f"Role: {role}\n"
        "Return only the benchmark answer for this role.\n\n"
        f"{base_prompt}"
    )


def _verify_prompt_digest(expected_digest: str, prompt: str) -> None:
    expected = require_sha256("prompt_digest", expected_digest)
    if not hmac.compare_digest(expected, _content_digest(prompt)):
        raise ValueError("configured_gateway_runner_prompt_digest_mismatch")


def _content_digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _token_count(text: str) -> int:
    return len(text.split())


__all__ = [
    "AIGatewayConfiguredModelCaller",
    "CONFIGURED_GATEWAY_RUNNER_SCHEMA_VERSION",
    "ConfiguredGatewayModelBudgetEvidence",
    "ConfiguredGatewayReasoningControlEvidence",
    "ConfiguredGatewayRunnerPolicy",
    "GatewayModelCallResult",
    "GatewayModelCaller",
    "MappingPromptSource",
    "PromptGuardApprovalReceipt",
    "PromptSource",
    "build_configured_gateway_benchmark_runner",
]
