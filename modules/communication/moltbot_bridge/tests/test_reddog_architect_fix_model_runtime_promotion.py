"""Focused model-runtime lineage tests for architect FIX promotion."""

from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import (
    canonical_model_runtime_binding_digest,
)
from modules.communication.moltbot_bridge.src import (
    reddog_architect_fix_signed_wsp15_work_order_promotion as promotion,
)
from modules.communication.moltbot_bridge.tests.model_runtime_binding_receipt_test_helpers import (
    model_selection_and_runtime_binding_receipts,
)
from modules.communication.moltbot_bridge.tests.test_reddog_architect_fix_signed_wsp15_work_order_promotion import (
    _promote,
)


def test_promotes_runtime_binding_into_queue_claim_and_authority_profile() -> None:
    selection, runtime = model_selection_and_runtime_binding_receipts(
        runtime_surface="reddog_artifact_generation",
        task_family="reddog_architect_fix_promotion",
    )
    result, store = _promote(
        model_selection_receipt=selection,
        model_runtime_binding_receipt=runtime,
    )
    assert result.accepted is True, result.rejection_reasons
    assert result.receipt is not None and result.authority_profile is not None
    assert result.receipt.model_runtime_binding_receipt_id == runtime["receipt_id"]
    assert result.receipt.model_runtime_binding_digest == canonical_model_runtime_binding_digest(runtime)
    verification_id = result.receipt.model_runtime_binding_verification_receipt_id
    verification_digest = result.receipt.model_runtime_binding_verification_digest
    assert verification_id and verification_id.startswith("model_runtime_binding_verification:")
    assert verification_digest and verification_digest.startswith("sha256:")
    profile = result.authority_profile
    assert profile["model_runtime_binding_receipt_id"] == runtime["receipt_id"]
    assert profile["model_runtime_binding_receipt"]["receipt_id"] == runtime["receipt_id"]
    assert profile["model_runtime_binding_principal_model"] == runtime["principal_model"]
    assert profile["model_runtime_binding_verification_receipt_id"] == verification_id
    assert profile["operational_context_binding"]["model_runtime_binding_receipt_id"] == runtime["receipt_id"]
    assert profile["operational_context_binding"]["model_runtime_binding_receipt"]["receipt_id"] == runtime["receipt_id"]
    snapshot = store.load()
    claim, queue_item = snapshot["worker_claims"][0], snapshot["wre_queue_items"][0]
    assert claim["model_runtime_binding_receipt_id"] == runtime["receipt_id"]
    assert queue_item["model_runtime_binding_receipt_id"] == runtime["receipt_id"]
    assert queue_item["model_runtime_binding_digest"] == canonical_model_runtime_binding_digest(runtime)
    assert queue_item["model_runtime_binding_verification_receipt_id"] == verification_id
    assert queue_item["model_runtime_binding_verification_digest"] == verification_digest
    assert f"model_runtime_binding:{runtime['receipt_id']}" in queue_item["evidence_refs"]
    assert snapshot["architect_fix_promotions"][0]["model_runtime_binding_receipt_id"] == runtime["receipt_id"]


def test_rejects_non_artifact_generation_runtime_surface() -> None:
    selection, runtime = model_selection_and_runtime_binding_receipts(
        runtime_surface="reddog_fusion",
        task_family="reddog_architect_fix_promotion",
    )
    result, store = _promote(
        model_selection_receipt=selection,
        model_runtime_binding_receipt=runtime,
    )
    assert result.accepted is False
    assert promotion.ArchitectFixPromotionReason.MODEL_RUNTIME_BINDING_INVALID in result.rejection_reasons
    assert store.load()["wre_queue_items"] == []


def test_promotes_canonical_panel_topology_runtime_binding() -> None:
    selection, runtime = model_selection_and_runtime_binding_receipts(
        runtime_surface="reddog_artifact_generation",
        task_family="reddog_architect_fix_promotion",
        panel_model_ids=("anthropic/claude-sonnet-4.5",),
    )

    result, store = _promote(
        model_selection_receipt=selection,
        model_runtime_binding_receipt=runtime,
    )

    assert result.accepted is True, result.rejection_reasons
    assert selection["panel_topology_digest"].startswith("panel_topology:")
    assert store.load()["wre_queue_items"][0]["model_runtime_binding_receipt_id"] == runtime["receipt_id"]
