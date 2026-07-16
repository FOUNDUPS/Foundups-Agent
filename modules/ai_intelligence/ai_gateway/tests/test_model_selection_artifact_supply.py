"""Tests for REDDOG_MODEL_SELECTION_ARTIFACT_SUPPLY_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.model_intelligence_catalog import (
    Availability,
    ModelCapabilityCard,
    PromotionState,
    build_model_catalog_snapshot,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_outcomes import (
    ModelOutcomeMetrics,
    build_model_benchmark_evidence_receipt,
    build_model_promotion_evidence_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_selection_artifact_supply import (
    EVIDENCE_BUNDLE_SCHEMA_VERSION,
    MODEL_SELECTION_ARTIFACT_SUPPLY_ACCEPT,
    MODEL_SELECTION_ARTIFACT_SUPPLY_REJECT,
    ModelSelectionArtifactSupplyReason,
    run_reddog_model_selection_artifact_supply,
)
from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import (
    ModelEvidenceSignerRole,
    StaticModelEvidenceKeyResolver,
)
from model_signed_evidence_test_helpers import (
    BENCHMARK_PUBLIC_KEY,
    PROMOTION_PUBLIC_KEY,
    DeterministicSignatureVerifier,
    make_signed_evidence_receipt,
    make_verified_production_evidence,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT / "modules" / "ai_intelligence" / "ai_gateway" / "src" / "model_selection_artifact_supply.py"
)
NOW = 1_800_000_000
MODEL_ID = "openai/gpt-5.6-code"
TASK = "reddog_architect_fix_promotion"


def _card() -> ModelCapabilityCard:
    return ModelCapabilityCard(
        provider="openai",
        model_id=MODEL_ID,
        canonical_model_id=MODEL_ID,
        source="test",
        availability=Availability.AVAILABLE,
        promotion_state=PromotionState.CHAMPION,
        task_families=(TASK,),
        context_window=256000,
        supports_structured_output=True,
        supports_reasoning=True,
        verifier_pass_rate=1.0,
        benchmark_scores={TASK: 1.0},
    ).normalized()


def _snapshot():
    return build_model_catalog_snapshot((_card(),), generated_at="2026-07-16T00:00:00+00:00")


def _benchmark():
    return build_model_benchmark_evidence_receipt(
        model_id=MODEL_ID,
        task_family=TASK,
        task_set_digest="sha256:task-set",
        held_out_split_digest="sha256:held-out",
        prompt_topology_digest="sha256:topology",
        verifier_digest="sha256:verifier",
        verifier_receipt_id="sha256:verifier-receipt",
        sample_count=12,
        accepted_count=12,
        metrics=ModelOutcomeMetrics(latency_ms=100, input_tokens=10, output_tokens=20),
    )


def _promotion(benchmark):
    return build_model_promotion_evidence_receipt(
        benchmark_receipt=benchmark,
        promotion_state=PromotionState.CHAMPION,
        promotion_authority_receipt_id="sha256:promotion-authority",
        signed_promotion_receipt_id="signature:promotion",
        min_verifier_pass_rate=0.8,
    )


def _requirements(**overrides):
    payload = {
        "task_family": TASK,
        "purpose": "production",
        "selection_mode": "single",
        "require_structured_output": True,
        "require_reasoning": True,
        "min_verifier_pass_rate": 0.8,
    }
    payload.update(overrides)
    return payload


def _serialized_evidence_bundle(snapshot):
    benchmark = _benchmark()
    promotion = _promotion(benchmark)
    benchmark_sig = make_signed_evidence_receipt(
        signer_role=ModelEvidenceSignerRole.BENCHMARK_VERIFIER,
        public_key=BENCHMARK_PUBLIC_KEY,
        fingerprint="fingerprint:benchmark",
        model_id=MODEL_ID,
        catalog_snapshot_id=snapshot.snapshot_id,
        selection_receipt_id="model_selection_receipt:pending",
        benchmark_run_receipt_id="model_combination_benchmark_run:test",
        benchmark_receipt=benchmark,
        nonce="nonce:benchmark",
    )
    promotion_sig = make_signed_evidence_receipt(
        signer_role=ModelEvidenceSignerRole.PROMOTION_AUTHORITY,
        public_key=PROMOTION_PUBLIC_KEY,
        fingerprint="fingerprint:promotion",
        model_id=MODEL_ID,
        catalog_snapshot_id=snapshot.snapshot_id,
        selection_receipt_id="model_selection_receipt:pending",
        benchmark_run_receipt_id="model_combination_benchmark_run:test",
        benchmark_receipt=benchmark,
        promotion_receipt=promotion,
        promotion_policy_digest="sha256:promotion-policy",
        nonce="nonce:promotion",
    )
    return {
        "schema_version": EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "catalog_snapshot_id": snapshot.snapshot_id,
        "selection_receipt_id": "model_selection_receipt:pending",
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


def test_supplier_verifies_serialized_evidence_and_writes_selection_receipt(tmp_path: Path) -> None:
    snapshot = _snapshot()
    output = tmp_path / "runtime" / "model_selection_receipt.json"

    result = run_reddog_model_selection_artifact_supply(
        repo_root=REPO_ROOT,
        catalog_snapshot=snapshot.to_dict(),
        verified_evidence_bundle=_serialized_evidence_bundle(snapshot),
        requirements=_requirements(),
        output_path=output,
        key_resolver=_key_resolver(),
        signature_verifier=DeterministicSignatureVerifier(),
        now=NOW,
    )

    assert result.accepted is True
    assert result.status == MODEL_SELECTION_ARTIFACT_SUPPLY_ACCEPT
    assert result.output_path == str(output.resolve())
    assert result.selection_receipt_id and result.selection_receipt_id.startswith("model_selection_receipt:")
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["decision"] == "selected"
    assert receipt["selected_model_ids"] == [MODEL_ID]
    assert receipt["requirements"]["purpose"] == "production"
    assert result.no_model_call_performed is True
    assert result.no_holoindex_reindex_performed is True


def test_supplier_accepts_typed_verified_evidence_object(tmp_path: Path) -> None:
    snapshot = _snapshot()
    benchmark = _benchmark()
    promotion = _promotion(benchmark)
    verified = make_verified_production_evidence(
        benchmark,
        promotion,
        catalog_snapshot_id=snapshot.snapshot_id,
    )

    result = run_reddog_model_selection_artifact_supply(
        repo_root=REPO_ROOT,
        catalog_snapshot=snapshot.to_dict(),
        verified_evidence_bundle=verified,
        requirements=_requirements(),
        output_path=tmp_path / "runtime" / "model_selection_receipt.json",
    )

    assert result.accepted is True
    assert result.selected_model_ids == (MODEL_ID,)


def test_supplier_rejects_serialized_evidence_without_signature_gate(tmp_path: Path) -> None:
    snapshot = _snapshot()

    result = run_reddog_model_selection_artifact_supply(
        repo_root=REPO_ROOT,
        catalog_snapshot=snapshot.to_dict(),
        verified_evidence_bundle=_serialized_evidence_bundle(snapshot),
        requirements=_requirements(),
        output_path=tmp_path / "runtime" / "model_selection_receipt.json",
    )

    assert result.accepted is False
    assert result.status == MODEL_SELECTION_ARTIFACT_SUPPLY_REJECT
    assert ModelSelectionArtifactSupplyReason.KEY_RESOLVER_MISSING in result.rejection_reasons
    assert ModelSelectionArtifactSupplyReason.SIGNATURE_VERIFIER_MISSING in result.rejection_reasons


def test_supplier_rejects_evaluation_requirements(tmp_path: Path) -> None:
    snapshot = _snapshot()
    benchmark = _benchmark()
    promotion = _promotion(benchmark)

    result = run_reddog_model_selection_artifact_supply(
        repo_root=REPO_ROOT,
        catalog_snapshot=snapshot.to_dict(),
        verified_evidence_bundle=make_verified_production_evidence(
            benchmark,
            promotion,
            catalog_snapshot_id=snapshot.snapshot_id,
        ),
        requirements=_requirements(purpose="evaluation"),
        output_path=tmp_path / "runtime" / "model_selection_receipt.json",
    )

    assert result.accepted is False
    assert ModelSelectionArtifactSupplyReason.NON_PRODUCTION_REQUIREMENTS in result.rejection_reasons


def test_supplier_rejects_output_inside_repo(tmp_path: Path) -> None:
    snapshot = _snapshot()
    benchmark = _benchmark()
    promotion = _promotion(benchmark)

    result = run_reddog_model_selection_artifact_supply(
        repo_root=REPO_ROOT,
        catalog_snapshot=snapshot.to_dict(),
        verified_evidence_bundle=make_verified_production_evidence(
            benchmark,
            promotion,
            catalog_snapshot_id=snapshot.snapshot_id,
        ),
        requirements=_requirements(),
        output_path=REPO_ROOT / "model_selection_receipt.json",
    )

    assert result.accepted is False
    assert ModelSelectionArtifactSupplyReason.OUTPUT_PATH_INVALID in result.rejection_reasons
    assert not (REPO_ROOT / "model_selection_receipt.json").exists()


def test_supplier_module_has_no_execution_network_or_reindex_imports() -> None:
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
