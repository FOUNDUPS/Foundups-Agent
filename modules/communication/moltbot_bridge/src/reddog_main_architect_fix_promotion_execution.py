"""Bounded locked execution for architect FIX promotion bootstrap."""

from __future__ import annotations

from holo_index.freshness_receipt import load_freshness_receipt
from holo_index.query_receipt import generation_binding_from_receipt

from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_publication import (
    AtomicArchitectFixPromotionPublisher,
)
from modules.communication.moltbot_bridge.src.reddog_architect_fix_signed_wsp15_work_order_promotion import (
    ARCHITECT_FIX_WSP15_PROMOTION_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    AtomicJsonAuthorityRuntimeStore,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
)


def run_locked_promotion(inputs):
    """Validate locked HoloIndex ownership, then execute one promotion."""

    from modules.communication.moltbot_bridge.src import (
        reddog_main_architect_fix_promotion_bootstrap as bootstrap,
    )

    with runtime_operation_lock(str(inputs.root) + ".architect-fix-promotion"):
        try:
            receipt = load_freshness_receipt(inputs.holoindex_file)
        except Exception:
            return bootstrap._not_ready(("malformed_holoindex_freshness_receipt",))
        repo_head = bootstrap.read_git_head_sha(inputs.root)
        owner = generation_binding_from_receipt(
            receipt, receipt_path=inputs.holoindex_file
        )
        try:
            route = bootstrap.resolve_query_replica_owner_route(
                canonical_repo_root=inputs.root,
                canonical_ssd_path=receipt.ssd_path,
                environment=inputs.environment,
            )
        except Exception:
            return bootstrap._not_ready(("holoindex_query_replica_route_not_current",))
        if not bootstrap.verify_reddog_holoindex_owner_binding(
            repo_root=inputs.root,
            expected_repo_head_sha=repo_head,
            expected_generation_id=receipt.generation_id,
            expected_receipt_digest=str(owner.get("freshness_receipt_digest") or ""),
            query_replica_route=route,
        ):
            return bootstrap._not_ready(("holoindex_owner_binding_not_current",))
        return _run_profile_transaction(inputs, repo_head, receipt)


def _run_profile_transaction(inputs, repo_head, holoindex_receipt):
    from modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap import (
        _not_ready,
    )

    store = AtomicJsonAuthorityRuntimeStore(
        inputs.work_state_file,
        allowed_root=inputs.runtime_root,
        repo_root=inputs.root,
    )
    publisher = AtomicArchitectFixPromotionPublisher(
        repo_root=inputs.root,
        runtime_root=inputs.runtime_root,
        authority_profile_path=inputs.output_path,
        work_state_store=store,
    )

    def operation(fence=None):
        return _recover_and_promote(
            inputs, store, publisher, repo_head, holoindex_receipt, fence
        )

    try:
        result = (
            inputs.promotion_claim_fence_executor(operation)
            if inputs.promotion_claim_fence_executor
            else operation()
        )
    except Exception as exc:
        return _not_ready(
            ("architect_fix_promotion_claim_fence_rejected", exc.__class__.__name__)
        )
    if not result.accepted:
        return _not_ready(
            list(result.rejection_reasons or ("architect_fix_promotion_rejected",))
        )
    return _applied_result(result, inputs.output_path)


def _recover_and_promote(inputs, store, publisher, repo_head, holo_receipt, fence):
    from modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap import (
        _not_ready,
    )

    try:
        publisher.recover()
    except Exception as exc:
        return _not_ready(
            ("architect_fix_publication_recovery_failed", exc.__class__.__name__)
        )
    return _promote_with_fence(inputs, store, publisher, repo_head, holo_receipt, fence)


def _promote_with_fence(inputs, store, publisher, repo_head, holo_receipt, fence):
    from modules.communication.moltbot_bridge.src import (
        reddog_main_architect_fix_promotion_bootstrap as bootstrap,
    )

    return bootstrap.promote_reddog_architect_fix_to_signed_wsp15_work_order(
        architect_determination=inputs.determination,
        work_state_store=store,
        authority_profile=inputs.authority_profile,
        model_selection_receipt=inputs.model_selection,
        model_runtime_binding_receipt=inputs.model_runtime_binding,
        model_runtime_binding_verification_capability=(
            inputs.model_runtime_binding_verification_capability
        ),
        memex_supply_receipt=inputs.memex_supply,
        proposal_authenticity_attestation=inputs.proposal_attestation,
        signer_runtime_config=inputs.signer_runtime_config,
        principal_key_resolver=inputs.principal_key_resolver,
        current_proposal_revoked_key_epochs=inputs.revoked_key_epochs,
        worker_id=inputs.worker_id,
        now_iso=inputs.now_iso,
        current_repo_head_sha=repo_head,
        current_holoindex_receipt=holo_receipt,
        authority_profile_publication_publisher=publisher.publish,
        agentdb_fix_promotion_claim_fence=fence,
    )


def _applied_result(result, output_path):
    from modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap import (
        REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_APPLIED,
        RedDogMainArchitectFixPromotionBootstrapResult,
        _not_ready,
    )

    if (
        result.status != ARCHITECT_FIX_WSP15_PROMOTION_ACCEPT
        or result.authority_profile is None
        or result.receipt is None
    ):
        return _not_ready(("architect_fix_promotion_missing_profile",))
    return RedDogMainArchitectFixPromotionBootstrapResult(
        accepted=True,
        status=REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_APPLIED,
        promotion_receipt_id=result.receipt.promotion_receipt_id,
        queue_item_id=result.receipt.queue_item_id,
        claim_id=result.receipt.claim_id,
        selected_slice=result.receipt.selected_slice,
        authority_profile_path=str(output_path),
        committed_revision=result.receipt.committed_revision,
        rejection_reasons=(),
    )


__all__ = ["run_locked_promotion"]
