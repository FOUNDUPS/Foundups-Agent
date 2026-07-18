"""Main-startup adapter for resident queue next-stage dispatch.

Slice: REDDOG_MAIN_RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_BOOTSTRAP_PHASE1

This adapter lets ``main.py`` invoke exactly one already-built resident queue
stage handler behind an explicit environment flag. Runtime handler selection is
assembled through the resident queue handler registry, but this bootstrap only
injects the dependencies it already owns. Later stages therefore fail closed as
missing-dependency registry entries until a dedicated runtime dependency slice
binds them.

It does not sign, verify signatures, open valves, spawn workers, create
worktrees, execute shell commands, enqueue OpenClaw, dispatch Hermes, publish
PRs, settle rewards, mutate repository files, or re-index HoloIndex.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)

from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    AtomicJsonResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT,
    invoke_reddog_resident_queue_next_stage_dispatch,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_stage_handler_registry import (
    build_reddog_resident_queue_stage_handler_registry,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_json_read import (
    read_reddog_runtime_json_mapping,
)


REDDOG_RESIDENT_QUEUE_DISPATCH_BOOTSTRAP_APPLIED = "REDDOG_RESIDENT_QUEUE_DISPATCH_BOOTSTRAP_APPLIED"
REDDOG_RESIDENT_QUEUE_DISPATCH_BOOTSTRAP_NOT_READY = "REDDOG_RESIDENT_QUEUE_DISPATCH_BOOTSTRAP_NOT_READY"


@dataclass(frozen=True)
class RedDogMainResidentQueueNextStageDispatchBootstrapResult:
    """Result emitted by the startup next-stage dispatch adapter."""

    accepted: bool
    status: str
    queue_item_id: Optional[str]
    selected_slice: Optional[str]
    dispatched_stage: Optional[str]
    next_action: Optional[str]
    chain_results_path: Optional[str]
    store_revision: Optional[str]
    rejection_reasons: tuple[str, ...]
    no_signing_performed: bool = True
    no_signature_verification_performed: bool = True
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


def run_reddog_main_resident_queue_next_stage_dispatch_bootstrap(
    *,
    repo_root: Path | str,
    runtime_allowed_root: Path | str | None = None,
    work_state_path: Path | str | None,
    chain_results_path: Path | str | None,
    authority_profile_path: Path | str | None,
    requested_queue_item_id: str | None = None,
    now_iso: str | None = None,
) -> RedDogMainResidentQueueNextStageDispatchBootstrapResult:
    """Load runtime inputs and dispatch the first resident queue stage."""

    root = Path(repo_root).resolve()
    if runtime_allowed_root is None:
        return _not_ready(("missing_runtime_artifact_root",), chain_results_path=None)
    runtime_root = Path(os.path.abspath(Path(runtime_allowed_root).expanduser()))
    try:
        validate_runtime_root_path(runtime_root, repo_root=root)
    except ValueError:
        return _not_ready(("invalid_runtime_artifact_root",), chain_results_path=None)
    snapshot, snapshot_reasons = _read_json_outside_repo(
        root,
        runtime_root,
        work_state_path,
        missing_reason="missing_authoritative_work_state_path",
        inside_reason="work_state_path_inside_repo",
        unreadable_reason="malformed_authoritative_work_state",
    )
    if snapshot_reasons:
        return _not_ready(snapshot_reasons, chain_results_path=None)
    assert snapshot is not None

    profile, profile_reasons = _read_json_outside_repo(
        root,
        runtime_root,
        authority_profile_path,
        missing_reason="missing_authority_profile_path",
        inside_reason="authority_profile_path_inside_repo",
        unreadable_reason="malformed_authority_profile",
    )
    if profile_reasons:
        return _not_ready(profile_reasons, chain_results_path=None)
    assert profile is not None

    chain_path, chain_reasons = _resolve_output_outside_repo(
        root,
        runtime_root,
        chain_results_path,
        missing_reason="missing_chain_results_path",
        inside_reason="chain_results_path_inside_repo",
    )
    if chain_reasons:
        return _not_ready(chain_reasons, chain_results_path=None)
    assert chain_path is not None

    store = AtomicJsonResidentQueueChainResultsStore(
        chain_path,
        allowed_root=runtime_root,
    )
    registry = build_reddog_resident_queue_stage_handler_registry(
        work_state_snapshot=snapshot,
        chain_results_store=store,
        authority_profile=profile,
        now_iso=now_iso or "",
    )
    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=snapshot,
        store=store,
        handlers=registry.handlers,
        now_iso=now_iso or "",
        requested_queue_item_id=requested_queue_item_id,
    )
    if result.accepted is not True or result.decision != RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT:
        return _not_ready(
            tuple(result.rejection_reasons or ("resident_queue_dispatch_rejected",)),
            chain_results_path=chain_path,
            queue_item_id=_plan_text(result.to_dict(), ("plan", "selected_queue_item_id")),
            selected_slice=_plan_text(result.to_dict(), ("plan", "selected_slice")),
            dispatched_stage=result.dispatched_stage,
            next_action=result.next_action,
        )

    record = result.record_result
    receipt = record.receipt if record else None
    return RedDogMainResidentQueueNextStageDispatchBootstrapResult(
        accepted=True,
        status=REDDOG_RESIDENT_QUEUE_DISPATCH_BOOTSTRAP_APPLIED,
        queue_item_id=receipt.queue_item_id if receipt else None,
        selected_slice=receipt.selected_slice if receipt else None,
        dispatched_stage=result.dispatched_stage,
        next_action=result.next_action,
        chain_results_path=str(chain_path),
        store_revision=receipt.store_revision if receipt else None,
        rejection_reasons=(),
    )


def _read_json_outside_repo(
    repo_root: Path,
    allowed_root: Path,
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
        path = Path(os.path.abspath(repo_root / path))
    else:
        path = Path(os.path.abspath(path))
    if _is_inside(path, repo_root):
        return None, (inside_reason,)
    if not path.exists() or not path.is_file():
        return None, (missing_reason,)
    try:
        validate_runtime_artifact_path(
            path, repo_root=repo_root, allowed_root=allowed_root
        )
        payload = read_reddog_runtime_json_mapping(path, allowed_root=allowed_root)
    except Exception:
        return None, (unreadable_reason,)
    if not isinstance(payload, Mapping):
        return None, (unreadable_reason,)
    return payload, ()


def _resolve_output_outside_repo(
    repo_root: Path,
    allowed_root: Path,
    value: Path | str | None,
    *,
    missing_reason: str,
    inside_reason: str,
) -> tuple[Optional[Path], tuple[str, ...]]:
    if not value:
        return None, (missing_reason,)
    path = Path(value)
    if not path.is_absolute():
        path = Path(os.path.abspath(repo_root / path))
    else:
        path = Path(os.path.abspath(path))
    if _is_inside(path, repo_root):
        return None, (inside_reason,)
    try:
        validate_runtime_artifact_path(
            path, repo_root=repo_root, allowed_root=allowed_root
        )
    except ValueError:
        return None, ("chain_results_path_outside_runtime_root_or_linked",)
    return path, ()


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


def _not_ready(
    reasons: tuple[str, ...],
    *,
    chain_results_path: Path | None,
    queue_item_id: Optional[str] = None,
    selected_slice: Optional[str] = None,
    dispatched_stage: Optional[str] = None,
    next_action: Optional[str] = None,
) -> RedDogMainResidentQueueNextStageDispatchBootstrapResult:
    return RedDogMainResidentQueueNextStageDispatchBootstrapResult(
        accepted=False,
        status=REDDOG_RESIDENT_QUEUE_DISPATCH_BOOTSTRAP_NOT_READY,
        queue_item_id=queue_item_id,
        selected_slice=selected_slice,
        dispatched_stage=dispatched_stage,
        next_action=next_action,
        chain_results_path=str(chain_results_path) if chain_results_path else None,
        store_revision=None,
        rejection_reasons=tuple(dict.fromkeys(str(reason) for reason in reasons if str(reason).strip())),
    )


def _plan_text(payload: Mapping[str, Any], path: tuple[str, str]) -> Optional[str]:
    parent = payload.get(path[0])
    if not isinstance(parent, Mapping):
        return None
    value = str(parent.get(path[1]) or "").strip()
    return value or None


__all__ = [
    "REDDOG_RESIDENT_QUEUE_DISPATCH_BOOTSTRAP_APPLIED",
    "REDDOG_RESIDENT_QUEUE_DISPATCH_BOOTSTRAP_NOT_READY",
    "RedDogMainResidentQueueNextStageDispatchBootstrapResult",
    "run_reddog_main_resident_queue_next_stage_dispatch_bootstrap",
]
