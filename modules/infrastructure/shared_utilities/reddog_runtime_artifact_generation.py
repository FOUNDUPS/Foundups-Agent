"""Shared generation fence for canonical RedDog runtime artifacts."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    confined_runtime_operation_lock,
    validate_runtime_root_path,
)


REDDOG_RUNTIME_ARTIFACT_GENERATION_LOCK = (
    ".reddog-runtime-artifact-generation.lock"
)
REDDOG_RUNTIME_ARTIFACT_GENERATION_SEAL = (
    ".reddog-runtime-artifact-generation-seal.json"
)
CANONICAL_REDDOG_RUNTIME_ARTIFACTS = frozenset(
    {
        "authoritative_work_state.json",
        "authority_profile.json",
        "execution_valve_env.json",
        "permission_snapshots.json",
        "principal_authority_records.json",
        "signer_service_config.json",
        "signer_service_run_packet.json",
    }
)


@contextmanager
def reddog_runtime_artifact_generation_lock(
    runtime_root: Path | str,
    *,
    repo_root: Path | str,
    allow_sealed: bool = False,
) -> Iterator[None]:
    """Serialize canonical artifact producers and manifest publication."""

    root = validate_runtime_root_path(runtime_root, repo_root=repo_root)
    with confined_runtime_operation_lock(
        root / REDDOG_RUNTIME_ARTIFACT_GENERATION_LOCK,
        repo_root=repo_root,
        allowed_root=root,
    ):
        seal = root / REDDOG_RUNTIME_ARTIFACT_GENERATION_SEAL
        if not allow_sealed and seal.exists():
            raise RuntimeError("runtime_artifact_generation_sealed")
        yield


__all__ = [
    "CANONICAL_REDDOG_RUNTIME_ARTIFACTS",
    "REDDOG_RUNTIME_ARTIFACT_GENERATION_LOCK",
    "REDDOG_RUNTIME_ARTIFACT_GENERATION_SEAL",
    "reddog_runtime_artifact_generation_lock",
]
