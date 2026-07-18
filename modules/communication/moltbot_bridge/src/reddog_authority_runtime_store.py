"""Principal-resolution and durable-state boundaries for RedDog authority."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Protocol, Tuple

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
)


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
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


class InMemoryAuthorityRuntimeStore:
    def __init__(
        self, initial: Optional[Mapping[str, Any]] = None, *, fail_commit: bool = False
    ) -> None:
        self._state: Dict[str, Any] = dict(initial or {})
        self.fail_commit = fail_commit

    def load(self) -> Dict[str, Any]:
        return json.loads(json.dumps(self._state, sort_keys=True))

    def commit(
        self, snapshot: Mapping[str, Any], *, expected_revision: Optional[str]
    ) -> str:
        if self.fail_commit:
            raise RuntimeError("commit_failed")
        if self._state.get("revision") != expected_revision:
            raise RuntimeError("revision_conflict")
        committed = json.loads(json.dumps(snapshot, sort_keys=True))
        revision = _canonical_digest(committed)
        committed["revision"] = revision
        self._state = committed
        return revision


class AtomicJsonAuthorityRuntimeStore:
    """Single-file authority store using durable atomic replace."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def commit(
        self, snapshot: Mapping[str, Any], *, expected_revision: Optional[str]
    ) -> str:
        with runtime_operation_lock(str(self.path.resolve()) + ".authority-state"):
            current = self.load()
            if current.get("revision") != expected_revision:
                raise RuntimeError("revision_conflict")
            committed = json.loads(json.dumps(snapshot, sort_keys=True))
            revision = _canonical_digest(committed)
            committed["revision"] = revision
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._atomic_write(committed)
            return revision

    def _atomic_write(self, committed: Mapping[str, Any]) -> None:
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", suffix=".tmp", dir=str(self.path.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(committed, handle, sort_keys=True, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, self.path)
            _fsync_parent_directory(self.path.parent)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)


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
]
