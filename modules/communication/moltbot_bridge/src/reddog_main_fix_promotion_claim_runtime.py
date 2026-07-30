"""Bound one main-process FIX promotion to its durable AgentDB claim."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_agentdb_fix_promotion_claim_fence import (
    execute_with_fix_promotion_claim_fence,
)
from modules.communication.moltbot_bridge.src.reddog_agentdb_fix_promotion_claim_record import (
    RedDogFixPromotionClaim,
)
from modules.communication.moltbot_bridge.src.reddog_agentdb_fix_promotion_claim_store import (
    AgentDbFixPromotionClaimStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_binding_profile import (
    resident_queue_runtime_root_path,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MainFixPromotionRuntimeInputs:
    work_state_path: Optional[str]
    architect_determination_path: Optional[str]
    model_selection_receipt_path: Optional[str]
    model_runtime_binding_receipt_path: Optional[str]
    model_runtime_binding_receipt_path_supplied: bool
    memex_supply_receipt_path: Optional[str]
    authority_profile_source_path: Optional[str]
    authority_profile_path: Optional[str]
    active_authority_profile_path: Optional[str]
    holoindex_receipt_path: Optional[str]


def run_claim_bound_fix_promotion_preflight(
    *,
    repo_root: Path,
    environment: Mapping[str, str],
    inputs: MainFixPromotionRuntimeInputs,
    durable_claim: RedDogFixPromotionClaim | None,
    durable_claim_store: AgentDbFixPromotionClaimStore | None,
) -> bool:
    required = _required_inputs_present(inputs)
    raw_requested = environment.get("REDDOG_ARCHITECT_FIX_PROMOTION_RUNTIME")
    if not (raw_requested == "1" or (raw_requested is None and required)):
        logger.info("[REDDOG-FIX-PROMOTION] Startup promotion bridge disabled")
        return True
    enforced = environment.get("REDDOG_ARCHITECT_FIX_PROMOTION_ENFORCED", "0") != "0"
    if _paths_alias(inputs.authority_profile_path, inputs.active_authority_profile_path):
        print(
            "[REDDOG-FIX-PROMOTION] preflight="
            f"{'FAIL' if enforced else 'WARN'} "
            "reason=inert_profile_aliases_active_authority_profile"
        )
        return not enforced
    if durable_claim and (
        durable_claim_store is None or not durable_claim_store.renew(durable_claim)
    ):
        print("[REDDOG-FIX-CLAIM] preflight=WARN reason=promotion_claim_lease_lost")
        return not enforced
    try:
        result = _run_promotion(
            repo_root,
            environment,
            inputs,
            durable_claim,
            durable_claim_store,
        )
    except Exception as exc:
        logger.error("[REDDOG-FIX-PROMOTION] Startup promotion failed: %s", exc)
        print(
            f"[REDDOG-FIX-PROMOTION] preflight={'FAIL' if enforced else 'WARN'} "
            f"error={type(exc).__name__}"
        )
        return not enforced
    return _finish_promotion(result, inputs, durable_claim, durable_claim_store, enforced)


def _run_promotion(repo_root, environment, inputs, claim, store):
    from modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap import (
        run_reddog_main_architect_fix_promotion_bootstrap,
    )
    from modules.communication.moltbot_bridge.src.reddog_model_runtime_verifier_bootstrap import (
        ModelRuntimeVerifierConfig,
    )

    fence_executor = None
    if claim is not None and store is not None:
        def fence_executor(operation):
            return execute_with_fix_promotion_claim_fence(
                store, claim, operation
            )
    return run_reddog_main_architect_fix_promotion_bootstrap(
        repo_root=repo_root,
        runtime_root=resident_queue_runtime_root_path(environment, repo_root),
        work_state_path=inputs.work_state_path,
        architect_determination_path=inputs.architect_determination_path,
        model_selection_receipt_path=inputs.model_selection_receipt_path,
        model_runtime_binding_receipt_path=(
            inputs.model_runtime_binding_receipt_path
            if inputs.model_runtime_binding_receipt_path_supplied
            else None
        ),
        model_runtime_verifier_config=ModelRuntimeVerifierConfig(
            catalog_path=environment.get("REDDOG_MODEL_CATALOG_SNAPSHOT_PATH"),
            benchmarks_path=environment.get("REDDOG_MODEL_BENCHMARK_EVIDENCE_RECEIPTS_PATH"),
            promotions_path=environment.get("REDDOG_MODEL_PROMOTION_EVIDENCE_RECEIPTS_PATH"),
            evidence_path=environment.get("REDDOG_MODEL_PRODUCTION_EVIDENCE_BUNDLE_PATH"),
            policy_path=environment.get("REDDOG_MODEL_RUNTIME_BINDING_POLICY_PATH"),
            trusted_keys_path=environment.get("REDDOG_MODEL_EVIDENCE_TRUSTED_KEYS_PATH"),
        ),
        memex_supply_receipt_path=inputs.memex_supply_receipt_path,
        authority_profile_source_path=inputs.authority_profile_source_path,
        authority_profile_output_path=inputs.authority_profile_path,
        holoindex_receipt_path=inputs.holoindex_receipt_path,
        worker_id=environment.get(
            "REDDOG_ARCHITECT_FIX_PROMOTION_WORKER_ID",
            "reddog-main-architect-fix-promotion",
        ),
        promotion_claim_fence_executor=fence_executor,
    )


def _finish_promotion(result, inputs, claim, store, enforced):
    status = "PASS" if result.accepted else "WARN"
    reasons = ",".join(result.rejection_reasons) or "(none)"
    print(
        f"[REDDOG-FIX-PROMOTION] preflight={status} status={result.status} "
        f"queue_item={result.queue_item_id or '(none)'} "
        f"selected_slice={result.selected_slice or '(none)'} reasons={reasons}"
    )
    if result.accepted and result.authority_profile_path:
        import os

        os.environ["REDDOG_ARCHITECT_FIX_INERT_PROFILE_PATH"] = result.authority_profile_path
        print(
            f"[REDDOG-FIX-PROMOTION] receipt={result.promotion_receipt_id} "
            f"revision={result.committed_revision} authority=INERT"
        )
        return True
    if claim is not None and store is not None:
        store.release(claim)
    if enforced:
        print("[REDDOG-FIX-PROMOTION] Startup blocked by REDDOG_ARCHITECT_FIX_PROMOTION_ENFORCED=1")
        return False
    return True


def _required_inputs_present(inputs: MainFixPromotionRuntimeInputs) -> bool:
    return all(
        str(value or "").strip()
        for value in (
            inputs.work_state_path,
            inputs.architect_determination_path,
            inputs.model_selection_receipt_path,
            inputs.memex_supply_receipt_path,
            inputs.authority_profile_source_path,
            inputs.holoindex_receipt_path,
        )
    ) and bool(inputs.authority_profile_path)


def _paths_alias(first: str | None, second: str | None) -> bool:
    return bool(
        first
        and second
        and Path(first).resolve() == Path(second).resolve()
    )


__all__ = [
    "MainFixPromotionRuntimeInputs",
    "run_claim_bound_fix_promotion_preflight",
]
