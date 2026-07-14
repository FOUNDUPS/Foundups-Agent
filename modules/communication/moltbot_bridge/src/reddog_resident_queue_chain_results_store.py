"""Resident RedDog queue chain-results store.

Slice: REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_STORE_PHASE1

This module atomically records one already-produced queue-chain stage result
for the resident RedDog loop. It does not invoke the stage. Before committing,
it replays the current resident queue orchestration plan and verifies the stage
being recorded is exactly the current missing stage. It then replays the plan
with the proposed result and commits only if the plan advances cleanly.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Protocol, Sequence

from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    RESIDENT_QUEUE_ORCHESTRATION_PLAN_COMPLETE,
    RESIDENT_QUEUE_ORCHESTRATION_PLAN_READY,
    ResidentQueueOrchestrationPlan,
    plan_reddog_resident_queue_orchestration,
)


CHAIN_RESULTS_SCHEMA_VERSION = "reddog_resident_queue_chain_results.v1"
CHAIN_RESULT_RECORDED = "CHAIN_RESULT_RECORDED"
CHAIN_RESULT_REJECTED = "CHAIN_RESULT_REJECTED"

FAIL_STAGE_KEY_REQUIRED = "FAIL_STAGE_KEY_REQUIRED"
FAIL_STAGE_RESULT_REQUIRED = "FAIL_STAGE_RESULT_REQUIRED"
FAIL_STAGE_ALREADY_RECORDED = "FAIL_STAGE_ALREADY_RECORDED"
FAIL_CURRENT_PLAN_NOT_READY = "FAIL_CURRENT_PLAN_NOT_READY"
FAIL_STAGE_NOT_CURRENT = "FAIL_STAGE_NOT_CURRENT"
FAIL_PROPOSED_PLAN_REJECTED = "FAIL_PROPOSED_PLAN_REJECTED"
FAIL_ATOMIC_COMMIT_FAILED = "FAIL_ATOMIC_COMMIT_FAILED"


class ResidentQueueChainResultsStore(Protocol):
    """Atomic store for resident queue chain results."""

    def load(self) -> Mapping[str, Any]:
        """Return current chain-results state, or an empty mapping."""

    def commit(self, snapshot: Mapping[str, Any], *, expected_revision: Optional[str]) -> str:
        """Atomically commit snapshot and return revision."""


class InMemoryResidentQueueChainResultsStore:
    """In-memory implementation used by tests and dry-run callers."""

    def __init__(self, initial: Optional[Mapping[str, Any]] = None, *, fail_commit: bool = False) -> None:
        self._state = json.loads(json.dumps(initial or {}, sort_keys=True))
        self.fail_commit = fail_commit

    def load(self) -> Mapping[str, Any]:
        return json.loads(json.dumps(self._state, sort_keys=True))

    def commit(self, snapshot: Mapping[str, Any], *, expected_revision: Optional[str]) -> str:
        if self.fail_commit:
            raise RuntimeError("commit_failed")
        current_revision = self._state.get("revision")
        if current_revision != expected_revision:
            raise RuntimeError("revision_conflict")
        committed = json.loads(json.dumps(snapshot, sort_keys=True))
        revision = _digest(committed)
        committed["revision"] = revision
        self._state = committed
        return revision


class AtomicJsonResidentQueueChainResultsStore:
    """Single-file JSON store using atomic replace."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> Mapping[str, Any]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def commit(self, snapshot: Mapping[str, Any], *, expected_revision: Optional[str]) -> str:
        current = self.load()
        if current.get("revision") != expected_revision:
            raise RuntimeError("revision_conflict")
        committed = json.loads(json.dumps(snapshot, sort_keys=True))
        revision = _digest(committed)
        committed["revision"] = revision
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{self.path.name}.", suffix=".tmp", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(committed, handle, sort_keys=True, indent=2)
                handle.write("\n")
            os.replace(tmp_name, self.path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        return revision


@dataclass(frozen=True)
class ResidentQueueChainResultReceipt:
    receipt_id: str
    queue_item_id: str
    selected_slice: str
    recorded_stage: str
    previous_plan_id: str
    next_plan_id: str
    next_action: str
    store_revision: Optional[str]
    no_bridge_invoked: bool = True
    no_authority_issued: bool = True
    no_worker_spawn_performed: bool = True
    no_worktree_created: bool = True
    no_shell_command_executed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pr_created: bool = True
    no_pattern_memory_write_performed: bool = True
    no_reward_settlement_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResidentQueueChainResultRecordResult:
    accepted: bool
    status: str
    rejection_reasons: list[str] = field(default_factory=list)
    receipt: Optional[ResidentQueueChainResultReceipt] = None
    previous_plan: Optional[ResidentQueueOrchestrationPlan] = None
    next_plan: Optional[ResidentQueueOrchestrationPlan] = None
    snapshot: Optional[Dict[str, Any]] = None
    no_bridge_invoked: bool = True
    no_authority_issued: bool = True
    no_worker_spawn_performed: bool = True
    no_worktree_created: bool = True
    no_shell_command_executed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pr_created: bool = True
    no_pattern_memory_write_performed: bool = True
    no_reward_settlement_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "accepted": self.accepted,
            "status": self.status,
            "rejection_reasons": self.rejection_reasons,
            "receipt": self.receipt.to_dict() if self.receipt else None,
            "previous_plan": self.previous_plan.to_dict() if self.previous_plan else None,
            "next_plan": self.next_plan.to_dict() if self.next_plan else None,
            "snapshot": self.snapshot,
            "no_bridge_invoked": self.no_bridge_invoked,
            "no_authority_issued": self.no_authority_issued,
            "no_worker_spawn_performed": self.no_worker_spawn_performed,
            "no_worktree_created": self.no_worktree_created,
            "no_shell_command_executed": self.no_shell_command_executed,
            "no_openclaw_enqueue_performed": self.no_openclaw_enqueue_performed,
            "no_hermes_dispatch_performed": self.no_hermes_dispatch_performed,
            "no_repo_mutation_performed": self.no_repo_mutation_performed,
            "no_holoindex_reindex_performed": self.no_holoindex_reindex_performed,
            "no_pr_created": self.no_pr_created,
            "no_pattern_memory_write_performed": self.no_pattern_memory_write_performed,
            "no_reward_settlement_performed": self.no_reward_settlement_performed,
        }


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    if isinstance(value, Mapping):
        return value
    return {}


