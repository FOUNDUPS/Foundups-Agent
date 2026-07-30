"""Focused model-runtime authority-profile materialization coverage."""

from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import (
    canonical_model_runtime_binding_digest,
    verification_receipt_digest,
    verified_runtime_binding_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_main_resident_queue_serial_loop_bootstrap import (
    _materialize_work_orders_from_authority_profile,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_0102_audit_worker_runtime import (
    RUNTIME_SURFACE_READONLY_AUDIT,
)
from modules.communication.moltbot_bridge.tests.model_runtime_binding_receipt_test_helpers import (
    model_selection_and_runtime_binding_receipts,
)
from modules.communication.moltbot_bridge.tests.test_reddog_main_resident_queue_serial_loop_bootstrap import (
    NOW,
    WORK_ORDER_ID,
    _mapping_digest,
    _profile,
    _snapshot,
)


def test_authority_profile_materializer_carries_model_runtime_binding_receipt() -> None:
    selection, binding = model_selection_and_runtime_binding_receipts(
        runtime_surface=RUNTIME_SURFACE_READONLY_AUDIT
    )
    verification = verified_runtime_binding_receipt(binding)
    assert verification is not None
    lineage = {
        "model_selection_receipt_id": selection["receipt_id"],
        "model_selection_digest": _mapping_digest(selection),
        "model_runtime_binding_receipt_id": binding["receipt_id"],
        "model_runtime_binding_digest": canonical_model_runtime_binding_digest(binding),
        "model_runtime_binding_verification_receipt_id": verification.receipt_id,
        "model_runtime_binding_verification_digest": verification_receipt_digest(verification),
    }
    snapshot = _snapshot()
    queue_item, claim = snapshot["wre_queue_items"][0], snapshot["worker_claims"][0]
    queue_item.update(lineage)
    claim.update({key: lineage[key] for key in (
        "model_selection_receipt_id",
        "model_runtime_binding_receipt_id",
        "model_runtime_binding_verification_receipt_id",
    )})
    queue_item["evidence_refs"].extend((
        f"model_selection:{selection['receipt_id']}",
        f"model_runtime_binding:{binding['receipt_id']}",
        f"model_runtime_binding_verification:{verification.receipt_id}",
    ))
    profile = _profile(
        model_selection_receipt=selection,
        model_runtime_binding_receipt=binding,
        model_runtime_binding_verification_receipt=verification.to_dict(),
        **lineage,
    )
    work_orders, reasons = _materialize_work_orders_from_authority_profile(
        snapshot=snapshot,
        authority_profile=profile,
        requested_queue_item_id="queue-1",
        now_iso=NOW,
    )
    assert reasons == () and work_orders is not None
    work_order = work_orders[WORK_ORDER_ID]
    assert work_order["model_runtime_binding_receipt_id"] == binding["receipt_id"]
    assert work_order["model_runtime_binding_digest"] == lineage["model_runtime_binding_digest"]
    assert work_order["model_runtime_binding_receipt"]["receipt_id"] == binding["receipt_id"]
    assert work_order["model_runtime_binding_verification_receipt_id"] == verification.receipt_id
    assert work_order["model_runtime_binding_verification_digest"] == lineage[
        "model_runtime_binding_verification_digest"
    ]
    assert work_order["model_runtime_binding_verification_receipt"]["receipt_id"] == verification.receipt_id
