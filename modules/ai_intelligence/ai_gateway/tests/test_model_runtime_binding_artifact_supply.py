"""Tests for REDDOG_MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

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
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import (
    VerifiedRuntimeBindingCapability,
    consume_verified_runtime_binding_capability,
    rehydrate_runtime_binding_verification_receipt,
    verification_receipt_digest,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_evidence_verifier import (
    verify_model_runtime_binding_artifact,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_capability import (
    build_verified_runtime_binding_capability_api,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_use_time_verifier import (
    ModelRuntimeBindingUseTimeVerifier,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_panel_rehydration import (
    PANEL_EVIDENCE_BUNDLE_SCHEMA_VERSION,
)
from modules.ai_intelligence.ai_gateway.src.model_panel_signed_evidence import (
    PanelEvidenceSignerRole,
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
from modules.ai_intelligence.ai_gateway.tests.test_model_panel_signed_evidence import (
    NOW as PANEL_NOW,
    PANEL_PUBLIC_KEY,
    _case as _panel_case,
)
from modules.communication.moltbot_bridge.src.reddog_model_runtime_verifier_bootstrap import (
    ModelRuntimeVerifierConfig,
    build_model_runtime_verifier,
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
            (
                ModelEvidenceSignerRole.BENCHMARK_VERIFIER.value,
                BENCHMARK_FINGERPRINT,
                "epoch-1",
            ): BENCHMARK_PUBLIC_KEY,
            (
                ModelEvidenceSignerRole.PROMOTION_AUTHORITY.value,
                PROMOTION_FINGERPRINT,
                "epoch-1",
            ): PROMOTION_PUBLIC_KEY,
        }
    )


def _trusted_keys_payload():
    return {
        "trusted_public_keys": _trusted_key_entries(
            {
                (
                    ModelEvidenceSignerRole.BENCHMARK_VERIFIER.value,
                    BENCHMARK_FINGERPRINT,
                    "epoch-1",
                ): BENCHMARK_PUBLIC_KEY,
                (
                    ModelEvidenceSignerRole.PROMOTION_AUTHORITY.value,
                    PROMOTION_FINGERPRINT,
                    "epoch-1",
                ): PROMOTION_PUBLIC_KEY,
            }
        )
    }


def _trusted_key_entries(keys):
    return [
        {
            "signer_role": role,
            "signer_key_fingerprint": fingerprint,
            "key_epoch": epoch,
            "public_key": public_key,
        }
        for (role, fingerprint, epoch), public_key in keys.items()
    ]


def _artifact(value):
    return json.loads(json.dumps(value, sort_keys=True))


def _serialized_panel_supply_case():
    case = _panel_case()
    aggregate = case["aggregate"]
    bundle = {
        "schema_version": PANEL_EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "catalog_snapshot_id": case["snapshot"].snapshot_id,
        "selection_receipt_id": case["selection"].receipt_id,
        "benchmark_run_receipt_id": aggregate.benchmark_run_receipt_id,
        "entries": [
            {
                "role": item.role,
                "model_id": item.model_id,
                "provider": item.provider,
                "benchmark_receipt": item.benchmark_receipt.to_dict(),
                "promotion_receipt": item.promotion_receipt.to_dict(),
                "benchmark_signature_receipt": (
                    item.benchmark_signature_receipt.to_dict()
                ),
                "promotion_signature_receipt": (
                    item.promotion_signature_receipt.to_dict()
                ),
            }
            for item in case["member_inputs"]
        ],
        "aggregate_receipt": aggregate.to_dict(),
    }
    keys = {
        (
            ModelEvidenceSignerRole.BENCHMARK_VERIFIER.value,
            BENCHMARK_FINGERPRINT,
            "epoch-1",
        ): BENCHMARK_PUBLIC_KEY,
        (
            ModelEvidenceSignerRole.PROMOTION_AUTHORITY.value,
            PROMOTION_FINGERPRINT,
            "epoch-1",
        ): PROMOTION_PUBLIC_KEY,
        (
            PanelEvidenceSignerRole.PANEL_AUTHORITY.value,
            aggregate.signer_key_fingerprint,
            aggregate.key_epoch,
        ): PANEL_PUBLIC_KEY,
    }
    policy = {
        **case["policy"].to_dict(),
        "panel_context_receipt_ids": {
            "task_receipt_id": aggregate.task_receipt_id,
            "topology_receipt_id": aggregate.topology_receipt_id,
            "policy_receipt_id": aggregate.policy_receipt_id,
            "runtime_surface_receipt_id": aggregate.runtime_surface_receipt_id,
        },
    }
    return case, bundle, keys, policy


def test_runtime_supplier_verifies_serialized_panel_evidence(tmp_path: Path) -> None:
    case, bundle, keys, policy = _serialized_panel_supply_case()
    output = tmp_path / "runtime" / "panel_model_runtime_binding_receipt.json"

    result = run_reddog_model_runtime_binding_artifact_supply(
        repo_root=REPO_ROOT,
        catalog_snapshot=_artifact(case["snapshot"].to_dict()),
        model_selection_receipt=_artifact(case["selection"].to_dict()),
        benchmark_evidence_receipts=tuple(
            _artifact(item.to_dict()) for item in case["benchmarks"]
        ),
        promotion_evidence_receipts=tuple(
            _artifact(item.to_dict()) for item in case["promotions"]
        ),
        verified_evidence_bundle=_artifact(bundle),
        trusted_keys_payload={"trusted_public_keys": _trusted_key_entries(keys)},
        runtime_policy=_artifact(policy),
        output_path=output,
        key_resolver=StaticModelEvidenceKeyResolver(keys),
        signature_verifier=DeterministicSignatureVerifier(),
        now=PANEL_NOW,
    )

    assert result.accepted is True
    artifact = json.loads(output.read_text(encoding="utf-8"))
    verification = rehydrate_runtime_binding_verification_receipt(
        artifact["verification_receipt"]
    )
    assert verification.selection_mode == "panel"
    assert verification.panel_aggregate_receipt_id == case["aggregate"].receipt_id
    assert tuple(artifact["panel_models"]) == tuple(
        case["selection"].selected_model_ids[1:]
    )


@pytest.mark.parametrize(
    ("mutation", "revoked_field"),
    (
        ("aggregate", None),
        ("context", None),
        (None, "revoked_panel_key_epochs"),
        (None, "revoked_member_key_epochs"),
    ),
)
def test_runtime_supplier_rejects_tampered_or_revoked_panel_evidence(
    tmp_path: Path,
    mutation: str | None,
    revoked_field: str | None,
) -> None:
    case, bundle, keys, policy = _serialized_panel_supply_case()
    if mutation == "aggregate":
        bundle["aggregate_receipt"]["required_roles"][0] = "attacker"
    if mutation == "context":
        policy["panel_context_receipt_ids"]["task_receipt_id"] = "task:attacker"
    trusted = {"trusted_public_keys": _trusted_key_entries(keys)}
    if revoked_field:
        trusted[revoked_field] = ["epoch-1"]
    result = run_reddog_model_runtime_binding_artifact_supply(
        repo_root=REPO_ROOT,
        catalog_snapshot=_artifact(case["snapshot"].to_dict()),
        model_selection_receipt=_artifact(case["selection"].to_dict()),
        benchmark_evidence_receipts=tuple(
            _artifact(item.to_dict()) for item in case["benchmarks"]
        ),
        promotion_evidence_receipts=tuple(
            _artifact(item.to_dict()) for item in case["promotions"]
        ),
        verified_evidence_bundle=_artifact(bundle),
        trusted_keys_payload=trusted,
        runtime_policy=_artifact(policy),
        output_path=tmp_path / "runtime" / "rejected.json",
        key_resolver=StaticModelEvidenceKeyResolver(keys),
        signature_verifier=DeterministicSignatureVerifier(),
        now=PANEL_NOW,
    )

    assert result.accepted is False
    assert ModelRuntimeBindingArtifactSupplyReason.EVIDENCE_INVALID in (
        result.rejection_reasons
    )
    assert not (tmp_path / "runtime" / "rejected.json").exists()


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
        trusted_keys_payload=_trusted_keys_payload(),
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
    verification = rehydrate_runtime_binding_verification_receipt(
        receipt["verification_receipt"]
    )
    assert verification.runtime_binding_receipt_id == receipt["receipt_id"]
    assert verification.selection_receipt_id == selection.receipt_id
    assert verification_receipt_digest(verification).startswith("sha256:")
    assert result.no_model_call_performed is True
    assert result.no_holoindex_reindex_performed is True


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


def test_runtime_supplier_rejects_process_local_typed_evidence_object(tmp_path: Path) -> None:
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
    assert ModelRuntimeBindingArtifactSupplyReason.EVIDENCE_INVALID in result.rejection_reasons


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
        write("benchmarks.json", {
            "benchmark_evidence_receipts": [_artifact(benchmark.to_dict())]
        }),
        write("promotions.json", {
            "promotion_evidence_receipts": [_artifact(promotion.to_dict())]
        }),
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


def test_runtime_supplier_rejects_serialized_evidence_without_signature_gate(tmp_path: Path) -> None:
    snapshot, selection, benchmark, promotion, _verified = _selection_chain()

    result = run_reddog_model_runtime_binding_artifact_supply(
        repo_root=REPO_ROOT,
        catalog_snapshot=_artifact(snapshot.to_dict()),
        model_selection_receipt=_artifact(selection.to_dict()),
        benchmark_evidence_receipts=(_artifact(benchmark.to_dict()),),
        promotion_evidence_receipts=(_artifact(promotion.to_dict()),),
        verified_evidence_bundle=_serialized_evidence_bundle(snapshot, selection, benchmark, promotion),
        trusted_keys_payload=_trusted_keys_payload(),
        runtime_policy=_policy(),
        output_path=tmp_path / "runtime" / "model_runtime_binding_receipt.json",
    )

    assert result.accepted is False
    assert result.status == MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY_REJECT
    assert ModelRuntimeBindingArtifactSupplyReason.KEY_RESOLVER_MISSING in result.rejection_reasons
    assert ModelRuntimeBindingArtifactSupplyReason.SIGNATURE_VERIFIER_MISSING in result.rejection_reasons


def test_runtime_supplier_rejects_binding_policy_mismatch_without_writing(tmp_path: Path) -> None:
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
        runtime_policy=_policy(required_task_set_digest="sha256:wrong"),
        output_path=output,
        key_resolver=_key_resolver(),
        signature_verifier=DeterministicSignatureVerifier(),
        now=NOW,
    )

    assert result.accepted is False
    assert ModelRuntimeBindingArtifactSupplyReason.RUNTIME_BINDING_REJECTED in result.rejection_reasons
    assert "task_set_digest_mismatch" in result.rejection_reasons
    assert not output.exists()


def test_runtime_supplier_rejects_output_inside_repo() -> None:
    snapshot, selection, benchmark, promotion, _verified = _selection_chain()

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
        output_path=REPO_ROOT / "model_runtime_binding_receipt.json",
        key_resolver=_key_resolver(),
        signature_verifier=DeterministicSignatureVerifier(),
        now=NOW,
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
