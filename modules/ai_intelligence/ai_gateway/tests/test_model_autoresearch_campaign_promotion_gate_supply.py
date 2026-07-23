"""Tests for MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_execution import (
    rehydrate_model_autoresearch_campaign_execution_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_execution_artifact_supply_bootstrap import (
    MODEL_AUTORESEARCH_CAMPAIGN_CONFIGURED_GATEWAY_RUNNER,
    MODEL_AUTORESEARCH_CAMPAIGN_OUTPUT_EVIDENCE_SEMANTIC_VERIFIER,
    run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_promotion_gate_supply import (
    MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_ACCEPT,
    MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_REJECT,
    rehydrate_model_autoresearch_campaign_promotion_gate_supply_receipt,
    run_reddog_model_autoresearch_campaign_promotion_gate_supply,
)
from modules.ai_intelligence.ai_gateway.src.model_promotion_gate import (
    ModelPromotionGateDecision,
    ModelPromotionPolicy,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_autoresearch_campaign_execution import (
    REPO_ROOT,
    _execution_payload,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_autoresearch_campaign_execution_artifact_supply_bootstrap import (
    _configured_semantic_inputs,
)


MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "ai_intelligence"
    / "ai_gateway"
    / "src"
    / "model_autoresearch_campaign_promotion_gate_supply.py"
)


def _policies(
    execution_payload: dict,
    *,
    min_pass_rate: float = 0.9,
    min_sample_count: int = 2,
) -> tuple[dict, ...]:
    execution = rehydrate_model_autoresearch_campaign_execution_receipt(execution_payload)
    benchmark = execution.benchmark_run_receipt
    return tuple(
        ModelPromotionPolicy(
            task_family=benchmark.task_family,
            candidate_id=candidate_id,
            min_verifier_pass_rate=min_pass_rate,
            min_sample_count=min_sample_count,
            required_task_set_digest=benchmark.task_set_digest,
            required_held_out_split_digest=benchmark.held_out_split_digest,
            required_verifier_digest=benchmark.verifier_digest,
        ).to_dict()
        for candidate_id in execution.executed_candidate_ids
    )


def test_campaign_promotion_gate_supply_emits_rehydratable_gate_receipts(tmp_path: Path) -> None:
    execution = _execution_payload(tmp_path)
    output = tmp_path / "runtime" / "promotion_gates.json"

    result = run_reddog_model_autoresearch_campaign_promotion_gate_supply(
        repo_root=REPO_ROOT,
        campaign_execution_receipt=execution,
        promotion_policies=_policies(execution),
        promotion_authority_receipt_id="authority:1",
        signed_promotion_receipt_id="signed:1",
        output_path=output,
    )

    assert result.accepted is True
    assert result.status == MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_ACCEPT
    assert result.supply_receipt_id
    assert len(result.promotion_gate_receipt_ids) == 2
    payload = json.loads(output.read_text(encoding="utf-8"))
    receipt = rehydrate_model_autoresearch_campaign_promotion_gate_supply_receipt(payload)
    assert receipt.receipt_id == result.supply_receipt_id
    assert [gate.decision for gate in receipt.promotion_gate_receipts] == [
        ModelPromotionGateDecision.PROMOTE_CHAMPION,
        ModelPromotionGateDecision.PROMOTE_CHAMPION,
    ]
    assert all(gate.promotion_evidence_receipt is not None for gate in receipt.promotion_gate_receipts)


def _semantic_execution_payload(tmp_path: Path, *, contains: str = "configured;gateway;answer") -> dict:
    files, gateway = _configured_semantic_inputs(tmp_path)
    tasks_payload = json.loads(files["tasks"].read_text(encoding="utf-8"))
    tasks_payload["tasks"][0]["metadata"] = {"expected_answer_contains": contains}
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
    return json.loads(files["output"].read_text(encoding="utf-8"))


def test_semantic_verified_configured_gateway_campaign_can_promote(tmp_path: Path) -> None:
    execution = _semantic_execution_payload(tmp_path)
    output = tmp_path / "runtime" / "semantic_promotion_gates.json"

    result = run_reddog_model_autoresearch_campaign_promotion_gate_supply(
        repo_root=REPO_ROOT,
        campaign_execution_receipt=execution,
        promotion_policies=_policies(execution, min_pass_rate=1.0, min_sample_count=1),
        promotion_authority_receipt_id="authority:semantic",
        signed_promotion_receipt_id="signed:semantic",
        output_path=output,
    )

    assert result.accepted is True
    receipt = rehydrate_model_autoresearch_campaign_promotion_gate_supply_receipt(
        json.loads(output.read_text(encoding="utf-8"))
    )
    assert len(receipt.promotion_gate_receipts) == 1
    gate = receipt.promotion_gate_receipts[0]
    assert gate.decision == ModelPromotionGateDecision.PROMOTE_CHAMPION
    assert gate.promotion_evidence_receipt is not None
    assert gate.promotion_evidence_receipt.signed_promotion_receipt_id == "signed:semantic"


def test_semantic_rejected_configured_gateway_campaign_cannot_promote(tmp_path: Path) -> None:
    execution = _semantic_execution_payload(tmp_path, contains="missing-term")
    output = tmp_path / "runtime" / "semantic_rejected_promotion_gates.json"

    result = run_reddog_model_autoresearch_campaign_promotion_gate_supply(
        repo_root=REPO_ROOT,
        campaign_execution_receipt=execution,
        promotion_policies=_policies(execution, min_pass_rate=1.0, min_sample_count=1),
        promotion_authority_receipt_id="authority:semantic",
        signed_promotion_receipt_id="signed:semantic",
        output_path=output,
    )

    assert result.accepted is True
    receipt = rehydrate_model_autoresearch_campaign_promotion_gate_supply_receipt(
        json.loads(output.read_text(encoding="utf-8"))
    )
    gate = receipt.promotion_gate_receipts[0]
    assert gate.decision == ModelPromotionGateDecision.KEEP_CHALLENGER
    assert gate.promotion_evidence_receipt is None
    assert "verifier_pass_rate_below_champion_threshold" in gate.rejection_reasons


def test_campaign_promotion_gate_supply_without_signed_authority_does_not_promote(tmp_path: Path) -> None:
    execution = _execution_payload(tmp_path)
    output = tmp_path / "runtime" / "promotion_gates_no_auth.json"

    result = run_reddog_model_autoresearch_campaign_promotion_gate_supply(
        repo_root=REPO_ROOT,
        campaign_execution_receipt=execution,
        promotion_policies=_policies(execution),
        output_path=output,
    )

    assert result.accepted is True
    payload = json.loads(output.read_text(encoding="utf-8"))
    receipt = rehydrate_model_autoresearch_campaign_promotion_gate_supply_receipt(payload)
    assert all(gate.decision == ModelPromotionGateDecision.REJECT for gate in receipt.promotion_gate_receipts)
    assert all("missing_promotion_authority_receipt" in gate.rejection_reasons for gate in receipt.promotion_gate_receipts)
    assert all(gate.promotion_evidence_receipt is None for gate in receipt.promotion_gate_receipts)


def test_campaign_promotion_gate_supply_rejects_policy_candidate_mismatch(tmp_path: Path) -> None:
    execution = _execution_payload(tmp_path)
    output = tmp_path / "runtime" / "promotion_gates.json"

    result = run_reddog_model_autoresearch_campaign_promotion_gate_supply(
        repo_root=REPO_ROOT,
        campaign_execution_receipt=execution,
        promotion_policies=_policies(execution)[:1],
        output_path=output,
    )

    assert result.accepted is False
    assert result.status == MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_REJECT
    assert "model_autoresearch_campaign_gate_policy_candidate_mismatch" in result.rejection_reasons
    assert not output.exists()


def test_campaign_promotion_gate_supply_rejects_tampered_execution_receipt(tmp_path: Path) -> None:
    execution = _execution_payload(tmp_path)
    execution["receipt_id"] = "model_autoresearch_campaign_execution:tampered"

    result = run_reddog_model_autoresearch_campaign_promotion_gate_supply(
        repo_root=REPO_ROOT,
        campaign_execution_receipt=execution,
        promotion_policies=(),
        output_path=tmp_path / "runtime" / "promotion_gates.json",
    )

    assert result.accepted is False
    assert "model_autoresearch_campaign_gate_execution_receipt_invalid" in result.rejection_reasons


def test_campaign_promotion_gate_supply_rejects_output_inside_repo(tmp_path: Path) -> None:
    execution = _execution_payload(tmp_path)
    output = REPO_ROOT / "model_autoresearch_campaign_promotion_gates.json"

    result = run_reddog_model_autoresearch_campaign_promotion_gate_supply(
        repo_root=REPO_ROOT,
        campaign_execution_receipt=execution,
        promotion_policies=_policies(execution),
        output_path=output,
    )

    assert result.accepted is False
    assert "model_autoresearch_campaign_gate_output_path_invalid" in result.rejection_reasons
    assert not output.exists()


def test_campaign_promotion_gate_supply_rehydration_rejects_tampered_gate_list(tmp_path: Path) -> None:
    execution = _execution_payload(tmp_path)
    output = tmp_path / "runtime" / "promotion_gates.json"
    result = run_reddog_model_autoresearch_campaign_promotion_gate_supply(
        repo_root=REPO_ROOT,
        campaign_execution_receipt=execution,
        promotion_policies=_policies(execution),
        promotion_authority_receipt_id="authority:1",
        signed_promotion_receipt_id="signed:1",
        output_path=output,
    )
    assert result.accepted is True
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["promotion_gate_receipt_ids"] = list(reversed(payload["promotion_gate_receipt_ids"]))

    try:
        rehydrate_model_autoresearch_campaign_promotion_gate_supply_receipt(payload)
    except ValueError as exc:
        assert str(exc) == "promotion_gate_supply_receipt_ids_mismatch"
    else:
        raise AssertionError("tampered promotion gate supply receipt was accepted")


def test_campaign_promotion_gate_supply_module_has_no_provider_network_command_runtime_or_holoindex_imports() -> None:
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
