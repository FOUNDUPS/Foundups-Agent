"""Tests for deterministic model-combination benchmark harness."""

from __future__ import annotations

import ast
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
    production_evidence_for_selection,
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


def _single_candidate(model_id: str = "provider/model-a"):
    return build_model_benchmark_candidate(
        (ModelBenchmarkRoleAssignment(role="principal", model_id=model_id, provider="provider"),)
    )


def _accepting_runner(task, candidate):
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


def test_single_model_benchmark_produces_evidence_receipt_bound_to_held_out_tasks():
    candidate = _single_candidate()

    receipt = run_model_combination_benchmark(
        tasks=_tasks(),
        candidates=(candidate,),
        runner=_accepting_runner,
        verifier=_accepting_verifier,
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
    )

    evidence = receipt.benchmark_evidence_receipts[0]
    assert receipt.receipt_id.startswith("model_combination_benchmark_run:")
    assert receipt.task_set_digest.startswith("model_benchmark_task_set:")
    assert receipt.held_out_split_digest.startswith("held_out_split:")
    assert evidence.model_id == "provider/model-a"
    assert evidence.sample_count == 2
    assert evidence.accepted_count == 2
    assert evidence.verifier_pass_rate == 1.0
    assert evidence.task_set_digest == receipt.task_set_digest
    assert evidence.held_out_split_digest == receipt.held_out_split_digest
    assert evidence.prompt_topology_digest == candidate.topology_digest
    assert evidence.metrics.input_tokens == 20
    assert evidence.metrics.output_tokens == 10


def test_panel_candidate_binds_role_topology_and_is_not_direct_model_id():
    candidate = build_model_benchmark_candidate(
        (
            ModelBenchmarkRoleAssignment(role="principal", model_id="a/lead", provider="a"),
            ModelBenchmarkRoleAssignment(role="critic", model_id="b/critic", provider="b"),
        )
    )

    receipt = run_model_combination_benchmark(
        tasks=_tasks(),
        candidates=(candidate,),
        runner=_accepting_runner,
        verifier=_accepting_verifier,
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
    )

    assert candidate.candidate_id.startswith("model_panel_candidate:")
    assert candidate.topology_digest.startswith("model_panel_topology:")
    assert receipt.benchmark_evidence_receipts[0].model_id == candidate.candidate_id
    assert [assignment.role for assignment in candidate.role_assignments] == ["principal", "critic"]


def test_candidate_rejects_verifier_role_inside_candidate_panel():
    try:
        build_model_benchmark_candidate(
            (
                ModelBenchmarkRoleAssignment(role="principal", model_id="a/lead", provider="a"),
                ModelBenchmarkRoleAssignment(role="verifier", model_id="b/verify", provider="b"),
            )
        )
    except ValueError as exc:
        assert str(exc) == "verifier_role_reserved_for_independent_verifier"
    else:
        raise AssertionError("expected verifier role rejection")


def test_runner_error_fails_closed_without_blocking_other_candidates():
    good = _single_candidate("provider/good")
    bad = _single_candidate("provider/bad")

    def runner(task, candidate):
        if candidate.candidate_id == "provider/bad":
            raise RuntimeError("provider unavailable")
        return _accepting_runner(task, candidate)

    receipt = run_model_combination_benchmark(
        tasks=_tasks(),
        candidates=(bad, good),
        runner=runner,
        verifier=_accepting_verifier,
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
    )

    by_model = {item.model_id: item for item in receipt.benchmark_evidence_receipts}
    assert by_model["provider/good"].verifier_pass_rate == 1.0
    assert by_model["provider/bad"].verifier_pass_rate == 0.0
    bad_samples = [sample for sample in receipt.samples if sample.candidate_id == "provider/bad"]
    assert all(sample.rejection_reasons == ("runner_error",) for sample in bad_samples)


def test_verifier_rejection_and_bad_evidence_reduce_pass_rate():
    candidate = _single_candidate()

    def verifier(task, candidate, output):
        if task.task_id == "task-001":
            return _accepting_verifier(task, candidate, output)
        return ModelBenchmarkVerifierResult(
            decision=VerifierDecision.ACCEPT,
            verifier_receipt_id=f"verify:{candidate.candidate_id}:{task.task_id}",
            evidence_correct=False,
            rejection_reasons=("wrong_file_line",),
        )

    receipt = run_model_combination_benchmark(
        tasks=_tasks(),
        candidates=(candidate,),
        runner=_accepting_runner,
        verifier=verifier,
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
    )

    evidence = receipt.benchmark_evidence_receipts[0]
    assert evidence.accepted_count == 1
    assert evidence.verifier_pass_rate == 0.5
    rejected = [sample for sample in receipt.samples if not sample.accepted]
    assert rejected[0].rejection_reasons == ("evidence_not_verified", "wrong_file_line")


def test_harness_digest_is_stable_and_changes_with_held_out_split():
    candidate = _single_candidate()
    first = run_model_combination_benchmark(
        tasks=_tasks(),
        candidates=(candidate,),
        runner=_accepting_runner,
        verifier=_accepting_verifier,
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
    )
    second = run_model_combination_benchmark(
        tasks=_tasks(),
        candidates=(candidate,),
        runner=_accepting_runner,
        verifier=_accepting_verifier,
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
    )
    changed = run_model_combination_benchmark(
        tasks=_tasks(),
        candidates=(candidate,),
        runner=_accepting_runner,
        verifier=_accepting_verifier,
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v2",
    )

    assert first.receipt_id == second.receipt_id
    assert first.receipt_id != changed.receipt_id


def test_harness_rejects_duplicate_or_mixed_task_sets():
    candidate = _single_candidate()
    duplicate = (_tasks()[0], _tasks()[0])
    mixed = (
        _tasks()[0],
        ModelBenchmarkTask(
            task_id="task-003",
            task_family="coding",
            prompt_digest="sha256:prompt-c",
            expected_output_digest="sha256:expected-c",
            verifier_contract_digest="sha256:verifier-contract",
        ),
    )

    for tasks, expected in ((duplicate, "duplicate_benchmark_task_ids"), (mixed, "mixed_task_families")):
        try:
            run_model_combination_benchmark(
                tasks=tasks,
                candidates=(candidate,),
                runner=_accepting_runner,
                verifier=_accepting_verifier,
                verifier_digest="sha256:verifier",
                held_out_split_id="heldout-v1",
            )
        except ValueError as exc:
            assert str(exc) == expected
        else:
            raise AssertionError(f"expected {expected}")


def test_panel_benchmark_evidence_is_not_accidentally_accepted_as_single_model_production_evidence():
    panel = build_model_benchmark_candidate(
        (
            ModelBenchmarkRoleAssignment(role="principal", model_id="a/lead", provider="a"),
            ModelBenchmarkRoleAssignment(role="critic", model_id="b/critic", provider="b"),
        )
    )
    receipt = run_model_combination_benchmark(
        tasks=_tasks(),
        candidates=(panel,),
        runner=_accepting_runner,
        verifier=_accepting_verifier,
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
    )

    evidence = receipt.benchmark_evidence_receipts[0]
    assert evidence.model_id == panel.candidate_id
    assert evidence.model_id not in {"a/lead", "b/critic"}

    # A later promotion gate may define panel production semantics. This harness
    # only measures the panel and must not silently map it to an individual model.
    assert production_evidence_for_selection


def test_harness_module_has_no_network_command_or_provider_imports():
    source = Path(
        "modules/ai_intelligence/ai_gateway/src/model_combination_benchmark_harness.py"
    ).read_text()
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
