"""Shared interprocess lock for all resident queue control-loop callers."""

from __future__ import annotations

import hashlib
import os
import tempfile
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Iterator, Mapping, Optional


CONTROL_LOOP_LOCK_PATH_ENV = "REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_LOCK_PATH"
_CONTROL_LOCK_IDENTITY: ContextVar[str] = ContextVar(
    "reddog_control_lock_identity", default=""
)


@dataclass(frozen=True)
class ResidentQueueControlLock:
    acquired: bool
    path: Path
    reason: str


def resident_queue_control_lock_path(
    repo_root: Path | str,
    environ: Optional[Mapping[str, str]] = None,
) -> Path:
    """Resolve one shared lock path for the repository/runtime pair."""

    env = os.environ if environ is None else environ
    explicit = str(env.get(CONTROL_LOOP_LOCK_PATH_ENV) or "").strip()
    if explicit:
        return Path(explicit).resolve()
    runtime = str(env.get("REDDOG_RESIDENT_RUNTIME_ROOT") or "").strip()
    if runtime:
        return (Path(runtime).resolve() / "resident_queue_control_loop.lock")
    root = Path(repo_root).resolve()
    digest = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:20]
    return Path(tempfile.gettempdir()).resolve() / "foundups-reddog-control-locks" / f"{digest}.lock"


@contextmanager
def acquire_resident_queue_control_lock(
    repo_root: Path | str,
    environ: Optional[Mapping[str, str]] = None,
    *,
    allow_reentrant: bool = False,
) -> Iterator[ResidentQueueControlLock]:
    """Acquire a non-blocking OS advisory lock that releases on process exit."""

    root = Path(repo_root).resolve()
    path = resident_queue_control_lock_path(root, environ)
    identity = _lock_identity(path)
    if allow_reentrant and _CONTROL_LOCK_IDENTITY.get() == identity:
        yield ResidentQueueControlLock(True, path, "control_lock_already_held_by_context")
        return
    if _is_inside(path, root):
        yield ResidentQueueControlLock(False, path, "control_lock_path_inside_repo")
        return
    handle: Optional[BinaryIO] = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = path.open("a+b")
        _lock_file(handle)
    except (OSError, BlockingIOError):
        if handle is not None:
            handle.close()
        yield ResidentQueueControlLock(False, path, "control_loop_already_running")
        return
    try:
        token = _CONTROL_LOCK_IDENTITY.set(identity)
        yield ResidentQueueControlLock(True, path, "ok")
    finally:
        _CONTROL_LOCK_IDENTITY.reset(token)
        _unlock_file(handle)
        handle.close()


def resident_queue_control_lock_held(
    repo_root: Path | str | None = None,
    environ: Optional[Mapping[str, str]] = None,
) -> bool:
    """Return whether this context owns the expected shared control lock."""

    held = _CONTROL_LOCK_IDENTITY.get()
    if repo_root is None:
        return bool(held)
    expected = resident_queue_control_lock_path(repo_root, environ)
    return held == _lock_identity(expected)


def _lock_identity(path: Path) -> str:
    return os.path.normcase(str(path.resolve()))


def _lock_file(handle: BinaryIO) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        if handle.read(1) == b"":
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        return
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_file(handle: BinaryIO) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


__all__ = [
    "CONTROL_LOOP_LOCK_PATH_ENV",
    "ResidentQueueControlLock",
    "acquire_resident_queue_control_lock",
    "resident_queue_control_lock_held",
    "resident_queue_control_lock_path",
]
