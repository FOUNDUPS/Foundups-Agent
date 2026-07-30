"""Authority-runtime resolver artifact supplier for resident RedDog.

Slice: REDDOG_AUTHORITY_RUNTIME_RESOLVER_ARTIFACT_SUPPLY_PHASE1

The GitHub principal/permission supplier produces singular runtime artifacts.
The resident queue authority runtime consumes resolver stores shaped as
``{"principals": ...}`` and ``{"snapshots": ...}``. This module bridges those
shapes outside the repository.

It does not sign, verify signatures, mutate signer state, invoke the authority
runtime, spawn workers, create worktrees, execute shell commands, enqueue
OpenClaw, dispatch Hermes, mutate work state, mutate repository files, write
PatternMemory, or re-index HoloIndex.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from modules.infrastructure.shared_utilities.reddog_runtime_artifact_generation import (
    reddog_runtime_artifact_generation_lock,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
)


AUTHORITY_RUNTIME_RESOLVER_SUPPLY_ACCEPT = "AUTHORITY_RUNTIME_RESOLVER_SUPPLY_ACCEPT"
AUTHORITY_RUNTIME_RESOLVER_SUPPLY_REJECT = "AUTHORITY_RUNTIME_RESOLVER_SUPPLY_REJECT"
AUTHORITY_RUNTIME_RESOLVER_SUPPLY_SCHEMA_VERSION = "reddog_authority_runtime_resolver_supply.v1"


class AuthorityRuntimeResolverSupplyReason:
    PRINCIPAL_INVALID = "principal_authority_record_invalid"
    PERMISSION_SNAPSHOT_INVALID = "permission_snapshot_invalid"
    PRINCIPAL_SNAPSHOT_MISMATCH = "principal_permission_snapshot_mismatch"
    OUTPUT_PATH_INVALID = "authority_runtime_resolver_output_path_invalid"
    OUTPUT_WRITE_FAILED = "authority_runtime_resolver_output_write_failed"
    NON_ASCII_INPUT = "authority_runtime_resolver_non_ascii_input"


@dataclass(frozen=True)
class AuthorityRuntimeResolverSupplyResult:
    accepted: bool
    status: str
    resolver_supply_receipt_id: Optional[str]
    principal_records_path: Optional[str]
    permission_snapshots_path: Optional[str]
    principal_records_loaded: int
    permission_snapshots_loaded: int
    rejection_reasons: tuple[str, ...]
    no_signing_performed: bool = True
    no_signature_verification_performed: bool = True
    no_signer_state_mutation_performed: bool = True
    no_authority_runtime_invoked: bool = True
    no_worker_spawn_performed: bool = True
    no_worktree_created: bool = True
    no_shell_command_executed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_work_state_mutation_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pattern_memory_write_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_authority_runtime_resolver_artifact_supply(
    *,
    repo_root: Path | str,
    principal_authority_record: Mapping[str, Any] | None,
    permission_snapshot: Mapping[str, Any] | None,
    principal_records_output_path: Path | str | None,
    permission_snapshots_output_path: Path | str | None,
) -> AuthorityRuntimeResolverSupplyResult:
    """Materialize plural resolver stores from singular authority artifacts."""

    root = Path(repo_root).resolve()
    principal, snapshot, reasons = _validated_resolver_inputs(
        principal_authority_record, permission_snapshot
    )
    principal_path, principal_path_reasons = _runtime_output_path(
        principal_records_output_path, root
    )
    snapshot_path, snapshot_path_reasons = _runtime_output_path(
        permission_snapshots_output_path, root
    )
    reasons.extend((*principal_path_reasons, *snapshot_path_reasons))
    if reasons:
        return _reject(reasons)

    assert principal_path is not None
    assert snapshot_path is not None
    principal_store, snapshot_store, receipt_id = _resolver_store_payloads(
        principal, snapshot, principal_path, snapshot_path
    )

    try:
        _write_resolver_artifacts(
            principal_path,
            principal_store,
            snapshot_path,
            snapshot_store,
            repo_root=root,
        )
    except Exception:
        return _reject((AuthorityRuntimeResolverSupplyReason.OUTPUT_WRITE_FAILED,))
    return AuthorityRuntimeResolverSupplyResult(
        accepted=True,
        status=AUTHORITY_RUNTIME_RESOLVER_SUPPLY_ACCEPT,
        resolver_supply_receipt_id=receipt_id,
        principal_records_path=str(principal_path),
        permission_snapshots_path=str(snapshot_path),
        principal_records_loaded=1,
        permission_snapshots_loaded=1,
        rejection_reasons=(),
    )


def _validated_resolver_inputs(
    principal_authority_record: Mapping[str, Any] | None,
    permission_snapshot: Mapping[str, Any] | None,
) -> tuple[Mapping[str, Any], Mapping[str, Any], list[str]]:
    principal = _mapping(principal_authority_record)
    snapshot = _mapping(permission_snapshot)
    reasons: list[str] = []
    if not _valid_principal(principal):
        reasons.append(AuthorityRuntimeResolverSupplyReason.PRINCIPAL_INVALID)
    if not _valid_snapshot(snapshot):
        reasons.append(AuthorityRuntimeResolverSupplyReason.PERMISSION_SNAPSHOT_INVALID)
    if principal and snapshot and not _principal_snapshot_match(principal, snapshot):
        reasons.append(AuthorityRuntimeResolverSupplyReason.PRINCIPAL_SNAPSHOT_MISMATCH)
    if not _ascii_deep({"principal": principal, "snapshot": snapshot}):
        reasons.append(AuthorityRuntimeResolverSupplyReason.NON_ASCII_INPUT)
    return principal, snapshot, reasons


def _resolver_store_payloads(
    principal: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    principal_path: Path,
    snapshot_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    principal_key = _principal_key(
        str(principal["principal_id"]), str(principal["principal_provider"])
    )
    principal_store = _resolver_store("principals", principal_key, principal)
    snapshot_store = _resolver_store(
        "snapshots", str(snapshot["evidence_digest"]), snapshot
    )
    receipt_id = _digest(
        {
            "principal_store": principal_store,
            "snapshot_store": snapshot_store,
            "principal_records_path": str(principal_path),
            "permission_snapshots_path": str(snapshot_path),
        }
    )
    principal_store["resolver_supply_receipt_id"] = receipt_id
    snapshot_store["resolver_supply_receipt_id"] = receipt_id
    return principal_store, snapshot_store, receipt_id


def _resolver_store(
    collection: str, key: str, value: Mapping[str, Any]
) -> dict[str, Any]:
    singular = collection.removesuffix("s")
    return {
        "schema_version": AUTHORITY_RUNTIME_RESOLVER_SUPPLY_SCHEMA_VERSION,
        collection: {key: dict(value)},
        f"{singular}_count": 1,
        "no_holoindex_reindex_performed": True,
    }


def _valid_principal(principal: Mapping[str, Any]) -> bool:
    required = (
        "principal_id",
        "principal_provider",
        "principal_public_key",
        "repo_scope",
        "foundup_scope",
        "verified_subject_digest",
    )
    if not principal or any(principal.get(field) in (None, "", (), []) for field in required):
        return False
    return isinstance(principal.get("repo_scope"), (list, tuple)) and isinstance(
        principal.get("foundup_scope"), (list, tuple)
    )


def _valid_snapshot(snapshot: Mapping[str, Any]) -> bool:
    required = ("evidence_digest", "expires_at", "repo_full_name")
    if not snapshot or any(snapshot.get(field) in (None, "") for field in required):
        return False
    try:
        int(snapshot["expires_at"])
    except Exception:
        return False
    return bool(snapshot.get("can_write") or snapshot.get("can_admin"))


def _principal_snapshot_match(principal: Mapping[str, Any], snapshot: Mapping[str, Any]) -> bool:
    repo = str(snapshot.get("repo_full_name") or "")
    repos = {str(item) for item in principal.get("repo_scope") or ()}
    return bool(repo and repo in repos)


def _runtime_output_path(value: Path | str | None, repo_root: Path) -> tuple[Path | None, list[str]]:
    if not value:
        return None, [AuthorityRuntimeResolverSupplyReason.OUTPUT_PATH_INVALID]
    path = Path(value)
    if not path.is_absolute():
        path = repo_root.parent / path
    resolved = path.resolve()
    if _is_inside(resolved, repo_root):
        return None, [AuthorityRuntimeResolverSupplyReason.OUTPUT_PATH_INVALID]
    return resolved, []


def _write_resolver_artifacts(
    principal_path: Path,
    principal_store: Mapping[str, Any],
    snapshot_path: Path,
    snapshot_store: Mapping[str, Any],
    *,
    repo_root: Path,
) -> None:
    with runtime_operation_lock(str(principal_path) + ".operation"):
        with runtime_operation_lock(str(snapshot_path) + ".operation"):
            with reddog_runtime_artifact_generation_lock(
                principal_path.parent, repo_root=repo_root
            ):
                _write_json_atomic_unlocked(principal_path, principal_store)
                _write_json_atomic_unlocked(snapshot_path, snapshot_store)


def _write_json_atomic_unlocked(path: Path, payload: Mapping[str, Any]) -> None:
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


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        try:
            candidate = value.to_dict()
            return candidate if isinstance(candidate, Mapping) else {}
        except Exception:
            return {}
    return value if isinstance(value, Mapping) else {}


def _principal_key(principal_id: str, principal_provider: str) -> str:
    return f"{principal_provider}|{principal_id}"


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


def _ascii_deep(value: Any) -> bool:
    if isinstance(value, str):
        return all(ord(char) < 128 for char in value)
    if isinstance(value, Mapping):
        return all(isinstance(key, str) and _ascii_deep(key) and _ascii_deep(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(_ascii_deep(item) for item in value)
    return True


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _reject(reasons: Sequence[str]) -> AuthorityRuntimeResolverSupplyResult:
    return AuthorityRuntimeResolverSupplyResult(
        accepted=False,
        status=AUTHORITY_RUNTIME_RESOLVER_SUPPLY_REJECT,
        resolver_supply_receipt_id=None,
        principal_records_path=None,
        permission_snapshots_path=None,
        principal_records_loaded=0,
        permission_snapshots_loaded=0,
        rejection_reasons=tuple(dict.fromkeys(str(reason) for reason in reasons if str(reason).strip())),
    )


__all__ = [
    "AUTHORITY_RUNTIME_RESOLVER_SUPPLY_ACCEPT",
    "AUTHORITY_RUNTIME_RESOLVER_SUPPLY_REJECT",
    "AUTHORITY_RUNTIME_RESOLVER_SUPPLY_SCHEMA_VERSION",
    "AuthorityRuntimeResolverSupplyReason",
    "AuthorityRuntimeResolverSupplyResult",
    "run_reddog_authority_runtime_resolver_artifact_supply",
]
