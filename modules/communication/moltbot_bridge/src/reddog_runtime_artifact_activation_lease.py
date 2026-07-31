"""Hold canonical runtime bytes stable during generation activation."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Sequence

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path,
)


@contextmanager
def runtime_artifact_activation_lease(
    paths: Sequence[Path | str],
    *,
    repo_root: Path | str,
    allowed_root: Path | str,
) -> Iterator[None]:
    """Deny ordinary writes while signed bytes become the active generation."""

    targets = _validated_targets(
        paths, repo_root=repo_root, allowed_root=allowed_root
    )
    if os.name == "nt":
        with _windows_activation_lease(targets):
            yield
        return
    raise RuntimeError(
        "runtime_artifact_activation_lease_external_owner_required"
    )


def _validated_targets(
    paths: Sequence[Path | str],
    *,
    repo_root: Path | str,
    allowed_root: Path | str,
) -> tuple[Path, ...]:
    targets = tuple(
        validate_runtime_artifact_path(
            path,
            repo_root=repo_root,
            allowed_root=allowed_root,
        )
        for path in paths
    )
    if not targets or len(set(targets)) != len(targets):
        raise ValueError("runtime_artifact_activation_lease_targets_invalid")
    for target in targets:
        metadata = target.lstat()
        if target.is_symlink() or not target.is_file() or metadata.st_nlink != 1:
            raise ValueError("runtime_artifact_activation_lease_target_invalid")
    return targets


@contextmanager
def _windows_activation_lease(paths: tuple[Path, ...]) -> Iterator[None]:
    from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store_windows import (
        close_windows_handle,
        open_windows_file_without_write_delete_share,
    )

    handles: list[int] = []
    try:
        for path in paths:
            handles.append(open_windows_file_without_write_delete_share(path))
        yield
    finally:
        for handle in reversed(handles):
            close_windows_handle(handle)

__all__ = ["runtime_artifact_activation_lease"]
