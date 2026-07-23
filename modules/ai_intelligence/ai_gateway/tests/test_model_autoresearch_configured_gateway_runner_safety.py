"""Adversarial safety contract for the configured AutoResearch gateway runner."""

from __future__ import annotations

import ast
import asyncio
import hashlib
import importlib
import inspect
import json
import math
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path

import pytest

from modules.ai_intelligence.ai_gateway.src import (
    model_autoresearch_configured_gateway_runner as runner_module,
)
from modules.ai_intelligence.ai_gateway.src.ai_gateway import AIGateway, ProviderConfig
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_execution_artifact_supply_bootstrap import (
    run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_configured_gateway_runner import (
    AIGatewayConfiguredModelCaller,
    ConfiguredGatewayRunnerPolicy,
    GatewayModelCallResult,
    MappingPromptSource,
    build_configured_gateway_benchmark_runner,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_output_evidence_bundle import (
    InMemoryModelAutoResearchOutputEvidenceStore,
)
from modules.ai_intelligence.ai_gateway.src.model_combination_benchmark_harness import (
    ModelBenchmarkRoleAssignment,
    ModelBenchmarkTask,
    build_model_benchmark_candidate,
)
from modules.communication.moltbot_bridge.src.fusion_redaction_gate import (
    evaluate_redaction_gate,
)


def _digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


GUARD_CONTRACT_DIGEST = _digest("canonical-autoresearch-prompt-guard-contract-v1")
GUARD_PROFILE_DIGEST = _digest("canonical-local-autoresearch-prompt-guard-profile-v1")
GUARD_REPORT_DIGEST = _digest("canonical-local-autoresearch-prompt-approved-v1")
CATALOG_EVIDENCE_DIGEST = _digest("openrouter-model-catalog-2026-07-24")
SOURCE_PROMPT = "Audit the bounded RedDog runtime path."


def _task(prompt: str = SOURCE_PROMPT) -> ModelBenchmarkTask:
    return ModelBenchmarkTask(
        task_id="task-001",
        task_family="architecture",
        prompt_digest=_digest(prompt),
        expected_output_digest=_digest("expected-output"),
        verifier_contract_digest=_digest("verifier-contract"),
    )


def _candidate(
    assignment_model_id: str = "openrouter/z-ai/glm-5.2",
    *,
    provider: str = "openrouter",
):
    return build_model_benchmark_candidate(
        (
            ModelBenchmarkRoleAssignment(
                role="principal",
                model_id=assignment_model_id,
                provider=provider,
            ),
        )
    )


def _budget(
    *,
    assignment_model_id: object = "openrouter/z-ai/glm-5.2",
    provider: object = "openrouter",
    api_model: object = "z-ai/glm-5.2",
    input_cost_per_million: object = "2.5",
    output_cost_per_million: object = "7.25",
    request_overhead_input_tokens: object = 11,
    max_completion_tokens: object = 13,
    reasoning_mode: object = "effort",
    reasoning_effort: object = "high",
    supported_reasoning_efforts: object = ("xhigh", "high"),
):
    budget_type = getattr(runner_module, "ConfiguredGatewayModelBudgetEvidence")
    reasoning_type = getattr(runner_module, "ConfiguredGatewayReasoningControlEvidence")
    return budget_type(
        assignment_model_id=assignment_model_id,
        provider=provider,
        api_model=api_model,
        input_cost_per_million=input_cost_per_million,
        output_cost_per_million=output_cost_per_million,
        request_overhead_input_tokens=request_overhead_input_tokens,
        max_completion_tokens=max_completion_tokens,
        reasoning_control=reasoning_type(
            mode=reasoning_mode,
            effort=reasoning_effort,
            supported_efforts=supported_reasoning_efforts,
            catalog_evidence_digest=CATALOG_EVIDENCE_DIGEST,
        ),
    )


def _policy(
    *,
    budgets=None,
    allowed_providers=("openrouter",),
    max_calls_per_sample: int = 1,
    max_total_calls: int = 1,
    max_cost: object = "1",
    allow_panel_candidates: object = False,
):
    resolved = (_budget(),) if budgets is None else tuple(budgets)
    return ConfiguredGatewayRunnerPolicy(
        allowed_providers=allowed_providers,
        model_budgets=resolved,
        max_calls_per_sample=max_calls_per_sample,
        max_total_calls=max_total_calls,
        max_cost_estimate_usd_per_sample=max_cost,
        allow_panel_candidates=allow_panel_candidates,
        required_prompt_guard_contract_digest=GUARD_CONTRACT_DIGEST,
        required_prompt_guard_profile_digest=GUARD_PROFILE_DIGEST,
    )


class Guard:
    def __init__(
        self,
        *,
        passed: object = True,
        returned_prompt: str | None = None,
        report_digest: str = GUARD_REPORT_DIGEST,
        contract_digest: str = GUARD_CONTRACT_DIGEST,
        profile_digest: str = GUARD_PROFILE_DIGEST,
        error: BaseException | None = None,
    ) -> None:
        self.passed = passed
        self.returned_prompt = returned_prompt
        self.report_digest = report_digest
        self.contract_digest = contract_digest
        self.profile_digest = profile_digest
        self.error = error
        self.calls: list[dict[str, str]] = []

    def __call__(self, *, prompt: str, task_id: str, source_prompt_digest: str):
        self.calls.append(
            {
                "prompt": prompt,
                "task_id": task_id,
                "source_prompt_digest": source_prompt_digest,
            }
        )
        if self.error is not None:
            raise self.error
        receipt_type = getattr(runner_module, "PromptGuardApprovalReceipt")
        return receipt_type(
            passed=self.passed,
            prompt=prompt if self.returned_prompt is None else self.returned_prompt,
            contract_digest=self.contract_digest,
            profile_digest=self.profile_digest,
            report_digest=self.report_digest,
        )


class Caller:
    def __init__(
        self,
        *,
        result_provider: str | None = None,
        result_model: str | None = None,
        success: object = True,
        response: str = "bounded answer",
        input_tokens: object = 0,
        output_tokens: object = 0,
        cost_estimate_usd: object = 0.0,
        entered: threading.Event | None = None,
        release: threading.Event | None = None,
        error: BaseException | None = None,
    ) -> None:
        self.result_provider = result_provider
        self.result_model = result_model
        self.success = success
        self.response = response
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cost_estimate_usd = cost_estimate_usd
        self.entered = entered
        self.release = release
        self.error = error
        self.calls: list[dict[str, object]] = []
        self._lock = threading.Lock()

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
        with self._lock:
            self.calls.append(
                {
                    "provider": provider,
                    "model": model,
                    "prompt": prompt,
                    "task_type": task_type,
                    "max_completion_tokens": max_completion_tokens,
                    "reasoning_effort": reasoning_effort,
                }
            )
        if self.entered is not None:
            self.entered.set()
        if self.release is not None:
            assert self.release.wait(timeout=5)
        if self.error is not None:
            raise self.error
        return GatewayModelCallResult(
            success=self.success,  # type: ignore[arg-type]
            provider=provider if self.result_provider is None else self.result_provider,
            model=model if self.result_model is None else self.result_model,
            response_text=self.response,
            latency_ms=25,
            input_tokens=self.input_tokens,  # type: ignore[arg-type]
            output_tokens=self.output_tokens,  # type: ignore[arg-type]
            cost_estimate_usd=self.cost_estimate_usd,  # type: ignore[arg-type]
        )


class ReceiptStore:
    def __init__(self) -> None:
        self.receipts: list[object] = []

    def append(self, receipt):
        self.receipts.append(receipt)
        return receipt.receipt_id


class AttemptReceiptStore:
    def __init__(self) -> None:
        self.receipts: list[object] = []

    def append(self, receipt):
        self.receipts.append(receipt)
        return receipt.attempt_receipt_id


def _runner(
    *,
    prompt: str = SOURCE_PROMPT,
    caller: Caller | None = None,
    guard: Guard | None = None,
    policy=None,
    output_store=None,
    receipt_store: ReceiptStore | None = None,
    attempt_store: AttemptReceiptStore | None = None,
):
    return build_configured_gateway_benchmark_runner(
        caller=caller if caller is not None else Caller(),
        prompt_source=MappingPromptSource({"task-001": prompt}),
        policy=policy if policy is not None else _policy(),
        prompt_guard=guard if guard is not None else Guard(),
        output_evidence_store=output_store,
        runner_receipt_store=receipt_store,
        call_attempt_receipt_store=attempt_store,
    )


def test_budget_is_immutable_structured_and_uses_canonical_decimal_strings():
    budget = _budget().normalized()
    assert budget.assignment_model_id == "openrouter/z-ai/glm-5.2"
    assert budget.provider == "openrouter"
    assert budget.api_model == "z-ai/glm-5.2"
    assert budget.to_dict()["input_cost_per_million"] == "2.5"
    with pytest.raises((AttributeError, TypeError)):
        budget.api_model = "substitute"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("input_cost_per_million", 1.0),
        ("input_cost_per_million", True),
        ("input_cost_per_million", "0"),
        ("input_cost_per_million", "-1"),
        ("input_cost_per_million", "NaN"),
        ("input_cost_per_million", "Infinity"),
        ("input_cost_per_million", "01"),
        ("input_cost_per_million", "1.0"),
        ("input_cost_per_million", "1e-3"),
        ("input_cost_per_million", "1000000001"),
        ("output_cost_per_million", 1.0),
        ("output_cost_per_million", "0"),
        ("output_cost_per_million", "-1"),
        ("output_cost_per_million", "NaN"),
        ("output_cost_per_million", "1000000001"),
        ("request_overhead_input_tokens", 0),
        ("request_overhead_input_tokens", True),
        ("request_overhead_input_tokens", 1_000_001),
        ("max_completion_tokens", 0),
        ("max_completion_tokens", True),
        ("max_completion_tokens", 1_000_001),
    ),
)
def test_budget_rejects_noncanonical_unbounded_rate_or_token_evidence(field, value):
    with pytest.raises(ValueError):
        _budget(**{field: value}).normalized()


