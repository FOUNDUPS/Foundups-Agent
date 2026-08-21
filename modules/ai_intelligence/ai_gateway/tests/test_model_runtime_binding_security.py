"""Security tests for verified model-runtime binding authority."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_artifact_supply import (
    ModelRuntimeBindingArtifactSupplyReason,
    run_reddog_model_runtime_binding_artifact_supply,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_capability import (
    build_verified_runtime_binding_capability_api,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_evidence_verifier import (
    verify_model_runtime_binding_artifact,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_use_time_verifier import (
    ModelRuntimeBindingUseTimeVerifier,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import (
    VerifiedRuntimeBindingCapability,
    consume_verified_runtime_binding_capability,
    rehydrate_runtime_binding_verification_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_topology_resolver import (
    consume_resolved_runtime_topology,
    resolve_verified_runtime_topology,
)
from modules.ai_intelligence.ai_gateway.tests.model_signed_evidence_test_helpers import (
    DeterministicSignatureVerifier,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_runtime_binding_artifact_supply import (
    NOW,
    REPO_ROOT,
    _artifact,
    _key_resolver,
    _policy,
    _selection_chain,
    _serialized_evidence_bundle,
    _trusted_keys_payload,
)
from modules.communication.moltbot_bridge.src.reddog_model_runtime_verifier_bootstrap import (
    ModelRuntimeVerifierConfig,
    build_model_runtime_verifier,
)


def _verified_runtime_artifact():
    snapshot, selection, benchmark, promotion, _verified = _selection_chain()
    inputs = {
        "catalog_snapshot": _artifact(snapshot.to_dict()),
        "model_selection_receipt": _artifact(selection.to_dict()),
        "benchmark_evidence_receipts": (_artifact(benchmark.to_dict()),),
        "promotion_evidence_receipts": (_artifact(promotion.to_dict()),),
        "verified_evidence_bundle": _serialized_evidence_bundle(
            snapshot, selection, benchmark, promotion
        ),
        "runtime_policy": _policy(),
        "trusted_keys_payload": _trusted_keys_payload(),
        "key_resolver": _key_resolver(),
        "signature_verifier": DeterministicSignatureVerifier(),
        "now": NOW,
    }
    return verify_model_runtime_binding_artifact(**inputs), selection


def test_verified_runtime_topology_resolver_preserves_exact_route_once() -> None:
    verified, selection = _verified_runtime_artifact()
    provider = verified.binding.role_bindings[0].provider

    resolution = resolve_verified_runtime_topology(
        verified=verified,
        selection=selection.to_dict(),
        available_providers=(provider,),
        now=NOW,
        expected_runtime_surface="reddog_backend_architect",
    )

    assert resolution.no_model_call_performed is True
    assert resolution.no_provider_fallback_performed is True
    assert resolution.endpoints[0].provider == provider
    assert resolution.endpoints[0].model_id == verified.binding.principal_model
    assert resolution.resolved_at == NOW
    assert resolution.valid_until == NOW + 60
    assert consume_resolved_runtime_topology(
        resolution, trusted_now_epoch=lambda: NOW
    ) == resolution.endpoints
    assert consume_resolved_runtime_topology(
        resolution, trusted_now_epoch=lambda: NOW
    ) is None


def test_runtime_topology_capability_expires_before_consumption() -> None:
    verified, selection = _verified_runtime_artifact()
    provider = verified.binding.role_bindings[0].provider
    resolution = resolve_verified_runtime_topology(
        verified=verified,
        selection=selection.to_dict(),
        available_providers=(provider,),
        now=NOW,
    )

    assert consume_resolved_runtime_topology(
        resolution, trusted_now_epoch=lambda: NOW + 61
    ) is None
    assert consume_resolved_runtime_topology(
        resolution, trusted_now_epoch=lambda: NOW
    ) is None


def test_runtime_topology_rejects_unavailable_provider_and_consumes_authority() -> None:
    verified, selection = _verified_runtime_artifact()

    with pytest.raises(ValueError, match="runtime_topology_provider_unavailable"):
        resolve_verified_runtime_topology(
            verified=verified,
            selection=selection.to_dict(),
            available_providers=("lm_studio_local",),
            now=NOW,
        )

    with pytest.raises(ValueError, match="runtime_topology_binding_capability_rejected"):
        resolve_verified_runtime_topology(
            verified=verified,
            selection=selection.to_dict(),
            available_providers=(verified.binding.role_bindings[0].provider,),
            now=NOW,
        )


def test_verification_receipt_rejects_self_rehashed_or_unknown_runtime_receipt(
    tmp_path: Path,
) -> None:
    snapshot, selection, benchmark, promotion, _verified = _selection_chain()
    output = tmp_path / "runtime" / "model_runtime_binding_receipt.json"
    result = run_reddog_model_runtime_binding_artifact_supply(
        repo_root=REPO_ROOT,
        catalog_snapshot=_artifact(snapshot.to_dict()),
        model_selection_receipt=_artifact(selection.to_dict()),
        benchmark_evidence_receipts=(_artifact(benchmark.to_dict()),),
        promotion_evidence_receipts=(_artifact(promotion.to_dict()),),
        verified_evidence_bundle=_serialized_evidence_bundle(
            snapshot, selection, benchmark, promotion
        ),
        trusted_keys_payload=_trusted_keys_payload(),
        runtime_policy=_policy(),
        output_path=output,
        key_resolver=_key_resolver(),
        signature_verifier=DeterministicSignatureVerifier(),
        now=NOW,
    )
    assert result.accepted is True
    receipt = json.loads(output.read_text(encoding="utf-8"))

    changed = dict(receipt["verification_receipt"])
    changed["runtime_binding_digest"] = "sha256:" + ("a" * 64)
    try:
        rehydrate_runtime_binding_verification_receipt(changed)
    except ValueError:
        pass
    else:
        raise AssertionError("self-rehashed verification mutation accepted")


def test_runtime_supplier_rejects_process_local_typed_evidence_object(
    tmp_path: Path,
) -> None:
    snapshot, selection, benchmark, promotion, verified = _selection_chain()

    result = run_reddog_model_runtime_binding_artifact_supply(
        repo_root=REPO_ROOT,
        catalog_snapshot=_artifact(snapshot.to_dict()),
        model_selection_receipt=_artifact(selection.to_dict()),
        benchmark_evidence_receipts=(_artifact(benchmark.to_dict()),),
        promotion_evidence_receipts=(_artifact(promotion.to_dict()),),
        verified_evidence_bundle=verified,
        trusted_keys_payload=_trusted_keys_payload(),
        runtime_policy=_policy(),
        output_path=tmp_path / "runtime" / "model_runtime_binding_receipt.json",
    )

    assert result.accepted is False
    assert ModelRuntimeBindingArtifactSupplyReason.EVIDENCE_INVALID in (
        result.rejection_reasons
    )


def test_signed_evidence_reverification_survives_supply_promotion_restart(
    tmp_path: Path,
) -> None:
    snapshot, selection, benchmark, promotion, _verified = _selection_chain()
    bundle = _serialized_evidence_bundle(snapshot, selection, benchmark, promotion)
    inputs = {
        "catalog_snapshot": _artifact(snapshot.to_dict()),
        "model_selection_receipt": _artifact(selection.to_dict()),
        "benchmark_evidence_receipts": (_artifact(benchmark.to_dict()),),
        "promotion_evidence_receipts": (_artifact(promotion.to_dict()),),
        "verified_evidence_bundle": bundle,
        "runtime_policy": _policy(),
        "trusted_keys_payload": _trusted_keys_payload(),
        "key_resolver": _key_resolver(),
        "signature_verifier": DeterministicSignatureVerifier(),
        "now": NOW,
    }
    first = verify_model_runtime_binding_artifact(**inputs)
    second = verify_model_runtime_binding_artifact(
        **inputs,
        receipt_verified_at=first.verification.verified_at,
    )

    assert first.to_artifact() == second.to_artifact()
    assert first.capability is not second.capability
    accepted = consume_verified_runtime_binding_capability(
        second.capability,
        binding=second.to_artifact(),
        selection=selection.to_dict(),
        receipt=second.verification,
    )
    assert accepted == second.verification
    assert (
        consume_verified_runtime_binding_capability(
            second.capability,
            binding=second.to_artifact(),
            selection=selection.to_dict(),
            receipt=second.verification,
        )
        is None
    )


def test_foreign_capability_registry_cannot_mint_production_authority() -> None:
    snapshot, selection, benchmark, promotion, _verified = _selection_chain()
    inputs = {
        "catalog_snapshot": _artifact(snapshot.to_dict()),
        "model_selection_receipt": _artifact(selection.to_dict()),
        "benchmark_evidence_receipts": (_artifact(benchmark.to_dict()),),
        "promotion_evidence_receipts": (_artifact(promotion.to_dict()),),
        "verified_evidence_bundle": _serialized_evidence_bundle(
            snapshot, selection, benchmark, promotion
        ),
        "runtime_policy": _policy(),
        "trusted_keys_payload": _trusted_keys_payload(),
        "key_resolver": _key_resolver(),
        "signature_verifier": DeterministicSignatureVerifier(),
        "now": NOW,
    }
    verified = verify_model_runtime_binding_artifact(**inputs)

    def attacker_inputs(**_inputs):
        return verified.to_artifact(), selection.to_dict(), verified.verification

    attacker_issue, _attacker_consume, _attacker_discard = (
        build_verified_runtime_binding_capability_api(attacker_inputs)
    )
    _binding, _selection, _receipt, forged = attacker_issue()

    assert (
        consume_verified_runtime_binding_capability(
            forged,
            binding=verified.to_artifact(),
            selection=selection.to_dict(),
            receipt=verified.verification,
        )
        is None
    )


def test_copied_runtime_capability_token_does_not_replace_issued_identity() -> None:
    snapshot, selection, benchmark, promotion, _verified = _selection_chain()
    verified = verify_model_runtime_binding_artifact(
        catalog_snapshot=_artifact(snapshot.to_dict()),
        model_selection_receipt=_artifact(selection.to_dict()),
        benchmark_evidence_receipts=(_artifact(benchmark.to_dict()),),
        promotion_evidence_receipts=(_artifact(promotion.to_dict()),),
        verified_evidence_bundle=_serialized_evidence_bundle(
            snapshot, selection, benchmark, promotion
        ),
        runtime_policy=_policy(),
        trusted_keys_payload=_trusted_keys_payload(),
        key_resolver=_key_resolver(),
        signature_verifier=DeterministicSignatureVerifier(),
        now=NOW,
    )
    token = object.__getattribute__(
        verified.capability, "_VerifiedRuntimeBindingCapability__token"
    )
    copied = VerifiedRuntimeBindingCapability(token)
    inputs = {
        "binding": verified.to_artifact(),
        "selection": selection.to_dict(),
        "receipt": verified.verification,
    }

    assert consume_verified_runtime_binding_capability(copied, **inputs) is None
    assert (
        consume_verified_runtime_binding_capability(verified.capability, **inputs)
        == verified.verification
    )


def test_runtime_capability_has_no_importable_issuer_or_seal() -> None:
    from modules.ai_intelligence.ai_gateway.src import (
        model_runtime_binding_evidence_dispatch as dispatch,
    )
    from modules.ai_intelligence.ai_gateway.src import (
        model_runtime_binding_evidence_verifier as verifier,
    )
    from modules.ai_intelligence.ai_gateway.src import (
        model_runtime_binding_verified_admission as admission,
    )

    assert not hasattr(dispatch, "_EVIDENCE_ADMISSION_SEAL")
    assert not hasattr(admission, "_CAPABILITIES")
    assert not hasattr(admission, "_issue_verified_runtime_binding_capability")
    assert not hasattr(verifier, "_issue_verified_runtime_binding_capability")


def test_use_time_verifier_rechecks_current_time_and_revocation() -> None:
    snapshot, selection, benchmark, promotion, _verified = _selection_chain()
    bundle = _serialized_evidence_bundle(snapshot, selection, benchmark, promotion)
    trusted = _trusted_keys_payload()
    inputs = {
        "catalog_snapshot": _artifact(snapshot.to_dict()),
        "benchmark_evidence_receipts": (_artifact(benchmark.to_dict()),),
        "promotion_evidence_receipts": (_artifact(promotion.to_dict()),),
        "verified_evidence_bundle": bundle,
        "runtime_policy": _policy(),
        "trusted_keys_payload": trusted,
        "key_resolver": _key_resolver(),
        "signature_verifier": DeterministicSignatureVerifier(),
    }
    persisted = verify_model_runtime_binding_artifact(
        **inputs,
        model_selection_receipt=_artifact(selection.to_dict()),
        now=NOW,
    ).to_artifact()
    verifier = ModelRuntimeBindingUseTimeVerifier(
        **inputs,
        trusted_now_epoch=lambda: NOW,
    )

    capability = verifier.verify(
        binding=persisted,
        selection=_artifact(selection.to_dict()),
    )

    assert capability is not None
    expired = ModelRuntimeBindingUseTimeVerifier(
        **inputs,
        trusted_now_epoch=lambda: NOW + 3_601,
    )
    with pytest.raises(ValueError):
        expired.verify(binding=persisted, selection=selection.to_dict())
    revoked_inputs = {
        **inputs,
        "trusted_keys_payload": {**trusted, "revoked_key_epochs": ["epoch-1"]},
    }
    revoked = ModelRuntimeBindingUseTimeVerifier(
        **revoked_inputs,
        trusted_now_epoch=lambda: NOW,
    )
    with pytest.raises(ValueError):
        revoked.verify(binding=persisted, selection=selection.to_dict())


def test_use_time_verifier_rejects_tampered_persisted_binding() -> None:
    snapshot, selection, benchmark, promotion, _verified = _selection_chain()
    inputs = {
        "catalog_snapshot": _artifact(snapshot.to_dict()),
        "benchmark_evidence_receipts": (_artifact(benchmark.to_dict()),),
        "promotion_evidence_receipts": (_artifact(promotion.to_dict()),),
        "verified_evidence_bundle": _serialized_evidence_bundle(
            snapshot, selection, benchmark, promotion
        ),
        "runtime_policy": _policy(),
        "trusted_keys_payload": _trusted_keys_payload(),
        "key_resolver": _key_resolver(),
        "signature_verifier": DeterministicSignatureVerifier(),
    }
    persisted = verify_model_runtime_binding_artifact(
        **inputs,
        model_selection_receipt=_artifact(selection.to_dict()),
        now=NOW,
    ).to_artifact()
    persisted["principal_model"] = "attacker/model"
    verifier = ModelRuntimeBindingUseTimeVerifier(
        **inputs,
        trusted_now_epoch=lambda: NOW,
    )

    with pytest.raises(ValueError):
        verifier.verify(binding=persisted, selection=selection.to_dict())


def test_resident_bootstrap_builds_verifier_from_runtime_files(tmp_path: Path) -> None:
    snapshot, selection, benchmark, promotion, _verified = _selection_chain()
    runtime_root = tmp_path / "runtime"
    repo_root = tmp_path / "repo"
    runtime_root.mkdir()
    repo_root.mkdir()

    def write(name: str, payload: object) -> Path:
        path = runtime_root / name
        path.write_text(json.dumps(payload, default=str), encoding="utf-8")
        return path

    paths = (
        write("catalog.json", _artifact(snapshot.to_dict())),
        write(
            "benchmarks.json",
            {"benchmark_evidence_receipts": [_artifact(benchmark.to_dict())]},
        ),
        write(
            "promotions.json",
            {"promotion_evidence_receipts": [_artifact(promotion.to_dict())]},
        ),
        write(
            "evidence.json",
            _serialized_evidence_bundle(snapshot, selection, benchmark, promotion),
        ),
        write("policy.json", _policy()),
        write("trusted.json", _trusted_keys_payload()),
    )

    verifier, reasons = build_model_runtime_verifier(
        repo_root=repo_root,
        runtime_root=runtime_root,
        config=ModelRuntimeVerifierConfig(
            *paths,
            verifier_backend="test",
            signature_verifier=DeterministicSignatureVerifier(),
        ),
        trusted_now=lambda: NOW,
        injected=None,
        artifact_generator=object(),
    )

    assert reasons == ()
    assert verifier is not None


def test_tampered_serialized_evidence_cannot_rebuild_promotion_capability() -> None:
    snapshot, selection, benchmark, promotion, _verified = _selection_chain()
    bundle = _serialized_evidence_bundle(snapshot, selection, benchmark, promotion)
    bundle["entries"][0]["benchmark_receipt"]["accepted_count"] = 0

    with pytest.raises(ValueError):
        verify_model_runtime_binding_artifact(
            catalog_snapshot=_artifact(snapshot.to_dict()),
            model_selection_receipt=_artifact(selection.to_dict()),
            benchmark_evidence_receipts=(_artifact(benchmark.to_dict()),),
            promotion_evidence_receipts=(_artifact(promotion.to_dict()),),
            verified_evidence_bundle=bundle,
            runtime_policy=_policy(),
            trusted_keys_payload=_trusted_keys_payload(),
            key_resolver=_key_resolver(),
            signature_verifier=DeterministicSignatureVerifier(),
            now=NOW,
        )
