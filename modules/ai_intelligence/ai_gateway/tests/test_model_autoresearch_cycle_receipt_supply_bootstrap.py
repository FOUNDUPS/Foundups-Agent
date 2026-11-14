"""Tests for REDDOG_MODEL_AUTORESEARCH_CYCLE_RECEIPT_SUPPLY_MAIN_PREFLIGHT_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_promotion_gate_supply import (
    run_reddog_model_autoresearch_campaign_promotion_gate_supply,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_cycle_receipt import (
    rehydrate_model_autoresearch_cycle_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_cycle_receipt_supply_bootstrap import (
    MODEL_AUTORESEARCH_CYCLE_RECEIPT_BOOTSTRAP_APPLIED,
    MODEL_AUTORESEARCH_CYCLE_RECEIPT_BOOTSTRAP_NOT_READY,
    run_reddog_model_autoresearch_cycle_receipt_supply_bootstrap,
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
    / "model_autoresearch_cycle_receipt_supply_bootstrap.py"
)


def _write_json(root: Path, name: str, payload: object) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _inputs(tmp_path: Path) -> dict[str, Path]:
    runtime = tmp_path / "runtime"
    plan = _plan()
    execution = _execution_payload(tmp_path)
    plan_path = _write_json(runtime, "plan.json", plan.to_dict())
    execution_path = _write_json(runtime, "campaign_execution.json", execution)
    gate_output = runtime / "promotion_gates.json"
    gate_result = run_reddog_model_autoresearch_campaign_promotion_gate_supply(
        repo_root=REPO_ROOT,
        campaign_execution_receipt=execution,
        promotion_policies=_policies(execution),
        promotion_authority_receipt_id="authority:1",
        signed_promotion_receipt_id="signed:1",
        output_path=gate_output,
    )
    assert gate_result.accepted is True
    return {
        "plan": plan_path,
        "execution": execution_path,
        "gate": gate_output,
        "output": runtime / "cycle_receipt.json",
    }


def test_cycle_receipt_bootstrap_materializes_rehydratable_cycle_receipt(tmp_path: Path) -> None:
    files = _inputs(tmp_path)

    result = run_reddog_model_autoresearch_cycle_receipt_supply_bootstrap(
        repo_root=REPO_ROOT,
        plan_receipt_path=files["plan"],
        campaign_execution_receipt_path=files["execution"],
        promotion_gate_supply_receipt_path=files["gate"],
        output_path=files["output"],
    )

    assert result.accepted is True
    assert result.status == MODEL_AUTORESEARCH_CYCLE_RECEIPT_BOOTSTRAP_APPLIED
    assert result.cycle_receipt_id
    assert (result.source_plan_receipt_id or "").startswith("model_autoresearch_plan:")
    assert result.campaign_execution_receipt_id
    assert result.promotion_gate_supply_receipt_id
    assert result.no_model_promotion_performed is True
    assert result.no_runtime_binding_performed is True
    assert result.no_repo_mutation_performed is True

    payload = json.loads(files["output"].read_text(encoding="utf-8"))
    receipt = rehydrate_model_autoresearch_cycle_receipt(payload)
    assert receipt.receipt_id == result.cycle_receipt_id


def test_cycle_receipt_bootstrap_rejects_inside_repo_inputs_and_output(tmp_path: Path) -> None:
    files = _inputs(tmp_path)
    repo_plan = REPO_ROOT / "model_autoresearch_plan_receipt.json"
    repo_output = REPO_ROOT / "model_autoresearch_cycle_receipt.json"
    repo_plan.write_text("{}", encoding="utf-8")
    try:
        result = run_reddog_model_autoresearch_cycle_receipt_supply_bootstrap(
            repo_root=REPO_ROOT,
            plan_receipt_path=repo_plan,
            campaign_execution_receipt_path=files["execution"],
            promotion_gate_supply_receipt_path=files["gate"],
            output_path=repo_output,
        )
    finally:
        repo_plan.unlink(missing_ok=True)
        repo_output.unlink(missing_ok=True)

    assert result.accepted is False
    assert result.status == MODEL_AUTORESEARCH_CYCLE_RECEIPT_BOOTSTRAP_NOT_READY
    assert "model_autoresearch_cycle_plan_receipt_path_inside_repo" in result.rejection_reasons
    assert "model_autoresearch_cycle_receipt_output_path_invalid" in result.rejection_reasons


def test_cycle_receipt_bootstrap_rejects_tampered_gate_supply(tmp_path: Path) -> None:
    files = _inputs(tmp_path)
    gate_payload = json.loads(files["gate"].read_text(encoding="utf-8"))
    gate_payload["source_execution_receipt_id"] = "model_autoresearch_campaign_execution:other"
    tampered_gate = _write_json(tmp_path / "runtime", "tampered_gate.json", gate_payload)

    result = run_reddog_model_autoresearch_cycle_receipt_supply_bootstrap(
        repo_root=REPO_ROOT,
        plan_receipt_path=files["plan"],
        campaign_execution_receipt_path=files["execution"],
        promotion_gate_supply_receipt_path=tampered_gate,
        output_path=files["output"],
    )

    assert result.accepted is False
    assert "model_autoresearch_cycle_receipt_invalid" in result.rejection_reasons
    assert not files["output"].exists()


def test_cycle_receipt_bootstrap_rejects_malformed_execution_payload(tmp_path: Path) -> None:
    files = _inputs(tmp_path)
    bad_execution = _write_json(tmp_path / "runtime", "bad_execution.json", {})

    result = run_reddog_model_autoresearch_cycle_receipt_supply_bootstrap(
        repo_root=REPO_ROOT,
        plan_receipt_path=files["plan"],
        campaign_execution_receipt_path=bad_execution,
        promotion_gate_supply_receipt_path=files["gate"],
        output_path=files["output"],
    )

    assert result.accepted is False
    assert "model_autoresearch_cycle_receipt_invalid" in result.rejection_reasons
    assert not files["output"].exists()


def test_cycle_receipt_bootstrap_module_has_no_provider_network_command_runtime_or_holoindex_imports() -> None:
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