def test_policy_rejects_empty_duplicate_assignment_and_provider_set_mismatch():
    with pytest.raises(ValueError, match="model_budgets_required"):
        _policy(budgets=()).normalized()
    first = _budget()
    duplicate_assignment = _budget()
    with pytest.raises(ValueError, match="duplicate_assignment"):
        _policy(budgets=(first, duplicate_assignment)).normalized()
    with pytest.raises(ValueError, match="provider_set_mismatch"):
        _policy(budgets=(first,), allowed_providers=("openrouter", "openai")).normalized()


@pytest.mark.parametrize(
    ("mode", "effort", "supported"),
    (
        ("max_tokens", "high", ("xhigh", "high")),
        ("effort", "max", ("xhigh", "high")),
        ("effort", "high", ("xhigh", "high", "high")),
        ("effort", "high", ()),
        ("effort", "HIGH", ("xhigh", "high")),
    ),
)
def test_reasoning_control_rejects_unsupported_mode_effort_or_catalog_set(
    mode,
    effort,
    supported,
):
    with pytest.raises(ValueError, match="reasoning"):
        _budget(
            reasoning_mode=mode,
            reasoning_effort=effort,
            supported_reasoning_efforts=supported,
        ).normalized()


@pytest.mark.parametrize(
    "assignment_model_id",
    (
        "openrouter/z-ai/glm-arbitrary",
        "openrouter/Z-AI/GLM-5.2",
        "openrouter/z-аi/glm-5.2",  # Cyrillic small a.
        "openrouter/z-ai/glm-5.2:free",
    ),
)
def test_assignment_case_homoglyph_alias_or_arbitrary_mismatch_is_precall(
    assignment_model_id,
):
    guard, caller = Guard(), Caller()
    runner = _runner(guard=guard, caller=caller)
    with pytest.raises(ValueError, match="model_not_allowed"):
        runner(_task(), _candidate(assignment_model_id))
    assert guard.calls == []
    assert caller.calls == []


