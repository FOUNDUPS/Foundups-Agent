"""Read-only authoritative RedDog work-state query.

This module turns one externally stored authoritative work-state snapshot into
a bounded status receipt. It performs no model, HoloIndex, queue, claim, shell,
worktree, repository, or execution operation.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_wre_queue_consumer_dryrun import (
    WRE_QUEUE_CONSUMER_DRYRUN_READY,
    plan_reddog_wre_queue_consumer_dry_run,
)
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    canonical_reddog_wsp15_allocation_digest,
    validate_reddog_wsp15_allocation_receipt,
)


SCHEMA_VERSION = "reddog_authoritative_work_state_query.v1"
STATUS_READY = "AUTHORITATIVE_WORK_STATE_READY"
STATUS_NOT_READY = "AUTHORITATIVE_WORK_STATE_NOT_READY"
MAX_SNAPSHOT_BYTES = 8 * 1024 * 1024
DEFAULT_MAX_AGE_SECONDS = 900
MAX_CLOCK_SKEW_SECONDS = 60


@dataclass(frozen=True)
class AuthoritativeWorkStateQueryReceipt:
    schema_version: str
    receipt_id: str
    accepted: bool
    status: str
    snapshot_revision: Optional[str]
    snapshot_content_digest: Optional[str]
    snapshot_updated_at: Optional[str]
    queue_consumer_receipt_id: Optional[str]
    queue_item_id: Optional[str]
    selected_slice: Optional[str]
    claim_id: Optional[str]
    worker_id: Optional[str]
    freshness_receipt_id: Optional[str]
    wsp15_allocation_receipt_id: Optional[str]
    wsp15_allocation_digest: Optional[str]
    wsp15_priority: Optional[str]
    wsp15_mps_total: Optional[int]
    reasoning_tier: Optional[str]
    next_required_gate: Optional[str]
    rejection_reasons: tuple[str, ...]
    no_model_call_performed: bool = True
    no_holoindex_query_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_queue_mutation_performed: bool = True
    no_claim_mutation_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_shell_command_executed: bool = True
    no_repo_mutation_performed: bool = True
    no_execution_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def query_authoritative_work_state(
    *,
    repo_root: Path | str,
    work_state_path: Path | str | None,
    now_iso: str | None = None,
    requested_queue_item_id: str | None = None,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
) -> AuthoritativeWorkStateQueryReceipt:
    """Validate and summarize one authoritative queue item without mutation."""

    reasons: list[str] = []
    root = Path(repo_root).resolve()
    state_path = _resolve_state_path(root, work_state_path, reasons)
    snapshot, content_digest = _read_snapshot(state_path, reasons)
    now = _parse_time(now_iso) if now_iso else datetime.now(timezone.utc)
    revision = _validate_snapshot(snapshot, now, max_age_seconds, reasons)
    queue_id = _queue_id_if_valid(snapshot, requested_queue_item_id, reasons)
    consumer = _run_consumer(snapshot, now, queue_id, reasons)
    selected = _selected_queue(snapshot, consumer)
    allocation = _mapping(selected.get("wsp15_allocation_receipt"))
    _validate_selected(snapshot, selected, allocation, consumer, reasons)
    fields = _receipt_fields(consumer, selected, allocation)
    return _build_receipt(
        reasons=reasons,
        revision=revision,
        content_digest=content_digest,
        updated_at=str(snapshot.get("updated_at") or "") or None,
        fields=fields,
    )


def _queue_id_if_valid(
    snapshot: Mapping[str, Any],
    requested_queue_item_id: Optional[str],
    reasons: list[str],
) -> Optional[str]:
    return (
        None
        if reasons
        else _queue_item_request(snapshot, requested_queue_item_id, reasons)
    )


def _queue_item_request(
    snapshot: Mapping[str, Any],
    requested_queue_item_id: Optional[str],
    reasons: list[str],
) -> Optional[str]:
    if requested_queue_item_id:
        return requested_queue_item_id
    selected_slice = str(snapshot.get("selected_slice") or "")
    if not selected_slice:
        reasons.append("selected_slice_missing")
        return None
    matches = [
        str(item.get("queue_item_id") or "")
        for item in snapshot.get("wre_queue_items") or ()
        if isinstance(item, Mapping)
        and str(item.get("slice_id") or "") == selected_slice
        and str(item.get("status") or "").upper() == "QUEUED"
    ]
    matches = [value for value in matches if value]
    if len(matches) != 1:
        reasons.append(
            "selected_slice_queue_missing" if not matches else "selected_slice_queue_ambiguous"
        )
        return None
    return matches[0]


def _run_consumer(
    snapshot: Mapping[str, Any],
    now: datetime,
    requested_queue_item_id: Optional[str],
    reasons: list[str],
) -> Any:
    if not snapshot or reasons:
        return None
    result = plan_reddog_wre_queue_consumer_dry_run(
        snapshot,
        now_iso=now.isoformat(),
        requested_queue_item_id=requested_queue_item_id,
        require_governed_lineage=True,
    )
    reasons.extend(result.rejection_reasons)
    return result


def _resolve_state_path(
    root: Path, work_state_path: Path | str | None, reasons: list[str]
) -> Optional[Path]:
    if not work_state_path:
        reasons.append("missing_authoritative_work_state_path")
        return None
    raw = Path(work_state_path)
    path = raw if raw.is_absolute() else root / raw
    if path.is_symlink():
        reasons.append("work_state_path_symlink_rejected")
        return None
    resolved = path.resolve()
    if resolved == root or root in resolved.parents:
        reasons.append("work_state_path_inside_repo")
        return None
    if not resolved.is_file():
        reasons.append("missing_authoritative_work_state")
        return None
    return resolved


def _read_snapshot(
    path: Optional[Path], reasons: list[str]
) -> tuple[dict[str, Any], Optional[str]]:
    if path is None:
        return {}, None
    try:
        before = path.stat()
        if before.st_size > MAX_SNAPSHOT_BYTES:
            reasons.append("authoritative_work_state_too_large")
            return {}, None
        raw = path.read_bytes()
        after = path.stat()
        if _file_identity(before) != _file_identity(after):
            reasons.append("authoritative_work_state_changed_during_read")
            return {}, None
        value = json.loads(raw.decode("utf-8"))
    except Exception:
        reasons.append("malformed_authoritative_work_state")
        return {}, None
    if not isinstance(value, dict):
        reasons.append("authoritative_work_state_not_mapping")
        return {}, None
    return value, _bytes_digest(raw)


def _validate_snapshot(
    snapshot: Mapping[str, Any],
    now: datetime,
    max_age_seconds: int,
    reasons: list[str],
) -> Optional[str]:
    if not snapshot:
        return None
    revision = str(snapshot.get("revision") or "")
    unsigned = dict(snapshot)
    unsigned.pop("revision", None)
    if not revision or revision != _canonical_digest(unsigned):
        reasons.append("authoritative_work_state_revision_invalid")
    updated = _parse_time(snapshot.get("updated_at"))
    if updated is None:
        reasons.append("authoritative_work_state_updated_at_invalid")
    else:
        age = (now - updated).total_seconds()
        if age < -MAX_CLOCK_SKEW_SECONDS:
            reasons.append("authoritative_work_state_from_future")
        if age > max(1, int(max_age_seconds)):
            reasons.append("authoritative_work_state_stale")
    return revision or None


def _selected_queue(
    snapshot: Mapping[str, Any], consumer: Any
) -> Mapping[str, Any]:
    queue_id = str(getattr(consumer, "selected_queue_item_id", "") or "")
    for item in snapshot.get("wre_queue_items") or ():
        if isinstance(item, Mapping) and str(item.get("queue_item_id") or "") == queue_id:
            return item
    return {}


def _validate_selected(
    snapshot: Mapping[str, Any],
    selected: Mapping[str, Any],
    allocation: Mapping[str, Any],
    consumer: Any,
    reasons: list[str],
) -> None:
    if consumer is None or consumer.status != WRE_QUEUE_CONSUMER_DRYRUN_READY:
        return
    selected_slice = str(getattr(consumer, "selected_slice", "") or "")
    if str(snapshot.get("selected_slice") or "") != selected_slice:
        reasons.append("selected_slice_snapshot_mismatch")
    validation = validate_reddog_wsp15_allocation_receipt(allocation)
    if not validation.accepted:
        reasons.extend(
            f"wsp15_allocation:{reason}" for reason in validation.rejection_reasons
        )
    receipt = consumer.receipt
    if receipt and canonical_reddog_wsp15_allocation_digest(allocation) != (
        receipt.wsp15_allocation_digest
    ):
        reasons.append("wsp15_allocation_digest_mismatch")


def _receipt_fields(
    consumer: Any,
    selected: Mapping[str, Any],
    allocation: Mapping[str, Any],
) -> dict[str, Any]:
    receipt = getattr(consumer, "receipt", None)
    return {
        "queue_consumer_receipt_id": getattr(receipt, "receipt_id", None),
        "queue_item_id": getattr(consumer, "selected_queue_item_id", None),
        "selected_slice": getattr(consumer, "selected_slice", None),
        "claim_id": str(selected.get("claim_id") or "") or None,
        "worker_id": str(selected.get("worker_id") or "") or None,
        "freshness_receipt_id": getattr(receipt, "freshness_receipt_id", None),
        "wsp15_allocation_receipt_id": str(allocation.get("receipt_id") or "") or None,
        "wsp15_allocation_digest": (
            canonical_reddog_wsp15_allocation_digest(allocation) if allocation else None
        ),
        "wsp15_priority": str(allocation.get("priority") or "") or None,
        "wsp15_mps_total": allocation.get("mps_total"),
        "reasoning_tier": str(allocation.get("reasoning_tier") or "") or None,
        "next_required_gate": getattr(consumer, "next_required_gate", None),
    }


def _build_receipt(
    *,
    reasons: list[str],
    revision: Optional[str],
    content_digest: Optional[str],
    updated_at: Optional[str],
    fields: Mapping[str, Any],
) -> AuthoritativeWorkStateQueryReceipt:
    rejected = tuple(dict.fromkeys(str(reason) for reason in reasons if reason))
    payload = {
        "schema_version": SCHEMA_VERSION,
        "accepted": not rejected,
        "status": STATUS_READY if not rejected else STATUS_NOT_READY,
        "snapshot_revision": revision,
        "snapshot_content_digest": content_digest,
        "snapshot_updated_at": updated_at,
        **fields,
        "rejection_reasons": rejected,
        **_no_side_effects(),
    }
    return AuthoritativeWorkStateQueryReceipt(
        receipt_id=_canonical_digest(payload),
        **payload,
    )


def _no_side_effects() -> dict[str, bool]:
    return {
        "no_model_call_performed": True,
        "no_holoindex_query_performed": True,
        "no_holoindex_reindex_performed": True,
        "no_queue_mutation_performed": True,
        "no_claim_mutation_performed": True,
        "no_worker_spawn_performed": True,
        "no_shell_command_executed": True,
        "no_repo_mutation_performed": True,
        "no_execution_performed": True,
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _parse_time(value: Any) -> Optional[datetime]:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _file_identity(stat_result: Any) -> tuple[int, int, int, int]:
    return (
        int(stat_result.st_size),
        int(stat_result.st_mtime_ns),
        int(stat_result.st_dev),
        int(stat_result.st_ino),
    )


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _bytes_digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


__all__ = [
    "AuthoritativeWorkStateQueryReceipt",
    "DEFAULT_MAX_AGE_SECONDS",
    "SCHEMA_VERSION",
    "STATUS_NOT_READY",
    "STATUS_READY",
    "query_authoritative_work_state",
]
