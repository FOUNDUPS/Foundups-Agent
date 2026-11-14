"""Tests for MODEL_AUTORESEARCH_CYCLE_FEEDBACK_CHAIN_BOOTSTRAP_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_execution_artifact_supply_bootstrap import (
    MODEL_AUTORESEARCH_CAMPAIGN_CONFIGURED_GATEWAY_RUNNER,
    MODEL_AUTORESEARCH_CAMPAIGN_OUTPUT_EVIDENCE_SEMANTIC_VERIFIER,
    run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_promotion_gate_supply import (
    rehydrate_model_autoresearch_campaign_promotion_gate_supply_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_cycle_feedback_chain_bootstrap import (
    MODEL_AUTORESEARCH_CYCLE_FEEDBACK_CHAIN_BOOTSTRAP_APPLIED,
    MODEL_AUTORESEARCH_CYCLE_FEEDBACK_CHAIN_BOOTSTRAP_NOT_READY,
    run_reddog_model_autoresearch_cycle_feedback_chain_bootstrap,
)
from modules.ai_intelligence.ai_gateway.src.model_promotion_gate import ModelPromotionGateDecision
from modules.ai_intelligence.ai_gateway.tests.test_model_autoresearch_campaign_execution import REPO_ROOT
from modules.ai_intelligence.ai_gateway.tests.test_model_autoresearch_campaign_execution_artifact_supply_bootstrap import (
    _configured_semantic_inputs,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_autoresearch_campaign_promotion_gate_supply import (
    _policies,
)


MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "ai_intelligence"
    / "ai_gateway"
    / "src"
    / "model_autoresearch_cycle_feedback_chain_bootstrap.py"
)


def _write_json(root: Path, name: str, payload: object) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _semantic_execution_files(tmp_path: Path, *, required_term: str = "configured;gateway;answer") -> dict[str, Path]:
    files, gateway = _configured_semantic_inputs(tmp_path)
    tasks_payload = json.loads(files["tasks"].read_text(encoding="utf-8"))
    tasks_payload["tasks"][0]["metadata"] = {"expected_answer_contains": required_term}
    files["tasks"].write_text(json.dumps(tasks_payload, sort_keys=True), encoding="utf-8")
    result = run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap(
        repo_root=REPO_ROOT,
        plan_receipt_path=files["plan"],
        candidate_pool_path=files["candidates"],
        tasks_path=files["tasks"],
        prompt_records_path=files["prompts"],
        output_evidence_path=files["evidence"],
        model_budget_evidence_path=files["budgets"],
        call_attempt_evidence_path=files["attempts"],
        runner_success_receipt_path=files["successes"],
        output_path=files["output"],
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
        runner_mode=MODEL_AUTORESEARCH_CAMPAIGN_CONFIGURED_GATEWAY_RUNNER,
        verifier_mode=MODEL_AUTORESEARCH_CAMPAIGN_OUTPUT_EVIDENCE_SEMANTIC_VERIFIER,
        runner_allowed_providers="provider",
        runner_max_prompt_chars=2000,
        runner_max_calls_per_sample=1,
        runner_max_total_calls=1,
        runner_max_cost_estimate_usd_per_sample="1",
        gateway=gateway,
    )
    assert result.accepted is True
    execution = json.loads(files["output"].read_text(encoding="utf-8"))
    files["policies"] = _write_json(
        tmp_path / "runtime",
        "promotion_policies.json",
        {"promotion_policies": list(_policies(execution, min_pass_rate=1.0, min_sample_count=1))},
    )
    files["gate_output"] = tmp_path / "runtime" / "promotion_gates.json"
    files["cycle_output"] = tmp_path / "runtime" / "cycle_receipt.json"
    files["feedback_output"] = tmp_path / "runtime" / "feedback.jsonl"
    return files


def test_cycle_feedback_chain_admits_semantic_verified_campaign(tmp_path: Path) -> None:
    files = _semantic_execution_files(tmp_path)

    result = run_reddog_model_autoresearch_cycle_feedback_chain_bootstrap(
        repo_root=REPO_ROOT,
        plan_receipt_path=files["plan"],
        campaign_execution_receipt_path=files["output"],
        promotion_policies_path=files["policies"],
        promotion_gate_output_path=files["gate_output"],
        cycle_receipt_output_path=files["cycle_output"],
        feedback_ledger_output_path=files["feedback_output"],
        promotion_authority_receipt_id="authority:semantic",
        signed_promotion_receipt_id="signed:semantic",
    )

    assert result.accepted is True
    assert result.status == MODEL_AUTORESEARCH_CYCLE_FEEDBACK_CHAIN_BOOTSTRAP_APPLIED
    assert result.promotion_gate_supply_receipt_id
    assert result.cycle_receipt_id
    assert result.feedback_admission_id
    assert result.feedback_record_id
    assert result.no_model_promotion_performed is True
    assert result.no_pattern_memory_write_performed is True
    assert result.no_holoindex_reindex_performed is True

    gate = rehydrate_model_autoresearch_campaign_promotion_gate_supply_receipt(
        json.loads(files["gate_output"].read_text(encoding="utf-8"))
    )
    assert gate.promotion_gate_receipts[0].decision == ModelPromotionGateDecision.PROMOTE_CHAMPION

    records = [json.loads(line) for line in files["feedback_output"].read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["cycle_receipt_id"] == result.cycle_receipt_id
    assert records[0]["source_plan_context_bound"] is True


def test_cycle_feedback_chain_admits_verified_negative_outcome_without_promotion(tmp_path: Path) -> None:
    files = _semantic_execution_files(tmp_path, required_term="missing-term")

    result = run_reddog_model_autoresearch_cycle_feedback_chain_bootstrap(
        repo_root=REPO_ROOT,
        plan_receipt_path=files["plan"],
        campaign_execution_receipt_path=files["output"],
        promotion_policies_path=files["policies"],
        promotion_gate_output_path=files["gate_output"],
        cycle_receipt_output_path=files["cycle_output"],
        feedback_ledger_output_path=files["feedback_output"],
        promotion_authority_receipt_id="authority:semantic",
        signed_promotion_receipt_id="signed:semantic",
    )

    assert result.accepted is True
    gate = rehydrate_model_autoresearch_campaign_promotion_gate_supply_receipt(
        json.loads(files["gate_output"].read_text(encoding="utf-8"))
    )
    assert gate.promotion_gate_receipts[0].decision == ModelPromotionGateDecision.KEEP_CHALLENGER
    assert gate.promotion_gate_receipts[0].promotion_evidence_receipt is None
    records = [json.loads(line) for line in files["feedback_output"].read_text(encoding="utf-8").splitlines()]
    assert records[0]["cycle_receipt_id"] == result.cycle_receipt_id


def test_cycle_feedback_chain_rejects_inside_repo_inputs_and_outputs(tmp_path: Path) -> None:
    files = _semantic_execution_files(tmp_path)
    repo_plan = REPO_ROOT / "model_autoresearch_plan_receipt.json"
    repo_output = REPO_ROOT / "model_autoresearch_feedback.jsonl"
    repo_plan.write_text("{}", encoding="utf-8")
    try:
        result = run_reddog_model_autoresearch_cycle_feedback_chain_bootstrap(
            repo_root=REPO_ROOT,
            plan_receipt_path=repo_plan,
            campaign_execution_receipt_path=files["output"],
            promotion_policies_path=files["policies"],
            promotion_gate_output_path=repo_output,
            cycle_receipt_output_path=files["cycle_output"],
            feedback_ledger_output_path=files["feedback_output"],
            promotion_authority_receipt_id="authority:semantic",
            signed_promotion_receipt_id="signed:semantic",
        )
    finally:
        repo_plan.unlink(missing_ok=True)
        repo_output.unlink(missing_ok=True)

    assert result.accepted is False
    assert result.status == MODEL_AUTORESEARCH_CYCLE_FEEDBACK_CHAIN_BOOTSTRAP_NOT_READY
    assert "model_autoresearch_chain_plan_receipt_path_inside_repo" in result.rejection_reasons
    assert "model_autoresearch_chain_promotion_gate_output_path_invalid" in result.rejection_reasons
    assert not files["cycle_output"].exists()
    assert not files["feedback_output"].exists()


def test_cycle_feedback_chain_rejects_malformed_policy_payload(tmp_path: Path) -> None:
    files = _semantic_execution_files(tmp_path)
    bad_policies = _write_json(tmp_path / "runtime", "bad_policies.json", {"promotion_policies": ["bad"]})

    result = run_reddog_model_autoresearch_cycle_feedback_chain_bootstrap(
        repo_root=REPO_ROOT,
        plan_receipt_path=files["plan"],
        campaign_execution_receipt_path=files["output"],
        promotion_policies_path=bad_policies,
        promotion_gate_output_path=files["gate_output"],
        cycle_receipt_output_path=files["cycle_output"],
        feedback_ledger_output_path=files["feedback_output"],
        promotion_authority_receipt_id="authority:semantic",
        signed_promotion_receipt_id="signed:semantic",
    )

    assert result.accepted is False
    assert "malformed_model_autoresearch_chain_promotion_policies" in result.rejection_reasons
    assert not files["gate_output"].exists()
    assert not files["cycle_output"].exists()
    assert not files["feedback_output"].exists()


def test_cycle_feedback_chain_rejects_duplicate_output_paths(tmp_path: Path) -> None:
    files = _semantic_execution_files(tmp_path)

    result = run_reddog_model_autoresearch_cycle_feedback_chain_bootstrap(
        repo_root=REPO_ROOT,
        plan_receipt_path=files["plan"],
        campaign_execution_receipt_path=files["output"],
        promotion_policies_path=files["policies"],
        promotion_gate_output_path=files["gate_output"],
        cycle_receipt_output_path=files["gate_output"],
        feedback_ledger_output_path=files["feedback_output"],
        promotion_authority_receipt_id="authority:semantic",
        signed_promotion_receipt_id="signed:semantic",
    )

    assert result.accepted is False
    assert "model_autoresearch_chain_output_paths_must_be_distinct" in result.rejection_reasons
    assert not files["gate_output"].exists()
    assert not files["feedback_output"].exists()


def test_cycle_feedback_chain_module_has_no_provider_network_command_runtime_or_holoindex_imports() -> None:
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