def _reserved_cost(prompt: str, budget) -> Decimal:
    input_upper = len(prompt.encode("utf-8")) + budget.request_overhead_input_tokens
    return (
        Decimal(input_upper) * Decimal(budget.input_cost_per_million)
        + Decimal(budget.max_completion_tokens)
        * Decimal(budget.output_cost_per_million)
    ) / Decimal(1_000_000)


def test_multibyte_role_prompt_reservation_has_precise_decimal_ceiling_boundary():
    source = "監査 RedDog 🐕"
    candidate = _candidate()
    role_prompt = runner_module._role_prompt(
        base_prompt=source,
        role="principal",
        candidate_id=candidate.candidate_id,
        task_id="task-001",
    )
    budget = _budget().normalized()
    exact = _reserved_cost(role_prompt, budget)
    caller, guard = Caller(), Guard()
    accepted = _runner(
        prompt=source,
        caller=caller,
        guard=guard,
        policy=_policy(max_cost=format(exact, "f")),
    )
    accepted(_task(source), candidate)
    assert guard.calls[0]["prompt"] == role_prompt
    assert caller.calls[0]["prompt"] == role_prompt

    lower = exact - Decimal("0.000000000001")
    blocked_caller = Caller()
    blocked_guard = Guard()
    blocked = _runner(
        prompt=source,
        caller=blocked_caller,
        guard=blocked_guard,
        policy=_policy(max_cost=format(lower, "f")),
    )
    with pytest.raises(ValueError, match="cost_reservation_exceeded"):
        blocked(_task(source), candidate)
    assert len(blocked_guard.calls) == 1
    assert blocked_caller.calls == []


def test_reserved_cost_not_forged_zero_caller_cost_is_public_receipt_authority():
    caller, guard, receipts = Caller(cost_estimate_usd=0), Guard(), ReceiptStore()
    attempts = AttemptReceiptStore()
    policy = _policy()
    output = _runner(
        caller=caller,
        guard=guard,
        policy=policy,
        receipt_store=receipts,
        attempt_store=attempts,
    )(_task(), _candidate())
    assert len(receipts.receipts) == 1
    receipt = receipts.receipts[0]
    sent_prompt = caller.calls[0]["prompt"]
    expected = _reserved_cost(sent_prompt, policy.normalized().model_budgets[0])
    assert receipt.receipt_id == output.runner_receipt_id
    assert receipt.source_prompt_digest == _task().prompt_digest
    assert receipt.guard_contract_digest == GUARD_CONTRACT_DIGEST
    assert receipt.guard_profile_digest == GUARD_PROFILE_DIGEST
    assert receipt.calls[0].guard_report_digest == GUARD_REPORT_DIGEST
    assert receipt.calls[0].sent_prompt_digest == _digest(sent_prompt)
    assert receipt.calls[0].reserved_cost_usd == format(expected, "f")
    assert output.metrics.cost_estimate_usd == float(expected)
    assert [item.status for item in attempts.receipts] == ["ATTEMPTED", "COMPLETED"]
    assert attempts.receipts[-1].sent_prompt_digest == _digest(sent_prompt)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("success", "false"),
        ("latency_ms", True),
        ("latency_ms", -1),
        ("latency_ms", 1_000_000_001),
        ("input_tokens", True),
        ("input_tokens", "1"),
        ("input_tokens", -1),
        ("input_tokens", 1_000_001),
        ("output_tokens", True),
        ("output_tokens", "1"),
        ("output_tokens", -1),
        ("output_tokens", 1_000_001),
        ("cost_estimate_usd", -1),
        ("cost_estimate_usd", math.nan),
        ("cost_estimate_usd", math.inf),
        ("cost_estimate_usd", 1_000_001),
        ("response_text", None),
        ("response_text", b"bytes"),
        ("response_text", ["not", "text"]),
        ("response_text", 123),
        ("response_text", "x" * 1_000_001),
    ),
    ids=lambda value: (
        "oversized-text"
        if isinstance(value, str) and len(value) > 100
        else f"{type(value).__name__}-{str(value)[:24]}"
    ),
)
def test_gateway_result_rejects_coercive_or_unbounded_values(field, value):
    values = dict(
        success=True,
        provider="openrouter",
        model="z-ai/glm-5.2",
        response_text="bounded",
        latency_ms=1,
        input_tokens=0,
        output_tokens=0,
        cost_estimate_usd=0,
    )
    values[field] = value
    with pytest.raises(ValueError):
        GatewayModelCallResult(**values).normalized()


