"""Tests for configured gateway benchmark runner."""

from __future__ import annotations

import ast
import hashlib
from dataclasses import replace
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.ai_gateway import AIGateway, ProviderConfig
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_configured_gateway_runner import (
    AIGatewayConfiguredModelCaller,
    ConfiguredGatewayModelBudgetEvidence,
    ConfiguredGatewayReasoningControlEvidence,
    ConfiguredGatewayRunnerPolicy,
    GatewayModelCallResult,
    MappingPromptSource,
    build_configured_gateway_benchmark_runner,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_canonical_prompt_guard import (
    CANONICAL_PROMPT_GUARD_CONTRACT_DIGEST,
    CANONICAL_PROMPT_GUARD_PROFILE_DIGEST,
    build_canonical_local_autoresearch_prompt_guard,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_output_evidence_bundle import (
    InMemoryModelAutoResearchOutputEvidenceStore,
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
    output_evidence_store=None,
):
    return build_configured_gateway_benchmark_runner(
        caller=caller or FakeConfiguredCaller(),
        prompt_source=MappingPromptSource({"task-001": prompt}),
        policy=policy
        or _policy(
            "openai/gpt-test",
            "openai/gpt-5.2",
            "anthropic/claude-test",
            allow_panel=True,
        ),
        prompt_guard=build_canonical_local_autoresearch_prompt_guard(),
        output_evidence_store=output_evidence_store,
    )


def _budget(model_id: str) -> ConfiguredGatewayModelBudgetEvidence:
    provider, api_model = model_id.split("/", 1)
    return ConfiguredGatewayModelBudgetEvidence(
        assignment_model_id=model_id,
        provider=provider,
        api_model=api_model,
        input_cost_per_million="1",
        output_cost_per_million="1",
        request_overhead_input_tokens=11,
        max_completion_tokens=1000,
        reasoning_control=ConfiguredGatewayReasoningControlEvidence(
            mode="effort",
            effort="high",
            supported_efforts=("high",),
            catalog_evidence_digest=_digest("test-catalog"),
        ),
    )


def _policy(
    *model_ids: str,
    allow_panel: bool = False,
    max_cost: str = "1",
) -> ConfiguredGatewayRunnerPolicy:
    budgets = tuple(_budget(item) for item in model_ids)
    return ConfiguredGatewayRunnerPolicy(
        allowed_providers=tuple(dict.fromkeys(item.provider for item in budgets)),
        model_budgets=budgets,
        max_calls_per_sample=max(1, len(budgets)),
        max_total_calls=max(4, len(budgets)),
        max_cost_estimate_usd_per_sample=max_cost,
        allow_panel_candidates=allow_panel,
        required_prompt_guard_contract_digest=CANONICAL_PROMPT_GUARD_CONTRACT_DIGEST,
        required_prompt_guard_profile_digest=CANONICAL_PROMPT_GUARD_PROFILE_DIGEST,
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
    assert output.runner_receipt_id.startswith("configured_gateway_runner:")
    assert output.metrics.latency_ms == 25
    assert 0 < output.metrics.cost_estimate_usd < 1
    assert prompt not in output.output_digest
    assert "This answer is bounded." not in output.runner_receipt_id


def test_configured_runner_writes_output_evidence_when_store_injected():
    prompt = "Audit the bounded RedDog runtime path."
    caller = FakeConfiguredCaller(response="Evidence-bearing answer.")
    store = InMemoryModelAutoResearchOutputEvidenceStore()
    runner = _runner(prompt=prompt, caller=caller, output_evidence_store=store)

    output = runner(_task(prompt), _candidate("openai/gpt-5.2"))

    assert len(store.records) == 1
    record = store.records[0]
    assert record["response_text"] == "Evidence-bearing answer."
    assert record["task_id"] == "task-001"
    assert record["candidate_id"] == "openai/gpt-5.2"
    assert record["role"] == "principal"
    assert record["provider"] == "openai"
    assert record["model"] == "gpt-5.2"
    digest_only_output = _runner(
        prompt=prompt,
        caller=FakeConfiguredCaller(response="Evidence-bearing answer."),
    )(_task(prompt), _candidate("openai/gpt-5.2"))
    assert output.output_digest != digest_only_output.output_digest
    assert output.output_digest.startswith("configured_gateway_benchmark_output:")
    assert record["record_id"] not in output.output_digest
    assert record["record_id"] not in output.runner_receipt_id
    assert "Evidence-bearing answer." not in output.output_digest
    assert "Evidence-bearing answer." not in output.runner_receipt_id


def test_configured_runner_secret_output_fails_before_evidence_store_write():
    prompt = "Audit the bounded RedDog runtime path."
    caller = FakeConfiguredCaller(response="token=abc123")
    store = InMemoryModelAutoResearchOutputEvidenceStore()
    runner = _runner(prompt=prompt, caller=caller, output_evidence_store=store)

    try:
        runner(_task(prompt), _candidate("openai/gpt-5.2"))
    except ValueError as exc:
        assert str(exc) == "model_autoresearch_output_evidence_secret_detected"
    else:
        raise AssertionError("expected secret output rejection")

    assert store.records == []


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
    assert 0 < output.metrics.cost_estimate_usd < 1
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
    policy = _policy("anthropic/claude-test")
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
        policy=_policy(
            "openai/gpt-5.2",
            "anthropic/claude-test",
            allow_panel=False,
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
        policy=_policy("openai/gpt-test", max_cost="0.000001"),
    )

    try:
        runner(_task(), _candidate())
    except ValueError as exc:
        assert str(exc) == "configured_gateway_runner_cost_reservation_exceeded"
    else:
        raise AssertionError("expected cost budget rejection")

    assert len(caller.calls) == 0


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

        def _call_provider(
            self, provider: ProviderConfig, prompt: str, task_type: str, **kwargs
        ) -> str:
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
        max_completion_tokens=1000,
        reasoning_effort="high",
    )

    assert result.success is True
    assert result.provider == "openai"
    assert result.model == "gpt-5.2"
    assert result.response_text == "gateway response"
    assert result.input_tokens == 2
    assert result.output_tokens == 2
    assert result.cost_estimate_usd == 0.0
    assert len(gateway.calls) == 1


def test_aigateway_adapter_targets_kimi_k3_through_openrouter_for_autoresearch():
    class FakeGateway:
        def __init__(self) -> None:
            self.providers = {
                "openrouter": ProviderConfig(
                    name="openrouter",
                    api_key="test-key",
                    base_url="https://openrouter.ai/api/v1",
                    models={"quick": "wrong-default"},
                    cost_per_token=0.000003,
                    rate_limit=1,
                    output_cost_per_token=0.000015,
                )
            }
            self.calls: list[tuple[ProviderConfig, str, str]] = []

        def _call_provider(
            self, provider: ProviderConfig, prompt: str, task_type: str, **kwargs
        ) -> str:
            self.calls.append((provider, prompt, task_type))
            assert provider.models[task_type] == "moonshotai/kimi-k3"
            return "kimi benchmark response"

    gateway = FakeGateway()
    result = AIGatewayConfiguredModelCaller(gateway).call_model(
        provider="openrouter",
        model="moonshotai/kimi-k3",
        prompt="held out task",
        task_type="model_autoresearch",
        max_completion_tokens=4096,
        reasoning_effort="max",
    )

    assert result.success is True
    assert result.provider == "openrouter"
    assert result.model == "moonshotai/kimi-k3"
    assert result.cost_estimate_usd == 0.0
    assert len(gateway.calls) == 1


def test_aigateway_kimi_k3_request_uses_openrouter_supported_parameters(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    requests_seen: list[dict[str, object]] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"choices": [{"message": {"content": "ok"}}]}

    def fake_post(url: str, **kwargs: object) -> FakeResponse:
        requests_seen.append({"url": url, **kwargs})
        return FakeResponse()

    monkeypatch.setattr(
        "modules.ai_intelligence.ai_gateway.src.ai_gateway.requests.post",
        fake_post,
    )
    gateway = AIGateway()
    provider = gateway.providers["openrouter"]

    assert "openrouter" not in gateway._get_provider_priority("coding")
    assert provider.automatic_routing_enabled is False
    for name, configured in gateway.providers.items():
        if name != "openrouter":
            configured.api_key = None
    automatic_calls: list[str] = []
    monkeypatch.setattr(
        gateway,
        "_call_provider",
        lambda *_args, **_kwargs: automatic_calls.append("called") or "unexpected",
    )
    assert gateway.call_optimized("must stay explicit", "coding").success is False
    assert automatic_calls == []

    monkeypatch.undo()
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(
        "modules.ai_intelligence.ai_gateway.src.ai_gateway.requests.post",
        fake_post,
    )
    gateway = AIGateway()
    provider = gateway.providers["openrouter"]
    assert gateway._call_provider(provider, "benchmark prompt", "coding") == "ok"
    assert requests_seen[0]["url"] == "https://openrouter.ai/api/v1/chat/completions"
    body = requests_seen[0]["json"]
    assert isinstance(body, dict)
    assert body["model"] == "moonshotai/kimi-k3"
    assert body["max_tokens"] == 4096
    assert body["reasoning"] == {"effort": "max"}
    assert "temperature" not in body


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
