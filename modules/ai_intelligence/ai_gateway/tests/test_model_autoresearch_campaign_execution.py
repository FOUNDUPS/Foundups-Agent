"""Tests for bounded model AutoResearch campaign execution."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_execution import (
    MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_ACCEPT,
    MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_REJECT,
    ModelAutoResearchCampaignExecutionReason,
    run_reddog_model_autoresearch_campaign_execution,
)
from modules.ai_intelligence.ai_gateway.src.model_champion_challenger_autoresearch import (
    plan_model_champion_challenger_autoresearch,
)
from modules.ai_intelligence.ai_gateway.src.model_combination_benchmark_harness import (
    ModelBenchmarkTask,
    ModelBenchmarkTaskOutput,
    ModelBenchmarkVerifierResult,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_outcomes import (
    ModelOutcomeMetrics,
    VerifierDecision,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_champion_challenger_autoresearch import (
    _candidate,
    _feedback_record,
    _gate,
    _policy,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "ai_intelligence"
    / "ai_gateway"
    / "src"
    / "model_autoresearch_campaign_execution.py"
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
        metrics=ModelOutcomeMetrics(
            latency_ms=100,
            input_tokens=10,
            output_tokens=5,
            cost_estimate_usd=0.01,
        ),
    )


def _verifier(task, candidate, output):
    return ModelBenchmarkVerifierResult(
        decision=VerifierDecision.ACCEPT,
        verifier_receipt_id=f"verify:{candidate.candidate_id}:{task.task_id}",
        evidence_correct=True,
    )


def _plan():
    challenger_gate = _gate("provider/challenger", pass_all=False)
    feedback = _feedback_record("provider/new", suffix="2")
    return plan_model_champion_challenger_autoresearch(
        promotion_gate_receipts=(challenger_gate,),
        candidate_pool=(
            _candidate("provider/challenger"),
            _candidate("provider/new"),
        ),
        policy=_policy(),
        feedback_records=(feedback,),
    )


def test_campaign_execution_runs_verified_plan_candidates_and_writes_receipt(tmp_path: Path) -> None:
    plan = _plan()
    output = tmp_path / "runtime" / "campaign_execution.json"

    result = run_reddog_model_autoresearch_campaign_execution(
        repo_root=REPO_ROOT,
        plan_receipt=plan.to_dict(),
        candidate_pool=(
            _candidate("provider/challenger").to_dict(),
            _candidate("provider/new").to_dict(),
        ),
        tasks=[task.to_dict() for task in _tasks()],
        runner=_runner,
        verifier=_verifier,
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
        output_path=output,
    )

    assert result.accepted is True
    assert result.status == MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_ACCEPT
    assert result.execution_receipt_id and result.execution_receipt_id.startswith(
        "model_autoresearch_campaign_execution:"
    )
    assert result.source_plan_receipt_id == plan.receipt_id
    assert result.executed_candidate_ids == ("provider/new", "provider/challenger")
    assert result.task_count == 2
    assert result.no_direct_provider_call_performed is True
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["receipt_id"] == result.execution_receipt_id
    assert payload["source_plan_receipt_id"] == plan.receipt_id
    assert payload["benchmark_run_receipt"]["task_family"] == "architecture"
    assert len(payload["benchmark_run_receipt"]["benchmark_evidence_receipts"]) == 2


def test_campaign_execution_rejects_tampered_plan_receipt(tmp_path: Path) -> None:
    plan = _plan().to_dict()
    plan["campaign_items"][0]["candidate_id"] = "provider/tampered"

    result = run_reddog_model_autoresearch_campaign_execution(
        repo_root=REPO_ROOT,
        plan_receipt=plan,
        candidate_pool=(_candidate("provider/new").to_dict(),),
        tasks=[task.to_dict() for task in _tasks()],
        runner=_runner,
        verifier=_verifier,
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
        output_path=tmp_path / "execution.json",
    )

    assert result.status == MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_REJECT
    assert ModelAutoResearchCampaignExecutionReason.PLAN_INVALID in result.rejection_reasons


def test_campaign_execution_rejects_candidate_pool_digest_mismatch(tmp_path: Path) -> None:
    result = run_reddog_model_autoresearch_campaign_execution(
        repo_root=REPO_ROOT,
        plan_receipt=_plan().to_dict(),
        candidate_pool=(_candidate("provider/challenger").to_dict(),),
        tasks=[task.to_dict() for task in _tasks()],
        runner=_runner,
        verifier=_verifier,
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
        output_path=tmp_path / "execution.json",
    )

    assert result.status == MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_REJECT
    assert ModelAutoResearchCampaignExecutionReason.CANDIDATE_POOL_DIGEST_MISMATCH in result.rejection_reasons
    assert ModelAutoResearchCampaignExecutionReason.CAMPAIGN_CANDIDATE_MISSING in result.rejection_reasons


def test_campaign_execution_rejects_verifier_digest_mismatch(tmp_path: Path) -> None:
    result = run_reddog_model_autoresearch_campaign_execution(
        repo_root=REPO_ROOT,
        plan_receipt=_plan().to_dict(),
        candidate_pool=(
            _candidate("provider/challenger").to_dict(),
            _candidate("provider/new").to_dict(),
        ),
        tasks=[task.to_dict() for task in _tasks()],
        runner=_runner,
        verifier=_verifier,
        verifier_digest="sha256:other",
        held_out_split_id="heldout-v1",
        output_path=tmp_path / "execution.json",
    )

    assert result.status == MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_REJECT
    assert ModelAutoResearchCampaignExecutionReason.VERIFIER_DIGEST_MISMATCH in result.rejection_reasons


def test_campaign_execution_rejects_stop_only_plan(tmp_path: Path) -> None:
    champion_gate = _gate("provider/champion", pass_all=True)
    plan = plan_model_champion_challenger_autoresearch(
        promotion_gate_receipts=(champion_gate,),
        candidate_pool=(_candidate("provider/champion"),),
        policy=_policy(),
    )

    result = run_reddog_model_autoresearch_campaign_execution(
        repo_root=REPO_ROOT,
        plan_receipt=plan.to_dict(),
        candidate_pool=(_candidate("provider/champion").to_dict(),),
        tasks=[task.to_dict() for task in _tasks()],
        runner=_runner,
        verifier=_verifier,
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
        output_path=tmp_path / "execution.json",
    )

    assert result.status == MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_REJECT
    assert ModelAutoResearchCampaignExecutionReason.NO_EXECUTABLE_CAMPAIGN_ITEMS in result.rejection_reasons


def test_campaign_execution_rejects_output_inside_repo_without_writing() -> None:
    output = REPO_ROOT / "model_autoresearch_campaign_execution.json"

    result = run_reddog_model_autoresearch_campaign_execution(
        repo_root=REPO_ROOT,
        plan_receipt=_plan().to_dict(),
        candidate_pool=(
            _candidate("provider/challenger").to_dict(),
            _candidate("provider/new").to_dict(),
        ),
        tasks=[task.to_dict() for task in _tasks()],
        runner=_runner,
        verifier=_verifier,
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
        output_path=output,
    )

    assert result.status == MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_REJECT
    assert ModelAutoResearchCampaignExecutionReason.OUTPUT_PATH_INVALID in result.rejection_reasons
    assert not output.exists()


def test_campaign_execution_module_has_no_provider_network_command_runtime_or_holoindex_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
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