def test_policy_and_guard_pass_require_exact_bool():
    with pytest.raises(ValueError, match="allow_panel_candidates"):
        _policy(allow_panel_candidates="false").normalized()
    caller = Caller()
    with pytest.raises(ValueError, match="prompt_guard"):
        _runner(caller=caller, guard=Guard(passed="true"))(_task(), _candidate())
    assert caller.calls == []


@pytest.mark.parametrize(
    "guard",
    (
        Guard(contract_digest=_digest("wrong-contract")),
        Guard(profile_digest=_digest("wrong-profile")),
        Guard(report_digest=""),
        Guard(passed=False),
    ),
)
def test_guard_contract_profile_report_or_block_mismatch_is_precall(guard):
    caller = Caller()
    with pytest.raises(ValueError, match="prompt_guard"):
        _runner(caller=caller, guard=guard)(_task(), _candidate())
    assert len(guard.calls) == 1
    assert caller.calls == []


def test_source_digest_precedes_fully_wrapped_guard_and_guard_change_blocks():
    guard, caller = Guard(), Caller()
    runner = _runner(prompt="different", guard=guard, caller=caller)
    with pytest.raises(ValueError, match="prompt_digest_mismatch"):
        runner(_task("expected"), _candidate())
    assert guard.calls == []
    assert caller.calls == []

    changed_guard, changed_caller = Guard(returned_prompt="redacted"), Caller()
    with pytest.raises(ValueError, match="prompt_guard"):
        _runner(guard=changed_guard, caller=changed_caller)(_task(), _candidate())
    assert "Role: principal" in changed_guard.calls[0]["prompt"]
    assert changed_caller.calls == []


def test_panel_guards_all_final_prompts_then_atomic_total_claim_blocks_all_calls():
    second = _budget(
        assignment_model_id="openrouter/moonshotai/kimi-k3",
        api_model="moonshotai/kimi-k3",
        reasoning_effort="max",
        supported_reasoning_efforts=("max", "high", "low"),
    )
    panel = build_model_benchmark_candidate(
        (
            ModelBenchmarkRoleAssignment(
                role="principal",
                model_id="openrouter/z-ai/glm-5.2",
                provider="openrouter",
            ),
            ModelBenchmarkRoleAssignment(
                role="critic",
                model_id="openrouter/moonshotai/kimi-k3",
                provider="openrouter",
            ),
        )
    )
    guard, caller, attempts = Guard(), Caller(), AttemptReceiptStore()
    policy = _policy(
        budgets=(_budget(), second),
        max_calls_per_sample=2,
        max_total_calls=1,
        allow_panel_candidates=True,
    )
    with pytest.raises(ValueError, match="total_call_budget_exceeded"):
        _runner(
            guard=guard,
            caller=caller,
            policy=policy,
            attempt_store=attempts,
        )(_task(), panel)
    assert len(guard.calls) == 2
    assert all("Role:" in call["prompt"] for call in guard.calls)
    assert caller.calls == []
    assert attempts.receipts == []


def test_twenty_contenders_claim_exactly_one_call():
    entered, release = threading.Event(), threading.Event()
    caller = Caller(entered=entered, release=release)
    runner = _runner(caller=caller)

    def invoke():
        try:
            runner(_task(), _candidate())
        except ValueError as exc:
            return str(exc)
        return "accepted"

    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = [pool.submit(invoke) for _ in range(20)]
        assert entered.wait(timeout=5)
        release.set()
        outcomes = [future.result(timeout=5) for future in futures]
    assert outcomes.count("accepted") == 1
    assert outcomes.count("configured_gateway_runner_total_call_budget_exceeded") == 19
    assert len(caller.calls) == 1


