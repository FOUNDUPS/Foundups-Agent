"""Tests for REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_MAIN_PREFLIGHT_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_promotion_gate_supply import (
    rehydrate_model_autoresearch_campaign_promotion_gate_supply_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_promotion_gate_supply_bootstrap import (
    MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_BOOTSTRAP_APPLIED,
    MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_BOOTSTRAP_NOT_READY,
    run_reddog_model_autoresearch_campaign_promotion_gate_supply_bootstrap,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_autoresearch_campaign_execution import (
    REPO_ROOT,
    _execution_payload,
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
    / "model_autoresearch_campaign_promotion_gate_supply_bootstrap.py"
)


def _write_json(root: Path, name: str, payload: object) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _inputs(tmp_path: Path) -> dict[str, Path]:
    runtime = tmp_path / "runtime"
    execution = _execution_payload(tmp_path)
    return {
        "execution": _write_json(runtime, "campaign_execution.json", execution),
        "policies": _write_json(runtime, "promotion_policies.json", {"promotion_policies": list(_policies(execution))}),
        "output": runtime / "promotion_gates.json",
    }


def test_campaign_promotion_gate_bootstrap_materializes_gate_supply(tmp_path: Path) -> None:
    files = _inputs(tmp_path)

    result = run_reddog_model_autoresearch_campaign_promotion_gate_supply_bootstrap(
        repo_root=REPO_ROOT,
        campaign_execution_receipt_path=files["execution"],
        promotion_policies_path=files["policies"],
        promotion_authority_receipt_id="authority:1",
        signed_promotion_receipt_id="signed:1",
        output_path=files["output"],
    )

    assert result.accepted is True
    assert result.status == MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_BOOTSTRAP_APPLIED
    assert result.supply_receipt_id
    assert len(result.promotion_gate_receipt_ids) == 2
    assert result.no_model_promotion_performed is True
    payload = json.loads(files["output"].read_text(encoding="utf-8"))
    receipt = rehydrate_model_autoresearch_campaign_promotion_gate_supply_receipt(payload)
    assert receipt.receipt_id == result.supply_receipt_id


def test_campaign_promotion_gate_bootstrap_rejects_inside_repo_inputs_and_output(tmp_path: Path) -> None:
    files = _inputs(tmp_path)
    repo_execution = REPO_ROOT / "model_autoresearch_campaign_execution_receipt.json"
    repo_output = REPO_ROOT / "model_autoresearch_campaign_promotion_gates.json"
    repo_execution.write_text("{}", encoding="utf-8")
    try:
        result = run_reddog_model_autoresearch_campaign_promotion_gate_supply_bootstrap(
            repo_root=REPO_ROOT,
            campaign_execution_receipt_path=repo_execution,
            promotion_policies_path=files["policies"],
            output_path=repo_output,
        )
    finally:
        repo_execution.unlink(missing_ok=True)
        repo_output.unlink(missing_ok=True)

    assert result.accepted is False
    assert result.status == MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_BOOTSTRAP_NOT_READY
    assert "model_autoresearch_campaign_execution_receipt_path_inside_repo" in result.rejection_reasons
    assert "model_autoresearch_campaign_promotion_gate_output_path_invalid" in result.rejection_reasons


def test_campaign_promotion_gate_bootstrap_rejects_malformed_policy_payload(tmp_path: Path) -> None:
    files = _inputs(tmp_path)
    bad_policy = _write_json(tmp_path / "runtime", "bad_policies.json", {"promotion_policies": [{}]})

    result = run_reddog_model_autoresearch_campaign_promotion_gate_supply_bootstrap(
        repo_root=REPO_ROOT,
        campaign_execution_receipt_path=files["execution"],
        promotion_policies_path=bad_policy,
        output_path=files["output"],
    )

    assert result.accepted is False
    assert "model_autoresearch_campaign_gate_policies_invalid" in result.rejection_reasons
    assert not files["output"].exists()


def test_campaign_promotion_gate_bootstrap_rejects_policy_candidate_mismatch(tmp_path: Path) -> None:
    files = _inputs(tmp_path)
    payload = json.loads(files["policies"].read_text(encoding="utf-8"))
    payload["promotion_policies"] = payload["promotion_policies"][:1]
    short_policy = _write_json(tmp_path / "runtime", "short_policies.json", payload)

    result = run_reddog_model_autoresearch_campaign_promotion_gate_supply_bootstrap(
        repo_root=REPO_ROOT,
        campaign_execution_receipt_path=files["execution"],
        promotion_policies_path=short_policy,
        output_path=files["output"],
    )

    assert result.accepted is False
    assert "model_autoresearch_campaign_gate_policy_candidate_mismatch" in result.rejection_reasons
    assert not files["output"].exists()


def test_campaign_promotion_gate_bootstrap_module_has_no_provider_network_command_runtime_or_holoindex_imports() -> None:
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
