"""Main-startup adapter for the RedDog resident queue orchestration planner.

This adapter wires ``main.py`` to the non-mutating resident queue planner. It
reads an existing authoritative work-state snapshot and optional chain-results
JSON from outside the repository checkout, then reports the next guarded bridge
RedDog should run. It does not invoke that bridge.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    RESIDENT_QUEUE_ORCHESTRATION_PLAN_COMPLETE,
    RESIDENT_QUEUE_ORCHESTRATION_PLAN_READY,
    plan_reddog_resident_queue_orchestration,
)


REDDOG_RESIDENT_QUEUE_PLAN_BOOTSTRAP_READY = "REDDOG_RESIDENT_QUEUE_PLAN_BOOTSTRAP_READY"
REDDOG_RESIDENT_QUEUE_PLAN_BOOTSTRAP_NOT_READY = "REDDOG_RESIDENT_QUEUE_PLAN_BOOTSTRAP_NOT_READY"


@dataclass(frozen=True)
class RedDogMainResidentQueuePlanBootstrapResult:
    """Result returned to ``main.py`` for startup reporting."""

    ready: bool
    status: str
    plan_id: Optional[str]
    queue_item_id: Optional[str]
    selected_slice: Optional[str]
    next_action: Optional[str]
    current_stage: Optional[str]
    accepted_stage_count: int
    rejection_reasons: tuple[str, ...]
    chain_complete: bool = False
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_main_resident_queue_orchestration_plan_bootstrap(
    *,
    repo_root: Path | str,
    work_state_path: Path | str | None,
    chain_results_path: Path | str | None = None,
    requested_queue_item_id: str | None = None,
    now_iso: str | None = None,
) -> RedDogMainResidentQueuePlanBootstrapResult:
    """Load queue state and emit the next resident RedDog bridge action."""

    root = Path(repo_root).resolve()
    snapshot_result = _read_json_outside_repo(
        root,
        work_state_path,
        missing_reason="missing_authoritative_work_state_path",
        inside_reason="work_state_path_inside_repo",
        unreadable_reason="malformed_authoritative_work_state",
    )
    if snapshot_result[1]:
        return _not_ready(snapshot_result[1])
    snapshot = snapshot_result[0]
    assert snapshot is not None

    chain_results: Mapping[str, Mapping[str, Any]] = {}
    if chain_results_path:
        chain_result = _read_json_outside_repo(
            root,
            chain_results_path,
            missing_reason="missing_chain_results",
            inside_reason="chain_results_path_inside_repo",
            unreadable_reason="malformed_chain_results",
        )
        if chain_result[1]:
            return _not_ready(chain_result[1])
        raw_chain = chain_result[0]
        if not isinstance(raw_chain, Mapping):
            return _not_ready(("chain_results_not_mapping",))
        chain_results = {
            str(key): value
            for key, value in raw_chain.items()
            if isinstance(value, Mapping)
        }
        if len(chain_results) != len(raw_chain):
            return _not_ready(("chain_results_contains_non_mapping_stage",))

    plan = plan_reddog_resident_queue_orchestration(
        snapshot,
        chain_results=chain_results,
        requested_queue_item_id=requested_queue_item_id,
        now_iso=now_iso,
    )
    if not plan.accepted or plan.status not in {
        RESIDENT_QUEUE_ORCHESTRATION_PLAN_READY,
        RESIDENT_QUEUE_ORCHESTRATION_PLAN_COMPLETE,
    }:
        return RedDogMainResidentQueuePlanBootstrapResult(
            ready=False,
            status=REDDOG_RESIDENT_QUEUE_PLAN_BOOTSTRAP_NOT_READY,
            plan_id=plan.plan_id,
            queue_item_id=plan.selected_queue_item_id,
            selected_slice=plan.selected_slice,
            next_action=plan.next_action,
            current_stage=plan.current_stage,
            accepted_stage_count=len(plan.accepted_stages),
            rejection_reasons=tuple(plan.rejection_reasons),
        )

    return RedDogMainResidentQueuePlanBootstrapResult(
        ready=True,
        status=REDDOG_RESIDENT_QUEUE_PLAN_BOOTSTRAP_READY,
        plan_id=plan.plan_id,
        queue_item_id=plan.selected_queue_item_id,
        selected_slice=plan.selected_slice,
        next_action=plan.next_action,
        current_stage=plan.current_stage,
        accepted_stage_count=len(plan.accepted_stages),
        rejection_reasons=(),
        chain_complete=plan.status == RESIDENT_QUEUE_ORCHESTRATION_PLAN_COMPLETE,
    )


def _read_json_outside_repo(
    repo_root: Path,
    value: Path | str | None,
    *,
    missing_reason: str,
    inside_reason: str,
    unreadable_reason: str,
) -> tuple[Optional[Mapping[str, Any]], tuple[str, ...]]:
    if not value:
        return None, (missing_reason,)
    path = Path(value)
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    else:
        path = path.resolve()
    if _is_inside(path, repo_root):
        return None, (inside_reason,)
    if not path.exists() or not path.is_file():
        return None, (missing_reason,)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, (unreadable_reason,)
    if not isinstance(payload, Mapping):
        return None, (unreadable_reason,)
    return payload, ()


def _not_ready(reasons: tuple[str, ...]) -> RedDogMainResidentQueuePlanBootstrapResult:
    return RedDogMainResidentQueuePlanBootstrapResult(
        ready=False,
        status=REDDOG_RESIDENT_QUEUE_PLAN_BOOTSTRAP_NOT_READY,
        plan_id=None,
        queue_item_id=None,
        selected_slice=None,
        next_action=None,
        current_stage=None,
        accepted_stage_count=0,
        rejection_reasons=reasons,
    )


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


__all__ = [
    "REDDOG_RESIDENT_QUEUE_PLAN_BOOTSTRAP_NOT_READY",
    "REDDOG_RESIDENT_QUEUE_PLAN_BOOTSTRAP_READY",
    "RedDogMainResidentQueuePlanBootstrapResult",
    "run_reddog_main_resident_queue_orchestration_plan_bootstrap",
]