def test_attempted_receipt_is_persisted_before_caller_entry():
    attempts = AttemptReceiptStore()

    class OrderingCaller(Caller):
        def call_model(self, **kwargs):
            assert [item.status for item in attempts.receipts] == ["ATTEMPTED"]
            return super().call_model(**kwargs)

    caller = OrderingCaller()
    _runner(caller=caller, attempt_store=attempts)(_task(), _candidate())
    assert [item.status for item in attempts.receipts] == ["ATTEMPTED", "COMPLETED"]


def _two_role_panel_and_policy():
    second = _budget(
        assignment_model_id="openrouter/moonshotai/kimi-k3",
        api_model="moonshotai/kimi-k3",
        reasoning_effort="max",
        supported_reasoning_efforts=("max",),
    )
    panel = build_model_benchmark_candidate(
        (
            ModelBenchmarkRoleAssignment(
                role="principal",
                model_id="openrouter/z-ai/glm-5.2",
                provider="openrouter",
            ),
            ModelBenchmarkRoleAssignment(
                role="critic",
                model_id="openrouter/moonshotai/kimi-k3",
                provider="openrouter",
            ),
        )
    )
    return panel, _policy(
        budgets=(_budget(), second),
        max_calls_per_sample=2,
        max_total_calls=2,
        allow_panel_candidates=True,
    )


@pytest.mark.parametrize("error", (RuntimeError("first failed"), asyncio.CancelledError()))
def test_panel_failure_releases_only_definitely_unstarted_suffix(error):
    panel, policy = _two_role_panel_and_policy()
    caller, attempts = Caller(error=error), AttemptReceiptStore()
    runner = _runner(caller=caller, policy=policy, attempt_store=attempts)
    if isinstance(error, Exception):
        with pytest.raises(ValueError, match="call_failed"):
            runner(_task(), panel)
    else:
        with pytest.raises(asyncio.CancelledError):
            runner(_task(), panel)
    caller.error = None
    runner(_task(), _candidate())
    assert len(caller.calls) == 2
    assert caller.calls[0]["model"] == "z-ai/glm-5.2"
    assert caller.calls[1]["model"] == "z-ai/glm-5.2"
    assert [item.status for item in attempts.receipts] == [
        "ATTEMPTED", "FAILED" if isinstance(error, Exception) else "CANCELLED",
        "ATTEMPTED", "COMPLETED",
    ]


def test_attempt_store_failure_releases_precall_reservation_for_retry():
    class FailFirstAttemptStore(AttemptReceiptStore):
        fail = True

        def append(self, receipt):
            if self.fail and receipt.status == "ATTEMPTED":
                self.fail = False
                raise RuntimeError("persistence unavailable")
            return super().append(receipt)

    attempts, caller = FailFirstAttemptStore(), Caller()
    runner = _runner(caller=caller, attempt_store=attempts)
    with pytest.raises(ValueError, match="attempt_evidence_unavailable"):
        runner(_task(), _candidate())
    runner(_task(), _candidate())
    assert len(caller.calls) == 1
    assert [item.status for item in attempts.receipts] == ["ATTEMPTED", "COMPLETED"]


def test_terminal_attempt_persistence_failure_is_indeterminate_and_consumes_slot():
    class FailTerminalStore(AttemptReceiptStore):
        def append(self, receipt):
            if self.receipts:
                raise RuntimeError("sensitive terminal persistence detail")
            return super().append(receipt)

    attempts = FailTerminalStore()
    caller = Caller(response="bounded output")
    outputs = InMemoryModelAutoResearchOutputEvidenceStore()
    successes = ReceiptStore()
    runner = _runner(
        caller=caller,
        output_store=outputs,
        receipt_store=successes,
        attempt_store=attempts,
    )
    with pytest.raises(ValueError) as raised:
        runner(_task(), _candidate())
    assert str(raised.value) == "configured_gateway_runner_attempt_evidence_indeterminate"
    assert "sensitive" not in str(raised.value)
    assert len(caller.calls) == 1
    assert [item.status for item in attempts.receipts] == ["ATTEMPTED"]
    assert len(outputs.records) == 1
    assert successes.receipts == []
    with pytest.raises(ValueError, match="total_call_budget_exceeded"):
        runner(_task(), _candidate())
    assert len(caller.calls) == 1


class CallerAbort(BaseException):  # Test-only non-Exception abort.
    pass
@pytest.mark.parametrize(
    "error",
    (asyncio.CancelledError(), KeyboardInterrupt(), SystemExit(), CallerAbort()),
)
def test_terminal_store_failure_never_swallows_caller_baseexception(error):
    class FailTerminalStore(AttemptReceiptStore):
        def append(self, receipt):
            if receipt.status != "ATTEMPTED":
                raise RuntimeError("terminal persistence failed")
            return super().append(receipt)

    caller = Caller(error=error)
    runner = _runner(caller=caller, attempt_store=FailTerminalStore())
    with pytest.raises(type(error)):
        runner(_task(), _candidate())
    caller.error = None
    with pytest.raises(ValueError, match="total_call_budget_exceeded"):
        runner(_task(), _candidate())
    assert len(caller.calls) == 1


