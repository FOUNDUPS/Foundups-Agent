"""Confined stores for RedDog authoritative work state."""

from __future__ import annotations

import hashlib
import json
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, Mapping, Optional, Protocol

from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    atomic_replace_confined_mapping,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_json_read import (
    read_reddog_runtime_json_mapping,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    confined_runtime_operation_lock,
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)


class AuthoritativeWorkStateStore(Protocol):
    """Atomic storage boundary shared by refresh and queue writers."""

    def load(self) -> Dict[str, Any]:
        """Return the current state."""

    def commit(
        self,
        snapshot: Mapping[str, Any],
        *,
        expected_revision: Optional[str],
    ) -> str:
        """Commit by compare-and-swap and return the new revision."""

    def locked_snapshot(self) -> Iterator[Dict[str, Any]]:
        """Hold the writer fence while yielding the current snapshot."""


class InMemoryAuthoritativeWorkStateStore:
    """Thread-safe test/runtime helper implementing optimistic commits."""

    def __init__(
        self,
        initial: Optional[Mapping[str, Any]] = None,
        *,
        fail_commit: bool = False,
    ) -> None:
        self._state: Dict[str, Any] = dict(initial or {})
        self.fail_commit = fail_commit
        self._lock = threading.RLock()

    def load(self) -> Dict[str, Any]:
        with self._lock:
            return _copy(self._state)

    def commit(
        self,
        snapshot: Mapping[str, Any],
        *,
        expected_revision: Optional[str],
    ) -> str:
        with self._lock:
            if self.fail_commit:
                raise RuntimeError("commit_failed")
            if self._state.get("revision") != expected_revision:
                raise RuntimeError("revision_conflict")
            committed = _copy(snapshot)
            revision = _revision(committed)
            committed["revision"] = revision
            self._state = committed
            return revision

    @contextmanager
    def locked_snapshot(self) -> Iterator[Dict[str, Any]]:
        with self._lock:
            yield _copy(self._state)


class AtomicJsonAuthoritativeWorkStateStore:
    """Confined JSON store using one durable cross-process writer fence."""

    def __init__(
        self,
        path: str | Path,
        *,
        allowed_root: str | Path,
        repo_root: str | Path,
    ) -> None:
        self.repo_root = Path(repo_root).expanduser().resolve()
        self.allowed_root = validate_runtime_root_path(
            allowed_root,
            repo_root=self.repo_root,
        )
        self.path = self._confine(path)
        self.lock_path = self._confine(
            self.path.with_name(self.path.name + ".operation.lock")
        )

    def load(self) -> Dict[str, Any]:
        with self._operation_lock():
            return self._load_unlocked()

    def commit(
        self,
        snapshot: Mapping[str, Any],
        *,
        expected_revision: Optional[str],
    ) -> str:
        with self._operation_lock():
            current = self._load_unlocked()
            if current.get("revision") != expected_revision:
                raise RuntimeError("revision_conflict")
            committed = _copy(snapshot)
            revision = _revision(committed)
            committed["revision"] = revision
            atomic_replace_confined_mapping(
                self.path,
                committed,
                allowed_root=self.allowed_root,
                repo_root=self.repo_root,
            )
            return revision

    @contextmanager
    def locked_snapshot(self) -> Iterator[Dict[str, Any]]:
        with self._operation_lock():
            yield self._load_unlocked()

    def _load_unlocked(self) -> Dict[str, Any]:
        target = self._confine(self.path)
        if not target.exists():
            return {}
        return dict(
            read_reddog_runtime_json_mapping(
                target,
                allowed_root=self.allowed_root,
            )
        )

    def _confine(self, path: Path | str) -> Path:
        return validate_runtime_artifact_path(
            path,
            repo_root=self.repo_root,
            allowed_root=self.allowed_root,
        )

    def _operation_lock(self) -> Iterator[None]:
        return confined_runtime_operation_lock(
            self.lock_path,
            repo_root=self.repo_root,
            allowed_root=self.allowed_root,
        )


def _copy(value: Mapping[str, Any]) -> Dict[str, Any]:
    return json.loads(json.dumps(value, sort_keys=True))


def _revision(value: Mapping[str, Any]) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "AtomicJsonAuthoritativeWorkStateStore",
    "AuthoritativeWorkStateStore",
    "InMemoryAuthoritativeWorkStateStore",
]
