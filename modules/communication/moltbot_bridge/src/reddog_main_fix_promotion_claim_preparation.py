"""Prepare the optional AgentDB FIX claim before startup suppliers run."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_agentdb_fix_promotion_claim import (
    AgentDbFixPromotionClaimStore,
    RedDogFixPromotionClaim,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_binding_profile import (
    resident_queue_runtime_flag_enabled,
)


@dataclass(frozen=True)
class MainFixPromotionClaimPreparation:
    requested: bool
    continue_pipeline: bool
    startup_result: bool
    claim: Optional[RedDogFixPromotionClaim]
    store: Optional[AgentDbFixPromotionClaimStore]
    architect_determination_path: Optional[str]
    memex_supply_receipt_path: Optional[str]
    rejection_reasons: tuple[str, ...] = ()


def prepare_reddog_main_fix_promotion_claim(
    *,
    repo_root: Path | str,
    environment: Mapping[str, str],
    architect_determination_path: Path | str | None,
    memex_supply_receipt_path: Path | str | None,
) -> MainFixPromotionClaimPreparation:
    requested = resident_queue_runtime_flag_enabled(
        environment, "REDDOG_AGENTDB_FIX_PROMOTION_CLAIM"
    )
    if not requested:
        return _preparation(False, True, True)
    try:
        from modules.communication.moltbot_bridge.src.reddog_main_fix_promotion_claim_handoff import (
            run_reddog_main_fix_promotion_claim_handoff,
        )

        handoff = run_reddog_main_fix_promotion_claim_handoff(
            repo_root=repo_root,
            architect_determination_output_path=architect_determination_path,
            memex_supply_receipt_output_path=memex_supply_receipt_path,
            worker_id=environment.get(
                "REDDOG_ARCHITECT_FIX_PROMOTION_WORKER_ID",
                "reddog-main-architect-fix-promotion",
            ),
        )
    except Exception as exc:
        print(f"[REDDOG-FIX-CLAIM] preflight=WARN error={type(exc).__name__}")
        return _preparation(True, False, not _enforced(environment), ("claim_runtime_error",))
    if not handoff.accepted or handoff.claim is None:
        reasons = handoff.rejection_reasons
        print(f"[REDDOG-FIX-CLAIM] preflight=WARN reasons={','.join(reasons) or '(none)'}")
        return _preparation(True, False, not _enforced(environment), reasons)
    print(
        "[REDDOG-FIX-CLAIM] preflight=PASS "
        f"determination={handoff.claim.determination_id} "
        f"queue_candidate={handoff.claim.queue_candidate_id}"
    )
    return MainFixPromotionClaimPreparation(
        True, True, True, handoff.claim, AgentDbFixPromotionClaimStore(),
        handoff.architect_determination_path, handoff.memex_supply_receipt_path,
    )


def _preparation(requested, continue_pipeline, startup_result, reasons=()):
    return MainFixPromotionClaimPreparation(
        requested, continue_pipeline, startup_result,
        None, None, None, None, reasons,
    )


def _enforced(environment: Mapping[str, str]) -> bool:
    return environment.get("REDDOG_ARCHITECT_FIX_PROMOTION_ENFORCED", "0") != "0"


__all__ = [
    "MainFixPromotionClaimPreparation",
    "prepare_reddog_main_fix_promotion_claim",
]
