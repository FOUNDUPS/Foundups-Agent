"""Tests for MODEL_AUTORESEARCH_CYCLE_RECEIPT_PHASE1."""

from __future__ import annotations

import ast
import json
from dataclasses import replace
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_execution import (
    rehydrate_model_autoresearch_campaign_execution_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_promotion_gate_supply import (
    rehydrate_model_autoresearch_campaign_promotion_gate_supply_receipt,
    run_reddog_model_autoresearch_campaign_promotion_gate_supply,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_cycle_receipt import (
    build_model_autoresearch_cycle_receipt,
    rehydrate_model_autoresearch_cycle_receipt,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_autoresearch_campaign_execution import (
    REPO_ROOT,
    _execution_payload,
    _plan,
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
    / "model_autoresearch_cycle_receipt.py"
)


def _cycle_sources(tmp_path: Path):
    plan = _plan()
    execution_payload = _execution_payload(tmp_path)
    execution = rehydrate_model_autoresearch_campaign_execution_receipt(execution_payload)
    gate_output = tmp_path / "runtime" / "promotion_gates.json"
    gate_result = run_reddog_model_autoresearch_campaign_promotion_gate_supply(
        repo_root=REPO_ROOT,
        campaign_execution_receipt=execution_payload,
        promotion_policies=_policies(execution_payload),
        promotion_authority_receipt_id="authority:1",
        signed_promotion_receipt_id="signed:1",
        output_path=gate_output,
    )
    assert gate_result.accepted is True
    gate_supply = rehydrate_model_autoresearch_campaign_promotion_gate_supply_receipt(
        json.loads(gate_output.read_text(encoding="utf-8"))
    )
    return plan, execution, gate_supply


def test_cycle_receipt_binds_plan_execution_and_gate_supply(tmp_path: Path) -> None:
    plan, execution, gate_supply = _cycle_sources(tmp_path)

    receipt = build_model_autoresearch_cycle_receipt(
        plan_receipt=plan,
        campaign_execution_receipt=execution,
        promotion_gate_supply_receipt=gate_supply,
    )

    assert receipt.receipt_id.startswith("model_autoresearch_cycle:")
    assert receipt.source_plan_receipt_id == plan.receipt_id
    assert receipt.campaign_execution_receipt_id == execution.receipt_id
    assert receipt.promotion_gate_supply_receipt_id == gate_supply.receipt_id
    assert receipt.executed_candidate_ids == ("provider/challenger", "provider/new")
    assert rehydrate_model_autoresearch_cycle_receipt(receipt.to_dict()) == receipt


def test_cycle_receipt_rejects_plan_execution_mismatch(tmp_path: Path) -> None:
    plan, execution, gate_supply = _cycle_sources(tmp_path)
    mismatched_execution = replace(execution, source_plan_receipt_id="model_autoresearch_plan:other")

    try:
        build_model_autoresearch_cycle_receipt(
            plan_receipt=plan,
            campaign_execution_receipt=mismatched_execution,
            promotion_gate_supply_receipt=gate_supply,
        )
    except ValueError as exc:
        assert str(exc) == "autoresearch_cycle_plan_execution_mismatch"
    else:
        raise AssertionError("mismatched plan/execution was accepted")


def test_cycle_receipt_rejects_execution_gate_mismatch(tmp_path: Path) -> None:
    plan, execution, gate_supply = _cycle_sources(tmp_path)
    mismatched_gate = replace(gate_supply, source_execution_receipt_id="model_autoresearch_campaign_execution:other")

    try:
        build_model_autoresearch_cycle_receipt(
            plan_receipt=plan,
            campaign_execution_receipt=execution,
            promotion_gate_supply_receipt=mismatched_gate,
        )
    except ValueError as exc:
        assert str(exc) == "autoresearch_cycle_execution_gate_mismatch"
    else:
        raise AssertionError("mismatched execution/gate was accepted")


def test_cycle_receipt_rejects_candidate_coverage_mismatch(tmp_path: Path) -> None:
    plan, execution, gate_supply = _cycle_sources(tmp_path)
    missing_gate = replace(gate_supply, promotion_gate_receipts=gate_supply.promotion_gate_receipts[:1])

    try:
        build_model_autoresearch_cycle_receipt(
            plan_receipt=plan,
            campaign_execution_receipt=execution,
            promotion_gate_supply_receipt=missing_gate,
        )
    except ValueError as exc:
        assert str(exc) == "autoresearch_cycle_candidate_mismatch"
    else:
        raise AssertionError("mismatched candidate coverage was accepted")


def test_cycle_receipt_rehydration_rejects_tamper(tmp_path: Path) -> None:
    plan, execution, gate_supply = _cycle_sources(tmp_path)
    receipt = build_model_autoresearch_cycle_receipt(
        plan_receipt=plan,
        campaign_execution_receipt=execution,
        promotion_gate_supply_receipt=gate_supply,
    ).to_dict()
    receipt["executed_candidate_ids"] = ["provider/new"]

    try:
        rehydrate_model_autoresearch_cycle_receipt(receipt)
    except ValueError as exc:
        assert str(exc) == "autoresearch_cycle_receipt_id_mismatch"
    else:
        raise AssertionError("tampered cycle receipt was accepted")


def test_cycle_receipt_module_has_no_provider_network_command_runtime_or_holoindex_imports() -> None:
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
