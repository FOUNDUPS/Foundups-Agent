"""Immutable contract for one start-operations Holo repair task."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from holo_index.repository_state import read_repository_state, repository_root_digest
from modules.communication.moltbot_bridge.src.reddog_grounded_target_assignment_continuity import (
    canonical_digest,
)


SCHEMA_VERSION = "reddog_start_operations_holo_repair.v1"
SOURCE = "reddog_start_operations_holo_repair"
TASK_PREFIX = "reddog_start_operations_holo_repair:"
CLAIM_AGENT_ID = "openclaw_supervisor"
REQUIRED_SKILLS = ["holo-search"]
REPAIRABLE_REASONS = frozenset(
    {
        "grounding_holoindex_owner_query_failed",
        "grounding_holoindex_generation_not_current",
    }
)


@dataclass(frozen=True)
class StartOperationsHoloRepairResult:
    accepted: bool
    status: str
    task_id: str = ""
    repair_request_id: str = ""
    repo_head_sha: str = ""
    generation_id: str = ""
    freshness_receipt_digest: str = ""
    maintenance_performed: bool = False
    rejection_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["rejection_reasons"] = list(self.rejection_reasons)
        return value


def repairable_grounding_failure(reasons: tuple[str, ...]) -> bool:
    """Return true only for a Holo-only grounding failure."""

    normalized = {str(reason) for reason in reasons if str(reason)}
    return bool(normalized.intersection(REPAIRABLE_REASONS)) and normalized.issubset(
        REPAIRABLE_REASONS
    )


def holo_repair_task_context(
    *,
    repo_root: Path,
    repo_head_sha: str,
    control_request_id: str,
) -> dict[str, Any]:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "source": SOURCE,
        "target_repo_head_sha": repo_head_sha,
        "target_repo_root_digest": repository_root_digest(repo_root),
        "control_request_id": control_request_id,
    }
    return {**payload, "repair_request_id": canonical_digest(payload)}


def holo_repair_task_id(context: Mapping[str, Any]) -> str:
    repair_id = str(context.get("repair_request_id") or "")
    return TASK_PREFIX + repair_id.removeprefix("sha256:")[:24]


def validate_holo_repair_task_binding(
    *, repo_root: Path | str, task_id: str, context: Mapping[str, Any]
) -> tuple[str, ...]:
    """Validate persisted task authority against current clean repository state."""

    root = Path(repo_root).resolve(strict=False)
    expected = holo_repair_task_context(
        repo_root=root,
        repo_head_sha=str(context.get("target_repo_head_sha") or ""),
        control_request_id=str(context.get("control_request_id") or ""),
    )
    state = read_repository_state(root)
    reasons: list[str] = []
    if dict(context) != expected:
        reasons.append("holo_repair_task_context_invalid")
    if task_id != holo_repair_task_id(context):
        reasons.append("holo_repair_task_id_invalid")
    if not state.proven_clean or state.head_sha != expected["target_repo_head_sha"]:
        reasons.append("holo_repair_repository_state_changed")
    return tuple(reasons)


__all__ = [
    "CLAIM_AGENT_ID",
    "REQUIRED_SKILLS",
    "SCHEMA_VERSION",
    "SOURCE",
    "TASK_PREFIX",
    "StartOperationsHoloRepairResult",
    "holo_repair_task_context",
    "holo_repair_task_id",
    "repairable_grounding_failure",
    "validate_holo_repair_task_binding",
]
