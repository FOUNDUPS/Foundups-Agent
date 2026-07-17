"""Tests for REDDOG_MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.model_intelligence_selection import (
    ModelTaskRequirements,
    SelectionPurpose,
    select_models_for_task,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_artifact_supply import (
    MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY_ACCEPT,
    MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY_REJECT,
    ModelRuntimeBindingArtifactSupplyReason,
    run_reddog_model_runtime_binding_artifact_supply,
)
from modules.ai_intelligence.ai_gateway.src.model_selection_artifact_supply import (
    EVIDENCE_BUNDLE_SCHEMA_VERSION,
)
from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import (
    ModelEvidenceSignerRole,
    StaticModelEvidenceKeyResolver,
)
from modules.ai_intelligence.ai_gateway.tests.model_signed_evidence_test_helpers import (
    BENCHMARK_FINGERPRINT,
    BENCHMARK_PUBLIC_KEY,
    PROMOTION_FINGERPRINT,
    PROMOTION_PUBLIC_KEY,
    DeterministicSignatureVerifier,
    make_signed_evidence_receipt,
    make_verified_production_evidence,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_selection_artifact_supply import (
    MODEL_ID,
    NOW,
    REPO_ROOT,
    TASK,
    _benchmark,
    _promotion,
    _snapshot,
)


MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "ai_intelligence"
    / "ai_gateway"
    / "src"
    / "model_runtime_binding_artifact_supply.py"
)


def _selection_chain():
    snapshot = _snapshot()
    benchmark = _benchmark()
    promotion = _promotion(benchmark)
    provisional = make_verified_production_evidence(
        benchmark,
        promotion,
        catalog_snapshot_id=snapshot.snapshot_id,
    )
    requirements = ModelTaskRequirements(
        task_family=TASK,
        purpose=SelectionPurpose.PRODUCTION,
        min_verifier_pass_rate=0.8,
        require_structured_output=True,
        require_reasoning=True,
    )
    first = select_models_for_task(snapshot, requirements, production_evidence=provisional)
    verified = make_verified_production_evidence(
        benchmark,
        promotion,
        catalog_snapshot_id=snapshot.snapshot_id,
        selection_receipt_id=first.receipt_id,
    )
    selection = select_models_for_task(snapshot, requirements, production_evidence=verified)
    assert selection.receipt_id == first.receipt_id
    return snapshot, selection, benchmark, promotion, verified


def _policy(**overrides):
    values = {
        "task_family": TASK,
        "runtime_surface": "reddog_backend_architect",
        "min_verifier_pass_rate": 0.8,
        "required_task_set_digest": "sha256:task-set",
        "required_held_out_split_digest": "sha256:held-out",
        "required_verifier_digest": "sha256:verifier",
        "authority_receipt_id": "runtime-authority:1",
    }
    values.update(overrides)
    return values


def _serialized_evidence_bundle(snapshot, selection, benchmark, promotion):
    benchmark_sig = make_signed_evidence_receipt(
        signer_role=ModelEvidenceSignerRole.BENCHMARK_VERIFIER,
        public_key=BENCHMARK_PUBLIC_KEY,
        fingerprint=BENCHMARK_FINGERPRINT,
        model_id=MODEL_ID,
        catalog_snapshot_id=snapshot.snapshot_id,
        selection_receipt_id=selection.receipt_id,
        benchmark_run_receipt_id="model_combination_benchmark_run:test",
        benchmark_receipt=benchmark,
        nonce=f"nonce:benchmark:{benchmark.receipt_id}:{selection.receipt_id}",
    )
    promotion_sig = make_signed_evidence_receipt(
        signer_role=ModelEvidenceSignerRole.PROMOTION_AUTHORITY,
        public_key=PROMOTION_PUBLIC_KEY,
        fingerprint=PROMOTION_FINGERPRINT,
        model_id=MODEL_ID,
        catalog_snapshot_id=snapshot.snapshot_id,
        selection_receipt_id=selection.receipt_id,
        benchmark_run_receipt_id="model_combination_benchmark_run:test",
        benchmark_receipt=benchmark,
        promotion_receipt=promotion,
        promotion_policy_digest="sha256:promotion-policy",
        nonce=f"nonce:promotion:{promotion.receipt_id}:{selection.receipt_id}",
    )
    return {
        "schema_version": EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "catalog_snapshot_id": snapshot.snapshot_id,
        "selection_receipt_id": selection.receipt_id,
        "benchmark_run_receipt_id": "model_combination_benchmark_run:test",
        "entries": [
            {
                "benchmark_receipt": benchmark.to_dict(),
                "promotion_receipt": promotion.to_dict(),
                "benchmark_signature_receipt": benchmark_sig.to_dict(),
                "promotion_signature_receipt": promotion_sig.to_dict(),
            }
        ],
    }


def _key_resolver():
    return StaticModelEvidenceKeyResolver(
        {
            ModelEvidenceSignerRole.BENCHMARK_VERIFIER.value: BENCHMARK_PUBLIC_KEY,
            ModelEvidenceSignerRole.PROMOTION_AUTHORITY.value: PROMOTION_PUBLIC_KEY,
        }
    )


def _artifact(value):
    return json.loads(json.dumps(value, sort_keys=True))


def test_runtime_supplier_verifies_serialized_evidence_and_writes_bound_receipt(tmp_path: Path) -> None:
    snapshot, selection, benchmark, promotion, _verified = _selection_chain()
    output = tmp_path / "runtime" / "model_runtime_binding_receipt.json"

    result = run_reddog_model_runtime_binding_artifact_supply(
        repo_root=REPO_ROOT,
        catalog_snapshot=_artifact(snapshot.to_dict()),
        model_selection_receipt=_artifact(selection.to_dict()),
        benchmark_evidence_receipts=(_artifact(benchmark.to_dict()),),
        promotion_evidence_receipts=(_artifact(promotion.to_dict()),),
        verified_evidence_bundle=_serialized_evidence_bundle(snapshot, selection, benchmark, promotion),
        runtime_policy=_policy(),
        output_path=output,
        key_resolver=_key_resolver(),
        signature_verifier=DeterministicSignatureVerifier(),
        now=NOW,
    )

    assert result.accepted is True
    assert result.status == MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY_ACCEPT
    assert result.runtime_binding_receipt_id and result.runtime_binding_receipt_id.startswith(
        "reddog_model_runtime_binding:"
    )
    assert result.output_path == str(output.resolve())
    assert result.principal_model == MODEL_ID
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["decision"] == "bound"
    assert receipt["runtime_surface"] == "reddog_backend_architect"
    assert receipt["selection_receipt_id"] == selection.receipt_id
    assert result.no_model_call_performed is True
    assert result.no_holoindex_reindex_performed is True


def test_runtime_supplier_accepts_typed_verified_evidence_object(tmp_path: Path) -> None:
    snapshot, selection, benchmark, promotion, verified = _selection_chain()

    result = run_reddog_model_runtime_binding_artifact_supply(
        repo_root=REPO_ROOT,
        catalog_snapshot=_artifact(snapshot.to_dict()),
        model_selection_receipt=_artifact(selection.to_dict()),
        benchmark_evidence_receipts=(_artifact(benchmark.to_dict()),),
        promotion_evidence_receipts=(_artifact(promotion.to_dict()),),
        verified_evidence_bundle=verified,
        runtime_policy=_policy(),
        output_path=tmp_path / "runtime" / "model_runtime_binding_receipt.json",
    )

    assert result.accepted is True
    assert result.selection_receipt_id == selection.receipt_id


def test_runtime_supplier_rejects_serialized_evidence_without_signature_gate(tmp_path: Path) -> None:
    snapshot, selection, benchmark, promotion, _verified = _selection_chain()

    result = run_reddog_model_runtime_binding_artifact_supply(
        repo_root=REPO_ROOT,
        catalog_snapshot=_artifact(snapshot.to_dict()),
        model_selection_receipt=_artifact(selection.to_dict()),
        benchmark_evidence_receipts=(_artifact(benchmark.to_dict()),),
        promotion_evidence_receipts=(_artifact(promotion.to_dict()),),
        verified_evidence_bundle=_serialized_evidence_bundle(snapshot, selection, benchmark, promotion),
        runtime_policy=_policy(),
        output_path=tmp_path / "runtime" / "model_runtime_binding_receipt.json",
    )

    assert result.accepted is False
    assert result.status == MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY_REJECT
    assert ModelRuntimeBindingArtifactSupplyReason.KEY_RESOLVER_MISSING in result.rejection_reasons
    assert ModelRuntimeBindingArtifactSupplyReason.SIGNATURE_VERIFIER_MISSING in result.rejection_reasons


def test_runtime_supplier_rejects_binding_policy_mismatch_without_writing(tmp_path: Path) -> None:
    snapshot, selection, benchmark, promotion, verified = _selection_chain()
    output = tmp_path / "runtime" / "model_runtime_binding_receipt.json"

    result = run_reddog_model_runtime_binding_artifact_supply(
        repo_root=REPO_ROOT,
        catalog_snapshot=_artifact(snapshot.to_dict()),
        model_selection_receipt=_artifact(selection.to_dict()),
        benchmark_evidence_receipts=(_artifact(benchmark.to_dict()),),
        promotion_evidence_receipts=(_artifact(promotion.to_dict()),),
        verified_evidence_bundle=verified,
        runtime_policy=_policy(required_task_set_digest="sha256:wrong"),
        output_path=output,
    )

    assert result.accepted is False
    assert ModelRuntimeBindingArtifactSupplyReason.RUNTIME_BINDING_REJECTED in result.rejection_reasons
    assert "task_set_digest_mismatch" in result.rejection_reasons
    assert not output.exists()


def test_runtime_supplier_rejects_output_inside_repo() -> None:
    snapshot, selection, benchmark, promotion, verified = _selection_chain()

    result = run_reddog_model_runtime_binding_artifact_supply(
        repo_root=REPO_ROOT,
        catalog_snapshot=_artifact(snapshot.to_dict()),
        model_selection_receipt=_artifact(selection.to_dict()),
        benchmark_evidence_receipts=(_artifact(benchmark.to_dict()),),
        promotion_evidence_receipts=(_artifact(promotion.to_dict()),),
        verified_evidence_bundle=verified,
        runtime_policy=_policy(),
        output_path=REPO_ROOT / "model_runtime_binding_receipt.json",
    )

    assert result.accepted is False
    assert ModelRuntimeBindingArtifactSupplyReason.OUTPUT_PATH_INVALID in result.rejection_reasons
    assert not (REPO_ROOT / "model_runtime_binding_receipt.json").exists()


def test_runtime_supplier_module_has_no_execution_network_or_reindex_imports() -> None:
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
