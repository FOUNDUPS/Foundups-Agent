"""Tests for model AutoResearch output-evidence semantic verifier."""

from __future__ import annotations

import ast
import hashlib
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_configured_gateway_runner import (
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
    build_model_autoresearch_output_evidence_record,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_semantic_verifier import (
    build_model_autoresearch_output_evidence_semantic_verifier,
)
from modules.ai_intelligence.ai_gateway.src.model_combination_benchmark_harness import (
    ModelBenchmarkRoleAssignment,
    ModelBenchmarkTask,
    build_model_benchmark_candidate,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_outcomes import VerifierDecision
from modules.ai_intelligence.ai_gateway.tests.test_model_autoresearch_campaign_execution import (
    REPO_ROOT,
)


MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "ai_intelligence"
    / "ai_gateway"
    / "src"
    / "model_autoresearch_semantic_verifier.py"
)


def _digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _task(
    *,
    prompt: str = "Audit RedDog evidence handling.",
    contains: str = "evidence;bounded",
    excludes: str = "",
) -> ModelBenchmarkTask:
    metadata = {"expected_answer_contains": contains}
    if excludes:
        metadata["expected_answer_excludes"] = excludes
    return ModelBenchmarkTask(
        task_id="task-001",
        task_family="architecture",
        prompt_digest=_digest(prompt),
        expected_output_digest="sha256:not-used-by-semantic-verifier",
        verifier_contract_digest="sha256:semantic-verifier",
        metadata=metadata,
    )


def _candidate(*roles: str):
    assignments = tuple(
        ModelBenchmarkRoleAssignment(
            role=role,
            model_id=f"provider/{role}-model",
            provider="provider",
        )
        for role in (roles or ("principal",))
    )
    return build_model_benchmark_candidate(assignments)


class FakeConfiguredCaller:
    def __init__(self, responses: dict[str, str] | None = None) -> None:
        self.responses = responses or {"principal": "bounded evidence answer"}

    def call_model(
        self, *, provider: str, model: str, prompt: str, task_type: str,
        max_completion_tokens: int, reasoning_effort: str,
    ) -> GatewayModelCallResult:
        role = prompt.split("Role: ", 1)[1].splitlines()[0]
        response = self.responses.get(role, self.responses.get("principal", "bounded evidence answer"))
        return GatewayModelCallResult(
            success=True,
            provider=provider,
            model=model,
            response_text=response,
            latency_ms=10,
            input_tokens=5,
            output_tokens=len(response.split()),
            cost_estimate_usd=0.01,
        )


class ReceiptStore:
    def __init__(self) -> None:
        self.receipts = []

    def append(self, receipt):
        self.receipts.append(receipt)
        return receipt.receipt_id


def _policy(candidate) -> ConfiguredGatewayRunnerPolicy:
    budgets = tuple(
        ConfiguredGatewayModelBudgetEvidence(
            assignment_model_id=item.model_id,
            provider=item.provider,
            api_model=item.model_id.split("/", 1)[1],
            input_cost_per_million="1",
            output_cost_per_million="1",
            request_overhead_input_tokens=11,
            max_completion_tokens=64,
            reasoning_control=ConfiguredGatewayReasoningControlEvidence(
                mode="effort",
                effort="high",
                supported_efforts=("high",),
                catalog_evidence_digest=_digest("semantic-verifier-test-catalog"),
            ),
        )
        for item in candidate.role_assignments
    )
    return ConfiguredGatewayRunnerPolicy(
        allowed_providers=("provider",),
        model_budgets=budgets,
        max_calls_per_sample=4,
        max_total_calls=4,
        max_cost_estimate_usd_per_sample="1",
        allow_panel_candidates=len(budgets) > 1,
        required_prompt_guard_contract_digest=CANONICAL_PROMPT_GUARD_CONTRACT_DIGEST,
        required_prompt_guard_profile_digest=CANONICAL_PROMPT_GUARD_PROFILE_DIGEST,
    )


def _run_sample(
    *,
    task: ModelBenchmarkTask | None = None,
    candidate=None,
    responses: dict[str, str] | None = None,
):
    prompt = "Audit RedDog evidence handling."
    task = task or _task(prompt=prompt)
    candidate = candidate or _candidate()
    store = InMemoryModelAutoResearchOutputEvidenceStore()
    receipts = ReceiptStore()
    runner = build_configured_gateway_benchmark_runner(
        caller=FakeConfiguredCaller(responses),
        prompt_source=MappingPromptSource({task.task_id: prompt}),
        policy=_policy(candidate),
        prompt_guard=build_canonical_local_autoresearch_prompt_guard(),
        output_evidence_store=store,
        runner_receipt_store=receipts,
    )
    output = runner(task, candidate)
    verifier = build_model_autoresearch_output_evidence_semantic_verifier(
        evidence_records=store.records,
        runner_receipts=receipts.receipts,
    )
    return task, candidate, output, store, verifier


def test_semantic_verifier_accepts_rehydrated_output_evidence() -> None:
    task, candidate, output, _store, verifier = _run_sample()

    result = verifier(task, candidate, output)

    assert result.decision == VerifierDecision.ACCEPT
    assert result.evidence_correct is True
    assert result.rejection_reasons == ()
    assert result.verifier_receipt_id.startswith("model_autoresearch_semantic_verifier:")


def test_semantic_verifier_rejects_missing_required_term() -> None:
    task = _task(contains="evidence;missing-term")
    task, candidate, output, _store, verifier = _run_sample(task=task)

    result = verifier(task, candidate, output)

    assert result.decision == VerifierDecision.REJECT
    assert result.evidence_correct is False
    assert "semantic_verifier_required_term_missing:missing-term" in result.rejection_reasons


def test_semantic_verifier_rejects_forbidden_term() -> None:
    task = _task(contains="evidence", excludes="unsafe")
    task, candidate, output, _store, verifier = _run_sample(
        task=task,
        responses={"principal": "bounded evidence unsafe answer"},
    )

    result = verifier(task, candidate, output)

    assert result.decision == VerifierDecision.REJECT
    assert "semantic_verifier_forbidden_term_present:unsafe" in result.rejection_reasons


def test_semantic_verifier_rejects_missing_task_requirements() -> None:
    task = _task(contains="")
    task, candidate, output, _store, verifier = _run_sample(task=task)

    result = verifier(task, candidate, output)

    assert result.decision == VerifierDecision.REJECT
    assert "semantic_verifier_required_terms_missing" in result.rejection_reasons


def test_semantic_verifier_rejects_missing_evidence_records() -> None:
    task, candidate, output, _store, _verifier = _run_sample()
    verifier = build_model_autoresearch_output_evidence_semantic_verifier(evidence_records=())

    result = verifier(task, candidate, output)

    assert result.decision == VerifierDecision.REJECT
    assert "semantic_verifier_evidence_record_count_mismatch" in result.rejection_reasons
    assert "semantic_verifier_role_evidence_missing:principal" in result.rejection_reasons


def test_semantic_verifier_rejects_digest_only_output_without_evidence_id_binding() -> None:
    prompt = "Audit RedDog evidence handling."
    task = _task(prompt=prompt)
    candidate = _candidate()
    evidence_store = InMemoryModelAutoResearchOutputEvidenceStore()
    evidence_receipts, digest_receipts = ReceiptStore(), ReceiptStore()
    evidence_output = build_configured_gateway_benchmark_runner(
        caller=FakeConfiguredCaller(),
        prompt_source=MappingPromptSource({task.task_id: prompt}),
        policy=_policy(candidate),
        prompt_guard=build_canonical_local_autoresearch_prompt_guard(),
        output_evidence_store=evidence_store,
        runner_receipt_store=evidence_receipts,
    )(task, candidate)
    digest_only_output = build_configured_gateway_benchmark_runner(
        caller=FakeConfiguredCaller(),
        prompt_source=MappingPromptSource({task.task_id: prompt}),
        policy=_policy(candidate),
        prompt_guard=build_canonical_local_autoresearch_prompt_guard(),
        runner_receipt_store=digest_receipts,
    )(task, candidate)
    assert evidence_output.output_digest != digest_only_output.output_digest
    verifier = build_model_autoresearch_output_evidence_semantic_verifier(
        evidence_records=evidence_store.records,
        runner_receipts=evidence_receipts.receipts,
    )

    result = verifier(task, candidate, digest_only_output)

    assert result.decision == VerifierDecision.REJECT
    assert "semantic_verifier_runner_receipt_missing" in result.rejection_reasons


def test_semantic_verifier_requires_each_panel_role_evidence() -> None:
    candidate = _candidate("principal", "critic")
    task, candidate, output, _store, verifier = _run_sample(
        candidate=candidate,
        responses={
            "principal": "bounded evidence principal",
            "critic": "bounded evidence critic",
        },
    )

    result = verifier(task, candidate, output)

    assert result.decision == VerifierDecision.ACCEPT
    assert result.evidence_correct is True


def test_semantic_verifier_rejects_distinct_duplicate_role_evidence() -> None:
    task, candidate, output, store, verifier = _run_sample()
    first = store.records[0]
    store.append(
        build_model_autoresearch_output_evidence_record(
            task_id=first["task_id"],
            prompt_digest=first["prompt_digest"],
            candidate_id=first["candidate_id"],
            candidate_topology_digest=first["candidate_topology_digest"],
            role=first["role"],
            provider=first["provider"],
            model=first["model"],
            policy_digest=first["policy_digest"],
            response_text="different bounded evidence answer",
            latency_ms=first["latency_ms"],
            input_tokens=first["input_tokens"],
            output_tokens=first["output_tokens"],
            cost_estimate_usd=first["cost_estimate_usd"],
        )
    )
    result = verifier(task, candidate, output)
    assert result.decision == VerifierDecision.REJECT
    assert "semantic_verifier_duplicate_role_evidence" in result.rejection_reasons


def test_semantic_verifier_module_has_no_network_command_runtime_or_holoindex_imports() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    banned_import_roots = {
        "subprocess",
        "requests",
        "urllib",
        "http",
        "socket",
        "openai",
        "holo_index",
        "pattern_memory",
        "git",
    }
    banned_calls = {"eval", "exec", "compile", "__import__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned_calls

    assert "extension.js" not in source
