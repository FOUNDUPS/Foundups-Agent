"""Immutable receipt contract for HoloIndex incident repair coordination."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from typing import Any, Mapping


SCHEMA_VERSION = "reddog_holoindex_incident_repair.v1"
REPAIRABLE_ERRORS = frozenset(
    {
        "HOLOINDEX_QUERY_SERVICE_EXITED_DURING_STARTUP",
        "QUERY_OWNER_POISONED",
        "SEMANTIC_BACKEND_UNAVAILABLE",
    }
)
DEFERRED_STATUSES = frozenset(
    {
        "ASSIGNED",
        "EXECUTING",
        "PENDING",
        "QUEUED",
        "REQUEUED",
        "RETRY_WAIT",
        "WAITING_COMPLETION_RECEIPT",
    }
)


def canonical_digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def coordination_fields(result: Any) -> tuple[Any, ...] | None:
    get = result.get if isinstance(result, Mapping) else (
        lambda key, default="": getattr(result, key, default)
    )
    fields = tuple(get(key, "") for key in (
        "status", "task_id", "target_repo_head_sha", "authority_root_digest"
    ))
    reasons = get("rejection_reasons", ())
    if any(type(value) is not str for value in fields):
        return None
    if not isinstance(reasons, (list, tuple)) or not all(
        type(value) is str for value in reasons
    ):
        return None
    return (get("accepted", False) is True, *fields, tuple(reasons))


@dataclass(frozen=True, slots=True)
class HoloIndexIncidentRepairReceipt:
    accepted: bool
    status: str
    incident_id: str = ""
    task_id: str = ""
    target_repo_head_sha: str = ""
    authority_root_digest: str = ""
    generation_id: str = ""
    freshness_receipt_digest: str = ""
    maintenance_enqueued: bool = False
    owner_requery_performed: bool = False
    coding_candidate_required: bool = False
    rejection_reasons: tuple[str, ...] = ()
    receipt_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["rejection_reasons"] = list(self.rejection_reasons)
        return value


def seal_receipt(
    receipt: HoloIndexIncidentRepairReceipt,
) -> HoloIndexIncidentRepairReceipt:
    payload = receipt.to_dict()
    payload.pop("receipt_id", None)
    return replace(receipt, receipt_id=canonical_digest(payload))


def rejected_receipt(reason: str, **values: Any) -> HoloIndexIncidentRepairReceipt:
    return seal_receipt(HoloIndexIncidentRepairReceipt(
        False, "REJECTED", rejection_reasons=(reason,), **values
    ))


def escalated_receipt(reason: str, **values: Any) -> HoloIndexIncidentRepairReceipt:
    return seal_receipt(HoloIndexIncidentRepairReceipt(
        False, "ESCALATE", rejection_reasons=(reason,), **values
    ))


def authority_binding_rejection(
    *, incident_id: str, task_id: str, target_head: str, authority_digest: str
) -> HoloIndexIncidentRepairReceipt:
    return seal_receipt(HoloIndexIncidentRepairReceipt(
        False, "ESCALATE", incident_id=incident_id, task_id=task_id,
        target_repo_head_sha=target_head, authority_root_digest=authority_digest,
        coding_candidate_required=True,
        rejection_reasons=("maintenance_authority_binding_mismatch",),
    ))


__all__ = [
    "DEFERRED_STATUSES",
    "HoloIndexIncidentRepairReceipt",
    "REPAIRABLE_ERRORS",
    "SCHEMA_VERSION",
    "canonical_digest",
    "coordination_fields",
    "authority_binding_rejection",
    "escalated_receipt",
    "rejected_receipt",
    "seal_receipt",
]
