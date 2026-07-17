"""Tests for REDDOG_MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY_MAIN_PREFLIGHT_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_artifact_supply_bootstrap import (
    MODEL_RUNTIME_BINDING_ARTIFACT_BOOTSTRAP_APPLIED,
    MODEL_RUNTIME_BINDING_ARTIFACT_BOOTSTRAP_NOT_READY,
    run_reddog_model_runtime_binding_artifact_supply_bootstrap,
)
from modules.ai_intelligence.ai_gateway.tests.model_signed_evidence_test_helpers import (
    BENCHMARK_FINGERPRINT,
    BENCHMARK_PUBLIC_KEY,
    KEY_EPOCH,
    PROMOTION_FINGERPRINT,
    PROMOTION_PUBLIC_KEY,
    DeterministicSignatureVerifier,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_runtime_binding_artifact_supply import (
    REPO_ROOT,
    _policy,
    _selection_chain,
    _serialized_evidence_bundle,
)


MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "ai_intelligence"
    / "ai_gateway"
    / "src"
    / "model_runtime_binding_artifact_supply_bootstrap.py"
)
NOW = 1_800_000_000


def _write_json(root: Path, name: str, payload: object) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _keys() -> dict[str, object]:
    return {
        "trusted_public_keys": [
            {
                "signer_role": "benchmark_verifier",
                "signer_key_fingerprint": BENCHMARK_FINGERPRINT,
                "key_epoch": KEY_EPOCH,
                "public_key": BENCHMARK_PUBLIC_KEY,
            },
            {
                "signer_role": "promotion_authority",
                "signer_key_fingerprint": PROMOTION_FINGERPRINT,
                "key_epoch": KEY_EPOCH,
                "public_key": PROMOTION_PUBLIC_KEY,
            },
        ]
    }


def _inputs(tmp_path: Path) -> dict[str, Path]:
    runtime = tmp_path / "runtime"
    snapshot, selection, benchmark, promotion, _verified = _selection_chain()
    return {
        "catalog": _write_json(runtime, "catalog.json", snapshot.to_dict()),
        "selection": _write_json(runtime, "selection.json", selection.to_dict()),
        "benchmarks": _write_json(
            runtime,
            "benchmarks.json",
            {"benchmark_evidence_receipts": [benchmark.to_dict()]},
        ),
        "promotions": _write_json(
            runtime,
            "promotions.json",
            {"promotion_evidence_receipts": [promotion.to_dict()]},
        ),
        "evidence": _write_json(
            runtime,
            "evidence.json",
            _serialized_evidence_bundle(snapshot, selection, benchmark, promotion),
        ),
        "policy": _write_json(runtime, "policy.json", _policy()),
        "keys": _write_json(runtime, "keys.json", _keys()),
        "output": runtime / "model_runtime_binding_receipt.json",
    }


def test_bootstrap_materializes_runtime_binding_receipt(tmp_path: Path) -> None:
    files = _inputs(tmp_path)

    result = run_reddog_model_runtime_binding_artifact_supply_bootstrap(
        repo_root=REPO_ROOT,
        catalog_snapshot_path=files["catalog"],
        model_selection_receipt_path=files["selection"],
        benchmark_evidence_receipts_path=files["benchmarks"],
        promotion_evidence_receipts_path=files["promotions"],
        evidence_bundle_path=files["evidence"],
        runtime_policy_path=files["policy"],
        trusted_keys_path=files["keys"],
        output_path=files["output"],
        signature_verifier=DeterministicSignatureVerifier(),
        now_epoch=NOW,
    )

    assert result.accepted is True
    assert result.status == MODEL_RUNTIME_BINDING_ARTIFACT_BOOTSTRAP_APPLIED
    assert result.runtime_binding_receipt_id and result.runtime_binding_receipt_id.startswith(
        "reddog_model_runtime_binding:"
    )
    receipt = json.loads(files["output"].read_text(encoding="utf-8"))
    assert receipt["decision"] == "bound"
    assert receipt["runtime_surface"] == "reddog_backend_architect"
    assert result.no_model_call_performed is True
    assert result.no_holoindex_reindex_performed is True


def test_bootstrap_rejects_missing_trusted_keys(tmp_path: Path) -> None:
    files = _inputs(tmp_path)

    result = run_reddog_model_runtime_binding_artifact_supply_bootstrap(
        repo_root=REPO_ROOT,
        catalog_snapshot_path=files["catalog"],
        model_selection_receipt_path=files["selection"],
        benchmark_evidence_receipts_path=files["benchmarks"],
        promotion_evidence_receipts_path=files["promotions"],
        evidence_bundle_path=files["evidence"],
        runtime_policy_path=files["policy"],
        trusted_keys_path=None,
        output_path=files["output"],
        signature_verifier=DeterministicSignatureVerifier(),
        now_epoch=NOW,
    )

    assert result.accepted is False
    assert result.status == MODEL_RUNTIME_BINDING_ARTIFACT_BOOTSTRAP_NOT_READY
    assert "missing_model_evidence_trusted_keys_path" in result.rejection_reasons
    assert not files["output"].exists()


def test_bootstrap_rejects_output_inside_repo(tmp_path: Path) -> None:
    files = _inputs(tmp_path)

    result = run_reddog_model_runtime_binding_artifact_supply_bootstrap(
        repo_root=REPO_ROOT,
        catalog_snapshot_path=files["catalog"],
        model_selection_receipt_path=files["selection"],
        benchmark_evidence_receipts_path=files["benchmarks"],
        promotion_evidence_receipts_path=files["promotions"],
        evidence_bundle_path=files["evidence"],
        runtime_policy_path=files["policy"],
        trusted_keys_path=files["keys"],
        output_path=REPO_ROOT / "model_runtime_binding_receipt.json",
        signature_verifier=DeterministicSignatureVerifier(),
        now_epoch=NOW,
    )

    assert result.accepted is False
    assert "model_runtime_binding_output_path_invalid" in result.rejection_reasons
    assert not (REPO_ROOT / "model_runtime_binding_receipt.json").exists()


def test_bootstrap_module_has_no_execution_network_or_reindex_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "subprocess",
        "requests",
        "urllib",
        "http",
        "socket",
        "git",
        "holo_index",
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
