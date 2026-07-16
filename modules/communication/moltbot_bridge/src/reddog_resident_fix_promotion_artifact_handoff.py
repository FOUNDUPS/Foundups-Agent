"""Resident-cycle artifact handoff for architect FIX promotion.

Slice: REDDOG_RESIDENT_CYCLE_FIX_PROMOTION_ARTIFACT_HANDOFF_PHASE1

This module bridges an accepted durable resident RedDog architect cycle into
the existing architect-FIX promotion preflight by materializing two runtime
artifacts outside the repository:

* backend architect determination JSON
* cycle-level operational Memex supply receipt JSON

It does not create model-selection receipts, authority profiles, signatures,
work orders, workers, shells, worktrees, PRs, PatternMemory entries, or
HoloIndex indexes. Those remain independently gated downstream.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_backend_architect_determination_runtime import (
    ACTION_FIX,
    ARCHITECT_DETERMINATION_ACCEPT,
    AgentDbArchitectDeterminationStore,
    ArchitectDeterminationStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle import (
    AgentDbResidentArchitectCycleStore,
    ResidentArchitectCycleStore,
    STATUS_DETERMINED,
)


RESIDENT_FIX_HANDOFF_APPLIED = "RESIDENT_FIX_HANDOFF_APPLIED"
RESIDENT_FIX_HANDOFF_NOT_READY = "RESIDENT_FIX_HANDOFF_NOT_READY"


class ResidentFixHandoffReason:
    MISSING_INTENT_ID = "missing_intent_id"
    CYCLE_NOT_FOUND = "resident_cycle_not_found"
    CYCLE_NOT_DETERMINED = "resident_cycle_not_determined"
    CYCLE_NOT_FIX = "resident_cycle_not_fix"
    DETERMINATION_NOT_FOUND = "architect_determination_not_found"
    DETERMINATION_NOT_ACCEPTED = "architect_determination_not_accepted"
    DETERMINATION_ID_MISMATCH = "architect_determination_id_mismatch"
    MISSING_MEMEX_SUPPLY_RECEIPT = "missing_memex_supply_receipt"
    MEMEX_SUPPLY_INVALID = "memex_supply_receipt_invalid"
    MEMEX_SNAPSHOT_MISMATCH = "memex_supply_snapshot_mismatch"
    DETERMINATION_OUTPUT_INVALID = "architect_determination_output_invalid"
    MEMEX_OUTPUT_INVALID = "memex_supply_output_invalid"
    OUTPUT_WRITE_FAILED = "artifact_output_write_failed"


@dataclass(frozen=True)
class ResidentFixPromotionArtifactHandoffResult:
    accepted: bool
    status: str
    intent_id: str
    cycle_id: str | None
    architect_determination_id: str | None
    architect_determination_path: str | None
    memex_supply_receipt_path: str | None
    rejection_reasons: tuple[str, ...]
    no_signing_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_shell_command_executed: bool = True
    no_worktree_operation_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_pr_created: bool = True
    no_pattern_memory_promotion_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_resident_fix_promotion_artifact_handoff(
    *,
    repo_root: Path | str,
    intent_id: str,
    architect_determination_output_path: Path | str | None,
    memex_supply_receipt_output_path: Path | str | None,
    cycle_store: ResidentArchitectCycleStore | None = None,
    architect_store: ArchitectDeterminationStore | None = None,
) -> ResidentFixPromotionArtifactHandoffResult:
    """Materialize promotion input artifacts from one determined resident cycle."""

    root = Path(repo_root).resolve()
    cleaned_intent = _clean(intent_id)
    if not cleaned_intent:
        return _reject(cleaned_intent, None, None, (ResidentFixHandoffReason.MISSING_INTENT_ID,))

    cycle_reader = cycle_store or AgentDbResidentArchitectCycleStore()
    architect_reader = architect_store or AgentDbArchitectDeterminationStore()
    cycle = cycle_reader.load_cycle_by_intent(cleaned_intent)
    if not isinstance(cycle, Mapping) or not cycle:
        return _reject(cleaned_intent, None, None, (ResidentFixHandoffReason.CYCLE_NOT_FOUND,))

    cycle_id = _clean(cycle.get("cycle_id"))
    architect_id = _clean(cycle.get("architect_determination_id"))
    reasons = _validate_cycle(cycle)
    determination_record: Mapping[str, Any] | None = None
    determination_payload: Mapping[str, Any] | None = None
    if cycle_id and not reasons:
        determination_record = architect_reader.load_architect_determination_by_cycle(cycle_id)
        determination_payload = _mapping(determination_record, "determination")
        reasons.extend(_validate_determination(determination_payload, expected_id=architect_id))
    else:
        reasons.append(ResidentFixHandoffReason.DETERMINATION_NOT_FOUND)

    memex_supply = _memex_supply_receipt(cycle)
    reasons.extend(_validate_memex_supply(memex_supply, determination_payload))
    determination_path, determination_reasons = _runtime_output_path(
        architect_determination_output_path,
        root,
        ResidentFixHandoffReason.DETERMINATION_OUTPUT_INVALID,
    )
    memex_path, memex_reasons = _runtime_output_path(
        memex_supply_receipt_output_path,
        root,
        ResidentFixHandoffReason.MEMEX_OUTPUT_INVALID,
    )
    reasons.extend(determination_reasons)
    reasons.extend(memex_reasons)
    deduped = _dedupe(reasons)
    if deduped:
        return _reject(cleaned_intent, cycle_id, architect_id, deduped)

    assert determination_payload is not None
    assert memex_supply is not None
    assert determination_path is not None
    assert memex_path is not None
    try:
        _write_json_atomic(determination_path, determination_payload)
        _write_json_atomic(memex_path, memex_supply)
    except Exception:
        return _reject(
            cleaned_intent,
            cycle_id,
            architect_id,
            (ResidentFixHandoffReason.OUTPUT_WRITE_FAILED,),
        )

    return ResidentFixPromotionArtifactHandoffResult(
        accepted=True,
        status=RESIDENT_FIX_HANDOFF_APPLIED,
        intent_id=cleaned_intent,
        cycle_id=cycle_id,
        architect_determination_id=architect_id,
        architect_determination_path=str(determination_path),
        memex_supply_receipt_path=str(memex_path),
        rejection_reasons=(),
    )


def _validate_cycle(cycle: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if _clean(cycle.get("status")) != STATUS_DETERMINED:
        reasons.append(ResidentFixHandoffReason.CYCLE_NOT_DETERMINED)
    if _clean(cycle.get("architect_action")) != ACTION_FIX:
        reasons.append(ResidentFixHandoffReason.CYCLE_NOT_FIX)
    if not _clean(cycle.get("cycle_id")) or not _clean(cycle.get("architect_determination_id")):
        reasons.append(ResidentFixHandoffReason.DETERMINATION_NOT_FOUND)
    return reasons


def _validate_determination(
    determination: Mapping[str, Any] | None,
    *,
    expected_id: str,
) -> list[str]:
    if not isinstance(determination, Mapping) or not determination:
        return [ResidentFixHandoffReason.DETERMINATION_NOT_FOUND]
    reasons: list[str] = []
    if determination.get("accepted") is not True or _clean(determination.get("status")) != ARCHITECT_DETERMINATION_ACCEPT:
        reasons.append(ResidentFixHandoffReason.DETERMINATION_NOT_ACCEPTED)
    if _clean(determination.get("action")) != ACTION_FIX:
        reasons.append(ResidentFixHandoffReason.CYCLE_NOT_FIX)
    if _clean(determination.get("determination_receipt_id")) != expected_id:
        reasons.append(ResidentFixHandoffReason.DETERMINATION_ID_MISMATCH)
    return reasons


def _memex_supply_receipt(cycle: Mapping[str, Any]) -> Mapping[str, Any] | None:
    for key in ("initial_bootstrap", "final_bootstrap"):
        bootstrap = cycle.get(key)
        if isinstance(bootstrap, Mapping):
            receipt = bootstrap.get("memex_snapshot_supply_receipt")
            if isinstance(receipt, Mapping) and receipt:
                return receipt
    return None


def _validate_memex_supply(
    receipt: Mapping[str, Any] | None,
    determination: Mapping[str, Any] | None,
) -> list[str]:
    if not isinstance(receipt, Mapping) or not receipt:
        return [ResidentFixHandoffReason.MISSING_MEMEX_SUPPLY_RECEIPT]
    reasons: list[str] = []
    required = (
        "schema_version",
        "receipt_id",
        "snapshot_receipt_id",
        "snapshot_content_digest",
        "memex_view_id",
        "holoindex_generation_id",
        "source_revision",
        "no_holoindex_reindex_performed",
    )
    missing = [field for field in required if receipt.get(field) in (None, "", ())]
    if missing or receipt.get("schema_version") != "reddog_operational_memex_snapshot_supply_receipt.v1":
        reasons.append(ResidentFixHandoffReason.MEMEX_SUPPLY_INVALID)
    if receipt.get("no_holoindex_reindex_performed") is not True:
        reasons.append(ResidentFixHandoffReason.MEMEX_SUPPLY_INVALID)
    if isinstance(determination, Mapping) and determination:
        if _clean(receipt.get("snapshot_receipt_id")) != _clean(determination.get("snapshot_receipt_id")):
            reasons.append(ResidentFixHandoffReason.MEMEX_SNAPSHOT_MISMATCH)
        if _clean(receipt.get("snapshot_content_digest")) != _clean(determination.get("snapshot_content_digest")):
            reasons.append(ResidentFixHandoffReason.MEMEX_SNAPSHOT_MISMATCH)
    return reasons


def _runtime_output_path(
    value: Path | str | None,
    repo_root: Path,
    reason: str,
) -> tuple[Path | None, list[str]]:
    if not value:
        return None, [reason]
    path = Path(value)
    if not path.is_absolute():
        path = repo_root.parent / path
    resolved = path.resolve()
    try:
        resolved.relative_to(repo_root)
        return None, [reason]
    except ValueError:
        pass
    if resolved.name == "":
        return None, [reason]
    return resolved, []


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, sort_keys=True, indent=2)
            handle.write("\n")
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def _mapping(value: Any, key: str) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    nested = value.get(key)
    return nested if isinstance(nested, Mapping) else None


def _reject(
    intent_id: str,
    cycle_id: str | None,
    architect_id: str | None,
    reasons: tuple[str, ...] | list[str],
) -> ResidentFixPromotionArtifactHandoffResult:
    return ResidentFixPromotionArtifactHandoffResult(
        accepted=False,
        status=RESIDENT_FIX_HANDOFF_NOT_READY,
        intent_id=intent_id,
        cycle_id=cycle_id,
        architect_determination_id=architect_id,
        architect_determination_path=None,
        memex_supply_receipt_path=None,
        rejection_reasons=tuple(_dedupe(reasons)),
    )


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _dedupe(values: Any) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if str(value).strip()))


__all__ = [
    "RESIDENT_FIX_HANDOFF_APPLIED",
    "RESIDENT_FIX_HANDOFF_NOT_READY",
    "ResidentFixHandoffReason",
    "ResidentFixPromotionArtifactHandoffResult",
    "run_reddog_resident_fix_promotion_artifact_handoff",
]
