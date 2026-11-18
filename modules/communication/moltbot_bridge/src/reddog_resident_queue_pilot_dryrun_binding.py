"""Resident queue bounded-worker pilot dry-run binding.

Slice: REDDOG_RESIDENT_QUEUE_PILOT_DRYRUN_BINDING_PHASE1

This module derives the generic-writer and governed-shell dry-run receipts for
the resident queue bounded-worker pilot from an explicit `bounded_worker_plan`
on the queue-bound work order plus already-recorded authority, valve, and
worktree chain results. It emits dry-run receipts only; it does not write files,
create worktrees, run commands, publish PRs, merge, settle rewards, enqueue
OpenClaw, dispatch Hermes, or re-index HoloIndex.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_generic_agent_worktree_writer_dryrun import (
    GENERIC_WRITER_DRYRUN_ACCEPT,
    plan_generic_agent_worktree_writer_dry_run,
)
from modules.communication.moltbot_bridge.src.reddog_wre_governed_shell_runner_dryrun import (
    GOVERNED_SHELL_DRYRUN_ACCEPT,
    plan_governed_shell_runner_dry_run,
)


PILOT_DRYRUN_BINDING_ACCEPT = "PILOT_DRYRUN_BINDING_ACCEPT"
PILOT_DRYRUN_BINDING_REJECT = "PILOT_DRYRUN_BINDING_REJECT"

FAIL_BOUNDED_WORKER_PLAN_MISSING = "FAIL_BOUNDED_WORKER_PLAN_MISSING"
FAIL_BOUNDED_WORKER_PLAN_INVALID = "FAIL_BOUNDED_WORKER_PLAN_INVALID"
FAIL_AUTHORITY_RUNTIME_MISSING = "FAIL_AUTHORITY_RUNTIME_MISSING"
FAIL_AUTHORITY_VERIFICATION_MISSING = "FAIL_AUTHORITY_VERIFICATION_MISSING"
FAIL_SIGNED_AUTHORITY_MISSING = "FAIL_SIGNED_AUTHORITY_MISSING"
FAIL_EXECUTION_VALVE_MISSING = "FAIL_EXECUTION_VALVE_MISSING"
FAIL_WORKTREE_CREATE_MISSING = "FAIL_WORKTREE_CREATE_MISSING"
FAIL_GENERIC_WRITER_DRYRUN_REJECTED = "FAIL_GENERIC_WRITER_DRYRUN_REJECTED"
FAIL_GOVERNED_SHELL_DRYRUN_REJECTED = "FAIL_GOVERNED_SHELL_DRYRUN_REJECTED"


@dataclass(frozen=True)
class ResidentQueuePilotDryRunBindingResult:
    decision: str
    accepted: bool
    generic_writer_dryrun_result: Dict[str, Any] = field(default_factory=dict)
    governed_shell_dryrun_result: Dict[str, Any] = field(default_factory=dict)
    rejection_reasons: list[str] = field(default_factory=list)
    no_file_write_performed: bool = True
    no_shell_command_executed: bool = True
    no_worktree_created: bool = True
    no_github_call_performed: bool = True
    no_pr_publish_performed: bool = True
    no_merge_performed: bool = True
    no_pattern_memory_write_performed: bool = True
    no_reward_settlement_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_resident_queue_pilot_dryruns(
    *,
    work_order: Mapping[str, Any],
    stage_results: Mapping[str, Mapping[str, Any]],
    repo_root: Path,
    operation_cwd: Optional[Path] = None,
    holoindex_evidence: Optional[Mapping[str, Any]] = None,
) -> ResidentQueuePilotDryRunBindingResult:
    """Build generic-writer and governed-shell dry-run receipts from chain state."""

    plan = _mapping(work_order.get("bounded_worker_plan"))
    reasons: list[str] = []
    if not plan:
        reasons.append(FAIL_BOUNDED_WORKER_PLAN_MISSING)

    authority_runtime = _mapping(stage_results.get("authority_runtime"))
    authority_result = _mapping(authority_runtime.get("authority_result"))
    work_authority = _mapping(authority_result.get("work_authority"))
    authority_receipt = _mapping(authority_result.get("receipt"))
    if not authority_runtime or authority_result.get("accepted") is not True:
        reasons.append(FAIL_AUTHORITY_RUNTIME_MISSING)
    if not work_authority:
        reasons.append(FAIL_SIGNED_AUTHORITY_MISSING)

    authority_verification = _mapping(stage_results.get("authority_verification"))
    verification = _mapping(authority_verification.get("verification_result"))
    if not authority_verification or verification.get("accepted") is not True:
        reasons.append(FAIL_AUTHORITY_VERIFICATION_MISSING)

    execution_valve = _mapping(stage_results.get("execution_valve"))
    valve_decision = _mapping(execution_valve.get("valve_decision"))
    if not execution_valve or not valve_decision:
        reasons.append(FAIL_EXECUTION_VALVE_MISSING)

    queue_worktree = _mapping(stage_results.get("worktree_create"))
    worktree_create = _mapping(queue_worktree.get("worktree_create_result"))
    worktree_path = str(worktree_create.get("worktree_path") or "")
    if not queue_worktree or not worktree_create or not worktree_path:
        reasons.append(FAIL_WORKTREE_CREATE_MISSING)

    required_plan_fields = (
        "operation",
        "domain_id",
        "domain_profile",
        "planned_artifacts",
        "shell_profile",
        "shell_argv",
        "selection_receipt",
        "signed_receipt_chain",
    )
    for field_name in required_plan_fields:
        if field_name not in plan or plan.get(field_name) in (None, "", (), [], {}):
            reasons.append(f"{FAIL_BOUNDED_WORKER_PLAN_INVALID}:{field_name}")

    if reasons:
        return _reject(reasons)

    signed_authority = {
        **dict(work_authority),
        "accepted": True,
        "signature_gate_digest": str(
            authority_receipt.get("work_authority_digest")
            or authority_receipt.get("receipt_id")
            or ""
        ),
    }
    permission_digest = str(
        _mapping(work_order.get("repo_permission_snapshot")).get("digest")
        or work_authority.get("permission_snapshot_digest")
        or ""
    )
    evidence = _mapping(holoindex_evidence) or _mapping(work_order.get("holoindex_evidence"))
    op_cwd = str(operation_cwd or worktree_path)
    allowed_paths = _list(plan.get("requested_allowed_paths")) or _list(work_order.get("allowed_paths"))

    writer = plan_generic_agent_worktree_writer_dry_run(
        {
            "work_order_id": str(work_order.get("work_order_id") or ""),
            "operation": str(plan.get("operation") or ""),
            "domain_id": str(plan.get("domain_id") or ""),
            "domain_profile": _mapping(plan.get("domain_profile")),
            "planned_artifacts": _list(plan.get("planned_artifacts")),
            "requested_allowed_paths": allowed_paths,
            "target_branch": str(work_order.get("branch_name") or ""),
            "repo_root": str(repo_root),
            "worktree_path": worktree_path,
            "operation_cwd": op_cwd,
            "selection_receipt": _mapping(plan.get("selection_receipt")),
            "signed_authority": signed_authority,
            "signed_receipt_chain": _mapping(plan.get("signed_receipt_chain")),
            "execution_valve_decision": valve_decision,
            "permission_snapshot_digest": permission_digest,
            "consensus_receipt_digest": plan.get("consensus_receipt_digest"),
            "holoindex_evidence": evidence,
        }
    )
    if writer.decision != GENERIC_WRITER_DRYRUN_ACCEPT:
        return _reject([FAIL_GENERIC_WRITER_DRYRUN_REJECTED, *writer.rejection_reasons])

    writer_payload = writer.to_dict()
    writer_receipt = _mapping(writer_payload.get("receipt"))
    shell = plan_governed_shell_runner_dry_run(
        {
            "work_order_id": str(work_order.get("work_order_id") or ""),
            "profile": _mapping(plan.get("shell_profile")),
            "argv": _list(plan.get("shell_argv")),
            "operation_cwd": op_cwd,
            "worktree_path": worktree_path,
            "repo_root": str(repo_root),
            "selection_receipt": _mapping(plan.get("selection_receipt")),
            "signed_authority": signed_authority,
            "signed_receipt_chain": _mapping(plan.get("signed_receipt_chain")),
            "execution_valve_decision": valve_decision,
            "generic_writer_dryrun_receipt": writer_receipt,
            "permission_snapshot_digest": permission_digest,
            "consensus_receipt_digest": plan.get("consensus_receipt_digest"),
            "stdin_policy": plan.get("stdin_policy") or "none",
            "env_policy": _mapping(plan.get("env_policy")) or {"scrubbed": True},
            "holoindex_evidence": evidence,
        }
    )
    if shell.decision != GOVERNED_SHELL_DRYRUN_ACCEPT:
        return _reject([FAIL_GOVERNED_SHELL_DRYRUN_REJECTED, *shell.rejection_reasons])

    return ResidentQueuePilotDryRunBindingResult(
        decision=PILOT_DRYRUN_BINDING_ACCEPT,
        accepted=True,
        generic_writer_dryrun_result=writer_payload,
        governed_shell_dryrun_result=shell.to_dict(),
        rejection_reasons=[],
    )


def _reject(reasons: list[str]) -> ResidentQueuePilotDryRunBindingResult:
    return ResidentQueuePilotDryRunBindingResult(
        decision=PILOT_DRYRUN_BINDING_REJECT,
        accepted=False,
        rejection_reasons=_dedupe(reasons),
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    return value if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            ordered.append(text)
    return ordered


__all__ = [
    "FAIL_AUTHORITY_RUNTIME_MISSING",
    "FAIL_AUTHORITY_VERIFICATION_MISSING",
    "FAIL_BOUNDED_WORKER_PLAN_INVALID",
    "FAIL_BOUNDED_WORKER_PLAN_MISSING",
    "FAIL_EXECUTION_VALVE_MISSING",
    "FAIL_GENERIC_WRITER_DRYRUN_REJECTED",
    "FAIL_GOVERNED_SHELL_DRYRUN_REJECTED",
    "FAIL_SIGNED_AUTHORITY_MISSING",
    "FAIL_WORKTREE_CREATE_MISSING",
    "PILOT_DRYRUN_BINDING_ACCEPT",
    "PILOT_DRYRUN_BINDING_REJECT",
    "ResidentQueuePilotDryRunBindingResult",
    "build_resident_queue_pilot_dryruns",
]