@pytest.mark.parametrize(
    "error",
    (
        RuntimeError("sensitive caller detail"),
        asyncio.CancelledError(),
        CallerAbort("terminal abort"),
    ),
)
def test_caller_failure_is_content_free_and_attempted_slot_is_never_reclaimed(error):
    caller = Caller(error=error)
    attempts = AttemptReceiptStore()
    runner = _runner(caller=caller, attempt_store=attempts)
    if isinstance(error, Exception):
        with pytest.raises(ValueError) as raised:
            runner(_task(), _candidate())
        assert str(raised.value) == "configured_gateway_runner_call_failed"
        assert "sensitive" not in str(raised.value)
    elif isinstance(error, asyncio.CancelledError):
        with pytest.raises(asyncio.CancelledError):
            runner(_task(), _candidate())
    else:
        with pytest.raises(CallerAbort):
            runner(_task(), _candidate())
    caller.error = None
    with pytest.raises(ValueError, match="total_call_budget_exceeded"):
        runner(_task(), _candidate())
    assert len(caller.calls) == 1
    terminal = "CANCELLED" if isinstance(error, asyncio.CancelledError) else "FAILED"
    assert [item.status for item in attempts.receipts] == ["ATTEMPTED", terminal]
    serialized = json.dumps([item.to_dict() for item in attempts.receipts], sort_keys=True)
    assert SOURCE_PROMPT not in serialized
    assert "sensitive caller detail" not in serialized
    assert "terminal abort" not in serialized


def test_guard_cancellation_consumes_zero_slot():
    guard, caller = Guard(error=asyncio.CancelledError()), Caller()
    attempts = AttemptReceiptStore()
    runner = _runner(guard=guard, caller=caller, attempt_store=attempts)
    with pytest.raises(asyncio.CancelledError):
        runner(_task(), _candidate())
    guard.error = None
    runner(_task(), _candidate())
    assert len(caller.calls) == 1
    assert [item.status for item in attempts.receipts] == ["ATTEMPTED", "COMPLETED"]


def test_guard_exception_is_content_free_and_consumes_zero_slot():
    guard, caller = Guard(error=RuntimeError("sensitive guard detail")), Caller()
    attempts = AttemptReceiptStore()
    runner = _runner(guard=guard, caller=caller, attempt_store=attempts)
    with pytest.raises(ValueError) as raised:
        runner(_task(), _candidate())
    assert str(raised.value) == "configured_gateway_runner_prompt_guard_failed"
    assert "sensitive" not in str(raised.value)
    guard.error = None
    runner(_task(), _candidate())
    assert len(caller.calls) == 1
    assert [item.status for item in attempts.receipts] == ["ATTEMPTED", "COMPLETED"]


@pytest.mark.parametrize(
    ("caller", "reason"),
    (
        (Caller(response="secret=do-not-store"), "secret_detected"),
        (Caller(output_tokens=14), "output_tokens_exceeded"),
    ),
)
def test_postcall_secret_or_oversized_output_writes_no_success_evidence_and_consumes_slot(
    caller,
    reason,
):
    outputs = InMemoryModelAutoResearchOutputEvidenceStore()
    receipts = ReceiptStore()
    attempts = AttemptReceiptStore()
    runner = _runner(
        caller=caller,
        output_store=outputs,
        receipt_store=receipts,
        attempt_store=attempts,
    )
    with pytest.raises(ValueError, match=reason):
        runner(_task(), _candidate())
    assert outputs.records == []
    assert receipts.receipts == []
    assert [item.status for item in attempts.receipts] == [
        "ATTEMPTED",
        "REJECTED_OUTPUT",
    ]
    serialized = json.dumps([item.to_dict() for item in attempts.receipts], sort_keys=True)
    assert SOURCE_PROMPT not in serialized
    assert caller.response not in serialized
    caller.response = "bounded"
    caller.output_tokens = 0
    with pytest.raises(ValueError, match="total_call_budget_exceeded"):
        runner(_task(), _candidate())
    assert len(caller.calls) == 1


@pytest.mark.parametrize(
    ("result_provider", "result_model"),
    (("openai", None), (None, "attacker/substitute")),
)
def test_caller_provider_or_model_route_mismatch_is_rejected(result_provider, result_model):
    caller = Caller(result_provider=result_provider, result_model=result_model)
    attempts = AttemptReceiptStore()
    with pytest.raises(ValueError, match="call_route_mismatch"):
        _runner(caller=caller, attempt_store=attempts)(_task(), _candidate())
    assert len(caller.calls) == 1
    assert [item.status for item in attempts.receipts] == [
        "ATTEMPTED",
        "ROUTE_MISMATCH",
    ]


