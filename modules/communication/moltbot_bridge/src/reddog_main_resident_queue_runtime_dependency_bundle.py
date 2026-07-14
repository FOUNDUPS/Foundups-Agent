"""Main-startup dependency bundle for the resident RedDog queue loop.

Slice: REDDOG_MAIN_RESIDENT_QUEUE_RUNTIME_DEPENDENCY_BUNDLE_PHASE1

This module constructs only the authority-runtime dependencies that ``main.py``
may safely own today: outside-repo JSON stores/resolvers and an optional client
for an already-running isolated signer. It does not load private keys, spawn a
signer, verify signatures, create worktrees, run shell commands, enqueue
OpenClaw, dispatch Hermes, publish PRs, mutate repository files, or re-index
HoloIndex.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    AtomicJsonAuthorityRuntimeStore,
    FailClosedPrincipalAuthorityResolver,
    FailClosedSignerClient,
    PrincipalAuthorityRecord,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_client import (
    DEFAULT_SIGNER_SOCKET_MAX_RESPONSE_BYTES,
    DEFAULT_SIGNER_SOCKET_TIMEOUT_S,
    SignerSocketConnector,
    build_reddog_isolated_signer_socket_client,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PermissionSnapshot,
)


REDDOG_RUNTIME_DEPENDENCY_BUNDLE_READY = "REDDOG_RUNTIME_DEPENDENCY_BUNDLE_READY"
REDDOG_RUNTIME_DEPENDENCY_BUNDLE_NOT_REQUESTED = "REDDOG_RUNTIME_DEPENDENCY_BUNDLE_NOT_REQUESTED"
REDDOG_RUNTIME_DEPENDENCY_BUNDLE_REJECT = "REDDOG_RUNTIME_DEPENDENCY_BUNDLE_REJECT"


class JsonPrincipalAuthorityResolver:
    """Resolve token-verified principal records from a caller-owned JSON snapshot."""

    def __init__(self, records: Mapping[str, PrincipalAuthorityRecord]) -> None:
        self._records = dict(records)

    def resolve(self, principal_id: str, principal_provider: str) -> Optional[PrincipalAuthorityRecord]:
        return self._records.get(_principal_key(principal_id, principal_provider))


class JsonPermissionSnapshotResolver:
    """Resolve permission snapshots from a caller-owned JSON snapshot."""

    def __init__(self, snapshots: Mapping[str, PermissionSnapshot]) -> None:
        self._snapshots = dict(snapshots)

    def resolve(self, digest: str) -> Optional[PermissionSnapshot]:
        return self._snapshots.get(str(digest))


@dataclass(frozen=True)
class RedDogMainResidentQueueRuntimeDependencyBundle:
    """Dependency bundle consumed by the serial-loop bootstrap."""

    accepted: bool
    status: str
    requested: bool
    rejection_reasons: tuple[str, ...]
    authority_store: Any = None
    signer: Any = None
    principal_resolver: Any = None
    snapshot_resolver: Any = None
    now_epoch: Optional[int] = None
    authority_state_path: Optional[str] = None
    signer_socket_path: Optional[str] = None
    permission_snapshots_loaded: int = 0
    principal_records_loaded: int = 0
    signer_mode: str = "none"
    no_real_signer_configured: bool = True
    no_private_key_loaded: bool = True
    no_signature_verification_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_worktree_created: bool = True
    no_shell_command_executed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pr_created: bool = True
    no_reward_settlement_performed: bool = True


def load_reddog_main_resident_queue_runtime_dependency_bundle(
    *,
    repo_root: Path | str,
    authority_state_path: Path | str | None,
    permission_snapshots_path: Path | str | None = None,
    principal_authority_records_path: Path | str | None = None,
    signer_socket_path: Path | str | None = None,
    signer_socket_timeout_s: float = DEFAULT_SIGNER_SOCKET_TIMEOUT_S,
    signer_socket_max_response_bytes: int = DEFAULT_SIGNER_SOCKET_MAX_RESPONSE_BYTES,
    signer_socket_connector: Optional[SignerSocketConnector] = None,
    now_epoch: int | None = None,
) -> RedDogMainResidentQueueRuntimeDependencyBundle:
    """Load safe queue-loop dependencies from outside-repo runtime artifacts."""

    root = Path(repo_root).resolve()
    if not authority_state_path:
        if (
            permission_snapshots_path
            or principal_authority_records_path
            or signer_socket_path
            or now_epoch is not None
        ):
            return _reject("runtime_dependency_bundle_partial_configuration")
        return RedDogMainResidentQueueRuntimeDependencyBundle(
            accepted=True,
            status=REDDOG_RUNTIME_DEPENDENCY_BUNDLE_NOT_REQUESTED,
            requested=False,
            rejection_reasons=(),
        )

    authority_path, authority_reasons = _resolve_path_outside_repo(
        root,
        authority_state_path,
        missing_reason="missing_authority_runtime_state_path",
        inside_reason="authority_runtime_state_path_inside_repo",
        must_exist=False,
    )
    if authority_reasons:
        return _reject(*authority_reasons)
    assert authority_path is not None

    snapshots, snapshot_reasons = _load_permission_snapshots(root, permission_snapshots_path)
    if snapshot_reasons:
        return _reject(*snapshot_reasons)

    principals, principal_reasons = _load_principal_records(root, principal_authority_records_path)
    if principal_reasons:
        return _reject(*principal_reasons)

    signer = FailClosedSignerClient()
    signer_mode = "fail_closed"
    signer_socket_resolved: Optional[str] = None
    no_real_signer_configured = True
    if signer_socket_path:
        signer_result = build_reddog_isolated_signer_socket_client(
            repo_root=root,
            socket_path=signer_socket_path,
            timeout_s=signer_socket_timeout_s,
            max_response_bytes=signer_socket_max_response_bytes,
            connector=signer_socket_connector,
        )
        if signer_result.accepted is not True or signer_result.client is None:
            return _reject(*signer_result.rejection_reasons)
        signer = signer_result.client
        signer_mode = "isolated_socket"
        signer_socket_resolved = signer_result.socket_path
        no_real_signer_configured = False

    return RedDogMainResidentQueueRuntimeDependencyBundle(
        accepted=True,
        status=REDDOG_RUNTIME_DEPENDENCY_BUNDLE_READY,
        requested=True,
        rejection_reasons=(),
        authority_store=AtomicJsonAuthorityRuntimeStore(authority_path),
        signer=signer,
        principal_resolver=(
            JsonPrincipalAuthorityResolver(principals)
            if principals
            else FailClosedPrincipalAuthorityResolver()
        ),
        snapshot_resolver=JsonPermissionSnapshotResolver(snapshots),
        now_epoch=now_epoch,
        authority_state_path=str(authority_path),
        signer_socket_path=signer_socket_resolved,
        permission_snapshots_loaded=len(snapshots),
        principal_records_loaded=len(principals),
        signer_mode=signer_mode,
        no_real_signer_configured=no_real_signer_configured,
    )


def _reject(*reasons: str) -> RedDogMainResidentQueueRuntimeDependencyBundle:
    return RedDogMainResidentQueueRuntimeDependencyBundle(
        accepted=False,
        status=REDDOG_RUNTIME_DEPENDENCY_BUNDLE_REJECT,
        requested=True,
        rejection_reasons=tuple(dict.fromkeys(reason for reason in reasons if reason)),
    )


def _resolve_path_outside_repo(
    repo_root: Path,
    value: Path | str | None,
    *,
    missing_reason: str,
    inside_reason: str,
    must_exist: bool,
) -> tuple[Optional[Path], tuple[str, ...]]:
    if not value:
        return None, ()
    path = Path(value)
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    else:
        path = path.resolve()
    if _is_inside(path, repo_root):
        return None, (inside_reason,)
    if must_exist and (not path.exists() or not path.is_file()):
        return None, (missing_reason,)
    return path, ()


def _read_json_mapping(
    repo_root: Path,
    value: Path | str | None,
    *,
    missing_reason: str,
    inside_reason: str,
    malformed_reason: str,
) -> tuple[Optional[Mapping[str, Any]], tuple[str, ...]]:
    path, reasons = _resolve_path_outside_repo(
        repo_root,
        value,
        missing_reason=missing_reason,
        inside_reason=inside_reason,
        must_exist=True,
    )
    if reasons:
        return None, reasons
    if path is None:
        return None, ()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, (malformed_reason,)
    if not isinstance(payload, Mapping):
        return None, (malformed_reason,)
    return payload, ()


def _load_permission_snapshots(
    repo_root: Path,
    value: Path | str | None,
) -> tuple[dict[str, PermissionSnapshot], tuple[str, ...]]:
    payload, reasons = _read_json_mapping(
        repo_root,
        value,
        missing_reason="missing_permission_snapshots_path",
        inside_reason="permission_snapshots_path_inside_repo",
        malformed_reason="malformed_permission_snapshots",
    )
    if reasons:
        return {}, reasons
    raw = payload.get("snapshots") if payload else {}
    if raw in (None, ""):
        raw = {}
    if not isinstance(raw, Mapping):
        return {}, ("malformed_permission_snapshots",)
    snapshots: dict[str, PermissionSnapshot] = {}
    try:
        for digest, item in raw.items():
            if not isinstance(item, Mapping):
                return {}, ("malformed_permission_snapshots",)
            evidence_digest = str(item.get("evidence_digest") or digest)
            snapshots[str(digest)] = PermissionSnapshot(
                evidence_digest=evidence_digest,
                expires_at=int(item["expires_at"]),
                can_write=bool(item.get("can_write", False)),
                can_admin=bool(item.get("can_admin", False)),
                repo_full_name=str(item.get("repo_full_name") or ""),
            )
    except Exception:
        return {}, ("malformed_permission_snapshots",)
    return snapshots, ()


def _load_principal_records(
    repo_root: Path,
    value: Path | str | None,
) -> tuple[dict[str, PrincipalAuthorityRecord], tuple[str, ...]]:
    payload, reasons = _read_json_mapping(
        repo_root,
        value,
        missing_reason="missing_principal_authority_records_path",
        inside_reason="principal_authority_records_path_inside_repo",
        malformed_reason="malformed_principal_authority_records",
    )
    if reasons:
        return {}, reasons
    raw = payload.get("principals") if payload else {}
    if raw in (None, ""):
        raw = {}
    if not isinstance(raw, Mapping):
        return {}, ("malformed_principal_authority_records",)
    records: dict[str, PrincipalAuthorityRecord] = {}
    try:
        for key, item in raw.items():
            if not isinstance(item, Mapping):
                return {}, ("malformed_principal_authority_records",)
            record = PrincipalAuthorityRecord(
                principal_id=str(item["principal_id"]),
                principal_provider=str(item["principal_provider"]),
                principal_public_key=str(item["principal_public_key"]),
                repo_scope=tuple(str(v) for v in item.get("repo_scope") or ()),
                foundup_scope=tuple(str(v) for v in item.get("foundup_scope") or ()),
                verified_subject_digest=str(item["verified_subject_digest"]),
                reward_account=(
                    str(item["reward_account"]) if item.get("reward_account") is not None else None
                ),
                owner_dae=str(item["owner_dae"]) if item.get("owner_dae") is not None else None,
                principal_wallet=(
                    str(item["principal_wallet"]) if item.get("principal_wallet") is not None else None
                ),
            )
            records[_principal_key(record.principal_id, record.principal_provider)] = record
            if str(key) not in {record.principal_id, _principal_key(record.principal_id, record.principal_provider)}:
                return {}, ("malformed_principal_authority_records",)
    except Exception:
        return {}, ("malformed_principal_authority_records",)
    return records, ()


def _principal_key(principal_id: str, principal_provider: str) -> str:
    return f"{principal_provider}|{principal_id}"


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


__all__ = [
    "JsonPermissionSnapshotResolver",
    "JsonPrincipalAuthorityResolver",
    "REDDOG_RUNTIME_DEPENDENCY_BUNDLE_NOT_REQUESTED",
    "REDDOG_RUNTIME_DEPENDENCY_BUNDLE_READY",
    "REDDOG_RUNTIME_DEPENDENCY_BUNDLE_REJECT",
    "RedDogMainResidentQueueRuntimeDependencyBundle",
    "load_reddog_main_resident_queue_runtime_dependency_bundle",
]
