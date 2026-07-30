"""Tests for signed model evidence rehydration and verification."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from model_signed_evidence_test_helpers import (
    BENCHMARK_FINGERPRINT,
    BENCHMARK_PUBLIC_KEY,
    DeterministicSignatureVerifier,
    KEY_EPOCH,
    NOW,
    make_signed_evidence_receipt,
    make_verified_production_evidence,
)

from modules.ai_intelligence.ai_gateway.src.model_intelligence_catalog import (
    ModelCapabilityCard,
    PromotionState,
    build_model_catalog_snapshot,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_outcomes import (
    build_model_benchmark_evidence_receipt,
    build_model_promotion_evidence_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import (
    InMemoryEvidenceNonceStore,
    ModelEvidenceSignerRole,
    ModelEvidenceSubjectType,
    StaticModelEvidenceKeyResolver,
    build_verified_model_production_evidence,
    rehydrate_model_benchmark_evidence_receipt,
    rehydrate_model_catalog_snapshot,
    rehydrate_model_signed_evidence_receipt,
    verify_model_signed_evidence_receipt,
)


TASK = "architecture"
TASK_SET = "sha256:task-set"
HELD_OUT = "sha256:held-out"
TOPOLOGY = "sha256:topology"
VERIFIER = "sha256:verifier"
CATALOG = "model_catalog_snapshot:test"
SELECTION = "model_selection_receipt:test"
BENCHMARK_RUN = "model_combination_benchmark_run:test"
PROMOTION_POLICY = "sha256:promotion-policy"


def _benchmark_resolver() -> StaticModelEvidenceKeyResolver:
    return StaticModelEvidenceKeyResolver(
        {
            (
                ModelEvidenceSignerRole.BENCHMARK_VERIFIER.value,
                BENCHMARK_FINGERPRINT,
                KEY_EPOCH,
            ): BENCHMARK_PUBLIC_KEY
        }
    )


def _benchmark(model_id: str = "provider/model"):
    return build_model_benchmark_evidence_receipt(
        model_id=model_id,
        task_family=TASK,
        task_set_digest=TASK_SET,
        held_out_split_digest=HELD_OUT,
        prompt_topology_digest=TOPOLOGY,
        verifier_digest=VERIFIER,
        verifier_receipt_id=f"verifier:{model_id}",
        sample_count=20,
        accepted_count=19,
    )


def _promotion(benchmark):
    return build_model_promotion_evidence_receipt(
        benchmark_receipt=benchmark,
        promotion_state=PromotionState.CHAMPION,
        promotion_authority_receipt_id=f"promotion-authority:{benchmark.model_id}",
        signed_promotion_receipt_id=f"signed-promotion:{benchmark.model_id}",
        min_verifier_pass_rate=0.9,
    )


def test_rehydrates_benchmark_and_catalog_by_recomputing_digest():
    benchmark = _benchmark()
    assert rehydrate_model_benchmark_evidence_receipt(benchmark.to_dict()) == benchmark

    tampered = benchmark.to_dict()
    tampered["accepted_count"] = 18
    try:
        rehydrate_model_benchmark_evidence_receipt(tampered)
    except ValueError as exc:
        assert str(exc) in {"benchmark_receipt_id_mismatch", "benchmark_pass_rate_mismatch"}
    else:
        raise AssertionError("tampered benchmark receipt must fail")

    snapshot = build_model_catalog_snapshot(
        (
            ModelCapabilityCard(
                provider="provider",
                model_id="provider/model",
                canonical_model_id="provider/model",
                source="test",
                promotion_state=PromotionState.CHAMPION,
                task_families=(TASK,),
            ).normalized(),
        ),
        generated_at="2026-07-16T00:00:00+00:00",
    )
    assert rehydrate_model_catalog_snapshot(snapshot.to_dict()) == snapshot

    snapshot_tampered = snapshot.to_dict()
    snapshot_tampered["cards"][0]["canonical_model_id"] = "provider/other"
    try:
        rehydrate_model_catalog_snapshot(snapshot_tampered)
    except ValueError as exc:
        assert str(exc) == "catalog_snapshot_id_mismatch"
    else:
        raise AssertionError("tampered catalog snapshot must fail")


def test_signed_evidence_verifies_role_key_ttl_and_signature():
    benchmark = _benchmark()
    signed = make_signed_evidence_receipt(
        signer_role=ModelEvidenceSignerRole.BENCHMARK_VERIFIER,
        public_key=BENCHMARK_PUBLIC_KEY,
        fingerprint=BENCHMARK_FINGERPRINT,
        model_id=benchmark.model_id,
        catalog_snapshot_id=CATALOG,
        selection_receipt_id=SELECTION,
        benchmark_run_receipt_id=BENCHMARK_RUN,
        benchmark_receipt=benchmark,
        nonce="nonce:benchmark",
    )
    assert rehydrate_model_signed_evidence_receipt(signed.to_dict()) == signed
    result = verify_model_signed_evidence_receipt(
        signed,
        expected_role=ModelEvidenceSignerRole.BENCHMARK_VERIFIER,
        key_resolver=_benchmark_resolver(),
        signature_verifier=DeterministicSignatureVerifier(),
        now=NOW,
    )
    assert result.accepted is True

    wrong_role = verify_model_signed_evidence_receipt(
        signed,
        expected_role=ModelEvidenceSignerRole.PROMOTION_AUTHORITY,
        key_resolver=_benchmark_resolver(),
        signature_verifier=DeterministicSignatureVerifier(),
        now=NOW,
    )
    assert wrong_role.accepted is False
    assert "signer_role_mismatch" in wrong_role.reason_codes

    forged = make_signed_evidence_receipt(
        signer_role=ModelEvidenceSignerRole.BENCHMARK_VERIFIER,
        public_key=BENCHMARK_PUBLIC_KEY,
        fingerprint=BENCHMARK_FINGERPRINT,
        model_id=benchmark.model_id,
        catalog_snapshot_id=CATALOG,
        selection_receipt_id=SELECTION,
        benchmark_run_receipt_id=BENCHMARK_RUN,
        benchmark_receipt=benchmark,
        nonce="nonce:forged",
        signature_override="test-sig:forged",
    )
    bad_signature = verify_model_signed_evidence_receipt(
        forged,
        expected_role=ModelEvidenceSignerRole.BENCHMARK_VERIFIER,
        key_resolver=_benchmark_resolver(),
        signature_verifier=DeterministicSignatureVerifier(),
        now=NOW,
    )
    assert bad_signature.accepted is False
    assert "signature_invalid" in bad_signature.reason_codes


def test_trust_anchor_requires_exact_role_fingerprint_and_epoch() -> None:
    with pytest.raises(
        ValueError, match="trusted_model_evidence_key_tuple_required"
    ):
        StaticModelEvidenceKeyResolver(
            {
                ModelEvidenceSignerRole.BENCHMARK_VERIFIER.value: (
                    BENCHMARK_PUBLIC_KEY
                )
            }
        )

    benchmark = _benchmark()
    spoofed = make_signed_evidence_receipt(
        signer_role=ModelEvidenceSignerRole.BENCHMARK_VERIFIER,
        public_key=BENCHMARK_PUBLIC_KEY,
        fingerprint="fingerprint:attacker-selected",
        model_id=benchmark.model_id,
        catalog_snapshot_id=CATALOG,
        selection_receipt_id=SELECTION,
        benchmark_run_receipt_id=BENCHMARK_RUN,
        benchmark_receipt=benchmark,
        nonce="nonce:spoofed-epoch",
    )
    result = verify_model_signed_evidence_receipt(
        spoofed,
        expected_role=ModelEvidenceSignerRole.BENCHMARK_VERIFIER,
        key_resolver=_benchmark_resolver(),
        signature_verifier=DeterministicSignatureVerifier(),
        now=NOW,
    )

    assert result.accepted is False
    assert result.reason_codes == ("signer_key_untrusted",)


def test_nonce_consumed_only_when_admission_requests_it():
    benchmark = _benchmark()
    signed = make_signed_evidence_receipt(
        signer_role=ModelEvidenceSignerRole.BENCHMARK_VERIFIER,
        public_key=BENCHMARK_PUBLIC_KEY,
        fingerprint=BENCHMARK_FINGERPRINT,
        model_id=benchmark.model_id,
        catalog_snapshot_id=CATALOG,
        selection_receipt_id=SELECTION,
        benchmark_run_receipt_id=BENCHMARK_RUN,
        benchmark_receipt=benchmark,
        nonce="nonce:single-use",
    )
    store = InMemoryEvidenceNonceStore()
    kwargs = {
        "expected_role": ModelEvidenceSignerRole.BENCHMARK_VERIFIER,
        "key_resolver": _benchmark_resolver(),
        "signature_verifier": DeterministicSignatureVerifier(),
        "now": NOW,
        "nonce_store": store,
    }
    assert verify_model_signed_evidence_receipt(signed, consume_nonce=False, **kwargs).accepted is True
    assert verify_model_signed_evidence_receipt(signed, consume_nonce=True, **kwargs).accepted is True
    replay = verify_model_signed_evidence_receipt(signed, consume_nonce=True, **kwargs)
    assert replay.accepted is False
    assert replay.reason_codes == ("nonce_replay",)


def test_benchmark_and_promotion_signers_must_be_independent() -> None:
    benchmark = _benchmark()
    promotion = _promotion(benchmark)
    benchmark_signature = make_signed_evidence_receipt(
        signer_role=ModelEvidenceSignerRole.BENCHMARK_VERIFIER,
        public_key=BENCHMARK_PUBLIC_KEY,
        fingerprint=BENCHMARK_FINGERPRINT,
        model_id=benchmark.model_id,
        catalog_snapshot_id=CATALOG,
        selection_receipt_id=SELECTION,
        benchmark_run_receipt_id=BENCHMARK_RUN,
        benchmark_receipt=benchmark,
        nonce="nonce:shared:benchmark",
    )
    promotion_signature = make_signed_evidence_receipt(
        signer_role=ModelEvidenceSignerRole.PROMOTION_AUTHORITY,
        public_key=BENCHMARK_PUBLIC_KEY,
        fingerprint=BENCHMARK_FINGERPRINT,
        model_id=benchmark.model_id,
        catalog_snapshot_id=CATALOG,
        selection_receipt_id=SELECTION,
        benchmark_run_receipt_id=BENCHMARK_RUN,
        benchmark_receipt=benchmark,
        promotion_receipt=promotion,
        promotion_policy_digest=PROMOTION_POLICY,
        nonce="nonce:shared:promotion",
    )
    resolver = StaticModelEvidenceKeyResolver(
        {
            (
                ModelEvidenceSignerRole.BENCHMARK_VERIFIER.value,
                BENCHMARK_FINGERPRINT,
                KEY_EPOCH,
            ): BENCHMARK_PUBLIC_KEY,
            (
                ModelEvidenceSignerRole.PROMOTION_AUTHORITY.value,
                BENCHMARK_FINGERPRINT,
                KEY_EPOCH,
            ): BENCHMARK_PUBLIC_KEY,
        }
    )

    with pytest.raises(
        ValueError, match="benchmark_and_promotion_signers_not_independent"
    ):
        build_verified_model_production_evidence(
            catalog_snapshot_id=CATALOG,
            selection_receipt_id=SELECTION,
            benchmark_run_receipt_id=BENCHMARK_RUN,
            benchmark_receipt=benchmark,
            promotion_receipt=promotion,
            benchmark_signature_receipt=benchmark_signature,
            promotion_signature_receipt=promotion_signature,
            key_resolver=resolver,
            signature_verifier=DeterministicSignatureVerifier(),
            now=NOW,
        )


def test_build_verified_production_evidence_rejects_panel_and_tampered_bindings():
    benchmark = _benchmark()
    promotion = _promotion(benchmark)
    evidence = make_verified_production_evidence(
        benchmark,
        promotion,
        catalog_snapshot_id=CATALOG,
        selection_receipt_id=SELECTION,
        benchmark_run_receipt_id=BENCHMARK_RUN,
        promotion_policy_digest=PROMOTION_POLICY,
    )
    assert evidence.signed_evidence_verified is True
    assert evidence.model_ids() == (benchmark.model_id,)

    panel_signature = make_signed_evidence_receipt(
        signer_role=ModelEvidenceSignerRole.BENCHMARK_VERIFIER,
        public_key=BENCHMARK_PUBLIC_KEY,
        fingerprint=BENCHMARK_FINGERPRINT,
        model_id=benchmark.model_id,
        catalog_snapshot_id=CATALOG,
        selection_receipt_id=SELECTION,
        benchmark_run_receipt_id=BENCHMARK_RUN,
        benchmark_receipt=benchmark,
        nonce="nonce:panel",
        subject_type=ModelEvidenceSubjectType.PANEL,
    )
    try:
        build_verified_model_production_evidence(
            catalog_snapshot_id=CATALOG,
            selection_receipt_id=SELECTION,
            benchmark_run_receipt_id=BENCHMARK_RUN,
            benchmark_receipt=benchmark,
            promotion_receipt=promotion,
            benchmark_signature_receipt=panel_signature,
            promotion_signature_receipt=evidence.entries[0].promotion_signature_receipt,
            key_resolver=_benchmark_resolver(),
            signature_verifier=DeterministicSignatureVerifier(),
            now=NOW,
        )
    except ValueError as exc:
        assert str(exc) == "panel_signed_evidence_deferred"
    else:
        raise AssertionError("panel signed evidence must remain deferred")


def test_signed_evidence_module_has_no_network_command_signer_or_runtime_mutation_imports():
    source = Path("modules/ai_intelligence/ai_gateway/src/model_signed_evidence.py").read_text()
    tree = ast.parse(source)
    imported: set[str] = set()
    banned_calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id in {
                "os",
                "subprocess",
                "requests",
                "urllib",
                "socket",
            }:
                banned_calls.append(f"{node.func.value.id}.{node.func.attr}")

    assert "subprocess" not in imported
    assert "requests" not in imported
    assert "urllib" not in imported
    assert "socket" not in imported
    assert "cryptography" not in imported
    assert banned_calls == []
