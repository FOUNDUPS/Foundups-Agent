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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_agentdb_architect_determination_reader import (
    load_agentdb_architect_determination,
)
from modules.communication.moltbot_bridge.src.reddog_backend_architect_determination_runtime import (
    ACTION_FIX,
    ARCHITECT_DETERMINATION_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle import (
    AgentDbResidentArchitectCycleStore,
    STATUS_DETERMINED,
)
from modules.communication.moltbot_bridge.src.reddog_operational_memex_supply_receipt import (
    rehydrate_operational_memex_supply_receipt,
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
    OUTPUT_PATHS_ALIAS = "artifact_output_paths_alias"
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
    expected_claim_binding: Mapping[str, str] | None = None,
    now_iso: str | None = None,
) -> ResidentFixPromotionArtifactHandoffResult:
    """Materialize promotion input artifacts from one determined resident cycle."""

    root, cleaned_intent = Path(repo_root).resolve(), _clean(intent_id)
    if not cleaned_intent:
        return _reject(cleaned_intent, None, None, (ResidentFixHandoffReason.MISSING_INTENT_ID,))

    cycle_reader = AgentDbResidentArchitectCycleStore()
    cycle = cycle_reader.load_cycle_by_intent(cleaned_intent)
    if not isinstance(cycle, Mapping) or not cycle:
        return _reject(cleaned_intent, None, None, (ResidentFixHandoffReason.CYCLE_NOT_FOUND,))

    cycle_id = _clean(cycle.get("cycle_id"))
    architect_id = _clean(cycle.get("architect_determination_id"))
    reasons = _validate_cycle(cycle)
    if cycle_id and architect_id and not reasons:
        determination_payload, determination_reasons = _load_determination(
            cycle,
            architect_id=architect_id,
            expected_claim_binding=expected_claim_binding,
        )
        reasons.extend(determination_reasons)
    else:
        determination_payload = None
        reasons.append(ResidentFixHandoffReason.DETERMINATION_NOT_FOUND)

    memex_supply = _memex_supply_receipt(cycle)
    reasons.extend(_validate_memex_supply(memex_supply, determination_payload, cycle=cycle, now_iso=_now_iso(now_iso)))
    determination_path, memex_path, path_reasons = _resolve_output_paths(
        architect_determination_output_path,
        memex_supply_receipt_output_path,
        root,
    )
    reasons.extend(path_reasons)
    deduped = _dedupe(reasons)
    if deduped:
        return _reject(cleaned_intent, cycle_id, architect_id, deduped)

    assert determination_payload is not None
    assert memex_supply is not None
    assert determination_path is not None
    assert memex_path is not None
    artifacts_written = _write_handoff_artifacts(
        determination_path, determination_payload, memex_path, memex_supply
    )
    if not artifacts_written:
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


def _validate_cycle(
    cycle: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []
    if cycle.get("_store_integrity_valid") is not True:
        reasons.append("resident_cycle_integrity_invalid")
    if _clean(cycle.get("status")) != STATUS_DETERMINED:
        reasons.append(ResidentFixHandoffReason.CYCLE_NOT_DETERMINED)
    if _clean(cycle.get("architect_action")) != ACTION_FIX:
        reasons.append(ResidentFixHandoffReason.CYCLE_NOT_FIX)
    if not _clean(cycle.get("cycle_id")) or not _clean(cycle.get("architect_determination_id")):
        reasons.append(ResidentFixHandoffReason.DETERMINATION_NOT_FOUND)
    return reasons


def _load_determination(
    cycle: Mapping[str, Any],
    *,
    architect_id: str,
    expected_claim_binding: Mapping[str, str] | None,
) -> tuple[Mapping[str, Any] | None, list[str]]:
    record = load_agentdb_architect_determination(architect_id)
    payload = _mapping(record, "determination")
    if payload is None and isinstance(record, Mapping):
        payload = record
    reasons = _validate_determination(payload, expected_id=architect_id)
    reasons.extend(
        _validate_expected_claim_binding(
            cycle,
            payload,
            expected_claim_binding,
        )
    )
    return payload, reasons


def _validate_expected_claim_binding(
    cycle: Mapping[str, Any],
    determination: Mapping[str, Any] | None,
    expected: Mapping[str, str] | None,
) -> list[str]:
    if expected is None:
        return ["fix_claim_binding_missing"]
    candidate = (
        determination.get("queue_candidate")
        if isinstance(determination, Mapping)
        else None
    )
    allocation = (
        candidate.get("wsp15_allocation_receipt")
        if isinstance(candidate, Mapping)
        else None
    )
    observed = {
        "cycle_id": _clean(cycle.get("cycle_id")),
        "snapshot_id": _clean(cycle.get("snapshot_id")),
        "determination_id": _clean(
            determination.get("determination_receipt_id")
            if isinstance(determination, Mapping)
            else ""
        ),
        "queue_candidate_id": _clean(
            candidate.get("queue_candidate_id")
            if isinstance(candidate, Mapping)
            else ""
        ),
        "wsp15_allocation_receipt_id": _clean(
            allocation.get("receipt_id") if isinstance(allocation, Mapping) else ""
        ),
    }
    return [] if observed == dict(expected) else ["fix_claim_binding_mismatch"]


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
    *,
    cycle: Mapping[str, Any],
    now_iso: str,
) -> list[str]:
    if not isinstance(receipt, Mapping) or not receipt:
        return [ResidentFixHandoffReason.MISSING_MEMEX_SUPPLY_RECEIPT]
    if not isinstance(determination, Mapping) or not determination:
        return [ResidentFixHandoffReason.MEMEX_SUPPLY_INVALID]
    proposal = determination.get("proposal_admission")
    intent = cycle.get("intent")
    expected_view_id = _memex_supply_view_id(cycle)
    if not isinstance(proposal, Mapping) or not isinstance(intent, Mapping):
        return [ResidentFixHandoffReason.MEMEX_SUPPLY_INVALID]
    expected_foundup = _clean(intent.get("foundup_id"))
    expected_principal = _clean(
        intent.get("principal_id")
        or intent.get("principal_ref")
        or intent.get("origin_principal")
    )
    if not expected_foundup or not expected_principal or not expected_view_id:
        return [ResidentFixHandoffReason.MEMEX_SUPPLY_INVALID]
    if _clean(receipt.get("memex_view_id")) != expected_view_id:
        return [ResidentFixHandoffReason.MEMEX_SUPPLY_INVALID]
    if (
        _clean(receipt.get("snapshot_receipt_id"))
        != _clean(determination.get("snapshot_receipt_id"))
        or _clean(receipt.get("snapshot_content_digest"))
        != _clean(determination.get("snapshot_content_digest"))
    ):
        return [ResidentFixHandoffReason.MEMEX_SNAPSHOT_MISMATCH]
    try:
        rehydrate_operational_memex_supply_receipt(
            receipt,
            expected_foundup_id=expected_foundup,
            expected_principal_id=expected_principal,
            expected_snapshot_receipt_id=_clean(determination.get("snapshot_receipt_id")),
            expected_snapshot_content_digest=_clean(determination.get("snapshot_content_digest")),
            expected_holoindex_generation_id=_clean(proposal.get("holoindex_generation_id")),
            expected_source_revision=_clean(proposal.get("work_state_revision")),
            now_iso=now_iso,
        )
    except (TypeError, ValueError):
        return [ResidentFixHandoffReason.MEMEX_SUPPLY_INVALID]
    return []


def _memex_supply_view_id(cycle: Mapping[str, Any]) -> str:
    for key in ("initial_bootstrap", "final_bootstrap"):
        bootstrap = cycle.get(key)
        if isinstance(bootstrap, Mapping):
            value = _clean(bootstrap.get("memex_snapshot_supply_view_id"))
            if value:
                return value
    return ""


def _now_iso(value: str | None) -> str:
    return value or datetime.now(timezone.utc).isoformat()


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


def _resolve_output_paths(
    determination_output: Path | str | None,
    memex_output: Path | str | None,
    repo_root: Path,
) -> tuple[Path | None, Path | None, list[str]]:
    determination_path, determination_reasons = _runtime_output_path(
        determination_output,
        repo_root,
        ResidentFixHandoffReason.DETERMINATION_OUTPUT_INVALID,
    )
    memex_path, memex_reasons = _runtime_output_path(
        memex_output,
        repo_root,
        ResidentFixHandoffReason.MEMEX_OUTPUT_INVALID,
    )
    reasons = [*determination_reasons, *memex_reasons]
    if determination_path is not None and determination_path == memex_path:
        reasons.append(ResidentFixHandoffReason.OUTPUT_PATHS_ALIAS)
    return determination_path, memex_path, reasons


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


def _write_json_pair_atomic(
    items: tuple[tuple[Path, Mapping[str, Any]], ...],
) -> None:
    prior = tuple(
        (path, path.read_bytes() if path.exists() else None)
        for path, _payload in items
    )
    try:
        for path, payload in items:
            _write_json_atomic(path, payload)
    except Exception:
        for path, content in prior:
            if content is None:
                path.unlink(missing_ok=True)
            else:
                _write_bytes_atomic(path, content)
        raise


def _write_handoff_artifacts(
    determination_path: Path,
    determination_payload: Mapping[str, Any],
    memex_path: Path,
    memex_supply: Mapping[str, Any],
) -> bool:
    try:
        _write_json_pair_atomic(
            (
                (determination_path, determination_payload),
                (memex_path, memex_supply),
            )
        )
    except Exception:
        return False
    return True


def _write_bytes_atomic(path: Path, content: bytes) -> None:
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
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
