"""Shared model-bound resident queue test inputs."""

from __future__ import annotations

from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import (
    canonical_model_runtime_binding_digest,
    verification_receipt_digest,
    verified_runtime_binding_receipt,
)
from modules.communication.moltbot_bridge.tests.model_runtime_binding_receipt_test_helpers import (
    model_selection_and_runtime_binding_receipts,
)
from modules.communication.moltbot_bridge.tests.test_reddog_main_resident_queue_serial_loop_bootstrap import (
    PILOT_OPERATION,
    RUNTIME_SURFACE_ARTIFACT_GENERATION,
    _mapping_digest,
    _pilot_allowed_paths,
    _pilot_bounded_worker_plan,
    _profile,
    _snapshot,
    _work_order,
)


def model_bound_queue_inputs(
    principal_public: str,
    reddog_public: str,
    overrides: dict,
) -> tuple[dict, dict, dict]:
    selection, binding = model_selection_and_runtime_binding_receipts(
        runtime_surface=RUNTIME_SURFACE_ARTIFACT_GENERATION
    )
    verification = verified_runtime_binding_receipt(binding)
    assert verification is not None
    return (
        model_bound_snapshot(selection, binding, verification),
        model_bound_profile(
            principal_public,
            reddog_public,
            selection,
            binding,
            verification,
            overrides,
        ),
        model_bound_work_order(selection, binding, verification, overrides),
    )


def model_bound_snapshot(selection, binding, verification) -> dict:
    snapshot = _snapshot(requested_operation=PILOT_OPERATION)
    queue = snapshot["wre_queue_items"][0]
    claim = snapshot["worker_claims"][0]
    queue.update(_model_lineage(selection, binding, verification))
    claim.update(
        {
            "model_selection_receipt_id": selection["receipt_id"],
            "model_runtime_binding_receipt_id": binding["receipt_id"],
            "model_runtime_binding_verification_receipt_id": verification.receipt_id,
        }
    )
    queue["evidence_refs"].extend(
        (
            f"model_selection:{selection['receipt_id']}",
            f"model_runtime_binding:{binding['receipt_id']}",
            f"model_runtime_binding_verification:{verification.receipt_id}",
        )
    )
    return snapshot


def model_bound_profile(
    principal_public,
    reddog_public,
    selection,
    binding,
    verification,
    overrides,
) -> dict:
    return _profile(
        principal_public_key=principal_public,
        reddog_public_key=reddog_public,
        requested_operation=PILOT_OPERATION,
        allowed_paths=_pilot_allowed_paths(),
        denied_paths=overrides["denied_paths"],
        model_selection_receipt=selection,
        model_runtime_binding_receipt=binding,
        **_model_lineage(selection, binding, verification),
    )


def model_bound_work_order(
    selection,
    binding,
    verification,
    overrides,
) -> dict:
    return _work_order(
        **overrides,
        bounded_worker_plan=_pilot_bounded_worker_plan(),
        model_selection_receipt=selection,
        model_runtime_binding_receipt=binding,
        **_model_lineage(selection, binding, verification),
    )


def _model_lineage(selection, binding, verification) -> dict[str, str]:
    return {
        "model_selection_receipt_id": selection["receipt_id"],
        "model_selection_digest": _mapping_digest(selection),
        "model_runtime_binding_receipt_id": binding["receipt_id"],
        "model_runtime_binding_digest": canonical_model_runtime_binding_digest(
            binding
        ),
        "model_runtime_binding_verification_receipt_id": verification.receipt_id,
        "model_runtime_binding_verification_digest": verification_receipt_digest(
            verification
        ),
    }


def runtime_binding_refs() -> dict[str, str]:
    return {
        "model_runtime_binding_receipt_id": "reddog_model_runtime_binding:abc123",
        "model_runtime_binding_digest": "sha256:" + "a" * 64,
        "model_runtime_binding_verification_receipt_id": (
            "model_runtime_binding_verification:" + "b" * 64
        ),
        "model_runtime_binding_verification_digest": "sha256:" + "c" * 64,
    }


__all__ = [
    "model_bound_profile",
    "model_bound_queue_inputs",
    "model_bound_snapshot",
    "model_bound_work_order",
    "runtime_binding_refs",
]