def test_exact_completion_cap_and_reasoning_effort_propagate_without_env_mutation(
    monkeypatch,
):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_MAX_TOKENS", "999")
    seen: list[dict[str, object]] = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setattr(
        "modules.ai_intelligence.ai_gateway.src.ai_gateway.requests.post",
        lambda url, **kwargs: seen.append({"url": url, **kwargs}) or Response(),
    )
    before = dict(os.environ)
    gateway = AIGateway()
    result = AIGatewayConfiguredModelCaller(gateway).call_model(
        provider="openrouter",
        model="z-ai/glm-5.2",
        prompt="held out",
        task_type="model_autoresearch",
        max_completion_tokens=13,
        reasoning_effort="high",
    )
    assert result.success is True
    assert seen[0]["json"]["max_tokens"] == 13
    assert seen[0]["json"]["reasoning"] == {"effort": "high"}
    assert dict(os.environ) == before


def test_kimi_exact_effort_preserves_no_temperature_request(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_TEMPERATURE", "0.9")
    seen: list[dict[str, object]] = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setattr(
        "modules.ai_intelligence.ai_gateway.src.ai_gateway.requests.post",
        lambda url, **kwargs: seen.append(kwargs) or Response(),
    )
    AIGatewayConfiguredModelCaller(AIGateway()).call_model(
        provider="openrouter",
        model="moonshotai/kimi-k3",
        prompt="held out",
        task_type="model_autoresearch",
        max_completion_tokens=4096,
        reasoning_effort="max",
    )
    assert seen[0]["json"]["reasoning"] == {"effort": "max"}
    assert seen[0]["json"]["max_tokens"] == 4096
    assert "temperature" not in seen[0]["json"]


@pytest.mark.parametrize(
    ("max_completion_tokens", "reasoning_effort"),
    ((True, "high"), (0, "high"), (1_000_001, "high"), (13, True), (13, "")),
)
def test_exact_call_rejects_invalid_caps_before_request(
    monkeypatch,
    max_completion_tokens,
    reasoning_effort,
):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    seen: list[object] = []
    monkeypatch.setattr(
        "modules.ai_intelligence.ai_gateway.src.ai_gateway.requests.post",
        lambda *args, **kwargs: seen.append((args, kwargs)),
    )
    with pytest.raises(ValueError, match="tokens"):
        AIGatewayConfiguredModelCaller(AIGateway()).call_model(
            provider="openrouter",
            model="z-ai/glm-5.2",
            prompt="held out",
            task_type="model_autoresearch",
            max_completion_tokens=max_completion_tokens,
            reasoning_effort=reasoning_effort,
        )
    assert seen == []


def test_call_provider_forwards_exact_keyword_only_caps_to_call_openai(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    gateway = AIGateway()
    provider = gateway.providers["openrouter"]
    seen: list[dict[str, object]] = []

    def fake_openai(
        provider_arg,
        prompt,
        model,
        *,
        max_completion_tokens,
        reasoning_effort,
    ):
        seen.append(
            {
                "provider": provider_arg,
                "prompt": prompt,
                "model": model,
                "max_completion_tokens": max_completion_tokens,
                "reasoning_effort": reasoning_effort,
            }
        )
        return "ok"

    monkeypatch.setattr(gateway, "_call_openai", fake_openai)
    assert (
        gateway._call_provider(
            provider,
            "prompt",
            "quick",
            max_completion_tokens=13,
            reasoning_effort="high",
        )
        == "ok"
    )
    assert seen[0]["max_completion_tokens"] == 13
    assert seen[0]["reasoning_effort"] == "high"


def test_configured_caller_never_retries_without_exact_keywords_after_type_error():
    class RejectingGateway:
        def __init__(self):
            self.providers = {
                "openrouter": ProviderConfig(
                    name="openrouter",
                    api_key="test",
                    base_url="https://example.invalid",
                    models={"quick": "wrong"},
                    cost_per_token=0,
                    output_cost_per_token=0,
                    rate_limit=1,
                )
            }
            self.calls = 0

        def _call_provider(self, *args, **kwargs):
            self.calls += 1
            raise TypeError("exact keyword seam unavailable")

    gateway = RejectingGateway()
    with pytest.raises(TypeError, match="exact keyword seam unavailable"):
        AIGatewayConfiguredModelCaller(gateway).call_model(
            provider="openrouter",
            model="z-ai/glm-5.2",
            prompt="prompt",
            task_type="model_autoresearch",
            max_completion_tokens=13,
            reasoning_effort="high",
        )
    assert gateway.calls == 1


def _canonical_guard(*, redaction_gate=None):
    module = importlib.import_module(
        "modules.ai_intelligence.ai_gateway.src."
        "model_autoresearch_canonical_prompt_guard"
    )
    factory = module.build_canonical_local_autoresearch_prompt_guard
    if redaction_gate is None:
        return factory()
    return factory(redaction_gate=redaction_gate)


def _fully_wrapped_prompt(source: str = SOURCE_PROMPT) -> str:
    candidate = _candidate()
    return runner_module._role_prompt(
        base_prompt=source,
        role="principal",
        candidate_id=candidate.candidate_id,
        task_id="task-001",
    )


def test_canonical_local_guard_clean_wrapped_prompt_passes_byte_identically():
    prompt = _fully_wrapped_prompt()
    calls: list[dict[str, object]] = []

    def audit_gate(value, **kwargs):
        calls.append({"prompt": value, **kwargs})
        return evaluate_redaction_gate(value, **kwargs)

    receipt = _canonical_guard(redaction_gate=audit_gate)(
        prompt=prompt,
        task_id="task-001",
        source_prompt_digest=_digest(SOURCE_PROMPT),
    )
    assert receipt.passed is True
    assert receipt.prompt == prompt
    assert receipt.contract_digest == GUARD_CONTRACT_DIGEST
    assert receipt.profile_digest == GUARD_PROFILE_DIGEST
    assert receipt.report_digest == GUARD_REPORT_DIGEST
    assert receipt.to_dict()["prompt"] == prompt
    assert calls == [{"prompt": prompt, "audit_mode": True}]


def test_canonical_local_guard_secret_redaction_never_returns_changed_prompt():
    secret = "OPENROUTER_API_KEY=sk-or-v1-abcdefghijklmnopqrstuvwxyz012345"
    prompt = _fully_wrapped_prompt() + "\n" + secret
    receipt = _canonical_guard()(
        prompt=prompt,
        task_id="task-001",
        source_prompt_digest=_digest(SOURCE_PROMPT),
    )
    assert receipt.passed is False
    assert receipt.prompt is None
    serialized = json.dumps(receipt.to_dict(), sort_keys=True)
    assert prompt not in serialized
    assert secret not in serialized
    assert "abcdefghijklmnopqrstuvwxyz012345" not in serialized


@pytest.mark.parametrize(
    "redaction_gate",
    (
        lambda prompt, **kwargs: (_ for _ in ()).throw(
            RuntimeError("sensitive redactor exception")
        ),
        lambda prompt, **kwargs: object(),
    ),
)
def test_canonical_local_guard_redactor_error_or_malformed_result_fails_content_free(
    redaction_gate,
):
    prompt = _fully_wrapped_prompt()
    receipt = _canonical_guard(redaction_gate=redaction_gate)(
        prompt=prompt,
        task_id="task-001",
        source_prompt_digest=_digest(SOURCE_PROMPT),
    )
    assert receipt.passed is False
    assert receipt.prompt is None
    serialized = json.dumps(receipt.to_dict(), sort_keys=True)
    assert prompt not in serialized
    assert "sensitive redactor exception" not in serialized


def test_canonical_local_guard_real_redaction_policy_block_is_content_free():
    prompt = _fully_wrapped_prompt() + "\n<thinking>private reasoning</thinking>"
    receipt = _canonical_guard()(
        prompt=prompt,
        task_id="task-001",
        source_prompt_digest=_digest(SOURCE_PROMPT),
    )
    assert receipt.passed is False
    assert receipt.prompt is None
    assert prompt not in json.dumps(receipt.to_dict(), sort_keys=True)


@pytest.mark.parametrize("bad_prompt", (None, b"bytes", ["text"], {"prompt": "x"}))
def test_canonical_local_guard_malformed_prompt_input_fails_content_free(bad_prompt):
    receipt = _canonical_guard()(
        prompt=bad_prompt,
        task_id="task-001",
        source_prompt_digest=_digest(SOURCE_PROMPT),
    )
    assert receipt.passed is False
    assert receipt.prompt is None
    serialized = json.dumps(receipt.to_dict(), sort_keys=True)
    assert repr(bad_prompt) not in serialized


def test_bootstrap_owns_canonical_guard_profile_and_has_no_callback_injection():
    signature = inspect.signature(
        run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap
    )
    assert "prompt_guard" not in signature.parameters
    profile_parameter = signature.parameters["runner_prompt_guard_profile"]
    assert profile_parameter.default == "canonical_local_v1"
    source_path = Path(
        "modules/ai_intelligence/ai_gateway/src/"
        "model_autoresearch_campaign_execution_artifact_supply_bootstrap.py"
    )
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert "build_canonical_local_autoresearch_prompt_guard" in imported
    factory_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and getattr(node.func, "id", "") == "build_canonical_local_autoresearch_prompt_guard"
    ]
    assert len(factory_calls) == 1
    runner_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and getattr(node.func, "id", "") == "build_configured_gateway_benchmark_runner"
    ]
    assert len(runner_calls) == 1
    prompt_guard_values = [
        keyword.value
        for keyword in runner_calls[0].keywords
        if keyword.arg == "prompt_guard"
    ]
    assert len(prompt_guard_values) == 1
    assert isinstance(prompt_guard_values[0], ast.Name)
    assert prompt_guard_values[0].id == "trusted_prompt_guard"
    assert "unsupported_model_autoresearch_campaign_prompt_guard_profile" in source


def test_canonical_guard_source_has_no_escape_or_sensitive_logging_surface():
    path = Path(
        "modules/ai_intelligence/ai_gateway/src/"
        "model_autoresearch_canonical_prompt_guard.py"
    )
    assert path.is_file()
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
    assert not imported_roots.intersection(
        {"logging", "os", "subprocess", "requests", "urllib", "socket"}
    )
    banned_calls = {"open", "print", "exec", "eval", "compile", "__import__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned_calls
    assert "environ" not in source
