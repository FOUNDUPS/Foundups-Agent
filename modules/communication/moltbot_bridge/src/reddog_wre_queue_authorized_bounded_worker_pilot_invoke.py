"""RedDog queue-authorized bounded worker pilot explicit invoke guard.

Slice: REDDOG_WRE_QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_PHASE1

This module consumes an accepted queue-authorized worktree-create result plus
accepted generic-writer and governed-shell dry-run receipts, then invokes the
existing bounded worktree worker pilot. It may materialize only the declared
text artifacts inside the already-created isolated worktree. It does not run
shell commands, enqueue OpenClaw, dispatch Hermes, create PRs, merge, settle
rewards, or mutate HoloIndex.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_bounded_worktree_worker_execution_pilot import (
    BOUNDED_WORKTREE_PILOT_ACCEPT,
    BoundedWorktreeWorkerExecutionPilotResult,
    run_bounded_worktree_worker_execution_pilot,
)
from modules.communication.moltbot_bridge.src.reddog_generic_agent_worktree_writer_dryrun import (
    GENERIC_WRITER_DRYRUN_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_governed_shell_runner_dryrun import (
    GOVERNED_SHELL_DRYRUN_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_operational_spine import (
    WORKTREE_SPINE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_worktree_create_invoke import (
    QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_worktree_create import (
    WORKTREE_CREATE_ACCEPT,
)


QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT = (
    "QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT"
)
QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT = (
    "QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT"
)


class QueueAuthorizedBoundedWorkerPilotInvokeReason:
    EXPLICIT_INVOKE_MISSING = "REJECT_EXPLICIT_QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_MISSING"
    WORKTREE_CREATE_NOT_ACCEPTED = "REJECT_QUEUE_WORKTREE_CREATE_NOT_ACCEPTED"
    WORKTREE_CREATE_PAYLOAD_MISSING = "REJECT_WORKTREE_CREATE_PAYLOAD_MISSING"
    WORKTREE_CREATE_PAYLOAD_NOT_ACCEPTED = "REJECT_WORKTREE_CREATE_PAYLOAD_NOT_ACCEPTED"
    WORKTREE_CREATE_MUTATION_FLAGS_INVALID = "REJECT_WORKTREE_CREATE_MUTATION_FLAGS_INVALID"
    GENERIC_WRITER_NOT_ACCEPTED = "REJECT_GENERIC_WRITER_DRYRUN_NOT_ACCEPTED"
    GENERIC_WRITER_RECEIPT_MISSING = "REJECT_GENERIC_WRITER_RECEIPT_MISSING"
    GOVERNED_SHELL_NOT_ACCEPTED = "REJECT_GOVERNED_SHELL_DRYRUN_NOT_ACCEPTED"
    GOVERNED_SHELL_RECEIPT_MISSING = "REJECT_GOVERNED_SHELL_RECEIPT_MISSING"
    WORK_ORDER_ID_MISMATCH = "REJECT_WORK_ORDER_ID_MISMATCH"
    ARTIFACT_CONTENTS_INVALID = "REJECT_ARTIFACT_CONTENTS_INVALID"
    PILOT_NOT_ACCEPTED = "REJECT_BOUNDED_WORKTREE_PILOT_NOT_ACCEPTED"


@dataclass(frozen=True)
class QueueAuthorizedBoundedWorkerPilotInvokeResult:
    decision: str
    rejection_reasons: List[str] = field(default_factory=list)
    pilot_result: Optional[BoundedWorktreeWorkerExecutionPilotResult] = None
    explicit_queue_authorized_bounded_worker_pilot_requested: bool = False
    bounded_task_execution_performed: bool = False
    bounded_file_edit_performed: bool = False
    shell_command_executed: bool = False
    draft_pr_created: bool = False
    merge_performed: bool = False
    openclaw_enqueue_performed: bool = False
    hermes_dispatch_performed: bool = False
    reward_settlement_performed: bool = False
    holoindex_reindex_performed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["pilot_result"] = self.pilot_result.to_dict() if self.pilot_result else None
        return payload


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    if isinstance(value, Mapping):
        return value
    return {}


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _dedupe(values: Sequence[str]) -> List[str]:
    return list(dict.fromkeys(str(v) for v in values if str(v or "").strip()))


def _reject(
    reasons: Sequence[str],
    *,
    explicit_requested: bool,
    pilot_result: Optional[BoundedWorktreeWorkerExecutionPilotResult] = None,
) -> QueueAuthorizedBoundedWorkerPilotInvokeResult:
    return QueueAuthorizedBoundedWorkerPilotInvokeResult(
        decision=QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT,
        rejection_reasons=_dedupe(reasons),
        pilot_result=pilot_result,
        explicit_queue_authorized_bounded_worker_pilot_requested=explicit_requested,
        bounded_task_execution_performed=bool(
            pilot_result.task_execution_performed if pilot_result else False
        ),
        bounded_file_edit_performed=bool(
            pilot_result.file_edit_performed if pilot_result else False
        ),
        shell_command_executed=bool(pilot_result.shell_command_executed if pilot_result else False),
        draft_pr_created=bool(pilot_result.draft_pr_created if pilot_result else False),
        merge_performed=bool(pilot_result.merge_performed if pilot_result else False),
        openclaw_enqueue_performed=bool(
            pilot_result.openclaw_enqueue_performed if pilot_result else False
        ),
        hermes_dispatch_performed=bool(pilot_result.hermes_dispatch_performed if pilot_result else False),
        reward_settlement_performed=bool(
            pilot_result.reward_settlement_performed if pilot_result else False
        ),
        holoindex_reindex_performed=bool(
            pilot_result.holoindex_reindex_performed if pilot_result else False
        ),
    )


def _writer_receipt(writer_result: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(writer_result.get("receipt"))


def _shell_receipt(shell_result: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(shell_result.get("receipt"))


def _work_order_ids(
    *,
    work_order: Mapping[str, Any],
    worktree_create: Mapping[str, Any],
    writer_receipt: Mapping[str, Any],
    shell_receipt: Mapping[str, Any],
) -> List[str]:
    return [
        str(work_order.get("work_order_id") or ""),
        str(worktree_create.get("work_order_id") or ""),
        str(writer_receipt.get("work_order_id") or ""),
        str(shell_receipt.get("work_order_id") or ""),
    ]


def _ids_match(ids: Sequence[str]) -> bool:
    return bool(ids) and bool(ids[0]) and all(value == ids[0] for value in ids)


def _spine_payload(
    *,
    work_order_id: str,
    queue_worktree_create_result: Mapping[str, Any],
    worktree_create_result: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "decision": WORKTREE_SPINE_ACCEPT,
        "work_order_id": work_order_id,
        "result_digest": _digest(
            {
                "queue_worktree_create_result": queue_worktree_create_result,
                "worktree_create_result": worktree_create_result,
            }
        ),
        "no_task_execution_performed": True,
        "no_file_edit_performed": True,
        "no_pr_created": True,
        "no_live_openclaw_enqueue": True,
        "no_hermes_dispatch": True,
        "merge_performed": False,
        "worktree_create_result": dict(worktree_create_result),
    }


def invoke_reddog_wre_queue_authorized_bounded_worker_pilot(
    *,
    explicit_queue_authorized_bounded_worker_pilot_requested: bool,
    queue_worktree_create_result: Mapping[str, Any],
    generic_writer_dryrun_result: Mapping[str, Any],
    governed_shell_dryrun_result: Mapping[str, Any],
    artifact_contents: Mapping[str, Any],
    work_order: Mapping[str, Any],
    repo_root: Path,
    operation_cwd: Optional[Path] = None,
    holoindex_evidence: Optional[Mapping[str, Any]] = None,
) -> QueueAuthorizedBoundedWorkerPilotInvokeResult:
    """Materialize bounded artifacts only after the queue-authorized chain accepts."""

    if explicit_queue_authorized_bounded_worker_pilot_requested is not True:
        return _reject(
            [QueueAuthorizedBoundedWorkerPilotInvokeReason.EXPLICIT_INVOKE_MISSING],
            explicit_requested=False,
        )

    reasons: List[str] = []
    queue_worktree = _mapping(queue_worktree_create_result)
    if queue_worktree.get("decision") != QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT:
        reasons.append(QueueAuthorizedBoundedWorkerPilotInvokeReason.WORKTREE_CREATE_NOT_ACCEPTED)

    worktree_create = _mapping(queue_worktree.get("worktree_create_result"))
    if not worktree_create:
        reasons.append(QueueAuthorizedBoundedWorkerPilotInvokeReason.WORKTREE_CREATE_PAYLOAD_MISSING)
    elif worktree_create.get("decision") != WORKTREE_CREATE_ACCEPT:
        reasons.append(
            QueueAuthorizedBoundedWorkerPilotInvokeReason.WORKTREE_CREATE_PAYLOAD_NOT_ACCEPTED
        )

    if worktree_create and (
        worktree_create.get("no_task_execution_performed") is not True
        or worktree_create.get("no_file_edit_performed") is not True
        or worktree_create.get("no_pr_created") is not True
        or worktree_create.get("merge_performed") is not False
    ):
        reasons.append(
            QueueAuthorizedBoundedWorkerPilotInvokeReason.WORKTREE_CREATE_MUTATION_FLAGS_INVALID
        )

    writer = _mapping(generic_writer_dryrun_result)
    writer_receipt = _writer_receipt(writer)
    if writer.get("decision") != GENERIC_WRITER_DRYRUN_ACCEPT:
        reasons.append(QueueAuthorizedBoundedWorkerPilotInvokeReason.GENERIC_WRITER_NOT_ACCEPTED)
    if not writer_receipt:
        reasons.append(QueueAuthorizedBoundedWorkerPilotInvokeReason.GENERIC_WRITER_RECEIPT_MISSING)

    shell = _mapping(governed_shell_dryrun_result)
    shell_receipt = _shell_receipt(shell)
    if shell.get("decision") != GOVERNED_SHELL_DRYRUN_ACCEPT:
        reasons.append(QueueAuthorizedBoundedWorkerPilotInvokeReason.GOVERNED_SHELL_NOT_ACCEPTED)
    if not shell_receipt:
        reasons.append(QueueAuthorizedBoundedWorkerPilotInvokeReason.GOVERNED_SHELL_RECEIPT_MISSING)

    if worktree_create and writer_receipt and shell_receipt:
        if not _ids_match(
            _work_order_ids(
                work_order=work_order,
                worktree_create=worktree_create,
                writer_receipt=writer_receipt,
                shell_receipt=shell_receipt,
            )
        ):
            reasons.append(QueueAuthorizedBoundedWorkerPilotInvokeReason.WORK_ORDER_ID_MISMATCH)

    if not isinstance(artifact_contents, Mapping):
        reasons.append(QueueAuthorizedBoundedWorkerPilotInvokeReason.ARTIFACT_CONTENTS_INVALID)

    if reasons:
        return _reject(reasons, explicit_requested=True)

    work_order_id = str(work_order.get("work_order_id"))
    request = {
        "work_order_id": work_order_id,
        "repo_root": str(Path(repo_root)),
        "worktree_path": str(worktree_create.get("worktree_path") or ""),
        "operation_cwd": str(operation_cwd or worktree_create.get("worktree_path") or ""),
        "canonical_root": str(writer_receipt.get("canonical_root") or ""),
        "worktree_spine_result": _spine_payload(
            work_order_id=work_order_id,
            queue_worktree_create_result=queue_worktree,
            worktree_create_result=worktree_create,
        ),
        "generic_writer_dryrun_result": writer,
        "governed_shell_dryrun_result": shell,
        "artifact_contents": dict(artifact_contents),
        "holoindex_evidence": dict(holoindex_evidence or work_order.get("holoindex_evidence") or {}),
    }
    pilot = run_bounded_worktree_worker_execution_pilot(request)
    if pilot.decision != BOUNDED_WORKTREE_PILOT_ACCEPT:
        return _reject(
            [
                QueueAuthorizedBoundedWorkerPilotInvokeReason.PILOT_NOT_ACCEPTED,
                *pilot.rejection_reasons,
            ],
            explicit_requested=True,
            pilot_result=pilot,
        )

    return QueueAuthorizedBoundedWorkerPilotInvokeResult(
        decision=QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT,
        rejection_reasons=[],
        pilot_result=pilot,
        explicit_queue_authorized_bounded_worker_pilot_requested=True,
        bounded_task_execution_performed=pilot.task_execution_performed,
        bounded_file_edit_performed=pilot.file_edit_performed,
        shell_command_executed=pilot.shell_command_executed,
        draft_pr_created=pilot.draft_pr_created,
        merge_performed=pilot.merge_performed,
        openclaw_enqueue_performed=pilot.openclaw_enqueue_performed,
        hermes_dispatch_performed=pilot.hermes_dispatch_performed,
        reward_settlement_performed=pilot.reward_settlement_performed,
        holoindex_reindex_performed=pilot.holoindex_reindex_performed,
    )


__all__ = [
    "QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT",
    "QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT",
    "QueueAuthorizedBoundedWorkerPilotInvokeReason",
    "QueueAuthorizedBoundedWorkerPilotInvokeResult",
    "invoke_reddog_wre_queue_authorized_bounded_worker_pilot",
]
