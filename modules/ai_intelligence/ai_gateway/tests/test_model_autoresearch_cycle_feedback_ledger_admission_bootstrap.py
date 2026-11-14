"""Tests for REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_MAIN_PREFLIGHT_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.model_autoresearch_cycle_feedback_ledger_admission_bootstrap import (
    MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_BOOTSTRAP_APPLIED,
    MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_BOOTSTRAP_NOT_READY,
    run_reddog_model_autoresearch_cycle_feedback_ledger_admission_bootstrap,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_cycle_receipt import (
    build_model_autoresearch_cycle_receipt,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_autoresearch_campaign_execution import REPO_ROOT
from modules.ai_intelligence.ai_gateway.tests.test_model_autoresearch_cycle_receipt import (
    _cycle_sources,
)


MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "ai_intelligence"
    / "ai_gateway"
    / "src"
    / "model_autoresearch_cycle_feedback_ledger_admission_bootstrap.py"
)


def _write_json(root: Path, name: str, payload: object) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _cycle_payload(tmp_path: Path) -> tuple[dict, dict]:
    plan, execution, gate_supply = _cycle_sources(tmp_path)
    cycle = build_model_autoresearch_cycle_receipt(
        plan_receipt=plan,
        campaign_execution_receipt=execution,
        promotion_gate_supply_receipt=gate_supply,
    )
    return cycle.to_dict(), plan.to_dict()


def test_cycle_feedback_bootstrap_appends_cycle_feedback_record(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    cycle_payload, plan_payload = _cycle_payload(tmp_path)
    plan_path = _write_json(runtime, "plan_receipt.json", plan_payload)
    cycle_path = _write_json(runtime, "cycle_receipt.json", cycle_payload)
    output_path = runtime / "cycle_feedback.jsonl"

    result = run_reddog_model_autoresearch_cycle_feedback_ledger_admission_bootstrap(
        repo_root=REPO_ROOT,
        plan_receipt_path=plan_path,
        cycle_receipt_path=cycle_path,
        output_path=output_path,
    )

    assert result.accepted is True
    assert result.status == MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_BOOTSTRAP_APPLIED
    assert result.admission_id
    assert result.cycle_receipt_id == cycle_payload["receipt_id"]
    assert result.feedback_record_id
    assert result.no_model_promotion_performed is True
    assert result.no_holoindex_reindex_performed is True
    records = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["cycle_receipt_id"] == cycle_payload["receipt_id"]
    assert records[0]["source_plan_context_bound"] is True
    assert records[0]["task_family"] == plan_payload["policy"]["task_family"]


def test_cycle_feedback_bootstrap_rejects_inside_repo_inputs_and_output(tmp_path: Path) -> None:
    repo_cycle = REPO_ROOT / "model_autoresearch_cycle_receipt.json"
    repo_output = REPO_ROOT / "model_autoresearch_cycle_feedback.jsonl"
    repo_cycle.write_text("{}", encoding="utf-8")
    try:
        result = run_reddog_model_autoresearch_cycle_feedback_ledger_admission_bootstrap(
            repo_root=REPO_ROOT,
            plan_receipt_path=repo_cycle,
            cycle_receipt_path=repo_cycle,
            output_path=repo_output,
        )
    finally:
        repo_cycle.unlink(missing_ok=True)
        repo_output.unlink(missing_ok=True)

    assert result.accepted is False
    assert result.status == MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_BOOTSTRAP_NOT_READY
    assert "model_autoresearch_cycle_feedback_plan_receipt_path_inside_repo" in result.rejection_reasons
    assert "model_autoresearch_cycle_receipt_path_inside_repo" in result.rejection_reasons
    assert "model_autoresearch_cycle_feedback_ledger_output_path_invalid" in result.rejection_reasons


def test_cycle_feedback_bootstrap_rejects_tampered_cycle_receipt(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    cycle_payload, plan_payload = _cycle_payload(tmp_path)
    plan_path = _write_json(runtime, "plan_receipt.json", plan_payload)
    cycle_payload["executed_candidate_ids"] = ["provider/tampered"]
    cycle_path = _write_json(runtime, "tampered_cycle_receipt.json", cycle_payload)
    output_path = runtime / "cycle_feedback.jsonl"

    result = run_reddog_model_autoresearch_cycle_feedback_ledger_admission_bootstrap(
        repo_root=REPO_ROOT,
        plan_receipt_path=plan_path,
        cycle_receipt_path=cycle_path,
        output_path=output_path,
    )

    assert result.accepted is False
    assert "REJECT_AUTORESEARCH_CYCLE_RECEIPT_INVALID" in result.rejection_reasons
    assert not output_path.exists()


def test_cycle_feedback_bootstrap_rejects_missing_output_path(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    cycle_payload, plan_payload = _cycle_payload(tmp_path)
    plan_path = _write_json(runtime, "plan_receipt.json", plan_payload)
    cycle_path = _write_json(runtime, "cycle_receipt.json", cycle_payload)

    result = run_reddog_model_autoresearch_cycle_feedback_ledger_admission_bootstrap(
        repo_root=REPO_ROOT,
        plan_receipt_path=plan_path,
        cycle_receipt_path=cycle_path,
        output_path=None,
    )

    assert result.accepted is False
    assert "model_autoresearch_cycle_feedback_ledger_output_path_invalid" in result.rejection_reasons


def test_cycle_feedback_bootstrap_rejects_tampered_plan_receipt(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    cycle_payload, plan_payload = _cycle_payload(tmp_path)
    plan_payload["policy"]["task_family"] = "security"
    plan_path = _write_json(runtime, "tampered_plan_receipt.json", plan_payload)
    cycle_path = _write_json(runtime, "cycle_receipt.json", cycle_payload)
    output_path = runtime / "cycle_feedback.jsonl"

    result = run_reddog_model_autoresearch_cycle_feedback_ledger_admission_bootstrap(
        repo_root=REPO_ROOT,
        plan_receipt_path=plan_path,
        cycle_receipt_path=cycle_path,
        output_path=output_path,
    )

    assert result.accepted is False
    assert "REJECT_AUTORESEARCH_CYCLE_SOURCE_PLAN_RECEIPT_INVALID" in result.rejection_reasons
    assert not output_path.exists()


def test_cycle_feedback_bootstrap_module_has_no_provider_network_command_runtime_or_holoindex_imports() -> None:
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
