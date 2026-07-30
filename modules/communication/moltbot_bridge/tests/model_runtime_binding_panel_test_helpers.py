"""Panel evidence fixtures for RedDog model runtime binding tests."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from modules.ai_intelligence.ai_gateway.src.model_panel_signed_evidence import (
    PanelEvidenceSignerRole,
    PanelMemberEvidenceInput,
    build_model_panel_signed_evidence_receipt,
    build_panel_member_evidence_binding,
    build_verified_model_panel_evidence,
    model_panel_signed_evidence_signing_input,
)
from modules.ai_intelligence.ai_gateway.tests.model_signed_evidence_test_helpers import (
    BENCHMARK_PUBLIC_KEY,
    BENCHMARK_FINGERPRINT,
    KEY_EPOCH,
    PROMOTION_PUBLIC_KEY,
    PROMOTION_FINGERPRINT,
    DeterministicSignatureVerifier,
    ModelEvidenceSignerRole,
    StaticModelEvidenceKeyResolver,
    deterministic_signature,
    make_verified_production_evidence,
)


def verified_panel_evidence(
    *,
    snapshot: Any,
    selection: Any,
    benchmarks: tuple[Any, ...],
    promotions: tuple[Any, ...],
    policy: Any,
) -> Any:
    """Build independently signed member and aggregate panel evidence."""

    run_id = "model_combination_benchmark_run:test"
    verified = _verified_member_evidence(
        snapshot, selection, benchmarks, promotions, run_id
    )
    inputs = _member_inputs(selection, verified)
    bindings = _member_bindings(inputs, verified)
    panel_key = "ed25519-pub-v1:test-panel"
    values = _aggregate_values(
        snapshot, selection, policy, bindings, run_id, panel_key
    )
    aggregate = _signed_aggregate(values, panel_key)
    return _verify_panel(
        snapshot, selection, policy, inputs, aggregate, values, panel_key
    )


def _verified_member_evidence(
    snapshot: Any,
    selection: Any,
    benchmarks: tuple[Any, ...],
    promotions: tuple[Any, ...],
    run_id: str,
) -> tuple[Any, ...]:
    return tuple(
        make_verified_production_evidence(
            benchmark,
            promotion,
            catalog_snapshot_id=snapshot.snapshot_id,
            selection_receipt_id=selection.receipt_id,
            benchmark_run_receipt_id=run_id,
        )
        for benchmark, promotion in zip(benchmarks, promotions)
    )


def _member_inputs(
    selection: Any,
    verified: tuple[Any, ...],
) -> tuple[PanelMemberEvidenceInput, ...]:
    return tuple(
        PanelMemberEvidenceInput(
            role=assignment.role,
            model_id=assignment.canonical_model_id,
            provider=assignment.provider,
            benchmark_receipt=item.entries[0].benchmark_receipt,
            promotion_receipt=item.entries[0].promotion_receipt,
            benchmark_signature_receipt=item.entries[0].benchmark_signature_receipt,
            promotion_signature_receipt=item.entries[0].promotion_signature_receipt,
        )
        for assignment, item in zip(selection.role_assignments, verified)
    )


def _member_bindings(
    inputs: tuple[PanelMemberEvidenceInput, ...],
    verified: tuple[Any, ...],
) -> tuple[Any, ...]:
    return tuple(
        build_panel_member_evidence_binding(
            ordinal=index,
            role=item.role,
            model_id=item.model_id,
            provider=item.provider,
            verified_evidence=proof,
        )
        for index, (item, proof) in enumerate(zip(inputs, verified))
    )


def _aggregate_values(
    snapshot: Any,
    selection: Any,
    policy: Any,
    bindings: tuple[Any, ...],
    run_id: str,
    panel_key: str,
) -> dict[str, Any]:
    return {
        "members": bindings,
        "required_roles": selection.requirements.panel_roles,
        "synthesizer_model_id": selection.role_assignments[0].canonical_model_id,
        "synthesizer_role": selection.role_assignments[0].role,
        "catalog_snapshot_id": snapshot.snapshot_id,
        "catalog_snapshot_digest": _content_digest(snapshot.to_dict()),
        "selection_receipt_id": selection.receipt_id,
        "selection_receipt_digest": _content_digest(selection.to_dict()),
        "task_receipt_id": "model_task_set:test",
        "task_receipt_digest": policy.required_task_set_digest,
        "topology_receipt_id": "model_panel_topology:test",
        "topology_receipt_digest": selection.panel_topology_digest,
        "policy_receipt_id": "model_runtime_binding_policy:test",
        "policy_receipt_digest": _content_digest(policy.normalized().to_dict()),
        "runtime_surface_receipt_id": "model_runtime_surface:test",
        "runtime_surface_receipt_digest": _content_digest(
            {"runtime_surface": policy.runtime_surface}
        ),
        "benchmark_run_receipt_id": run_id,
        "signer_role": PanelEvidenceSignerRole.PANEL_AUTHORITY,
        "signer_public_key": panel_key,
        "signer_key_fingerprint": "fingerprint:test-panel",
        "key_epoch": "epoch-test",
        "issued_at": 1_800_000_000,
        "expires_at": 1_800_003_600,
        "nonce": "nonce:test-panel",
    }


def _signed_aggregate(values: dict[str, Any], panel_key: str) -> Any:
    placeholder = build_model_panel_signed_evidence_receipt(
        signature="placeholder",
        **values,
    )
    return build_model_panel_signed_evidence_receipt(
        signature=deterministic_signature(
            panel_key,
            model_panel_signed_evidence_signing_input(placeholder),
        ),
        **values,
    )


def _verify_panel(
    snapshot: Any,
    selection: Any,
    policy: Any,
    inputs: tuple[PanelMemberEvidenceInput, ...],
    aggregate: Any,
    values: dict[str, Any],
    panel_key: str,
) -> Any:
    return build_verified_model_panel_evidence(
        catalog_snapshot=snapshot,
        selection_receipt=selection,
        member_inputs=inputs,
        aggregate_receipt=aggregate,
        runtime_policy=policy,
        task_receipt_id=values["task_receipt_id"],
        topology_receipt_id=values["topology_receipt_id"],
        policy_receipt_id=values["policy_receipt_id"],
        runtime_surface_receipt_id=values["runtime_surface_receipt_id"],
        member_key_resolver=StaticModelEvidenceKeyResolver(
            {
                (
                    ModelEvidenceSignerRole.BENCHMARK_VERIFIER.value,
                    BENCHMARK_FINGERPRINT,
                    KEY_EPOCH,
                ): BENCHMARK_PUBLIC_KEY,
                (
                    ModelEvidenceSignerRole.PROMOTION_AUTHORITY.value,
                    PROMOTION_FINGERPRINT,
                    KEY_EPOCH,
                ): PROMOTION_PUBLIC_KEY,
            }
        ),
        member_signature_verifier=DeterministicSignatureVerifier(),
        panel_key_resolver=StaticModelEvidenceKeyResolver(
            {
                (
                    PanelEvidenceSignerRole.PANEL_AUTHORITY.value,
                    "fingerprint:test-panel",
                    "epoch-test",
                ): panel_key
            }
        ),
        panel_signature_verifier=DeterministicSignatureVerifier(),
        now=1_800_000_000,
    )


def _content_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()
