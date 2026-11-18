"""Tests for model AutoResearch plan artifact supply."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.model_autoresearch_plan_artifact_supply import (
    MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY_ACCEPT,
    MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY_REJECT,
    ModelAutoResearchPlanArtifactSupplyReason,
    run_reddog_model_autoresearch_plan_artifact_supply,
)
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
    ModelPromotionPolicy,
    evaluate_model_promotion_gate,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "ai_intelligence"
    / "ai_gateway"
    / "src"
    / "model_autoresearch_plan_artifact_supply.py"
)


def _candidate(model_id: str):
    return build_model_benchmark_candidate(
        (ModelBenchmarkRoleAssignment(role="principal", model_id=model_id, provider="provider"),)
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


def _runner(task, candidate):
    return ModelBenchmarkTaskOutput(
        output_digest=f"sha256:output:{candidate.candidate_id}:{task.task_id}",
        runner_receipt_id=f"runner:{candidate.candidate_id}:{task.task_id}",
        metrics=ModelOutcomeMetrics(latency_ms=100, input_tokens=10, output_tokens=5, cost_estimate_usd=0.01),
    )


def _verifier(pass_all: bool):
    def verifier(task, candidate, output):
        if pass_all or task.task_id == "task-001":
            return ModelBenchmarkVerifierResult(
                decision=VerifierDecision.ACCEPT,
                verifier_receipt_id=f"verify:{candidate.candidate_id}:{task.task_id}",
                evidence_correct=True,
            )
        return ModelBenchmarkVerifierResult(
            decision=VerifierDecision.REJECT,
            verifier_receipt_id=f"verify:{candidate.candidate_id}:{task.task_id}",
            evidence_correct=False,
            rejection_reasons=("bad_claim",),
        )

    return verifier


def _gate(candidate_id: str, *, pass_all: bool):
    candidate = _candidate(candidate_id)
    run = run_model_combination_benchmark(
        tasks=_tasks(),
        candidates=(candidate,),
        runner=_runner,
        verifier=_verifier(pass_all),
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
    )
    policy = ModelPromotionPolicy(
        task_family="architecture",
        candidate_id=candidate_id,
        min_verifier_pass_rate=0.9,
        min_sample_count=2,
        required_task_set_digest=run.task_set_digest,
        required_held_out_split_digest=run.held_out_split_digest,
        required_verifier_digest=run.verifier_digest,
    )
    return evaluate_model_promotion_gate(
        benchmark_run_receipt=run,
        policy=policy,
        promotion_authority_receipt_id="authority:1",
        signed_promotion_receipt_id="signed:1",
    )


def _policy():
    return {
        "schema_version": "model_autoresearch_policy.v1",
        "task_family": "architecture",
        "catalog_snapshot_id": "model_catalog_snapshot:1",
        "max_campaign_items": 3,
        "required_verifier_digest": "sha256:verifier",
        "cost_budget_receipt_id": "cost_budget:1",
    }


def _feedback_record(model_id: str) -> dict:
    return {
        "record_type": "model_selection_outcome_feedback",
        "schema_version": "model_feedback_ledger_record.v1",
        "feedback_record_id": "model_feedback_runtime",
        "outcome_receipt_id": "model_selection_outcome_receipt:runtime",
        "selection_receipt_id": "model_selection_receipt:runtime",
        "catalog_snapshot_id": "model_catalog_snapshot:1",
        "task_family": "architecture",
        "selected_model_ids": [model_id],
        "verification_receipt_ids": ["verify:runtime"],
        "source_ratchet_id": "outcome_ratchet_runtime",
        "source_ratchet_digest": "sha256:" + "1" * 64,
    }


def _cycle_feedback_record(model_id: str) -> dict:
    return {
        "record_type": "model_autoresearch_cycle_feedback",
        "schema_version": "model_autoresearch_cycle_feedback_record.v1",
        "feedback_record_id": "model_autoresearch_cycle_feedback_runtime",
        "cycle_receipt_id": "model_autoresearch_cycle:runtime",
        "source_plan_receipt_id": "model_autoresearch_plan:runtime",
        "source_plan_context_bound": True,
        "campaign_execution_receipt_id": "model_autoresearch_campaign_execution:runtime",
        "promotion_gate_supply_receipt_id": "model_autoresearch_promotion_gate_supply:runtime",
        "catalog_snapshot_id": "model_catalog_snapshot:1",
        "task_family": "architecture",
        "executed_candidate_ids": [model_id],
        "promotion_gate_receipt_ids": ["model_promotion_gate:runtime"],
        "source_plan_receipt_digest": "sha256:" + "2" * 64,
    }


def test_supplier_writes_plan_from_serialized_inputs_and_feedback(tmp_path: Path):
    challenger = _gate("provider/challenger", pass_all=False)
    output = tmp_path / "runtime" / "autoresearch_plan.json"

    result = run_reddog_model_autoresearch_plan_artifact_supply(
        repo_root=REPO_ROOT,
        promotion_gate_receipts=(challenger.to_dict(),),
        candidate_pool=(
            _candidate("provider/challenger").to_dict(),
            _candidate("provider/new").to_dict(),
        ),
        policy=_policy(),
        feedback_records=(_feedback_record("provider/new"),),
        output_path=output,
    )

    assert result.accepted is True
    assert result.status == MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY_ACCEPT
    assert result.plan_receipt_id and result.plan_receipt_id.startswith("model_autoresearch_plan:")
    assert result.source_gate_receipt_ids == (challenger.receipt_id,)
    assert result.source_feedback_record_ids == ("model_feedback_runtime",)
    assert result.no_model_call_performed is True
    assert result.no_benchmark_run_performed is True
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["receipt_id"] == result.plan_receipt_id
    assert payload["campaign_items"][0]["candidate_id"] == "provider/new"
    assert payload["campaign_items"][0]["reason"] == "verified_runtime_feedback_unbenchmarked_candidate"


def test_supplier_writes_plan_from_context_bound_cycle_feedback(tmp_path: Path):
    challenger = _gate("provider/challenger", pass_all=False)
    output = tmp_path / "runtime" / "autoresearch_plan.json"

    result = run_reddog_model_autoresearch_plan_artifact_supply(
        repo_root=REPO_ROOT,
        promotion_gate_receipts=(challenger.to_dict(),),
        candidate_pool=(
            _candidate("provider/challenger").to_dict(),
            _candidate("provider/new").to_dict(),
        ),
        policy=_policy(),
        feedback_records=(_cycle_feedback_record("provider/new"),),
        output_path=output,
    )

    assert result.accepted is True
    assert result.status == MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY_ACCEPT
    assert result.source_feedback_record_ids == ("model_autoresearch_cycle_feedback_runtime",)
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["source_feedback_record_ids"] == ["model_autoresearch_cycle_feedback_runtime"]
    assert payload["campaign_items"][0]["candidate_id"] == "provider/new"
    assert payload["campaign_items"][0]["priority"] == "P0"
    assert payload["campaign_items"][0]["reason"] == "verified_runtime_feedback_unbenchmarked_candidate"


def test_supplier_rejects_inside_repo_output_without_writing():
    challenger = _gate("provider/challenger", pass_all=False)
    output = REPO_ROOT / "autoresearch_plan.json"

    result = run_reddog_model_autoresearch_plan_artifact_supply(
        repo_root=REPO_ROOT,
        promotion_gate_receipts=(challenger.to_dict(),),
        candidate_pool=(_candidate("provider/challenger").to_dict(),),
        policy=_policy(),
        output_path=output,
    )

    assert result.status == MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY_REJECT
    assert ModelAutoResearchPlanArtifactSupplyReason.OUTPUT_PATH_INVALID in result.rejection_reasons
    assert not output.exists()


def test_supplier_rejects_tampered_gate_and_candidate(tmp_path: Path):
    gate = _gate("provider/challenger", pass_all=False).to_dict()
    gate["benchmark_run_receipt_id"] = "tampered"
    candidate = _candidate("provider/challenger").to_dict()
    tampered_candidate = dict(candidate)
    tampered_candidate["topology_digest"] = "sha256:tampered"

    bad_gate = run_reddog_model_autoresearch_plan_artifact_supply(
        repo_root=REPO_ROOT,
        promotion_gate_receipts=(gate,),
        candidate_pool=(candidate,),
        policy=_policy(),
        output_path=tmp_path / "gate.json",
    )
    bad_candidate = run_reddog_model_autoresearch_plan_artifact_supply(
        repo_root=REPO_ROOT,
        promotion_gate_receipts=(_gate("provider/challenger", pass_all=False).to_dict(),),
        candidate_pool=(tampered_candidate,),
        policy=_policy(),
        output_path=tmp_path / "candidate.json",
    )

    assert ModelAutoResearchPlanArtifactSupplyReason.PROMOTION_GATES_INVALID in bad_gate.rejection_reasons
    assert ModelAutoResearchPlanArtifactSupplyReason.CANDIDATE_POOL_INVALID in bad_candidate.rejection_reasons
    assert not (tmp_path / "gate.json").exists()
    assert not (tmp_path / "candidate.json").exists()


def test_supplier_rejects_feedback_record_that_fails_planner_validation(tmp_path: Path):
    challenger = _gate("provider/challenger", pass_all=False)
    feedback = _feedback_record("provider/new")
    feedback["source_ratchet_digest"] = "not-a-digest"

    result = run_reddog_model_autoresearch_plan_artifact_supply(
        repo_root=REPO_ROOT,
        promotion_gate_receipts=(challenger.to_dict(),),
        candidate_pool=(_candidate("provider/new").to_dict(),),
        policy=_policy(),
        feedback_records=(feedback,),
        output_path=tmp_path / "plan.json",
    )

    assert result.status == MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY_REJECT
    assert ModelAutoResearchPlanArtifactSupplyReason.FEEDBACK_RECORDS_INVALID in result.rejection_reasons
    assert not (tmp_path / "plan.json").exists()


def test_supplier_module_has_no_provider_network_command_runtime_or_holoindex_imports():
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
