"""Main-startup adapter for the RedDog WRE queue consumer dry-run."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    secure_read_confined_text,
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)

from modules.communication.moltbot_bridge.src.reddog_wre_queue_consumer_dryrun import (
    WRE_QUEUE_CONSUMER_DRYRUN_READY,
    plan_reddog_wre_queue_consumer_dry_run,
)


REDDOG_WRE_QUEUE_BOOTSTRAP_READY = "REDDOG_WRE_QUEUE_BOOTSTRAP_READY"
REDDOG_WRE_QUEUE_BOOTSTRAP_NOT_READY = "REDDOG_WRE_QUEUE_BOOTSTRAP_NOT_READY"


@dataclass(frozen=True)
class RedDogMainWREQueueConsumerBootstrapResult:
    ready: bool
    status: str
    queue_item_id: Optional[str]
    selected_slice: Optional[str]
    next_required_gate: Optional[str]
    execution_ready: bool
    rejection_reasons: tuple[str, ...]
    receipt_id: Optional[str] = None
    no_queue_mutation_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_worktree_created: bool = True
    no_shell_command_executed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pr_created: bool = True
    no_reward_settlement_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_main_wre_queue_consumer_bootstrap(
    *,
    repo_root: Path | str,
    runtime_allowed_root: Path | str | None = None,
    work_state_path: Path | str | None,
    now_iso: str | None = None,
    requested_queue_item_id: str | None = None,
) -> RedDogMainWREQueueConsumerBootstrapResult:
    """Load authoritative work state and dry-run consume one WRE queue item."""

    root = Path(repo_root).resolve()
    runtime_root, reasons = _resolve_runtime_root(root, runtime_allowed_root)
    if reasons:
        return _not_ready(reasons)
    assert runtime_root is not None
    path, reasons = _resolve_work_state_path(
        root,
        runtime_root,
        work_state_path,
    )
    if reasons:
        return _not_ready(reasons)
    assert path is not None
    try:
        snapshot = json.loads(
            secure_read_confined_text(path, allowed_root=runtime_root)
        )
    except Exception:
        return _not_ready(("malformed_authoritative_work_state",))

    result = plan_reddog_wre_queue_consumer_dry_run(
        snapshot,
        now_iso=now_iso,
        requested_queue_item_id=requested_queue_item_id,
    )
    return _bootstrap_result(result)


def _bootstrap_result(result: Any) -> RedDogMainWREQueueConsumerBootstrapResult:
    if not result.accepted or result.status != WRE_QUEUE_CONSUMER_DRYRUN_READY:
        return RedDogMainWREQueueConsumerBootstrapResult(
            ready=False,
            status=REDDOG_WRE_QUEUE_BOOTSTRAP_NOT_READY,
            queue_item_id=result.selected_queue_item_id,
            selected_slice=result.selected_slice,
            next_required_gate=result.next_required_gate,
            execution_ready=False,
            rejection_reasons=tuple(result.rejection_reasons),
        )
    receipt_id = result.receipt.receipt_id if result.receipt else None
    return RedDogMainWREQueueConsumerBootstrapResult(
        ready=True,
        status=REDDOG_WRE_QUEUE_BOOTSTRAP_READY,
        queue_item_id=result.selected_queue_item_id,
        selected_slice=result.selected_slice,
        next_required_gate=result.next_required_gate,
        execution_ready=result.execution_ready,
        rejection_reasons=(),
        receipt_id=receipt_id,
    )


def _resolve_runtime_root(
    repo_root: Path,
    value: Path | str | None,
) -> tuple[Optional[Path], tuple[str, ...]]:
    if value is None or not str(value).strip():
        return None, ("missing_runtime_artifact_root",)
    runtime_root = Path(os.path.abspath(Path(value).expanduser()))
    try:
        return validate_runtime_root_path(runtime_root, repo_root=repo_root), ()
    except ValueError:
        return None, ("invalid_runtime_artifact_root",)


def _resolve_work_state_path(
    repo_root: Path,
    runtime_root: Path,
    value: Path | str | None,
) -> tuple[Optional[Path], tuple[str, ...]]:
    if not value:
        return None, ("missing_authoritative_work_state_path",)
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path(os.path.abspath(repo_root / path))
    else:
        path = Path(os.path.abspath(path))
    if _is_inside(path, repo_root):
        return None, ("work_state_path_inside_repo",)
    try:
        path = validate_runtime_artifact_path(
            path,
            repo_root=repo_root,
            allowed_root=runtime_root,
        )
    except ValueError:
        return None, ("work_state_path_outside_runtime_root_or_linked",)
    if not path.exists() or not path.is_file():
        return None, ("missing_authoritative_work_state",)
    return path, ()


def _not_ready(reasons: tuple[str, ...]) -> RedDogMainWREQueueConsumerBootstrapResult:
    return RedDogMainWREQueueConsumerBootstrapResult(
        ready=False,
        status=REDDOG_WRE_QUEUE_BOOTSTRAP_NOT_READY,
        queue_item_id=None,
        selected_slice=None,
        next_required_gate=None,
        execution_ready=False,
        rejection_reasons=reasons,
    )


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


__all__ = [
    "REDDOG_WRE_QUEUE_BOOTSTRAP_NOT_READY",
    "REDDOG_WRE_QUEUE_BOOTSTRAP_READY",
    "RedDogMainWREQueueConsumerBootstrapResult",
    "run_reddog_main_wre_queue_consumer_bootstrap",
]
