"""Canonical, non-secret execution-valve environment supplier.

The supplier materializes one outside-repository runtime artifact from already
promoted authority and work-state artifacts.  It does not mint authority,
execute work, contact a signer/model, or mutate repository state.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    canonical_reddog_wsp15_allocation_digest,
    validate_reddog_wsp15_allocation_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    CANONICAL_AUTHORIZATION_MODE,
    CANONICAL_BINDING_FIELDS,
    GovernedExecutionValveEnvironment,
    VALVE_CLOSED,
    VALVE_OPEN_DRYRUN_ONLY,
    VALVE_OPEN_LIVE_ENQUEUE,
    VALVE_OPEN_WORKTREE_CREATE,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
)


SCHEMA_VERSION = "reddog_execution_valve_environment.v1"
RECEIPT_SCHEMA_VERSION = "reddog_execution_valve_environment_supply_receipt.v1"
SUPPLY_ACCEPT = "EXECUTION_VALVE_ENVIRONMENT_SUPPLY_ACCEPT"
SUPPLY_REJECT = "EXECUTION_VALVE_ENVIRONMENT_SUPPLY_REJECT"
_STATES = {
    VALVE_CLOSED,
    VALVE_OPEN_DRYRUN_ONLY,
    VALVE_OPEN_LIVE_ENQUEUE,
    VALVE_OPEN_WORKTREE_CREATE,
}


@dataclass(frozen=True)
class ExecutionValveEnvironmentSupplyResult:
    accepted: bool
    status: str
    output_path: Optional[str]
    environment_digest: Optional[str]
    supply_receipt_id: Optional[str]
    rejection_reasons: tuple[str, ...]
    no_execution_performed: bool = True
    no_authority_minted: bool = True
    no_signing_performed: bool = True
    no_model_call_performed: bool = True
    no_repo_mutation_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_execution_valve_environment_supply(
    *,
    repo_root: Path | str,
    work_state: Mapping[str, Any],
    authority_profile: Mapping[str, Any],
    permission_snapshots: Mapping[str, Any],
    principal_authority_records: Mapping[str, Any],
    output_path: Path | str | None,
    requested_valve_state: str = VALVE_CLOSED,
    queue_item_id: str = "",
    now_epoch: int | None = None,
    permission_ttl_seconds: int = 300,
) -> ExecutionValveEnvironmentSupplyResult:
    """Validate governed inputs and atomically write a canonical valve artifact."""
    root = Path(repo_root).resolve()
    target, path_reasons = _output_path(output_path, root)
    state = str(requested_valve_state or VALVE_CLOSED)
    reasons = list(path_reasons)
    if state not in _STATES:
        reasons.append("requested_valve_state_invalid")
    lineage, lineage_reasons = _lineage(
        work_state, authority_profile, permission_snapshots, principal_authority_records, queue_item_id
    )
    reasons.extend(lineage_reasons)
    ttl = permission_ttl_seconds if type(permission_ttl_seconds) is int else 0
    if not 1 <= ttl <= 3600:
        reasons.append("permission_ttl_invalid")
    epoch = int(datetime.now(timezone.utc).timestamp()) if now_epoch is None else now_epoch
    if type(epoch) is not int:
        reasons.append("now_epoch_invalid")
    if reasons or target is None:
        return _reject(reasons)

    assert lineage is not None
    expires_epoch = min(epoch + ttl, int(lineage["permission_expires_at_epoch"]))
    if expires_epoch <= epoch:
        return _reject(("permission_snapshot_expired",))
    return _materialize_environment(target, state, lineage, ttl, expires_epoch)


def _materialize_environment(
    target: Path, state: str, lineage: Mapping[str, Any], ttl: int, expires_epoch: int,
) -> ExecutionValveEnvironmentSupplyResult:
    core = _environment_core(state, lineage, ttl, expires_epoch)
    environment_digest = _digest(core)
    receipt = _supply_receipt(core, lineage, environment_digest)
    payload = dict(core)
    payload["supply_provenance"] = receipt
    try:
        governed = GovernedExecutionValveEnvironment.from_mapping(payload)
        _write_json_atomic(target, governed.to_dict())
    except Exception:
        return _reject(("execution_valve_environment_write_failed",))
    return ExecutionValveEnvironmentSupplyResult(
        accepted=True,
        status=SUPPLY_ACCEPT,
        output_path=str(target),
        environment_digest=environment_digest,
        supply_receipt_id=str(receipt["receipt_id"]),
        rejection_reasons=(),
    )


def resolve_reddog_execution_valve_expected_bindings(
    *, work_state: Mapping[str, Any], authority_profile: Mapping[str, Any],
    permission_snapshots: Mapping[str, Any], principal_authority_records: Mapping[str, Any],
    queue_item_id: str,
) -> tuple[dict[str, Any] | None, tuple[str, ...]]:
    """Resolve canonical bindings from independent governed artifacts without writing."""

    lineage, reasons = _lineage(
        work_state, authority_profile, permission_snapshots,
        principal_authority_records, queue_item_id,
    )
    if reasons or lineage is None:
        return None, tuple(reasons)
    return {field: lineage[field] for field in CANONICAL_BINDING_FIELDS}, ()


def _lineage(
    work_state: Mapping[str, Any],
    profile: Mapping[str, Any],
    permissions: Mapping[str, Any],
    principals: Mapping[str, Any],
    queue_item_id: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    reasons: list[str] = []
    if work_state.get("schema_version") != "reddog_authoritative_work_state.v1":
        reasons.append("work_state_schema_invalid")
    queue, claim, allocation, expected, queue_reasons = _queue_lineage(work_state, queue_item_id)
    reasons.extend(queue_reasons)
    binding, authority_reasons = _authority_binding(profile, expected)
    reasons.extend(authority_reasons)
    snapshot, principal, resolver_reasons = _resolver_records(profile, permissions, principals)
    reasons.extend(resolver_reasons)
    reasons.extend(_binding_reasons(binding, expected))
    reasons.extend(_cross_bind(profile, snapshot, principal, queue, claim, expected))
    if reasons:
        return None, list(dict.fromkeys(reasons))
    return _lineage_payload(work_state, profile, permissions, snapshot, allocation, expected), []


def _authority_binding(
    profile: Mapping[str, Any], expected: Mapping[str, str]
) -> tuple[Mapping[str, Any], list[str]]:
    reasons: list[str] = []
    binding = profile.get("operational_context_binding")
    if not isinstance(binding, Mapping):
        reasons.append("authority_operational_context_missing")
        binding = {}
    required = (
        "principal_id", "principal_provider", "principal_public_key", "reddog_id",
        "reddog_public_key", "repo_full_name", "foundup_id", "permission_snapshot_digest",
        "key_epoch", "work_order_id", "requested_operation", "valve_state_required",
        "consensus_receipt_digest",
        "sovereign_authorization_digest",
    )
    if any(profile.get(key) in (None, "") for key in required):
        reasons.append("authority_profile_incomplete")
    if expected.get("work_order_id") != str(profile.get("work_order_id") or ""):
        reasons.append("authority_work_order_binding_mismatch")
    return binding, reasons


def _resolver_records(
    profile: Mapping[str, Any], permissions: Mapping[str, Any], principals: Mapping[str, Any]
) -> tuple[Mapping[str, Any], Mapping[str, Any], list[str]]:
    reasons: list[str] = []
    permission_digest = str(profile.get("permission_snapshot_digest") or "")
    snapshots = permissions.get("snapshots")
    snapshot = snapshots.get(permission_digest) if isinstance(snapshots, Mapping) else None
    principal_key = f'{profile.get("principal_provider")}|{profile.get("principal_id")}'
    records = principals.get("principals")
    principal = records.get(principal_key) if isinstance(records, Mapping) else None
    if not isinstance(snapshot, Mapping):
        reasons.append("permission_snapshot_binding_missing")
        snapshot = {}
    if not isinstance(principal, Mapping):
        reasons.append("principal_authority_binding_missing")
        principal = {}
    if permissions.get("resolver_supply_receipt_id") != principals.get("resolver_supply_receipt_id"):
        reasons.append("resolver_supply_receipt_mismatch")
    return snapshot, principal, reasons


def _queue_lineage(
    work_state: Mapping[str, Any], queue_item_id: str
) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], dict[str, str], list[str]]:
    reasons: list[str] = []
    queue = _select(work_state.get("wre_queue_items"), "queue_item_id", queue_item_id)
    claim_id = str(queue.get("claim_id") or "")
    claim = _select(work_state.get("worker_claims"), "claim_id", claim_id)
    if not queue or not claim:
        reasons.append("queue_lineage_missing")
    allocation = queue.get("wsp15_allocation_receipt")
    allocation = allocation if isinstance(allocation, Mapping) else {}
    if not validate_reddog_wsp15_allocation_receipt(allocation).accepted:
        reasons.append("wsp15_allocation_invalid")
    expected = {
        "work_order_id": "wre-queue-" + hashlib.sha256(
            str(queue.get("queue_item_id") or "").encode("utf-8")
        ).hexdigest()[:16],
        "queue_item_id": str(queue.get("queue_item_id") or ""),
        "claim_id": claim_id,
        "wsp15_allocation_receipt_id": str((allocation or {}).get("receipt_id") or ""),
        "model_selection_receipt_id": str(queue.get("model_selection_receipt_id") or ""),
        "model_selection_digest": str(queue.get("model_selection_digest") or ""),
        "model_runtime_binding_receipt_id": str(queue.get("model_runtime_binding_receipt_id") or ""),
        "model_runtime_binding_digest": str(queue.get("model_runtime_binding_digest") or ""),
        "memex_supply_receipt_id": str(queue.get("memex_supply_receipt_id") or ""),
        "memex_supply_digest": str(queue.get("memex_supply_digest") or ""),
        "determination_receipt_id": str(queue.get("source_determination_receipt_id") or ""),
    }
    return queue, claim, allocation, expected, reasons


def _binding_reasons(binding: Mapping[str, Any], expected: Mapping[str, str]) -> list[str]:
    reasons: list[str] = []
    binding_values = dict(binding)
    binding_values["determination_receipt_id"] = binding.get("determination_id")
    bound_allocation = binding.get("wsp15_allocation_receipt")
    binding_values["wsp15_allocation_receipt_id"] = (
        bound_allocation.get("receipt_id") if isinstance(bound_allocation, Mapping) else None
    )
    for key, value in expected.items():
        if not value and key not in {
            "model_runtime_binding_receipt_id", "model_runtime_binding_digest"
        }:
            reasons.append(f"authority_queue_binding_missing:{key}")
        elif str(binding_values.get(key) or "") != value:
            reasons.append(f"authority_queue_binding_mismatch:{key}")
    return reasons


def _lineage_payload(
    work_state: Mapping[str, Any], profile: Mapping[str, Any], permissions: Mapping[str, Any],
    snapshot: Mapping[str, Any], allocation: Mapping[str, Any], expected: Mapping[str, str],
) -> dict[str, Any]:
    return {
        **expected,
        "work_order_id": str(profile["work_order_id"]),
        "requested_operation": str(profile["requested_operation"]),
        "valve_state_required": str(profile["valve_state_required"]),
        "repo_full_name": str(profile["repo_full_name"]),
        "foundup_id": str(profile["foundup_id"]),
        "principal_id": str(profile["principal_id"]),
        "reddog_id": str(profile["reddog_id"]),
        "key_epoch": str(profile["key_epoch"]),
        "permission_snapshot_digest": str(profile["permission_snapshot_digest"]),
        "permission_expires_at_epoch": int(snapshot["expires_at"]),
        "sovereign_authorization_digest": str(profile["sovereign_authorization_digest"]),
        "consensus_receipt_digest": str(profile["consensus_receipt_digest"]),
        "authority_profile_digest": _digest(profile),
        "work_state_revision": str(work_state.get("revision") or ""),
        "wsp15_allocation_digest": canonical_reddog_wsp15_allocation_digest(allocation),
        "resolver_supply_receipt_id": str(permissions.get("resolver_supply_receipt_id") or ""),
    }


def _cross_bind(
    profile: Mapping[str, Any], snapshot: Mapping[str, Any], principal: Mapping[str, Any],
    queue: Mapping[str, Any], claim: Mapping[str, Any], expected: Mapping[str, str],
) -> list[str]:
    reasons: list[str] = []
    for key in (
        "model_selection_receipt_id", "model_selection_digest",
        "model_runtime_binding_receipt_id", "model_runtime_binding_digest",
        "memex_supply_receipt_id", "memex_supply_digest",
    ):
        if str(profile.get(key) or "") != str(expected.get(key) or ""):
            reasons.append(f"authority_profile_binding_mismatch:{key}")
    if str(snapshot.get("repo_full_name") or "") != str(profile.get("repo_full_name") or ""):
        reasons.append("permission_repo_mismatch")
    if not (snapshot.get("can_write") is True or snapshot.get("can_admin") is True):
        reasons.append("permission_write_not_granted")
    if str(principal.get("principal_public_key") or "") != str(profile.get("principal_public_key") or ""):
        reasons.append("principal_public_key_mismatch")
    if str(profile.get("repo_full_name") or "") not in principal.get("repo_scope", ()):
        reasons.append("principal_repo_scope_mismatch")
    if str(profile.get("foundup_id") or "") not in principal.get("foundup_scope", ()):
        reasons.append("principal_foundup_scope_mismatch")
    claim_expected = {
        "claim_id": expected.get("claim_id"),
        "source_determination_receipt_id": expected.get("determination_receipt_id"),
        "model_selection_receipt_id": expected.get("model_selection_receipt_id"),
        "model_runtime_binding_receipt_id": expected.get("model_runtime_binding_receipt_id"),
        "memex_supply_receipt_id": expected.get("memex_supply_receipt_id"),
    }
    for key, value in claim_expected.items():
        if key not in claim or str(claim.get(key) or "") != str(value or ""):
            reasons.append(f"claim_queue_binding_mismatch:{key}")
    runtime_pair = (expected["model_runtime_binding_receipt_id"], expected["model_runtime_binding_digest"])
    if bool(runtime_pair[0]) != bool(runtime_pair[1]):
        reasons.append("model_runtime_binding_half_pair")
    return reasons


def _environment_core(state: str, lineage: Mapping[str, Any], ttl: int, expires: int) -> dict[str, Any]:
    flags = {
        "valve_dryrun_enabled": state != VALVE_CLOSED,
        "valve_live_enqueue_enabled": state == VALVE_OPEN_LIVE_ENQUEUE,
        "valve_worktree_create_enabled": state == VALVE_OPEN_WORKTREE_CREATE,
    }
    del ttl, expires
    bindings = {key: lineage[key] for key in (
        "work_order_id", "requested_operation", "valve_state_required",
        "queue_item_id", "claim_id", "determination_receipt_id",
        "repo_full_name", "foundup_id", "principal_id", "reddog_id", "key_epoch",
        "permission_snapshot_digest", "authority_profile_digest", "work_state_revision",
        "wsp15_allocation_receipt_id", "wsp15_allocation_digest",
        "model_selection_receipt_id", "model_selection_digest",
        "model_runtime_binding_receipt_id", "model_runtime_binding_digest",
        "memex_supply_receipt_id", "memex_supply_digest", "resolver_supply_receipt_id",
        "consensus_receipt_digest", "sovereign_authorization_digest",
    )}
    authorization_mode = CANONICAL_AUTHORIZATION_MODE
    authorization_binding_digest = _digest(
        {"authorization_mode": authorization_mode, "bindings": bindings}
    )
    values = {
        "schema_version": SCHEMA_VERSION,
        "authorization_mode": authorization_mode,
        "authorization_binding_digest": authorization_binding_digest,
        "requested_valve_state": state,
        **flags,
        **bindings,
    }
    return values


def _supply_receipt(core: Mapping[str, Any], lineage: Mapping[str, Any], digest: str) -> dict[str, Any]:
    body = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "environment_digest": digest,
        "authority_profile_digest": lineage["authority_profile_digest"],
        "work_state_revision": lineage["work_state_revision"],
        "permission_snapshot_digest": lineage["permission_snapshot_digest"],
        "resolver_supply_receipt_id": lineage["resolver_supply_receipt_id"],
        "no_secret_values_serialized": True,
        "no_execution_performed": True,
        "no_authority_minted": True,
        "no_repo_mutation_performed": True,
    }
    return {**body, "receipt_id": _digest(body)}


def _select(values: Any, key: str, wanted: str) -> Mapping[str, Any]:
    items = [item for item in values or () if isinstance(item, Mapping)]
    if wanted:
        matches = [item for item in items if str(item.get(key) or "") == wanted]
        return matches[0] if len(matches) == 1 else {}
    return items[0] if len(items) == 1 else {}


def _output_path(value: Path | str | None, repo_root: Path) -> tuple[Path | None, list[str]]:
    if not value:
        return None, ["execution_valve_environment_output_path_invalid"]
    path = Path(value)
    if not path.is_absolute():
        return None, ["execution_valve_environment_output_path_not_absolute"]
    if path.is_symlink():
        return None, ["execution_valve_environment_output_path_symlink"]
    resolved = path.resolve()
    if resolved == repo_root or repo_root in resolved.parents or (resolved.exists() and not resolved.is_file()):
        return None, ["execution_valve_environment_output_path_invalid"]
    return resolved, []


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    with runtime_operation_lock(str(path) + ".operation"):
        _write_json_atomic_unlocked(path, payload)


def _write_json_atomic_unlocked(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, sort_keys=True, indent=2, ensure_ascii=True)
            handle.write("\n")
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _reject(reasons: Sequence[str]) -> ExecutionValveEnvironmentSupplyResult:
    return ExecutionValveEnvironmentSupplyResult(
        accepted=False,
        status=SUPPLY_REJECT,
        output_path=None,
        environment_digest=None,
        supply_receipt_id=None,
        rejection_reasons=tuple(dict.fromkeys(str(reason) for reason in reasons if reason)),
    )


__all__ = [
    "RECEIPT_SCHEMA_VERSION", "SCHEMA_VERSION", "SUPPLY_ACCEPT", "SUPPLY_REJECT",
    "ExecutionValveEnvironmentSupplyResult", "run_reddog_execution_valve_environment_supply",
    "resolve_reddog_execution_valve_expected_bindings",
]