def _stage_results(state: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    if state.get("schema_version") == CHAIN_RESULTS_SCHEMA_VERSION:
        raw = state.get("stage_results")
    else:
        raw = state
    if not isinstance(raw, Mapping):
        return {}
    return {
        str(key): value
        for key, value in raw.items()
        if isinstance(value, Mapping)
    }


def _receipts(state: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = state.get("receipts") if state.get("schema_version") == CHAIN_RESULTS_SCHEMA_VERSION else ()
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, Mapping)]


def _dedupe(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value or "").strip()))


def _reject(
    reasons: Sequence[str],
    *,
    previous_plan: Optional[ResidentQueueOrchestrationPlan] = None,
    next_plan: Optional[ResidentQueueOrchestrationPlan] = None,
) -> ResidentQueueChainResultRecordResult:
    return ResidentQueueChainResultRecordResult(
        accepted=False,
        status=CHAIN_RESULT_REJECTED,
        rejection_reasons=_dedupe(reasons),
        previous_plan=previous_plan,
        next_plan=next_plan,
    )


def record_resident_queue_stage_result(
    *,
    work_state_snapshot: Mapping[str, Any],
    store: ResidentQueueChainResultsStore,
    stage_key: str,
    stage_result: Mapping[str, Any],
    now_iso: str,
    requested_queue_item_id: Optional[str] = None,
) -> ResidentQueueChainResultRecordResult:
    """Atomically record one stage result if it is the planner's current stage."""

    clean_stage_key = str(stage_key or "").strip()
    if not clean_stage_key:
        return _reject((FAIL_STAGE_KEY_REQUIRED,))
    clean_stage_result = _mapping(stage_result)
    if not clean_stage_result:
        return _reject((FAIL_STAGE_RESULT_REQUIRED,))

    current = store.load()
    existing = _stage_results(current)
    if clean_stage_key in existing:
        return _reject((FAIL_STAGE_ALREADY_RECORDED, f"stage:{clean_stage_key}"))

    previous_plan = plan_reddog_resident_queue_orchestration(
        work_state_snapshot,
        chain_results=existing,
        requested_queue_item_id=requested_queue_item_id,
        now_iso=now_iso,
    )
    if (
        previous_plan.accepted is not True
        or previous_plan.status not in {
            RESIDENT_QUEUE_ORCHESTRATION_PLAN_READY,
            RESIDENT_QUEUE_ORCHESTRATION_PLAN_COMPLETE,
        }
        or previous_plan.current_stage is None
    ):
        return _reject(
            (FAIL_CURRENT_PLAN_NOT_READY, *previous_plan.rejection_reasons),
            previous_plan=previous_plan,
        )
    if previous_plan.current_stage != clean_stage_key:
        return _reject(
            (
                FAIL_STAGE_NOT_CURRENT,
                f"expected:{previous_plan.current_stage}",
                f"actual:{clean_stage_key}",
            ),
            previous_plan=previous_plan,
        )

    proposed_results = {**existing, clean_stage_key: dict(clean_stage_result)}
    next_plan = plan_reddog_resident_queue_orchestration(
        work_state_snapshot,
        chain_results=proposed_results,
        requested_queue_item_id=requested_queue_item_id,
        now_iso=now_iso,
    )
    if next_plan.accepted is not True:
        return _reject(
            (FAIL_PROPOSED_PLAN_REJECTED, *next_plan.rejection_reasons),
            previous_plan=previous_plan,
            next_plan=next_plan,
        )

    receipt_seed = {
        "queue_item_id": previous_plan.selected_queue_item_id,
        "selected_slice": previous_plan.selected_slice,
        "recorded_stage": clean_stage_key,
        "previous_plan_id": previous_plan.plan_id,
        "next_plan_id": next_plan.plan_id,
    }
    receipt = ResidentQueueChainResultReceipt(
        receipt_id=_digest(receipt_seed),
        queue_item_id=str(previous_plan.selected_queue_item_id or ""),
        selected_slice=str(previous_plan.selected_slice or ""),
        recorded_stage=clean_stage_key,
        previous_plan_id=previous_plan.plan_id,
        next_plan_id=next_plan.plan_id,
        next_action=next_plan.next_action,
        store_revision=None,
    )
    snapshot = {
        "schema_version": CHAIN_RESULTS_SCHEMA_VERSION,
        "updated_at": now_iso,
        "queue_item_id": previous_plan.selected_queue_item_id,
        "selected_slice": previous_plan.selected_slice,
        "stage_results": proposed_results,
        "receipts": [*list(_receipts(current)), receipt.to_dict()],
        "no_bridge_invoked": True,
        "no_authority_issued": True,
        "no_worker_spawn_performed": True,
        "no_worktree_created": True,
        "no_shell_command_executed": True,
        "no_openclaw_enqueue_performed": True,
        "no_hermes_dispatch_performed": True,
        "no_repo_mutation_performed": True,
        "no_holoindex_reindex_performed": True,
        "no_pr_created": True,
        "no_pattern_memory_write_performed": True,
        "no_reward_settlement_performed": True,
    }
    try:
        revision = store.commit(snapshot, expected_revision=_mapping(current).get("revision"))
    except Exception as exc:  # noqa: BLE001 - store errors fail closed.
        return _reject(
            (FAIL_ATOMIC_COMMIT_FAILED, exc.__class__.__name__),
            previous_plan=previous_plan,
            next_plan=next_plan,
        )
    committed_receipt = ResidentQueueChainResultReceipt(
        **{**receipt.to_dict(), "store_revision": revision}
    )
    snapshot["revision"] = revision
    snapshot["receipts"][-1] = committed_receipt.to_dict()
    return ResidentQueueChainResultRecordResult(
        accepted=True,
        status=CHAIN_RESULT_RECORDED,
        rejection_reasons=[],
        receipt=committed_receipt,
        previous_plan=previous_plan,
        next_plan=next_plan,
        snapshot=snapshot,
    )


__all__ = [
    "AtomicJsonResidentQueueChainResultsStore",
    "CHAIN_RESULTS_SCHEMA_VERSION",
    "CHAIN_RESULT_RECORDED",
    "CHAIN_RESULT_REJECTED",
    "FAIL_ATOMIC_COMMIT_FAILED",
    "FAIL_CURRENT_PLAN_NOT_READY",
    "FAIL_PROPOSED_PLAN_REJECTED",
    "FAIL_STAGE_ALREADY_RECORDED",
    "FAIL_STAGE_KEY_REQUIRED",
    "FAIL_STAGE_NOT_CURRENT",
    "FAIL_STAGE_RESULT_REQUIRED",
    "InMemoryResidentQueueChainResultsStore",
    "ResidentQueueChainResultReceipt",
    "ResidentQueueChainResultRecordResult",
    "ResidentQueueChainResultsStore",
    "record_resident_queue_stage_result",
]
