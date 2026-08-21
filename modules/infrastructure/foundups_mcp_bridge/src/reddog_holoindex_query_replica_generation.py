"""Atomic no-replace publication for immutable replica generation directories."""

from __future__ import annotations

import ctypes
import os
from pathlib import Path


class QueryReplicaGenerationError(RuntimeError):
    """Stable generation-publication failure."""


def publish_directory_no_replace(source: Path, target: Path) -> None:
    """Atomically publish one directory while refusing replacement."""

    if target.exists():
        raise QueryReplicaGenerationError("QUERY_REPLICA_GENERATION_EXISTS")
    if os.name == "nt":
        os.rename(source, target)
        return
    if os.uname().sysname != "Linux":
        raise QueryReplicaGenerationError(
            "QUERY_REPLICA_ATOMIC_DIRECTORY_PUBLISH_UNAVAILABLE"
        )
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise QueryReplicaGenerationError(
            "QUERY_REPLICA_ATOMIC_DIRECTORY_PUBLISH_UNAVAILABLE"
        )
    result = renameat2(-100, os.fsencode(source), -100, os.fsencode(target), 1)
    if result == 0:
        return
    error = ctypes.get_errno()
    if error == 17:
        raise QueryReplicaGenerationError("QUERY_REPLICA_GENERATION_EXISTS")
    raise OSError(error, os.strerror(error))


__all__ = ["QueryReplicaGenerationError", "publish_directory_no_replace"]
