"""Tests for REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_ARTIFACT_SUPPLY_MAIN_PREFLIGHT_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_execution import (
    rehydrate_model_autoresearch_campaign_execution_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_execution_artifact_supply_bootstrap import (
    MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_BOOTSTRAP_APPLIED,
    MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_BOOTSTRAP_NOT_READY,
    run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_autoresearch_campaign_execution import (
    REPO_ROOT,
    _plan,
    _tasks,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_champion_challenger_autoresearch import (
    _candidate,
)


MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "ai_intelligence"
    / "ai_gateway"
    / "src"
    / "model_autoresearch_campaign_execution_artifact_supply_bootstrap.py"
)


def _write_json(root: Path, name: str, payload: object) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _inputs(tmp_path: Path) -> dict[str, Path]:
    runtime = tmp_path / "runtime"
    return {
        "plan": _write_json(runtime, "autoresearch_plan.json", _plan().to_dict()),
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
        "tasks": _write_json(runtime, "tasks.json", {"tasks": [task.to_dict() for task in _tasks()]}),
        "output": runtime / "campaign_execution.json",
    }


def test_campaign_execution_bootstrap_materializes_rehydratable_receipt(tmp_path: Path) -> None:
    files = _inputs(tmp_path)

    result = run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap(
        repo_root=REPO_ROOT,
        plan_receipt_path=files["plan"],
        candidate_pool_path=files["candidates"],
        tasks_path=files["tasks"],
        output_path=files["output"],
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
    )

    assert result.accepted is True
    assert result.status == MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_BOOTSTRAP_APPLIED
    assert result.execution_receipt_id
    assert result.execution_receipt_id.startswith("model_autoresearch_campaign_execution:")
    assert result.executed_candidate_ids == ("provider/new", "provider/challenger")
    assert result.task_count == 2
    assert result.no_direct_provider_call_performed is True
    assert result.no_holoindex_reindex_performed is True
    payload = json.loads(files["output"].read_text(encoding="utf-8"))
    receipt = rehydrate_model_autoresearch_campaign_execution_receipt(payload)
    assert receipt.receipt_id == result.execution_receipt_id


def test_campaign_execution_bootstrap_rejects_inside_repo_inputs_and_output(tmp_path: Path) -> None:
    files = _inputs(tmp_path)
    repo_plan = REPO_ROOT / "model_autoresearch_plan_receipt.json"
    repo_output = REPO_ROOT / "model_autoresearch_campaign_execution.json"
    repo_plan.write_text("{}", encoding="utf-8")
    try:
        result = run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap(
            repo_root=REPO_ROOT,
            plan_receipt_path=repo_plan,
            candidate_pool_path=files["candidates"],
            tasks_path=files["tasks"],
            output_path=repo_output,
            verifier_digest="sha256:verifier",
            held_out_split_id="heldout-v1",
        )
    finally:
        repo_plan.unlink(missing_ok=True)
        repo_output.unlink(missing_ok=True)

    assert result.accepted is False
    assert result.status == MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_BOOTSTRAP_NOT_READY
    assert "model_autoresearch_plan_receipt_path_inside_repo" in result.rejection_reasons
    assert "model_autoresearch_campaign_execution_output_path_invalid" in result.rejection_reasons


def test_campaign_execution_bootstrap_rejects_malformed_tasks_before_execution(tmp_path: Path) -> None:
    files = _inputs(tmp_path)
    bad_tasks = _write_json(tmp_path / "runtime", "bad_tasks.json", {"tasks": [{"task_id": "missing"}]})

    result = run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap(
        repo_root=REPO_ROOT,
        plan_receipt_path=files["plan"],
        candidate_pool_path=files["candidates"],
        tasks_path=bad_tasks,
        output_path=files["output"],
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
    )

    assert result.accepted is False
    assert "model_autoresearch_execution_tasks_invalid" in result.rejection_reasons
    assert not files["output"].exists()


def test_campaign_execution_bootstrap_rejects_verifier_mismatch(tmp_path: Path) -> None:
    files = _inputs(tmp_path)

    result = run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap(
        repo_root=REPO_ROOT,
        plan_receipt_path=files["plan"],
        candidate_pool_path=files["candidates"],
        tasks_path=files["tasks"],
        output_path=files["output"],
        verifier_digest="sha256:wrong",
        held_out_split_id="heldout-v1",
    )

    assert result.accepted is False
    assert "model_autoresearch_execution_verifier_digest_mismatch" in result.rejection_reasons
    assert not files["output"].exists()


def test_campaign_execution_bootstrap_rejects_non_fixture_modes(tmp_path: Path) -> None:
    files = _inputs(tmp_path)

    result = run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap(
        repo_root=REPO_ROOT,
        plan_receipt_path=files["plan"],
        candidate_pool_path=files["candidates"],
        tasks_path=files["tasks"],
        output_path=files["output"],
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
        runner_mode="provider",
        verifier_mode="remote",
    )

    assert result.accepted is False
    assert "unsupported_model_autoresearch_campaign_runner_mode" in result.rejection_reasons
    assert "unsupported_model_autoresearch_campaign_verifier_mode" in result.rejection_reasons
    assert not files["output"].exists()


def test_campaign_execution_bootstrap_module_has_no_provider_network_command_runtime_or_holoindex_imports() -> None:
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
