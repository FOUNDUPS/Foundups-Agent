"""Tests for REDDOG_MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY_MAIN_PREFLIGHT_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.model_autoresearch_plan_artifact_supply_bootstrap import (
    MODEL_AUTORESEARCH_PLAN_ARTIFACT_BOOTSTRAP_APPLIED,
    MODEL_AUTORESEARCH_PLAN_ARTIFACT_BOOTSTRAP_NOT_READY,
    run_reddog_model_autoresearch_plan_artifact_supply_bootstrap,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_autoresearch_plan_artifact_supply import (
    REPO_ROOT,
    _candidate,
    _cycle_feedback_record,
    _feedback_record,
    _gate,
    _policy,
)


MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "ai_intelligence"
    / "ai_gateway"
    / "src"
    / "model_autoresearch_plan_artifact_supply_bootstrap.py"
)


def _write_json(root: Path, name: str, payload: object) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _write_jsonl(root: Path, name: str, records: tuple[dict, ...]) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    return path


def _inputs(tmp_path: Path) -> dict[str, Path]:
    runtime = tmp_path / "runtime"
    return {
        "gates": _write_json(
            runtime,
            "promotion_gates.json",
            {"promotion_gate_receipts": [_gate("provider/challenger", pass_all=False).to_dict()]},
        ),
        "candidates": _write_json(
            runtime,
            "candidate_pool.json",
            {
                "candidate_pool": [
                    _candidate("provider/challenger").to_dict(),
                    _candidate("provider/new").to_dict(),
                ]
            },
        ),
        "policy": _write_json(runtime, "policy.json", _policy()),
        "feedback": _write_jsonl(runtime, "feedback.jsonl", (_feedback_record("provider/new"),)),
        "output": runtime / "autoresearch_plan.json",
    }


def test_bootstrap_materializes_autoresearch_plan_with_jsonl_feedback(tmp_path: Path) -> None:
    files = _inputs(tmp_path)

    result = run_reddog_model_autoresearch_plan_artifact_supply_bootstrap(
        repo_root=REPO_ROOT,
        promotion_gate_receipts_path=files["gates"],
        candidate_pool_path=files["candidates"],
        policy_path=files["policy"],
        feedback_records_path=files["feedback"],
        output_path=files["output"],
    )

    assert result.accepted is True
    assert result.status == MODEL_AUTORESEARCH_PLAN_ARTIFACT_BOOTSTRAP_APPLIED
    assert result.plan_receipt_id and result.plan_receipt_id.startswith("model_autoresearch_plan:")
    assert result.source_feedback_record_ids == ("model_feedback_runtime",)
    assert result.campaign_item_count == 2
    assert result.no_model_call_performed is True
    assert result.no_benchmark_run_performed is True
    assert result.no_holoindex_reindex_performed is True
    payload = json.loads(files["output"].read_text(encoding="utf-8"))
    assert payload["receipt_id"] == result.plan_receipt_id
    assert any(
        item["reason"] == "verified_runtime_feedback_unbenchmarked_candidate"
        for item in payload["campaign_items"]
    )


def test_bootstrap_materializes_autoresearch_plan_with_cycle_feedback_jsonl(tmp_path: Path) -> None:
    files = _inputs(tmp_path)
    cycle_feedback = _write_jsonl(
        tmp_path / "runtime",
        "cycle_feedback.jsonl",
        (_cycle_feedback_record("provider/new"),),
    )

    result = run_reddog_model_autoresearch_plan_artifact_supply_bootstrap(
        repo_root=REPO_ROOT,
        promotion_gate_receipts_path=files["gates"],
        candidate_pool_path=files["candidates"],
        policy_path=files["policy"],
        feedback_records_path=cycle_feedback,
        output_path=files["output"],
    )

    assert result.accepted is True
    assert result.status == MODEL_AUTORESEARCH_PLAN_ARTIFACT_BOOTSTRAP_APPLIED
    assert result.source_feedback_record_ids == ("model_autoresearch_cycle_feedback_runtime",)
    payload = json.loads(files["output"].read_text(encoding="utf-8"))
    assert payload["source_feedback_record_ids"] == ["model_autoresearch_cycle_feedback_runtime"]
    assert payload["campaign_items"][0]["candidate_id"] == "provider/new"
    assert payload["campaign_items"][0]["priority"] == "P0"
    assert payload["campaign_items"][0]["reason"] == "verified_runtime_feedback_unbenchmarked_candidate"


def test_bootstrap_accepts_missing_optional_feedback_path(tmp_path: Path) -> None:
    files = _inputs(tmp_path)

    result = run_reddog_model_autoresearch_plan_artifact_supply_bootstrap(
        repo_root=REPO_ROOT,
        promotion_gate_receipts_path=files["gates"],
        candidate_pool_path=files["candidates"],
        policy_path=files["policy"],
        feedback_records_path=None,
        output_path=files["output"],
    )

    assert result.accepted is True
    assert result.status == MODEL_AUTORESEARCH_PLAN_ARTIFACT_BOOTSTRAP_APPLIED
    assert result.source_feedback_record_ids == ()
    assert files["output"].exists()


def test_bootstrap_rejects_inside_repo_inputs_and_output(tmp_path: Path) -> None:
    files = _inputs(tmp_path)
    repo_input = REPO_ROOT / "model_autoresearch_promotion_gates.json"
    repo_output = REPO_ROOT / "model_autoresearch_plan.json"
    repo_input.write_text("{}", encoding="utf-8")
    try:
        result = run_reddog_model_autoresearch_plan_artifact_supply_bootstrap(
            repo_root=REPO_ROOT,
            promotion_gate_receipts_path=repo_input,
            candidate_pool_path=files["candidates"],
            policy_path=files["policy"],
            feedback_records_path=files["feedback"],
            output_path=repo_output,
        )
    finally:
        repo_input.unlink(missing_ok=True)
        repo_output.unlink(missing_ok=True)

    assert result.accepted is False
    assert result.status == MODEL_AUTORESEARCH_PLAN_ARTIFACT_BOOTSTRAP_NOT_READY
    assert "model_autoresearch_promotion_gate_receipts_path_inside_repo" in result.rejection_reasons
    assert "model_autoresearch_output_path_invalid" in result.rejection_reasons


def test_bootstrap_rejects_tampered_gate(tmp_path: Path) -> None:
    files = _inputs(tmp_path)
    gate_payload = json.loads(files["gates"].read_text(encoding="utf-8"))
    gate_payload["promotion_gate_receipts"][0]["receipt_id"] = "tampered"
    bad_gate_path = _write_json(tmp_path / "runtime", "bad_gates.json", gate_payload)

    result = run_reddog_model_autoresearch_plan_artifact_supply_bootstrap(
        repo_root=REPO_ROOT,
        promotion_gate_receipts_path=bad_gate_path,
        candidate_pool_path=files["candidates"],
        policy_path=files["policy"],
        feedback_records_path=files["feedback"],
        output_path=files["output"],
    )

    assert result.accepted is False
    assert "model_autoresearch_promotion_gates_invalid" in result.rejection_reasons
    assert not files["output"].exists()


def test_bootstrap_rejects_malformed_feedback_before_planning(tmp_path: Path) -> None:
    files = _inputs(tmp_path)
    bad_feedback_path = tmp_path / "runtime" / "bad_feedback.jsonl"
    bad_feedback_path.write_text('{"ok": true}\nnot-json\n', encoding="utf-8")

    result = run_reddog_model_autoresearch_plan_artifact_supply_bootstrap(
        repo_root=REPO_ROOT,
        promotion_gate_receipts_path=files["gates"],
        candidate_pool_path=files["candidates"],
        policy_path=files["policy"],
        feedback_records_path=bad_feedback_path,
        output_path=files["output"],
    )

    assert result.accepted is False
    assert result.rejection_reasons == ("malformed_model_autoresearch_feedback_records",)
    assert not files["output"].exists()


def test_bootstrap_module_has_no_execution_network_runtime_or_holoindex_imports() -> None:
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
