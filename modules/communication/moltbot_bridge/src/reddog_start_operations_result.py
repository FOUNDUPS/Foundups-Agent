"""Wire schemas and typed terminal result for start operations."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping


RESULT_SCHEMA = "reddog_start_operations_control_result.v1"
PROGRESS_SCHEMA = "reddog_start_operations_progress.v1"
EFFECT_EVIDENCE_LEVEL = "IMPLEMENTATION_BOUNDARY_ATTESTATION"


@dataclass(frozen=True)
class StartOperationsControlResult:
    schema_version: str
    response_id: str
    accepted: bool
    action: str
    control_request_id: str
    operations_profile_id: str
    intent_id: str
    cycle_id: str
    status: str
    repo_head_sha: str
    architect_action: str
    architect_next_slice: str
    determination_id: str
    task_status_counts: Mapping[str, int]
    duplicate_intent_reused: bool
    recovered_existing_cycle: bool
    deferred_holo_maintenance: bool
    holo_repair_attempted: bool
    holo_repair_task_id: str
    holo_repair_status: str
    holo_repair_generation_id: str
    holo_repair_freshness_receipt_digest: str
    grounding_retried_after_repair: bool
    rejection_reasons: tuple[str, ...]
    effect_evidence_level: str = EFFECT_EVIDENCE_LEVEL
    no_extension_fusion_call_performed: bool = True
    no_maintenance_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_shell_command_executed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_worktree_operation_performed: bool = True
    no_pr_created: bool = True
    no_merge_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def holo_repair_payload(repair: Any | None) -> dict[str, Any]:
    attempted = repair is not None
    return {
        "holo_repair_attempted": attempted,
        "holo_repair_task_id": str(getattr(repair, "task_id", "") or ""),
        "holo_repair_status": str(getattr(repair, "status", "") or ""),
        "holo_repair_generation_id": str(
            getattr(repair, "generation_id", "") or ""
        ),
        "holo_repair_freshness_receipt_digest": str(
            getattr(repair, "freshness_receipt_digest", "") or ""
        ),
        "grounding_retried_after_repair": bool(
            attempted and getattr(repair, "accepted", False)
        ),
        "no_maintenance_performed": not bool(
            getattr(repair, "maintenance_performed", False)
        ),
    }


def result_json(result: StartOperationsControlResult) -> str:
    return json.dumps(result.to_dict(), sort_keys=True, separators=(",", ":"))


__all__ = [
    "EFFECT_EVIDENCE_LEVEL",
    "PROGRESS_SCHEMA",
    "RESULT_SCHEMA",
    "StartOperationsControlResult",
    "holo_repair_payload",
    "result_json",
]
