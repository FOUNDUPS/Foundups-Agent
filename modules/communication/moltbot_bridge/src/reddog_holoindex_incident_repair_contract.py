"""Immutable receipt contract for HoloIndex incident repair coordination."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, fields, replace
from typing import Any, Mapping

from modules.infrastructure.idle_automation.src.holoindex_postmerge_contract import (
    HOLOINDEX_INCIDENT_KINDS,
    REQUEST_EVENT_PREFIX,
    TASK_PREFIX,
)


SCHEMA_VERSION = "reddog_holoindex_incident_repair.v2"
REPAIRABLE_ERRORS = HOLOINDEX_INCIDENT_KINDS
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
    schema_version: str = SCHEMA_VERSION
    incident_kind: str = ""
    incident_id: str = ""
    task_id: str = ""
    request_event_id: str = ""
    target_repo_head_sha: str = ""
    workspace_repo_head_sha: str = ""
    observed_authority_head_sha: str = ""
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


def _deferred_receipt_binding_valid(
    receipt: HoloIndexIncidentRepairReceipt,
) -> bool:
    sha = r"[0-9a-f]{40}"
    digest = r"sha256:[0-9a-f]{64}"
    mismatch = receipt.incident_kind == "HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH"
    return bool(
        receipt.accepted and receipt.maintenance_enqueued
        and receipt.status in DEFERRED_STATUSES
        and receipt.schema_version == SCHEMA_VERSION
        and receipt.incident_kind in REPAIRABLE_ERRORS
        and re.fullmatch(digest, receipt.incident_id)
        and re.fullmatch(digest, receipt.receipt_id)
        and re.fullmatch(digest, receipt.authority_root_digest)
        and re.fullmatch(sha, receipt.target_repo_head_sha)
        and receipt.workspace_repo_head_sha == receipt.target_repo_head_sha
        and re.fullmatch(sha, receipt.observed_authority_head_sha)
        and receipt.task_id == TASK_PREFIX + receipt.target_repo_head_sha
        and receipt.request_event_id
        == REQUEST_EVENT_PREFIX + receipt.target_repo_head_sha
        and (
            mismatch
            and receipt.observed_authority_head_sha
            != receipt.target_repo_head_sha
            or not mismatch
            and receipt.observed_authority_head_sha
            == receipt.target_repo_head_sha
        )
    )


def rehydrate_deferred_receipt(
    value: Mapping[str, Any],
) -> HoloIndexIncidentRepairReceipt | None:
    """Rehydrate one self-consistent observation before durable authority checks."""

    names = frozenset(item.name for item in fields(HoloIndexIncidentRepairReceipt))
    bool_names = {
        "accepted", "maintenance_enqueued", "owner_requery_performed",
        "coding_candidate_required",
    }
    if set(value) != names or not all(type(value.get(name)) is bool for name in bool_names):
        return None
    str_names = names - bool_names - {"rejection_reasons"}
    reasons = value.get("rejection_reasons")
    if (
        not all(type(value.get(name)) is str for name in str_names)
        or not isinstance(reasons, (list, tuple))
        or not all(type(reason) is str for reason in reasons)
    ):
        return None
    try:
        receipt = HoloIndexIncidentRepairReceipt(
            **{**value, "rejection_reasons": tuple(reasons)}
        )
        expected = seal_receipt(replace(receipt, receipt_id=""))
    except (TypeError, ValueError):
        return None
    return receipt if receipt == expected and _deferred_receipt_binding_valid(receipt) else None


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
    "rehydrate_deferred_receipt",
    "seal_receipt",
]
