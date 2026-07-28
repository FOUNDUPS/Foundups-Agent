"""Principal-resolution and durable-state boundaries for RedDog authority."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, Mapping, Optional, Protocol, Tuple

from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store_posix import (
    posix_atomic_replace,
    recover_posix_interrupted_files,
)
from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store_windows import (
    close_windows_handle,
    open_windows_directory_without_delete_share,
    recover_windows_interrupted_files,
    windows_atomic_replace,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_json_read import (
    read_reddog_runtime_json_mapping,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    confined_runtime_operation_lock,
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)

_NO_REVISION_CHECK = object()


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    unsigned = dict(payload)
    unsigned.pop("revision", None)
    raw = json.dumps(
        unsigned,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PrincipalAuthorityRecord:
    """Token-verified principal basis supplied by an external resolver."""

    principal_id: str
    principal_provider: str
    principal_public_key: str
    repo_scope: Tuple[str, ...]
    foundup_scope: Tuple[str, ...]
    verified_subject_digest: str
    reward_account: Optional[str] = None
    owner_dae: Optional[str] = None
    principal_wallet: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PrincipalAuthorityResolver(Protocol):
    def resolve(
        self, principal_id: str, principal_provider: str
    ) -> Optional[PrincipalAuthorityRecord]: ...


class FailClosedPrincipalAuthorityResolver:
    def resolve(
        self, principal_id: str, principal_provider: str
    ) -> Optional[PrincipalAuthorityRecord]:
        return None


class AuthorityRuntimeStore(Protocol):
    def load(self) -> Dict[str, Any]: ...

    def commit(
        self, snapshot: Mapping[str, Any], *, expected_revision: Optional[str]
    ) -> str: ...

    def consume_verified_work_authority_nonce(self, nonce: str) -> bool: ...

    def advance_verified_work_authority_publication(
        self, nonce: str, binding_digest: str, target_status: str
    ) -> str: ...


class InMemoryAuthorityRuntimeStore:
    def __init__(
        self, initial: Optional[Mapping[str, Any]] = None, *, fail_commit: bool = False
    ) -> None:
        self._state: Dict[str, Any] = dict(initial or {})
        self.fail_commit = fail_commit
        self._lock = threading.Lock()

    def load(self) -> Dict[str, Any]:
        return json.loads(json.dumps(self._state, sort_keys=True))

    def commit(
        self, snapshot: Mapping[str, Any], *, expected_revision: Optional[str]
    ) -> str:
        with self._lock:
            if self.fail_commit:
                raise RuntimeError("commit_failed")
            if self._state.get("revision") != expected_revision:
                raise RuntimeError("revision_conflict")
            committed = json.loads(json.dumps(snapshot, sort_keys=True))
            revision = _canonical_digest(committed)
            committed["revision"] = revision
            self._state = committed
            return revision

    def consume_verified_work_authority_nonce(self, nonce: str) -> bool:
        with self._lock:
            seen = self._state.get("verified_work_authority_nonces", [])
            if not isinstance(seen, list) or nonce in set(map(str, seen)):
                return False
            committed = json.loads(json.dumps(self._state, sort_keys=True))
            committed["verified_work_authority_nonces"] = [*seen, nonce]
            committed["revision"] = _canonical_digest(committed)
            self._state = committed
            return True

    def advance_verified_work_authority_publication(
        self, nonce: str, binding_digest: str, target_status: str
    ) -> str:
        with self._lock:
            updated, status = _advanced_publication_snapshot(
                self._state,
                nonce=nonce,
                binding_digest=binding_digest,
                target_status=target_status,
            )
            if not status:
                return ""
            updated["revision"] = _canonical_digest(updated)
            self._state = updated
            return status


class AtomicJsonAuthorityRuntimeStore:
    """Single-file authority store using durable atomic replace."""

    def __init__(
        self,
        path: str | Path,
        *,
        allowed_root: str | Path,
        repo_root: str | Path,
    ) -> None:
        repo_candidate = Path(repo_root).expanduser()
        root_candidate = Path(allowed_root).expanduser()
        if not repo_candidate.is_absolute():
            raise ValueError("authority_runtime_store_repo_root_not_absolute")
        if not root_candidate.is_absolute():
            raise ValueError("authority_runtime_store_root_not_absolute")
        self.repo_root = repo_candidate.resolve()
        self.allowed_root = validate_runtime_root_path(
            root_candidate,
            repo_root=self.repo_root,
        )
        self.path = self._validated_path(path)
        self.lock_path = validate_runtime_artifact_path(
            self.path.with_name(self.path.name + ".operation.lock"),
            repo_root=self.repo_root,
            allowed_root=self.allowed_root,
        )

    def load(self) -> Dict[str, Any]:
        with self._operation_lock():
            return self._load_unlocked()

    def _load_unlocked(
        self,
        *,
        expected_recovery_revision: object = _NO_REVISION_CHECK,
    ) -> Dict[str, Any]:
        target = self._validated_path(self.path)
        self._recover_interrupted_write(
            target,
            expected_revision=expected_recovery_revision,
        )
        target = self._validated_path(self.path)
        if not target.exists():
            return {}
        return dict(
            read_reddog_runtime_json_mapping(
                target,
                allowed_root=self.allowed_root,
            )
        )

    def commit(
        self, snapshot: Mapping[str, Any], *, expected_revision: Optional[str]
    ) -> str:
        with self._operation_lock():
            current = self._load_unlocked(
                expected_recovery_revision=expected_revision,
            )
            if current.get("revision") != expected_revision:
                raise RuntimeError("revision_conflict")
            return self._write_snapshot(
                snapshot,
                expected_revision=expected_revision,
            )

    def consume_verified_work_authority_nonce(self, nonce: str) -> bool:
        with self._operation_lock():
            current = self._load_unlocked()
            seen = current.get("verified_work_authority_nonces", [])
            if not isinstance(seen, list) or nonce in set(map(str, seen)):
                return False
            updated = dict(current)
            updated["verified_work_authority_nonces"] = [*seen, nonce]
            self._write_snapshot(
                updated,
                expected_revision=current.get("revision"),
            )
            return True

    def advance_verified_work_authority_publication(
        self, nonce: str, binding_digest: str, target_status: str
    ) -> str:
        with self._operation_lock():
            current = self._load_unlocked()
            updated, status = _advanced_publication_snapshot(
                current,
                nonce=nonce,
                binding_digest=binding_digest,
                target_status=target_status,
            )
            if not status:
                return ""
            if updated != current:
                self._write_snapshot(
                    updated,
                    expected_revision=current.get("revision"),
                )
            return status

    def _operation_lock(self) -> Iterator[None]:
        return confined_runtime_operation_lock(
            self.lock_path,
            repo_root=self.repo_root,
            allowed_root=self.allowed_root,
        )

    def _write_snapshot(
        self,
        snapshot: Mapping[str, Any],
        *,
        expected_revision: Optional[str],
    ) -> str:
        committed = json.loads(json.dumps(snapshot, sort_keys=True))
        revision = _canonical_digest(committed)
        committed["revision"] = revision
        target = self._validated_path(self.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target = self._validated_path(target)
        self._atomic_write(
            target,
            committed,
            expected_revision=expected_revision,
        )
        return revision

    def _atomic_write(
        self,
        target: Path,
        committed: Mapping[str, Any],
        *,
        expected_revision: Optional[str],
    ) -> None:
        atomic_replace_confined_mapping(
            target,
            committed,
            allowed_root=self.allowed_root,
            repo_root=self.repo_root,
            expected_revision=expected_revision,
        )

    def _recover_interrupted_write(
        self,
        target: Path,
        *,
        expected_revision: object,
    ) -> None:
        if not target.parent.exists():
            return
        recovery_revision = (
            expected_revision
            if isinstance(expected_revision, str) and expected_revision
            else None
        )
        with _stable_parent_directory(target.parent) as parent_handle:
            if os.name == "nt":
                recover_windows_interrupted_files(
                    target,
                    expected_revision=recovery_revision,
                )
            else:
                recover_posix_interrupted_files(
                    parent_handle,
                    target.name,
                    expected_revision=recovery_revision,
                )

    def _validated_path(self, path: str | Path) -> Path:
        target = validate_runtime_artifact_path(
            path,
            repo_root=self.repo_root,
            allowed_root=self.allowed_root,
        )
        expected = getattr(self, "path", target)
        if os.path.normcase(str(target)) != os.path.normcase(str(expected)):
            raise ValueError("authority_runtime_store_path_changed")
        return target


def _advanced_publication_snapshot(
    snapshot: Mapping[str, Any],
    *,
    nonce: str,
    binding_digest: str,
    target_status: str,
) -> tuple[Dict[str, Any], str]:
    order = {"RESERVED": 0, "AUTHORIZED": 1, "APPLIED": 2}
    if (
        not nonce
        or not _valid_sha256(binding_digest)
        or target_status not in order
    ):
        return dict(snapshot), ""
    updated = json.loads(json.dumps(snapshot, sort_keys=True))
    publications = updated.setdefault(
        "verified_work_authority_publications", {}
    )
    seen = updated.setdefault("verified_work_authority_nonces", [])
    if not isinstance(publications, dict) or not isinstance(seen, list):
        return dict(snapshot), ""
    current = publications.get(nonce)
    if current is None:
        if nonce in set(map(str, seen)) or target_status != "RESERVED":
            return dict(snapshot), ""
        seen.append(nonce)
        publications[nonce] = {
            "binding_digest": binding_digest,
            "status": target_status,
        }
        return updated, target_status
    return _advance_existing_publication(
        snapshot=updated,
        current=current,
        binding_digest=binding_digest,
        target_status=target_status,
        order=order,
    )


def _advance_existing_publication(
    *,
    snapshot: Dict[str, Any],
    current: Any,
    binding_digest: str,
    target_status: str,
    order: Mapping[str, int],
) -> tuple[Dict[str, Any], str]:
    if not isinstance(current, dict) or not hmac.compare_digest(
        str(current.get("binding_digest") or ""), binding_digest
    ):
        return snapshot, ""
    current_status = str(current.get("status") or "")
    if current_status not in order:
        return snapshot, ""
    if order[target_status] > order[current_status] + 1:
        return snapshot, ""
    if order[target_status] > order[current_status]:
        current["status"] = target_status
        current_status = target_status
    return snapshot, current_status


def _valid_sha256(value: str) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("sha256:")
        and len(value) == 71
        and all(char in "0123456789abcdef" for char in value[7:])
    )


def atomic_replace_confined_mapping(
    path: Path | str,
    payload: Mapping[str, Any],
    *,
    allowed_root: Path | str,
    repo_root: Path | str,
    expected_revision: object = _NO_REVISION_CHECK,
) -> Path:
    """Atomically replace one JSON mapping under an explicit runtime root."""

    root = validate_runtime_root_path(allowed_root, repo_root=repo_root)
    target = validate_runtime_artifact_path(
        path,
        repo_root=repo_root,
        allowed_root=root,
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target = validate_runtime_artifact_path(
        target,
        repo_root=repo_root,
        allowed_root=root,
    )
    encoded = (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode("utf-8")
    check_revision = expected_revision is not _NO_REVISION_CHECK
    with _stable_parent_directory(target.parent) as parent_handle:
        if os.name == "nt":
            windows_atomic_replace(
                parent_handle,
                target,
                encoded,
                check_revision=check_revision,
                expected_revision=(
                    None if expected_revision is _NO_REVISION_CHECK
                    else expected_revision
                ),
            )
        else:
            posix_atomic_replace(
                parent_handle,
                target.parent,
                target.name,
                encoded,
                check_revision=check_revision,
                expected_revision=(
                    None if expected_revision is _NO_REVISION_CHECK
                    else expected_revision
                ),
            )
        if os.name == "nt":
            validate_runtime_artifact_path(
                target,
                repo_root=repo_root,
                allowed_root=root,
            )
            _fsync_parent_directory(target.parent)
    return target


@contextmanager
def _stable_parent_directory(path: Path) -> Iterator[int]:
    if os.name == "nt":
        handle = open_windows_directory_without_delete_share(path)
        try:
            yield handle
        finally:
            close_windows_handle(handle)
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        expected = os.stat(path, follow_symlinks=False)
        if (opened.st_dev, opened.st_ino) != (expected.st_dev, expected.st_ino):
            raise ValueError("authority_runtime_store_parent_changed")
        yield descriptor
    finally:
        os.close(descriptor)


def _fsync_parent_directory(path: Path) -> None:
    """Persist the rename itself on platforms supporting directory fsync."""

    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(str(path), flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


__all__ = [
    "AtomicJsonAuthorityRuntimeStore",
    "AuthorityRuntimeStore",
    "FailClosedPrincipalAuthorityResolver",
    "InMemoryAuthorityRuntimeStore",
    "PrincipalAuthorityRecord",
    "PrincipalAuthorityResolver",
    "atomic_replace_confined_mapping",
]
