"""Tests for configured gateway benchmark runner."""

from __future__ import annotations

import ast
import hashlib
from dataclasses import replace
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.ai_gateway import ProviderConfig
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_configured_gateway_runner import (
    AIGatewayConfiguredModelCaller,
    ConfiguredGatewayRunnerPolicy,
    GatewayModelCallResult,
    MappingPromptSource,
    build_configured_gateway_benchmark_runner,
)
from modules.ai_intelligence.ai_gateway.src.model_combination_benchmark_harness import (
    ModelBenchmarkRoleAssignment,
    ModelBenchmarkTask,
    ModelBenchmarkTaskOutput,
    ModelBenchmarkVerifierResult,
    build_model_benchmark_candidate,
    run_model_combination_benchmark,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_outcomes import VerifierDecision


def _digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _task(prompt: str = "Audit the bounded RedDog runtime path.") -> ModelBenchmarkTask:
    return ModelBenchmarkTask(
        task_id="task-001",
        task_family="architecture",
        prompt_digest=_digest(prompt),
        expected_output_digest="sha256:expected-output",
        verifier_contract_digest="sha256:verifier-contract",
    )


def _candidate(model_id: str = "openai/gpt-test"):
    return build_model_benchmark_candidate(
        (ModelBenchmarkRoleAssignment(role="principal", model_id=model_id, provider="openai"),)
    )


class FakeConfiguredCaller:
    def __init__(
        self,
        *,
        response: str = "bounded answer",
        cost_estimate_usd: float = 0.01,
    ) -> None:
        self.response = response
        self.cost_estimate_usd = cost_estimate_usd
        self.calls: list[dict[str, str]] = []

    def call_model(self, *, provider: str, model: str, prompt: str, task_type: str) -> GatewayModelCallResult:
        self.calls.append(
            {
                "provider": provider,
                "model": model,
                "prompt": prompt,
                "task_type": task_type,
            }
        )
        return GatewayModelCallResult(
            success=True,
            provider=provider,
            model=model,
            response_text=self.response,
            latency_ms=25,
            input_tokens=len(prompt.split()),
            output_tokens=len(self.response.split()),
            cost_estimate_usd=self.cost_estimate_usd,
        )


def _runner(
    *,
    prompt: str = "Audit the bounded RedDog runtime path.",
    caller: FakeConfiguredCaller | None = None,
    policy: ConfiguredGatewayRunnerPolicy | None = None,
):
    return build_configured_gateway_benchmark_runner(
        caller=caller or FakeConfiguredCaller(),
        prompt_source=MappingPromptSource({"task-001": prompt}),
        policy=policy
        or ConfiguredGatewayRunnerPolicy(
            allowed_providers=("openai", "anthropic"),
            max_cost_estimate_usd_per_sample=1.0,
        ),
    )


def _accepting_verifier(task, candidate, output: ModelBenchmarkTaskOutput):
    return ModelBenchmarkVerifierResult(
        decision=VerifierDecision.ACCEPT,
        verifier_receipt_id=f"verify:{candidate.candidate_id}:{task.task_id}",
        evidence_correct=True,
    )


def test_configured_runner_calls_explicit_provider_model_and_returns_digest_only_output():
    prompt = "Audit the bounded RedDog runtime path."
    caller = FakeConfiguredCaller(response="This answer is bounded.")
    runner = _runner(prompt=prompt, caller=caller)

    output = runner(_task(prompt), _candidate("openai/gpt-5.2"))

    assert caller.calls[0]["provider"] == "openai"
    assert caller.calls[0]["model"] == "gpt-5.2"
    assert caller.calls[0]["task_type"] == "model_autoresearch"
    assert "Role: principal" in caller.calls[0]["prompt"]
    assert output.output_digest.startswith("configured_gateway_benchmark_output:")
    assert output.runner_receipt_id.startswith("configured_gateway_benchmark_runner:")
    assert output.metrics.latency_ms == 25
    assert output.metrics.cost_estimate_usd == 0.01
    assert prompt not in output.output_digest
    assert "This answer is bounded." not in output.runner_receipt_id


def test_configured_runner_integrates_with_combination_benchmark_harness():
    prompt = "Audit the bounded RedDog runtime path."
    caller = FakeConfiguredCaller()
    receipt = run_model_combination_benchmark(
        tasks=(_task(prompt),),
        candidates=(_candidate("openai/gpt-5.2"),),
        runner=_runner(prompt=prompt, caller=caller),
        verifier=_accepting_verifier,
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
    )

    evidence = receipt.benchmark_evidence_receipts[0]
    assert receipt.receipt_id.startswith("model_combination_benchmark_run:")
    assert evidence.model_id == "openai/gpt-5.2"
    assert evidence.sample_count == 1
    assert evidence.verifier_pass_rate == 1.0
    assert len(caller.calls) == 1


def test_panel_candidate_calls_each_non_verifier_role_and_aggregates_metrics():
    prompt = "Audit the bounded RedDog runtime path."
    caller = FakeConfiguredCaller(cost_estimate_usd=0.1)
    panel = build_model_benchmark_candidate(
        (
            ModelBenchmarkRoleAssignment(role="principal", model_id="openai/gpt-5.2", provider="openai"),
            ModelBenchmarkRoleAssignment(role="critic", model_id="anthropic/claude-test", provider="anthropic"),
        )
    )

    output = _runner(prompt=prompt, caller=caller)(_task(prompt), panel)

    assert [call["provider"] for call in caller.calls] == ["openai", "anthropic"]
    assert [call["model"] for call in caller.calls] == ["gpt-5.2", "claude-test"]
    assert "Role: principal" in caller.calls[0]["prompt"]
    assert "Role: critic" in caller.calls[1]["prompt"]
    assert output.metrics.cost_estimate_usd == 0.2
    assert output.metrics.latency_ms == 50


def test_prompt_digest_mismatch_fails_before_model_call():
    caller = FakeConfiguredCaller()
    runner = _runner(prompt="different prompt", caller=caller)

    try:
        runner(_task("expected prompt"), _candidate())
    except ValueError as exc:
        assert str(exc) == "configured_gateway_runner_prompt_digest_mismatch"
    else:
        raise AssertionError("expected prompt digest mismatch")

    assert caller.calls == []


def test_disallowed_provider_fails_before_model_call():
    caller = FakeConfiguredCaller()
    policy = ConfiguredGatewayRunnerPolicy(allowed_providers=("anthropic",))
    runner = _runner(caller=caller, policy=policy)

    try:
        runner(_task(), _candidate("openai/gpt-5.2"))
    except ValueError as exc:
        assert str(exc) == "configured_gateway_runner_provider_not_allowed"
    else:
        raise AssertionError("expected provider rejection")

    assert caller.calls == []


def test_candidate_id_or_topology_tamper_fails_before_model_call():
    caller = FakeConfiguredCaller()
    forged = replace(_candidate("openai/gpt-5.2"), candidate_id="openai/forged")
    runner = _runner(caller=caller)

    try:
        runner(_task(), forged)
    except ValueError as exc:
        assert str(exc) == "configured_gateway_runner_candidate_mismatch"
    else:
        raise AssertionError("expected candidate mismatch")

    assert caller.calls == []


def test_panel_candidate_can_be_disabled_by_policy():
    panel = build_model_benchmark_candidate(
        (
            ModelBenchmarkRoleAssignment(role="principal", model_id="openai/gpt-5.2", provider="openai"),
            ModelBenchmarkRoleAssignment(role="critic", model_id="anthropic/claude-test", provider="anthropic"),
        )
    )
    caller = FakeConfiguredCaller()
    runner = _runner(
        caller=caller,
        policy=ConfiguredGatewayRunnerPolicy(
            allowed_providers=("openai", "anthropic"),
            allow_panel_candidates=False,
        ),
    )

    try:
        runner(_task(), panel)
    except ValueError as exc:
        assert str(exc) == "configured_gateway_runner_panel_disabled"
    else:
        raise AssertionError("expected panel rejection")

    assert caller.calls == []


def test_cost_budget_fails_closed_after_call_without_returning_successful_output():
    caller = FakeConfiguredCaller(cost_estimate_usd=5.0)
    runner = _runner(
        caller=caller,
        policy=ConfiguredGatewayRunnerPolicy(
            allowed_providers=("openai",),
            max_cost_estimate_usd_per_sample=0.01,
        ),
    )

    try:
        runner(_task(), _candidate())
    except ValueError as exc:
        assert str(exc) == "configured_gateway_runner_cost_budget_exceeded"
    else:
        raise AssertionError("expected cost budget rejection")

    assert len(caller.calls) == 1


def test_aigateway_adapter_targets_exact_provider_and_model_without_fallback():
    class FakeGateway:
        def __init__(self) -> None:
            self.providers = {
                "openai": ProviderConfig(
                    name="openai",
                    api_key="test-key",
                    base_url="https://example.invalid",
                    models={"quick": "wrong-default"},
                    cost_per_token=0.25,
                    rate_limit=1,
                )
            }
            self.calls: list[tuple[ProviderConfig, str, str]] = []

        def _call_provider(self, provider: ProviderConfig, prompt: str, task_type: str) -> str:
            self.calls.append((provider, prompt, task_type))
            assert provider.models[task_type] == "gpt-5.2"
            return "gateway response"

    gateway = FakeGateway()
    caller = AIGatewayConfiguredModelCaller(gateway)

    result = caller.call_model(
        provider="openai",
        model="gpt-5.2",
        prompt="hello world",
        task_type="model_autoresearch",
    )

    assert result.success is True
    assert result.provider == "openai"
    assert result.model == "gpt-5.2"
    assert result.response_text == "gateway response"
    assert result.input_tokens == 2
    assert result.output_tokens == 2
    assert result.cost_estimate_usd == 0.5
    assert len(gateway.calls) == 1


def test_configured_runner_module_has_no_direct_network_command_runtime_or_holoindex_imports():
    source = Path(
        "modules/ai_intelligence/ai_gateway/src/model_autoresearch_configured_gateway_runner.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    banned_attr_roots = {"os", "subprocess", "requests", "urllib", "openai", "holo_index"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert not (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id in banned_attr_roots
            )

    assert "subprocess" not in imported
    assert "requests" not in imported
    assert "urllib" not in imported
    assert "openai" not in imported
    assert "holo_index" not in imported
    assert "pattern_memory" not in source
    assert "extension.js" not in source
