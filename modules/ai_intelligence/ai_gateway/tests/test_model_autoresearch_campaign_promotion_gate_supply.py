"""Tests for MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_execution import (
    rehydrate_model_autoresearch_campaign_execution_receipt,
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


MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "ai_intelligence"
    / "ai_gateway"
    / "src"
    / "model_autoresearch_campaign_promotion_gate_supply.py"
)


def _policies(execution_payload: dict, *, min_pass_rate: float = 0.9) -> tuple[dict, ...]:
    execution = rehydrate_model_autoresearch_campaign_execution_receipt(execution_payload)
    benchmark = execution.benchmark_run_receipt
    return tuple(
        ModelPromotionPolicy(
            task_family=benchmark.task_family,
            candidate_id=candidate_id,
            min_verifier_pass_rate=min_pass_rate,
            min_sample_count=2,
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
