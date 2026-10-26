"""Import-stable spawned-process support for runtime lock contracts."""

from __future__ import annotations

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
)


def hold_runtime_lock(identity: str, ready, release) -> None:
    """Hold one runtime lock until the parent releases the spawned process."""
    with runtime_operation_lock(identity):
        ready.set()
        release.wait(10)
