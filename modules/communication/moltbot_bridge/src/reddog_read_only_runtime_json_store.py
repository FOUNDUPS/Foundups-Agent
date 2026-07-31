"""Read-only confined access to one runtime JSON mapping."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_runtime_json_read import (
    read_reddog_runtime_json_mapping,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    confined_runtime_operation_lock,
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)


class ReadOnlyRuntimeJsonStore:
    """Path-confined reader with no write or signing capability."""

    __slots__ = ("allowed_root", "lock_path", "path", "repo_root")

    def __init__(
        self,
        path: Path | str,
        *,
        allowed_root: Path | str,
        repo_root: Path | str,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.allowed_root = validate_runtime_root_path(
            allowed_root,
            repo_root=self.repo_root,
        )
        self.path = validate_runtime_artifact_path(
            path,
            repo_root=self.repo_root,
            allowed_root=self.allowed_root,
        )
        self.lock_path = validate_runtime_artifact_path(
            self.path.with_name(self.path.name + ".operation.lock"),
            repo_root=self.repo_root,
            allowed_root=self.allowed_root,
        )

    def load(self) -> Mapping[str, Any]:
        with confined_runtime_operation_lock(
            self.lock_path,
            repo_root=self.repo_root,
            allowed_root=self.allowed_root,
        ):
            path = validate_runtime_artifact_path(
                self.path,
                repo_root=self.repo_root,
                allowed_root=self.allowed_root,
            )
            if not path.exists():
                return {}
            return dict(
                read_reddog_runtime_json_mapping(
                    path,
                    allowed_root=self.allowed_root,
                )
            )


__all__ = ["ReadOnlyRuntimeJsonStore"]
