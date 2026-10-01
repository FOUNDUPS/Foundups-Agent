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

from .reddog_reviewer_designation_contract import validate_reviewer_designation
from .reddog_signer_owner_e0_principal_records import (
    SCHEMA_VERSION_V2, parse_principal_artifact, parse_principal_records, principal_record_key,
)
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
    REVIEWER_AUTHORIZATION_INVALID = "reviewer_authorization_invalid"


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
    reviewer_authorizations: Sequence[Mapping[str, Any]] | None = None,
    reviewer_principal_records: Sequence[Mapping[str, Any]] | None = None,
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
    try:
        principal_store, snapshot_store, receipt_id = _resolver_store_payloads(
            principal, snapshot, principal_path, snapshot_path,
            reviewer_authorizations=reviewer_authorizations,
            reviewer_principal_records=reviewer_principal_records,
        )
    except (TypeError, ValueError):
        if reviewer_authorizations is None and reviewer_principal_records is None:
            raise
        return _reject((AuthorityRuntimeResolverSupplyReason.REVIEWER_AUTHORIZATION_INVALID,))
    return _write_supply_result(
        principal_store, snapshot_store, receipt_id, principal_path, snapshot_path, root,
    )


def _write_supply_result(
    principal_store: Mapping[str, Any], snapshot_store: Mapping[str, Any], receipt_id: str,
    principal_path: Path, snapshot_path: Path, root: Path,
) -> AuthorityRuntimeResolverSupplyResult:
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
        principal_records_loaded=len(principal_store["principals"]),
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
    *, reviewer_authorizations: Sequence[Mapping[str, Any]] | None = None,
    reviewer_principal_records: Sequence[Mapping[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    principal_key = _principal_key(
        str(principal["principal_id"]), str(principal["principal_provider"])
    )
    principal_store = _resolver_store("principals", principal_key, principal)
    principal_store = _with_reviewer_authorizations(
        principal_store, reviewer_authorizations, reviewer_principal_records,
    )
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
    if reviewer_authorizations is not None:
        parse_principal_artifact(json.dumps(principal_store, ensure_ascii=True).encode("ascii"))
    return principal_store, snapshot_store, receipt_id


def _with_reviewer_authorizations(
    principal_store: dict[str, Any], authorizations: Any, reviewer_records: Any,
) -> dict[str, Any]:
    if authorizations is None and reviewer_records is None:
        return principal_store
    if type(authorizations) is not list or len(authorizations) != 1:
        raise ValueError("reviewer_authorization_invalid")
    designation = validate_reviewer_designation(authorizations[0])
    records, reviewer_keys = _merged_reviewer_principals(principal_store, reviewer_records)
    entries = {
        principal_record_key(entry["principal_id"], entry["principal_provider"]): entry
        for entry in designation["reviewers"]
    }
    if len(entries) != len(designation["reviewers"]) or set(entries) != reviewer_keys:
        raise ValueError("reviewer_principal_pair_mismatch")
    for key, entry in entries.items():
        record = records[key]
        if (record.principal_id != entry["principal_id"]
                or record.principal_provider != entry["principal_provider"]
                or record.principal_public_key != entry["public_key"]
                or designation["repo_full_name"] not in record.repo_scope
                or designation["foundup_id"] not in record.foundup_scope):
            raise ValueError("reviewer_principal_binding_mismatch")
    return {
        **principal_store, "schema_version": SCHEMA_VERSION_V2,
        "principals": {key: asdict(record) for key, record in records.items()},
        "principal_count": len(records), "reviewer_authorizations": [designation],
    }


def _merged_reviewer_principals(principal_store: dict[str, Any], values: Any):
    if type(values) is not list or not 1 <= len(values) <= 8:
        raise ValueError("reviewer_principals_invalid")
    merged = dict(principal_store["principals"])
    reviewer_keys = set()
    for value in values:
        if (type(value) is not dict or type(value.get("principal_id")) is not str
                or type(value.get("principal_provider")) is not str):
            raise ValueError("reviewer_principals_invalid")
        key = principal_record_key(value["principal_id"], value["principal_provider"])
        if key in merged:
            raise ValueError("reviewer_principal_collision")
        merged[key] = value
        reviewer_keys.add(key)
    envelope = {
        **principal_store, "principals": merged, "principal_count": len(merged),
        "resolver_supply_receipt_id": "sha256:" + "0" * 64,
    }
    raw = json.dumps(envelope, ensure_ascii=True, allow_nan=False).encode("ascii")
    return parse_principal_records(raw), reviewer_keys


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
