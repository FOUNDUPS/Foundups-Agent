"""Append-only receipts for the resident RedDog control loop.

Slice: REDDOG_RESIDENT_CONTROL_LOOP_RECEIPT_PERSISTENCE_PHASE1

This module records compact control-loop summaries after the already-governed
resident queue serial loop and OpenClaw signed-worker claim loop run. It does
not invoke workers, mutate source, issue authority, reindex HoloIndex, or
settle rewards.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping


CONTROL_LOOP_RECEIPT_SCHEMA_VERSION = "reddog_resident_control_loop_receipt.v1"


@dataclass(frozen=True)
class ResidentControlLoopReceipt:
    schema_version: str
    receipt_id: str
    accepted: bool
    status: str
    rounds: int
    serial_progress: int
    claim_progress: int
    receipt_ids: tuple[str, ...]
    rejection_reasons: tuple[str, ...]
    created_at: str
    repo_root_digest: str
    control_lock_acquired: bool
    no_authority_issued: bool = True
    no_worker_spawn_performed: bool = True
    no_shell_command_executed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_merge_performed: bool = True
    no_reward_settlement_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["receipt_ids"] = list(self.receipt_ids)
        payload["rejection_reasons"] = list(self.rejection_reasons)
        return payload


def build_resident_control_loop_receipt(
    *,
    result: Mapping[str, Any],
    repo_root: Path | str,
    created_at: str,
) -> ResidentControlLoopReceipt:
    """Build a deterministic receipt for an already-produced control result."""

    payload = {
        "schema_version": CONTROL_LOOP_RECEIPT_SCHEMA_VERSION,
        "accepted": bool(result.get("accepted")),
        "status": str(result.get("status") or ""),
        "rounds": _int(result.get("rounds")),
        "serial_progress": _int(result.get("serial_progress")),
        "claim_progress": _int(result.get("claim_progress")),
        "receipt_ids": _string_tuple(result.get("receipt_ids")),
        "rejection_reasons": _string_tuple(result.get("rejection_reasons")),
        "created_at": str(created_at or ""),
        "repo_root_digest": _digest(str(Path(repo_root).resolve())),
        "control_lock_acquired": result.get("control_lock_acquired") is True,
        "no_authority_issued": True,
        "no_worker_spawn_performed": True,
        "no_shell_command_executed": True,
        "no_holoindex_reindex_performed": True,
        "no_merge_performed": True,
        "no_reward_settlement_performed": True,
    }
    payload["receipt_id"] = "reddog_resident_control_loop_" + _digest(payload)[:16]
    return ResidentControlLoopReceipt(**payload)


def append_resident_control_loop_receipt(
    *,
    path: Path | str,
    result: Mapping[str, Any],
    repo_root: Path | str,
    created_at: str,
) -> ResidentControlLoopReceipt:
    """Append one control-loop receipt as JSONL and return it."""

    receipt = build_resident_control_loop_receipt(
        result=result,
        repo_root=repo_root,
        created_at=created_at,
    )
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(receipt.to_dict(), sort_keys=True, separators=(",", ":")))
        handle.write("\n")
    return receipt


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item) for item in value if str(item or "").strip())


def _int(value: Any) -> int:
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "CONTROL_LOOP_RECEIPT_SCHEMA_VERSION",
    "ResidentControlLoopReceipt",
    "append_resident_control_loop_receipt",
    "build_resident_control_loop_receipt",
]
