"""Tests for model champion/challenger promotion gate."""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.model_combination_benchmark_harness import (
    ModelBenchmarkRoleAssignment,
    ModelBenchmarkTask,
    ModelBenchmarkTaskOutput,
    ModelBenchmarkVerifierResult,
    build_model_benchmark_candidate,
    run_model_combination_benchmark,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_outcomes import (
    ModelOutcomeMetrics,
    VerifierDecision,
)
from modules.ai_intelligence.ai_gateway.src.model_promotion_gate import (
    ModelPromotionGateDecision,
    ModelPromotionPolicy,
    evaluate_model_promotion_gate,
    rehydrate_model_promotion_gate_receipt,
)


def _tasks():
    return (
        ModelBenchmarkTask(
            task_id="task-001",
            task_family="architecture",
            prompt_digest="sha256:prompt-a",
            expected_output_digest="sha256:expected-a",
            verifier_contract_digest="sha256:verifier-contract",
        ),
        ModelBenchmarkTask(
            task_id="task-002",
            task_family="architecture",
            prompt_digest="sha256:prompt-b",
            expected_output_digest="sha256:expected-b",
            verifier_contract_digest="sha256:verifier-contract",
        ),
    )


def _candidate(model_id: str = "provider/model-a"):
    return build_model_benchmark_candidate(
        (ModelBenchmarkRoleAssignment(role="principal", model_id=model_id, provider="provider"),)
    )


def _runner(task, candidate):
    return ModelBenchmarkTaskOutput(
        output_digest=f"sha256:output:{candidate.candidate_id}:{task.task_id}",
        runner_receipt_id=f"runner:{candidate.candidate_id}:{task.task_id}",
        metrics=ModelOutcomeMetrics(latency_ms=100, input_tokens=10, output_tokens=5, cost_estimate_usd=0.01),
    )


def _accepting_verifier(task, candidate, output):
    return ModelBenchmarkVerifierResult(
        decision=VerifierDecision.ACCEPT,
        verifier_receipt_id=f"verify:{candidate.candidate_id}:{task.task_id}",
        evidence_correct=True,
    )


def _rejecting_verifier(task, candidate, output):
    if task.task_id == "task-001":
        return _accepting_verifier(task, candidate, output)
    return ModelBenchmarkVerifierResult(
        decision=VerifierDecision.REJECT,
        verifier_receipt_id=f"verify:{candidate.candidate_id}:{task.task_id}",
        evidence_correct=False,
        rejection_reasons=("bad_claim",),
    )


def _benchmark(verifier=_accepting_verifier):
    return run_model_combination_benchmark(
        tasks=_tasks(),
        candidates=(_candidate(),),
        runner=_runner,
        verifier=verifier,
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
    )


def _policy(run):
    return ModelPromotionPolicy(
        task_family="architecture",
        candidate_id="provider/model-a",
        min_verifier_pass_rate=0.9,
        min_sample_count=2,
        required_task_set_digest=run.task_set_digest,
        required_held_out_split_digest=run.held_out_split_digest,
        required_verifier_digest=run.verifier_digest,
        max_latency_ms=200,
        max_cost_estimate_usd=1.0,
    )


def test_gate_promotes_champion_only_with_signed_authority_and_matching_benchmark():
    run = _benchmark()
    receipt = evaluate_model_promotion_gate(
        benchmark_run_receipt=run,
        policy=_policy(run),
        promotion_authority_receipt_id="authority:1",
        signed_promotion_receipt_id="signed:1",
    )

    assert receipt.decision == ModelPromotionGateDecision.PROMOTE_CHAMPION
    assert receipt.rejection_reasons == ()
    assert receipt.promotion_evidence_receipt is not None
    assert receipt.promotion_evidence_receipt.model_id == "provider/model-a"
    assert receipt.promotion_evidence_receipt.signed_promotion_receipt_id == "signed:1"
    assert receipt.receipt_id.startswith("model_promotion_gate:")


def test_gate_rejects_champion_when_signed_authority_is_missing():
    run = _benchmark()

    receipt = evaluate_model_promotion_gate(
        benchmark_run_receipt=run,
        policy=_policy(run),
        promotion_authority_receipt_id="authority:1",
    )

    assert receipt.decision == ModelPromotionGateDecision.REJECT
    assert receipt.promotion_evidence_receipt is None
    assert receipt.rejection_reasons == ("missing_signed_promotion_receipt",)


def test_gate_keeps_challenger_when_benchmark_is_below_threshold():
    run = _benchmark(verifier=_rejecting_verifier)

    receipt = evaluate_model_promotion_gate(
        benchmark_run_receipt=run,
        policy=_policy(run),
        promotion_authority_receipt_id="authority:1",
        signed_promotion_receipt_id="signed:1",
    )

    assert receipt.decision == ModelPromotionGateDecision.KEEP_CHALLENGER
    assert receipt.promotion_evidence_receipt is None
    assert receipt.rejection_reasons == ("verifier_pass_rate_below_champion_threshold",)


def test_gate_rejects_missing_or_wrong_candidate_evidence():
    run = _benchmark()
    policy = ModelPromotionPolicy(
        task_family="architecture",
        candidate_id="provider/missing",
        min_verifier_pass_rate=0.9,
        min_sample_count=2,
        required_task_set_digest=run.task_set_digest,
        required_held_out_split_digest=run.held_out_split_digest,
        required_verifier_digest=run.verifier_digest,
    )

    receipt = evaluate_model_promotion_gate(
        benchmark_run_receipt=run,
        policy=policy,
        promotion_authority_receipt_id="authority:1",
        signed_promotion_receipt_id="signed:1",
    )

    assert receipt.decision == ModelPromotionGateDecision.REJECT
    assert receipt.rejection_reasons == ("benchmark_evidence_missing_or_ambiguous",)


def test_gate_rejects_tampered_benchmark_projection():
    run = _benchmark()
    evidence = replace(run.benchmark_evidence_receipts[0], held_out_split_digest="held_out_split:tampered")
    tampered = replace(run, benchmark_evidence_receipts=(evidence,))

    receipt = evaluate_model_promotion_gate(
        benchmark_run_receipt=tampered,
        policy=_policy(run),
        promotion_authority_receipt_id="authority:1",
        signed_promotion_receipt_id="signed:1",
    )

    assert receipt.decision == ModelPromotionGateDecision.REJECT
    assert "evidence_held_out_split_digest_mismatch" in receipt.rejection_reasons


def test_gate_rejects_policy_digest_and_metric_conflicts():
    run = _benchmark()
    bad_policy = replace(
        _policy(run),
        required_task_set_digest="model_benchmark_task_set:wrong",
        max_latency_ms=50,
    )

    receipt = evaluate_model_promotion_gate(
        benchmark_run_receipt=run,
        policy=bad_policy,
        promotion_authority_receipt_id="authority:1",
        signed_promotion_receipt_id="signed:1",
    )

    assert receipt.decision == ModelPromotionGateDecision.REJECT
    assert "task_set_digest_mismatch" in receipt.rejection_reasons
    assert "latency_above_policy" in receipt.rejection_reasons


def test_gate_policy_requires_nonzero_threshold_and_sample_count():
    run = _benchmark()
    for kwargs, expected in (
        ({"min_verifier_pass_rate": 0.0}, "invalid_verifier_threshold"),
        ({"min_sample_count": 0}, "invalid_min_sample_count"),
    ):
        data = {
            "task_family": "architecture",
            "candidate_id": "provider/model-a",
            "min_verifier_pass_rate": 0.9,
            "min_sample_count": 2,
            "required_task_set_digest": run.task_set_digest,
            "required_held_out_split_digest": run.held_out_split_digest,
            "required_verifier_digest": run.verifier_digest,
        }
        data.update(kwargs)
        try:
            ModelPromotionPolicy(**data).normalized()
        except ValueError as exc:
            assert str(exc) == expected
        else:
            raise AssertionError(f"expected {expected}")


def test_gate_digest_is_stable_and_binds_signed_receipt():
    run = _benchmark()
    first = evaluate_model_promotion_gate(
        benchmark_run_receipt=run,
        policy=_policy(run),
        promotion_authority_receipt_id="authority:1",
        signed_promotion_receipt_id="signed:1",
    )
    second = evaluate_model_promotion_gate(
        benchmark_run_receipt=run,
        policy=_policy(run),
        promotion_authority_receipt_id="authority:1",
        signed_promotion_receipt_id="signed:1",
    )
    changed = evaluate_model_promotion_gate(
        benchmark_run_receipt=run,
        policy=_policy(run),
        promotion_authority_receipt_id="authority:1",
        signed_promotion_receipt_id="signed:2",
    )

    assert first.receipt_id == second.receipt_id
    assert first.receipt_id != changed.receipt_id


def test_rehydrate_promotion_gate_receipt_round_trips_champion_and_challenger():
    champion = evaluate_model_promotion_gate(
        benchmark_run_receipt=_benchmark(),
        policy=_policy(_benchmark()),
        promotion_authority_receipt_id="authority:1",
        signed_promotion_receipt_id="signed:1",
    )
    challenger_run = _benchmark(verifier=_rejecting_verifier)
    challenger = evaluate_model_promotion_gate(
        benchmark_run_receipt=challenger_run,
        policy=_policy(challenger_run),
        promotion_authority_receipt_id="authority:1",
        signed_promotion_receipt_id="signed:1",
    )

    hydrated_champion = rehydrate_model_promotion_gate_receipt(champion.to_dict())
    hydrated_challenger = rehydrate_model_promotion_gate_receipt(challenger.to_dict())

    assert hydrated_champion.receipt_id == champion.receipt_id
    assert hydrated_champion.promotion_evidence_receipt is not None
    assert hydrated_challenger.receipt_id == challenger.receipt_id
    assert hydrated_challenger.decision == ModelPromotionGateDecision.KEEP_CHALLENGER


def test_rehydrate_promotion_gate_rejects_tampering_and_inconsistent_evidence():
    receipt = evaluate_model_promotion_gate(
        benchmark_run_receipt=_benchmark(),
        policy=_policy(_benchmark()),
        promotion_authority_receipt_id="authority:1",
        signed_promotion_receipt_id="signed:1",
    ).to_dict()

    tampered_id = dict(receipt)
    tampered_id["benchmark_run_receipt_id"] = "model_combination_benchmark_run_projection:tampered"
    missing_evidence = dict(receipt)
    missing_evidence["promotion_evidence_receipt"] = None
    mismatched_evidence = dict(receipt)
    mismatched_evidence["promotion_evidence_receipt"] = dict(receipt["promotion_evidence_receipt"])
    mismatched_evidence["promotion_evidence_receipt"]["model_id"] = "provider/other"

    for payload, expected in (
        (tampered_id, "promotion_gate_receipt_id_mismatch"),
        (missing_evidence, "promotion_evidence_missing"),
        (mismatched_evidence, "promotion_evidence_receipt_id_mismatch"),
    ):
        try:
            rehydrate_model_promotion_gate_receipt(payload)
        except ValueError as exc:
            assert str(exc) == expected
        else:
            raise AssertionError("tampered promotion gate receipt was accepted")


def test_promotion_gate_module_has_no_network_command_or_runtime_binding_imports():
    source = Path("modules/ai_intelligence/ai_gateway/src/model_promotion_gate.py").read_text()
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert not (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id in {"os", "subprocess", "requests", "urllib", "openai"}
            )

    assert "subprocess" not in imported
    assert "requests" not in imported
    assert "urllib" not in imported
    assert "openai" not in imported
