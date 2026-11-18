"""Main-startup dependency bundle for the resident RedDog queue loop.

Slice: REDDOG_MAIN_RESIDENT_QUEUE_RUNTIME_DEPENDENCY_BUNDLE_PHASE1

This module constructs only the queue dependencies that ``main.py`` may safely
own today: outside-repo JSON stores/resolvers, an optional client for an
already-running isolated signer, and an optional public-key signature verifier.
It does not load private keys, spawn a signer, create worktrees, run shell
commands, enqueue OpenClaw, dispatch Hermes, publish PRs, mutate repository
files, or re-index HoloIndex.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    AtomicJsonAuthorityRuntimeStore,
    AuthorityRuntimeStore,
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
from modules.communication.moltbot_bridge.src.reddog_runtime_json_read import (
    read_reddog_runtime_json_mapping,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PermissionSnapshot,
)


REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519 = "ed25519"
REDDOG_RUNTIME_DEPENDENCY_BUNDLE_READY = "REDDOG_RUNTIME_DEPENDENCY_BUNDLE_READY"
REDDOG_RUNTIME_DEPENDENCY_BUNDLE_NOT_REQUESTED = "REDDOG_RUNTIME_DEPENDENCY_BUNDLE_NOT_REQUESTED"
REDDOG_RUNTIME_DEPENDENCY_BUNDLE_REJECT = "REDDOG_RUNTIME_DEPENDENCY_BUNDLE_REJECT"


class JsonPrincipalAuthorityResolver:
    """Resolve token-verified principal records from a caller-owned JSON snapshot."""

    def __init__(self, records: Mapping[str, PrincipalAuthorityRecord]) -> None:
        self._records = dict(records)

    def resolve(self, principal_id: str, principal_provider: str) -> Optional[PrincipalAuthorityRecord]:
        return self._records.get(_principal_key(principal_id, principal_provider))


class JsonPrincipalKeyResolver:
    """Resolve token-verified principal public keys for signature verification."""

    def __init__(self, records: Mapping[str, PrincipalAuthorityRecord]) -> None:
        self._records = dict(records)

    def resolve(self, principal_id: str, principal_provider: str) -> Optional[str]:
        record = self._records.get(_principal_key(principal_id, principal_provider))
        return record.principal_public_key if record is not None else None


class JsonPermissionSnapshotResolver:
    """Resolve permission snapshots from a caller-owned JSON snapshot."""

    def __init__(self, snapshots: Mapping[str, PermissionSnapshot]) -> None:
        self._snapshots = dict(snapshots)

    def resolve(self, digest: str) -> Optional[PermissionSnapshot]:
        return self._snapshots.get(str(digest))


class AuthorityRuntimeWorkAuthorityNonceStore:
    """Durably consume work-authority nonces in the outside-repo authority state."""

    def __init__(self, store: AuthorityRuntimeStore) -> None:
        self._store = store

    def consume(self, nonce: str) -> bool:
        if not isinstance(nonce, str) or not nonce.strip():
            return False
        atomic_consume = getattr(
            self._store, "consume_verified_work_authority_nonce", None)
        if not callable(atomic_consume):
            return False
        try:
            return bool(atomic_consume(nonce))
        except Exception:
            return False

    def advance_publication(
        self, nonce: str, binding_digest: str, target_status: str) -> str:
        advance = getattr(
            self._store, "advance_verified_work_authority_publication", None)
        if not callable(advance):
            return ""
        try:
            return str(advance(nonce, binding_digest, target_status) or "")
        except Exception:
            return ""

class AuthorityRuntimeRevocationOracle:
    """Read revocation lists from the outside-repo authority runtime state."""

    def __init__(self, store: AuthorityRuntimeStore) -> None:
        self._store = store

    def is_revoked(
        self, *, reddog_id: str, fingerprint: str, principal_id: str, key_epoch: str
    ) -> bool:
        state = self._store.load()
        revocations = state.get("revocations", {})
        if not isinstance(revocations, Mapping):
            return True
        return (
            principal_id in set(map(str, revocations.get("principal_ids", [])))
            or reddog_id in set(map(str, revocations.get("reddog_ids", [])))
            or fingerprint in set(map(str, revocations.get("reddog_fingerprints", [])))
            or key_epoch in set(map(str, revocations.get("key_epochs", [])))
        )


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
    signature_verifier: Any = None
    principal_key_resolver: Any = None
    nonce_store: Any = None
    revocation_oracle: Any = None
    elevated_consensus_capability_supplier: Any = None
    now_epoch: Optional[int] = None
    authority_state_path: Optional[str] = None
    signer_socket_path: Optional[str] = None
    signature_verifier_backend: str = "none"
    permission_snapshots_loaded: int = 0
    principal_records_loaded: int = 0
    signer_mode: str = "none"
    signature_verifier_mode: str = "none"
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
    runtime_allowed_root: Path | str | None = None,
    authority_state_path: Path | str | None,
    permission_snapshots_path: Path | str | None = None,
    principal_authority_records_path: Path | str | None = None,
    signer_socket_path: Path | str | None = None,
    signer_socket_timeout_s: float = DEFAULT_SIGNER_SOCKET_TIMEOUT_S,
    signer_socket_max_response_bytes: int = DEFAULT_SIGNER_SOCKET_MAX_RESPONSE_BYTES,
    signer_socket_connector: Optional[SignerSocketConnector] = None,
    signature_verifier_backend: str | None = None,
    elevated_consensus_capability_supplier: Any = None,
    now_epoch: int | None = None,
) -> RedDogMainResidentQueueRuntimeDependencyBundle:
    """Load safe queue-loop dependencies from outside-repo runtime artifacts."""
    root = Path(repo_root).resolve()
    if not authority_state_path:
        if (
            permission_snapshots_path
            or principal_authority_records_path
            or signer_socket_path
            or signature_verifier_backend
            or elevated_consensus_capability_supplier is not None
            or now_epoch is not None
        ):
            return _reject("runtime_dependency_bundle_partial_configuration")
        return RedDogMainResidentQueueRuntimeDependencyBundle(
            accepted=True,
            status=REDDOG_RUNTIME_DEPENDENCY_BUNDLE_NOT_REQUESTED,
            requested=False,
            rejection_reasons=(),
        )

    if runtime_allowed_root is None:
        return _reject("missing_runtime_artifact_root")
    if elevated_consensus_capability_supplier is not None and not callable(elevated_consensus_capability_supplier):
        return _reject("elevated_consensus_capability_supplier_invalid")
    runtime_root = Path(os.path.abspath(Path(runtime_allowed_root).expanduser()))
    try:
        validate_runtime_root_path(runtime_root, repo_root=root)
    except ValueError:
        return _reject("invalid_runtime_artifact_root")
    authority_path, authority_reasons = _resolve_path_outside_repo(
        root,
        runtime_root,
        authority_state_path,
        missing_reason="missing_authority_runtime_state_path",
        inside_reason="authority_runtime_state_path_inside_repo",
        must_exist=False,
    )
    if authority_reasons:
        return _reject(*authority_reasons)
    assert authority_path is not None
    snapshots, snapshot_reasons = _load_permission_snapshots(
        root, runtime_root, permission_snapshots_path
    )
    if snapshot_reasons:
        return _reject(*snapshot_reasons)
    principals, principal_reasons = _load_principal_records(
        root, runtime_root, principal_authority_records_path
    )
    if principal_reasons:
        return _reject(*principal_reasons)
    authority_store = AtomicJsonAuthorityRuntimeStore(
        authority_path, allowed_root=runtime_root, repo_root=root
    )
    signer = FailClosedSignerClient()
    signer_mode = "fail_closed"
    signer_socket_resolved: Optional[str] = None
    no_real_signer_configured = True
    if signer_socket_path:
        signer_candidate = Path(signer_socket_path)
        if not signer_candidate.is_absolute():
            signer_candidate = Path(os.path.abspath(root / signer_candidate))
        if _is_inside(signer_candidate, root):
            return _reject("FAIL_SIGNER_SOCKET_PATH_INSIDE_REPO")
        try:
            signer_path = validate_runtime_artifact_path(
                signer_candidate,
                repo_root=root,
                allowed_root=runtime_root,
            )
        except ValueError:
            return _reject("signer_socket_path_outside_runtime_root")
        signer_result = build_reddog_isolated_signer_socket_client(
            repo_root=root,
            socket_path=signer_path,
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
    (
        signature_verifier,
        principal_key_resolver,
        nonce_store,
        revocation_oracle,
        verifier_mode,
        verifier_backend,
        verifier_reasons,
    ) = _build_signature_verification_dependencies(
        backend=signature_verifier_backend,
        authority_store=authority_store,
        principals=principals,
    )
    if verifier_reasons:
        return _reject(*verifier_reasons)
    return RedDogMainResidentQueueRuntimeDependencyBundle(
        accepted=True,
        status=REDDOG_RUNTIME_DEPENDENCY_BUNDLE_READY,
        requested=True,
        rejection_reasons=(),
        authority_store=authority_store,
        signer=signer,
        principal_resolver=(
            JsonPrincipalAuthorityResolver(principals)
            if principals
            else FailClosedPrincipalAuthorityResolver()
        ),
        snapshot_resolver=JsonPermissionSnapshotResolver(snapshots),
        signature_verifier=signature_verifier,
        principal_key_resolver=principal_key_resolver,
        nonce_store=nonce_store,
        revocation_oracle=revocation_oracle,
        elevated_consensus_capability_supplier=elevated_consensus_capability_supplier,
        now_epoch=now_epoch,
        authority_state_path=str(authority_path),
        signer_socket_path=signer_socket_resolved,
        signature_verifier_backend=verifier_backend,
        permission_snapshots_loaded=len(snapshots),
        principal_records_loaded=len(principals),
        signer_mode=signer_mode,
        signature_verifier_mode=verifier_mode,
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
    allowed_root: Path,
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
        path = Path(os.path.abspath(repo_root / path))
    else:
        path = Path(os.path.abspath(path))
    resolved = path.resolve()
    if _is_inside(resolved, repo_root):
        return None, (inside_reason,)
    try:
        validate_runtime_artifact_path(
            path,
            repo_root=repo_root,
            allowed_root=allowed_root,
        )
    except ValueError:
        return None, ("runtime_dependency_path_outside_allowed_root",)
    if must_exist and (not path.exists() or not path.is_file()):
        return None, (missing_reason,)
    return path, ()


def _read_json_mapping(
    repo_root: Path,
    allowed_root: Path,
    value: Path | str | None,
    *,
    missing_reason: str,
    inside_reason: str,
    malformed_reason: str,
) -> tuple[Optional[Mapping[str, Any]], tuple[str, ...]]:
    path, reasons = _resolve_path_outside_repo(
        repo_root,
        allowed_root,
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
        with runtime_operation_lock(str(path) + ".operation"):
            payload = read_reddog_runtime_json_mapping(
                path,
                allowed_root=allowed_root,
            )
    except Exception:
        return None, (malformed_reason,)
    if not isinstance(payload, Mapping):
        return None, (malformed_reason,)
    return payload, ()


def _load_permission_snapshots(
    repo_root: Path,
    allowed_root: Path,
    value: Path | str | None,
) -> tuple[dict[str, PermissionSnapshot], tuple[str, ...]]:
    payload, reasons = _read_json_mapping(
        repo_root,
        allowed_root,
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
    allowed_root: Path,
    value: Path | str | None,
) -> tuple[dict[str, PrincipalAuthorityRecord], tuple[str, ...]]:
    payload, reasons = _read_json_mapping(
        repo_root,
        allowed_root,
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


def _build_signature_verification_dependencies(
    *,
    backend: str | None,
    authority_store: AuthorityRuntimeStore,
    principals: Mapping[str, PrincipalAuthorityRecord],
) -> tuple[Any, Any, Any, Any, str, str, tuple[str, ...]]:
    requested = str(backend or "").strip().lower()
    if not requested or requested in {"none", "fail_closed"}:
        return None, None, None, None, "none", "none", ()
    if requested != REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519:
        return None, None, None, None, "none", requested, ("unsupported_signature_verifier_backend",)
    if not principals:
        return None, None, None, None, "none", requested, (
            "missing_principal_authority_records_for_signature_verification",
        )
    from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
        Ed25519SignatureVerifier,
    )

    return (
        Ed25519SignatureVerifier(),
        JsonPrincipalKeyResolver(principals),
        AuthorityRuntimeWorkAuthorityNonceStore(authority_store),
        AuthorityRuntimeRevocationOracle(authority_store),
        REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
        REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
        (),
    )


def _principal_key(principal_id: str, principal_provider: str) -> str:
    return f"{principal_provider}|{principal_id}"


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


__all__ = [
    "AuthorityRuntimeRevocationOracle",
    "AuthorityRuntimeWorkAuthorityNonceStore",
    "JsonPermissionSnapshotResolver",
    "JsonPrincipalAuthorityResolver",
    "JsonPrincipalKeyResolver",
    "REDDOG_RUNTIME_DEPENDENCY_BUNDLE_NOT_REQUESTED",
    "REDDOG_RUNTIME_DEPENDENCY_BUNDLE_READY",
    "REDDOG_RUNTIME_DEPENDENCY_BUNDLE_REJECT",
    "REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519",
    "RedDogMainResidentQueueRuntimeDependencyBundle",
    "load_reddog_main_resident_queue_runtime_dependency_bundle",
]
