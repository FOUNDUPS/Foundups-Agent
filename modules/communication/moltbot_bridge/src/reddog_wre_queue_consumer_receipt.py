"""Canonical receipt value object for governed WRE queue consumption."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, Mapping, Optional


@dataclass(frozen=True)
class WREQueueConsumerDryRunReceipt:
    """Receipt for one validated authoritative queue item."""

    receipt_id: str
    queue_item_id: str
    slice_id: str
    claim_id: str
    worker_id: str
    freshness_receipt_id: str
    operational_snapshot_id: str
    wsp15_allocation_receipt_id: str
    wsp15_allocation_digest: str
    wsp15_priority: str
    wsp15_mps_total: int
    reasoning_tier: str
    progressive_policy_stage_receipt_id: str
    progressive_policy_stage_digest: str
    next_required_gate: str
    model_selection_receipt_id: Optional[str] = None
    model_selection_digest: Optional[str] = None
    model_runtime_binding_receipt_id: Optional[str] = None
    model_runtime_binding_digest: Optional[str] = None
    model_runtime_binding_verification_receipt_id: Optional[str] = None
    model_runtime_binding_verification_digest: Optional[str] = None
    memex_supply_receipt_id: Optional[str] = None
    memex_supply_digest: Optional[str] = None
    execution_ready: bool = False
    no_queue_mutation_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_worktree_created: bool = True
    no_shell_command_executed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pr_created: bool = True
    no_reward_settlement_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_queue_consumer_receipt(
    seed: Mapping[str, Any],
) -> WREQueueConsumerDryRunReceipt:
    """Materialize the canonical receipt from a validated planner seed."""

    optional = (
        "model_selection_receipt_id",
        "model_selection_digest",
        "model_runtime_binding_receipt_id",
        "model_runtime_binding_digest",
        "model_runtime_binding_verification_receipt_id",
        "model_runtime_binding_verification_digest",
        "memex_supply_receipt_id",
        "memex_supply_digest",
    )
    values = {key: (str(seed.get(key) or "") or None) for key in optional}
    return WREQueueConsumerDryRunReceipt(
        receipt_id="wre_queue_consumer_" + _digest(seed)[7:23],
        queue_item_id=str(seed["queue_item_id"]),
        slice_id=str(seed["slice_id"]),
        claim_id=str(seed["claim_id"]),
        worker_id=str(seed["worker_id"]),
        freshness_receipt_id=str(seed["freshness_receipt_id"]),
        operational_snapshot_id=str(seed["operational_snapshot_id"]),
        wsp15_allocation_receipt_id=str(seed["wsp15_allocation_receipt_id"]),
        wsp15_allocation_digest=str(seed["wsp15_allocation_digest"]),
        wsp15_priority=str(seed["wsp15_priority"]),
        wsp15_mps_total=int(seed["wsp15_mps_total"]),
        reasoning_tier=str(seed["reasoning_tier"]),
        progressive_policy_stage_receipt_id=str(
            seed["progressive_policy_stage_receipt_id"]
        ),
        progressive_policy_stage_digest=str(
            seed["progressive_policy_stage_digest"]
        ),
        next_required_gate=str(seed["next_required_gate"]),
        **values,
    )


def _digest(payload: Any) -> str:
    raw = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = ["WREQueueConsumerDryRunReceipt", "build_queue_consumer_receipt"]
