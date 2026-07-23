"""RedDog WRE execution valve evaluator (closed by default, pure evaluation).

Slice: REDDOG_WRE_EXECUTION_VALVE_PHASE1
Contract: docs/audits/architecture/REDDOG_WRE_EXECUTION_VALVE_CONTRACT_PHASE1.md

Evaluates whether a fully gated RedDog spine may proceed to adapter dry-run or
worktree-create slices. Default is VALVE_CLOSED unless explicit environment flags
are set. No worktrees, branches, file edits, subprocess, git, or WRE execution.

WSP 97 TRUTH BOUNDARIES:
  DOES:
    - Require accepted spine artifacts (#893-#898)
    - Enforce #901 intake targets (FoundUpJob / autonomous_task)
    - Reject AssignmentDispatcher and direct launch paths
    - Emit valve_state, gates_checked, rejection_reasons, decision_digest
    - Always set no_execution_performed: true

  DOES NOT:
    - Create worktrees, branches, PRs, or mutate repository content
    - Invoke OpenClaw, Hermes, WRE executor, Skillz, or subprocess/git/gh
    - Wire extension runtime or dispatch live workers
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, Optional, Union

from modules.communication.moltbot_bridge.src.reddog_governed_work_order_dryrun import (
    _is_write_sensitive_operation,
    _normalize_operation,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_work_order_policy_gate import (
    DEFAULT_PERMISSION_TTL_SECONDS,
    POLICY_ACCEPT,
    TRUTH_NEEDS_VERIFICATION,
    permission_truth_label,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_runtime_invocation import (
    INVOCATION_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_executor_dryrun import (
    EXECUTOR_PLAN_ACCEPT,
)

VALVE_CLOSED = "VALVE_CLOSED"
VALVE_OPEN_DRYRUN_ONLY = "VALVE_OPEN_DRYRUN_ONLY"
VALVE_OPEN_LIVE_ENQUEUE = "VALVE_OPEN_LIVE_ENQUEUE"
VALVE_OPEN_WORKTREE_CREATE = "VALVE_OPEN_WORKTREE_CREATE"

INTAKE_FOUNDUP_JOB = "foundup_job"
INTAKE_AUTONOMOUS_TASK = "autonomous_task"
INTAKE_ASSIGNMENT_DISPATCHER = "assignment_dispatcher"

CANONICAL_INTAKE_TARGETS = frozenset({INTAKE_FOUNDUP_JOB, INTAKE_AUTONOMOUS_TASK})
FORBIDDEN_INTAKE_TARGETS = frozenset({INTAKE_ASSIGNMENT_DISPATCHER})

CANONICAL_ENVIRONMENT_SCHEMA_VERSION = "reddog_execution_valve_environment.v1"
CANONICAL_AUTHORIZATION_MODE = "signed_work_authority_consensus"
CANONICAL_PROVENANCE_SCHEMA_VERSION = "reddog_execution_valve_environment_supply_receipt.v1"
CANONICAL_BINDING_FIELDS = frozenset(
    {
        "work_order_id",
        "requested_operation",
        "valve_state_required",
        "queue_item_id",
        "claim_id",
        "determination_receipt_id",
        "repo_full_name",
        "foundup_id",
        "principal_id",
        "reddog_id",
        "key_epoch",
        "permission_snapshot_digest",
        "authority_profile_digest",
        "work_state_revision",
        "wsp15_allocation_receipt_id",
        "wsp15_allocation_digest",
        "model_selection_receipt_id",
        "model_selection_digest",
        "model_runtime_binding_receipt_id",
        "model_runtime_binding_digest",
        "memex_supply_receipt_id",
        "memex_supply_digest",
        "resolver_supply_receipt_id",
        "consensus_receipt_digest",
        "sovereign_authorization_digest",
    }
)
_CANONICAL_ENVIRONMENT_FIELDS = CANONICAL_BINDING_FIELDS | {
    "schema_version",
    "authorization_mode",
    "authorization_binding_digest",
    "requested_valve_state",
    "valve_dryrun_enabled",
    "valve_live_enqueue_enabled",
    "valve_worktree_create_enabled",
    "supply_provenance",
}


@dataclass
class ExecutionValveRequest:
    work_order: Mapping[str, Any]
    policy_gate_receipt: Mapping[str, Any]
    reddog_work_order_receipt: Mapping[str, Any]
    invocation_result: Mapping[str, Any]
    executor_plan_result: Mapping[str, Any]
    intake_target: str
    permission_snapshot: Mapping[str, Any]
    direct_worker_launch: bool = False
    direct_model_launch: bool = False
    direct_wre_executor_call: bool = False
    protected_branch_mutation: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionValveEnvironment:
    valve_dryrun_enabled: bool = False
    valve_live_enqueue_enabled: bool = False
    valve_worktree_create_enabled: bool = False
    sovereign_live_enqueue_token: Optional[str] = None
    sovereign_worktree_token: Optional[str] = None
    permission_ttl_seconds: int = DEFAULT_PERMISSION_TTL_SECONDS
    permission_expires_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GovernedExecutionValveEnvironment:
    """Allowlisted canonical environment with no legacy token surface."""

    values: Mapping[str, Any]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "GovernedExecutionValveEnvironment":
        if set(value) != _CANONICAL_ENVIRONMENT_FIELDS:
            raise ValueError("canonical_environment_field_set_mismatch")
        if any(key in value for key in ("sovereign_live_enqueue_token", "sovereign_worktree_token")):
            raise ValueError("canonical_environment_token_key_forbidden")
        return cls(values=dict(value))

    def to_dict(self) -> Dict[str, Any]:
        return {key: self.values[key] for key in sorted(_CANONICAL_ENVIRONMENT_FIELDS)}


@dataclass
class ExecutionValveDecision:
    valve_state: str
    work_order_id: str
    rejection_reasons: List[str]
    gates_checked: List[str]
    no_execution_performed: bool
    decision_digest: str
    intake_target: str = ""
    authorization_mode: str = "legacy_environment"
    authorization_binding_digest: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _utc_now(now: Optional[datetime] = None) -> datetime:
    value = now or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc)


def _iso8601(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def _parse_iso8601(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _mapping(value: Union[ExecutionValveRequest, Mapping[str, Any]]) -> Mapping[str, Any]:
    if isinstance(value, ExecutionValveRequest):
        return value.to_dict()
    return value


def _env_mapping(value: Union[ExecutionValveEnvironment, Mapping[str, Any]]) -> Mapping[str, Any]:
    if isinstance(value, ExecutionValveEnvironment):
        return value.to_dict()
    return value


def _permission_snapshot_fresh(
    captured_at: str,
    *,
    now: datetime,
    ttl_seconds: int = DEFAULT_PERMISSION_TTL_SECONDS,
    expires_at: Optional[str] = None,
) -> bool:
    if expires_at:
        try:
            return now <= _parse_iso8601(expires_at)
        except ValueError:
            return False
    try:
        captured = _parse_iso8601(captured_at)
        return now <= captured + timedelta(seconds=max(1, ttl_seconds))
    except ValueError:
        return False


def _work_order_id(work_order: Mapping[str, Any]) -> str:
    return str(work_order.get("work_order_id") or "unknown")


def _holoindex_index_gap_write_blocked(work_order: Mapping[str, Any]) -> bool:
    holo = work_order.get("holoindex_evidence")
    if not isinstance(holo, Mapping):
        return False
    op_norm = _normalize_operation(str(work_order.get("requested_operation") or ""))
    gap = holo.get("index_gap_detected") is True or holo.get("retrieval_quality") == "INDEX_GAP"
    return gap and _is_write_sensitive_operation(op_norm)


def _validate_spine_chain(
    request: Mapping[str, Any],
    gates_checked: List[str],
) -> List[str]:
    reasons: List[str] = []
    work_order = dict(request.get("work_order") or {})
    policy = dict(request.get("policy_gate_receipt") or {})
    receipt = dict(request.get("reddog_work_order_receipt") or {})
    invocation = dict(request.get("invocation_result") or {})
    executor = dict(request.get("executor_plan_result") or {})

    gates_checked.append("policy_gate_accepted")
    if policy.get("decision") != POLICY_ACCEPT:
        reasons.append("policy_gate_not_accepted")
    if policy.get("no_execution_performed") is not True:
        reasons.append("policy_gate_execution_detected")

    gates_checked.append("reddog_work_order_receipt_present")
    if not receipt.get("receipt_id") or not receipt.get("receipt_digest"):
        reasons.append("missing_reddog_work_order_receipt")
    if receipt.get("no_execution_performed") is not True:
        reasons.append("receipt_execution_detected")
    policy_digest = str(policy.get("receipt_digest") or "")
    if policy_digest and receipt.get("policy_gate_receipt_digest") != policy_digest:
        reasons.append("receipt_policy_digest_mismatch")

    gates_checked.append("invocation_dryrun_accepted")
    if invocation.get("decision") != INVOCATION_ACCEPT:
        reasons.append("invocation_not_accepted")
    if invocation.get("no_execution_performed") is not True:
        reasons.append("invocation_execution_detected")
    if not invocation.get("receipt_digest"):
        reasons.append("missing_invocation_receipt_digest")
    if policy_digest and invocation.get("policy_gate_receipt_digest") != policy_digest:
        reasons.append("invocation_policy_digest_mismatch")

    gates_checked.append("executor_plan_accepted")
    if executor.get("decision") != EXECUTOR_PLAN_ACCEPT:
        reasons.append("executor_plan_not_accepted")
    if executor.get("no_mutation_performed") is not True:
        reasons.append("executor_mutation_detected")
    plan = executor.get("plan")
    if not isinstance(plan, Mapping):
        reasons.append("missing_executor_plan")
    else:
        if not plan.get("plan_id") or not plan.get("plan_digest"):
            reasons.append("incomplete_executor_plan")
        inv_digest = str(invocation.get("receipt_digest") or "")
        if inv_digest and plan.get("invocation_receipt_digest") != inv_digest:
            reasons.append("executor_plan_invocation_digest_mismatch")

    gates_checked.append("receipt_chain_complete")
    if not policy_digest:
        reasons.append("missing_policy_gate_receipt_digest")

    gates_checked.append("index_gap_write_policy")
    if _holoindex_index_gap_write_blocked(work_order):
        reasons.append("index_gap_blocks_write_operation")

    return reasons


def _validate_intake_and_launch(request: Mapping[str, Any], gates_checked: List[str]) -> List[str]:
    reasons: List[str] = []
    intake = str(request.get("intake_target") or "").strip().lower()

    gates_checked.append("intake_target_canonical")
    if intake in FORBIDDEN_INTAKE_TARGETS:
        reasons.append("assignment_dispatcher_forbidden_target")
    elif intake not in CANONICAL_INTAKE_TARGETS:
        reasons.append("intake_target_not_canonical")

    gates_checked.append("direct_launch_forbidden")
    if request.get("direct_worker_launch") is True:
        reasons.append("direct_worker_launch_forbidden")
    if request.get("direct_model_launch") is True:
        reasons.append("direct_model_launch_forbidden")
    if request.get("direct_wre_executor_call") is True:
        reasons.append("direct_wre_executor_call_forbidden")
    if request.get("protected_branch_mutation") is True:
        reasons.append("protected_branch_mutation_forbidden")

    return reasons


def _validate_permission(
    request: Mapping[str, Any],
    environment: Mapping[str, Any],
    *,
    now: datetime,
    gates_checked: List[str],
) -> List[str]:
    reasons: List[str] = []
    work_order = dict(request.get("work_order") or {})
    snap = dict(request.get("permission_snapshot") or {})
    if not snap:
        snap = dict(work_order.get("repo_permission_snapshot") or {})

    gates_checked.append("permission_snapshot_present")
    if not snap.get("captured_at"):
        reasons.append("missing_permission_snapshot")
    if not snap.get("digest"):
        reasons.append("missing_permission_snapshot_digest")

    gates_checked.append("permission_snapshot_freshness")
    ttl = int(environment.get("permission_ttl_seconds") or DEFAULT_PERMISSION_TTL_SECONDS)
    expires_at = environment.get("permission_expires_at")
    captured_at = str(snap.get("captured_at") or "")
    if captured_at and not _permission_snapshot_fresh(
        captured_at,
        now=now,
        ttl_seconds=ttl,
        expires_at=str(expires_at) if expires_at else None,
    ):
        reasons.append("stale_permission_snapshot")

    gates_checked.append("permission_truth_for_write")
    level = str(snap.get("permission_level") or "")
    source = str(snap.get("source") or "")
    truth = permission_truth_label(level, source)
    op_norm = _normalize_operation(str(work_order.get("requested_operation") or ""))
    if truth == TRUTH_NEEDS_VERIFICATION and _is_write_sensitive_operation(op_norm):
        reasons.append("permission_needs_verification")

    return reasons


def _resolve_valve_state(
    environment: Mapping[str, Any],
    reasons: List[str],
) -> str:
    if reasons:
        return VALVE_CLOSED
    dryrun = bool(environment.get("valve_dryrun_enabled"))
    live_enqueue = bool(environment.get("valve_live_enqueue_enabled"))
    worktree = bool(environment.get("valve_worktree_create_enabled"))
    live_token = str(environment.get("sovereign_live_enqueue_token") or "").strip()
    token = str(environment.get("sovereign_worktree_token") or "").strip()

    if worktree:
        if token:
            return VALVE_OPEN_WORKTREE_CREATE
        return VALVE_CLOSED
    if live_enqueue:
        if live_token:
            return VALVE_OPEN_LIVE_ENQUEUE
        return VALVE_CLOSED
    if dryrun:
        return VALVE_OPEN_DRYRUN_ONLY
    return VALVE_CLOSED


def evaluate_reddog_execution_valve(
    request: Union[ExecutionValveRequest, Mapping[str, Any]],
    environment: Union[ExecutionValveEnvironment, Mapping[str, Any]],
    *,
    now: Optional[datetime] = None,
) -> ExecutionValveDecision:
    """Evaluate RedDog execution valve state. Pure evaluation; no execution performed."""
    req = _mapping(request)
    env = _env_mapping(environment)
    checked = _utc_now(now)
    checked_at = _iso8601(checked)
    work_order = dict(req.get("work_order") or {})
    work_order_id = _work_order_id(work_order)
    intake_target = str(req.get("intake_target") or "").strip().lower()

    gates_checked: List[str] = ["execution_valve_evaluator"]
    rejection_reasons: List[str] = []

    rejection_reasons.extend(_validate_spine_chain(req, gates_checked))
    rejection_reasons.extend(_validate_intake_and_launch(req, gates_checked))
    rejection_reasons.extend(
        _validate_permission(req, env, now=checked, gates_checked=gates_checked)
    )

    gates_checked.append("explicit_valve_flag_required")
    valve_state = _resolve_valve_state(env, rejection_reasons)
    if not rejection_reasons and valve_state == VALVE_CLOSED:
        if env.get("valve_worktree_create_enabled") and not str(
            env.get("sovereign_worktree_token") or ""
        ).strip():
            rejection_reasons.append("worktree_valve_missing_sovereign_token")
        elif env.get("valve_live_enqueue_enabled") and not str(
            env.get("sovereign_live_enqueue_token") or ""
        ).strip():
            rejection_reasons.append("live_enqueue_valve_missing_sovereign_token")
        else:
            rejection_reasons.append("explicit_valve_flag_missing")

    deduped = list(dict.fromkeys(rejection_reasons))
    if deduped:
        valve_state = VALVE_CLOSED

    body = {
        "valve_state": valve_state,
        "work_order_id": work_order_id,
        "intake_target": intake_target,
        "rejection_reasons": deduped,
        "gates_checked": gates_checked,
        "no_execution_performed": True,
        "checked_at": checked_at,
    }
    return ExecutionValveDecision(
        valve_state=valve_state,
        work_order_id=work_order_id,
        rejection_reasons=deduped,
        gates_checked=gates_checked,
        no_execution_performed=True,
        decision_digest=_canonical_digest(body),
        intake_target=intake_target,
    )


def evaluate_reddog_execution_valve_canonical(
    request: Union[ExecutionValveRequest, Mapping[str, Any]], environment: GovernedExecutionValveEnvironment, *,
    expected_bindings: Mapping[str, Any],
    permission_ttl_seconds: int,
    permission_expires_at: str,
    now: Optional[datetime] = None,
) -> ExecutionValveDecision:
    """Evaluate an allowlisted environment against independently verified bindings."""

    env = environment.to_dict()
    reasons = _validate_canonical_environment(env, expected_bindings)
    reasons.extend(_validate_canonical_request_bindings(_mapping(request), expected_bindings))
    if type(permission_ttl_seconds) is not int or not 1 <= permission_ttl_seconds <= 3600:
        reasons.append("canonical_permission_ttl_invalid")
    state = str(env.get("requested_valve_state") or "")
    internal = {
        "valve_dryrun_enabled": env.get("valve_dryrun_enabled") is True,
        "valve_live_enqueue_enabled": env.get("valve_live_enqueue_enabled") is True,
        "valve_worktree_create_enabled": env.get("valve_worktree_create_enabled") is True,
        "permission_ttl_seconds": permission_ttl_seconds,
        "permission_expires_at": permission_expires_at,
    }
    if not reasons and state == VALVE_OPEN_LIVE_ENQUEUE:
        internal["sovereign_live_enqueue_token"] = "governed-internal"
    if not reasons and state == VALVE_OPEN_WORKTREE_CREATE:
        internal["sovereign_worktree_token"] = "governed-internal"
    decision = evaluate_reddog_execution_valve(request, internal, now=now)
    combined = list(dict.fromkeys([*reasons, *decision.rejection_reasons]))
    valve_state = VALVE_CLOSED if combined else decision.valve_state
    binding_digest = str(env.get("authorization_binding_digest") or "")
    final_gates = [*decision.gates_checked, "canonical_governed_environment"]
    body = {
        **decision.to_dict(),
        "valve_state": valve_state,
        "rejection_reasons": combined,
        "gates_checked": final_gates,
        "authorization_mode": env.get("authorization_mode"),
        "authorization_binding_digest": binding_digest,
    }
    body.pop("decision_digest", None)
    return ExecutionValveDecision(
        valve_state=valve_state,
        work_order_id=decision.work_order_id,
        rejection_reasons=combined,
        gates_checked=final_gates,
        no_execution_performed=True,
        decision_digest=_canonical_digest(body),
        intake_target=decision.intake_target,
        authorization_mode=str(env.get("authorization_mode") or ""),
        authorization_binding_digest=binding_digest or None,
    )


def _validate_canonical_environment(
    environment: Mapping[str, Any], expected: Mapping[str, Any]
) -> List[str]:
    reasons: List[str] = []
    if set(environment) != _CANONICAL_ENVIRONMENT_FIELDS:
        reasons.append("canonical_environment_field_set_mismatch")
    if environment.get("schema_version") != CANONICAL_ENVIRONMENT_SCHEMA_VERSION:
        reasons.append("canonical_environment_schema_mismatch")
    if environment.get("authorization_mode") != CANONICAL_AUTHORIZATION_MODE:
        reasons.append("canonical_authorization_mode_mismatch")
    if set(expected) != CANONICAL_BINDING_FIELDS:
        reasons.append("canonical_expected_binding_field_set_mismatch")
    for field in CANONICAL_BINDING_FIELDS:
        if environment.get(field) != expected.get(field):
            reasons.append(f"canonical_environment_binding_mismatch:{field}")
    digest_fields = (
        "permission_snapshot_digest", "authority_profile_digest", "wsp15_allocation_digest",
        "model_selection_digest", "model_runtime_binding_digest", "memex_supply_digest",
        "consensus_receipt_digest", "sovereign_authorization_digest",
    )
    for field in digest_fields:
        value = expected.get(field)
        if value and not _valid_prefixed_sha256(value):
            reasons.append(f"canonical_binding_digest_malformed:{field}")
    state = str(environment.get("requested_valve_state") or "")
    expected_flags = {
        "valve_dryrun_enabled": state != VALVE_CLOSED,
        "valve_live_enqueue_enabled": state == VALVE_OPEN_LIVE_ENQUEUE,
        "valve_worktree_create_enabled": state == VALVE_OPEN_WORKTREE_CREATE,
    }
    if state not in {
        VALVE_CLOSED, VALVE_OPEN_DRYRUN_ONLY, VALVE_OPEN_LIVE_ENQUEUE,
        VALVE_OPEN_WORKTREE_CREATE,
    }:
        reasons.append("canonical_requested_valve_state_invalid")
    if state != VALVE_CLOSED and state != expected.get("valve_state_required"):
        reasons.append("canonical_required_valve_state_mismatch")
    for field, value in expected_flags.items():
        if environment.get(field) is not value:
            reasons.append(f"canonical_valve_flag_mismatch:{field}")
    if state in {VALVE_OPEN_LIVE_ENQUEUE, VALVE_OPEN_WORKTREE_CREATE}:
        for field in ("consensus_receipt_digest", "sovereign_authorization_digest"):
            if not str(expected.get(field) or "").startswith("sha256:"):
                reasons.append(f"canonical_high_authority_binding_missing:{field}")
    for first, second in (
        ("model_runtime_binding_receipt_id", "model_runtime_binding_digest"),
    ):
        if bool(expected.get(first)) != bool(expected.get(second)):
            reasons.append(f"canonical_binding_half_pair:{first}")
    expected_digest = "sha256:" + _canonical_digest(
        {
            "authorization_mode": environment.get("authorization_mode"),
            "bindings": {field: expected.get(field) for field in sorted(CANONICAL_BINDING_FIELDS)},
        }
    )
    if environment.get("authorization_binding_digest") != expected_digest:
        reasons.append("canonical_authorization_binding_digest_mismatch")
    reasons.extend(_validate_canonical_provenance(environment))
    return list(dict.fromkeys(reasons))


def validate_governed_execution_valve_environment(
    environment: GovernedExecutionValveEnvironment, expected_bindings: Mapping[str, Any]
) -> tuple[str, ...]:
    """Validate canonical structure/provenance against independent expected bindings."""

    return tuple(_validate_canonical_environment(environment.to_dict(), expected_bindings))


def _validate_canonical_request_bindings(
    request: Mapping[str, Any], expected: Mapping[str, Any]
) -> List[str]:
    work_order = request.get("work_order")
    if not isinstance(work_order, Mapping):
        return ["canonical_work_order_missing"]
    snapshot = work_order.get("repo_permission_snapshot")
    snapshot_digest = snapshot.get("digest") if isinstance(snapshot, Mapping) else None
    allocation = work_order.get("wsp15_allocation_receipt")
    checks = {
        "work_order_id": work_order.get("work_order_id"),
        "requested_operation": work_order.get("requested_operation"),
        "repo_full_name": work_order.get("repo_full_name"),
        "foundup_id": work_order.get("foundup_id"),
        "permission_snapshot_digest": snapshot_digest,
        "wsp15_allocation_receipt_id": (
            allocation.get("receipt_id") if isinstance(allocation, Mapping) else None
        ),
    }
    return [
        f"canonical_work_order_binding_mismatch:{field}"
        for field, value in checks.items()
        if value != expected.get(field)
    ]


def _validate_canonical_provenance(environment: Mapping[str, Any]) -> List[str]:
    provenance = environment.get("supply_provenance")
    if not isinstance(provenance, Mapping):
        return ["canonical_environment_provenance_missing"]
    core = dict(environment)
    core.pop("supply_provenance", None)
    environment_digest = "sha256:" + _canonical_digest(core)
    reasons: List[str] = []
    expected_fields = {
        "schema_version", "environment_digest", "authority_profile_digest",
        "work_state_revision", "permission_snapshot_digest", "resolver_supply_receipt_id",
        "no_secret_values_serialized", "no_execution_performed", "no_authority_minted",
        "no_repo_mutation_performed", "receipt_id",
    }
    if set(provenance) != expected_fields:
        reasons.append("canonical_environment_provenance_field_set_mismatch")
    if provenance.get("environment_digest") != environment_digest:
        reasons.append("canonical_environment_digest_mismatch")
    if provenance.get("schema_version") != CANONICAL_PROVENANCE_SCHEMA_VERSION:
        reasons.append("canonical_environment_provenance_schema_mismatch")
    receipt_body = dict(provenance)
    receipt_id = receipt_body.pop("receipt_id", None)
    expected_receipt_id = "sha256:" + _canonical_digest(receipt_body)
    if receipt_id != expected_receipt_id:
        reasons.append("canonical_environment_provenance_receipt_mismatch")
    required_true = (
        "no_secret_values_serialized",
        "no_execution_performed",
        "no_authority_minted",
        "no_repo_mutation_performed",
    )
    reasons.extend(
        f"canonical_environment_provenance_attestation_missing:{field}"
        for field in required_true
        if provenance.get(field) is not True
    )
    return reasons


def _valid_prefixed_sha256(value: Any) -> bool:
    text = str(value or "")
    if not text.startswith("sha256:") or len(text) != 71:
        return False
    try:
        int(text[7:], 16)
    except ValueError:
        return False
    return True


__all__ = [
    "CANONICAL_INTAKE_TARGETS",
    "CANONICAL_ENVIRONMENT_SCHEMA_VERSION",
    "CANONICAL_AUTHORIZATION_MODE",
    "CANONICAL_BINDING_FIELDS",
    "ExecutionValveDecision",
    "ExecutionValveEnvironment",
    "ExecutionValveRequest",
    "GovernedExecutionValveEnvironment",
    "FORBIDDEN_INTAKE_TARGETS",
    "INTAKE_ASSIGNMENT_DISPATCHER",
    "INTAKE_AUTONOMOUS_TASK",
    "INTAKE_FOUNDUP_JOB",
    "VALVE_CLOSED",
    "VALVE_OPEN_DRYRUN_ONLY",
    "VALVE_OPEN_LIVE_ENQUEUE",
    "VALVE_OPEN_WORKTREE_CREATE",
    "evaluate_reddog_execution_valve",
    "evaluate_reddog_execution_valve_canonical",
    "validate_governed_execution_valve_environment",
]
