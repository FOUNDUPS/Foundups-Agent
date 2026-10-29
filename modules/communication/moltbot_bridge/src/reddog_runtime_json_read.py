"""Bounded no-follow JSON reads for caller-owned RedDog runtime artifacts."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping, Optional

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    secure_read_confined_bytes,
    validate_runtime_artifact_path,
)
from modules.communication.moltbot_bridge.src.reddog_authority_profile_rehydration import (
    rehydrate_authority_profile_effect_scope,
)

MAX_REDDOG_RUNTIME_JSON_BYTES = 1024 * 1024


def read_reddog_runtime_json_mapping(
    path: Path | str, *, allowed_root: Path | str
) -> Mapping[str, Any]:
    """Read one exact regular JSON mapping through the confined descriptor helper."""

    candidate = Path(path)
    if candidate.is_symlink():
        raise ValueError("runtime_json_symlink_forbidden")
    raw, _ = secure_read_confined_bytes(
        candidate,
        allowed_root=allowed_root,
        max_bytes=MAX_REDDOG_RUNTIME_JSON_BYTES,
    )
    if len(raw) >= MAX_REDDOG_RUNTIME_JSON_BYTES:
        raise ValueError("runtime_json_too_large")
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("runtime_json_not_mapping")
    return payload


def read_reddog_runtime_json_outside_repo(
    repo_root: Path,
    allowed_root: Path,
    value: Path | str | None,
    *,
    missing_reason: str,
    inside_reason: str,
    unreadable_reason: str,
    required: bool = True,
) -> tuple[Optional[Mapping[str, Any]], tuple[str, ...]]:
    """Resolve and securely read one runtime mapping outside the repository."""

    if not value:
        return None, (missing_reason,) if required else ()
    raw_path = Path(value)
    candidate = raw_path if raw_path.is_absolute() else repo_root / raw_path
    candidate = Path(os.path.abspath(candidate.expanduser()))
    root = repo_root.resolve()
    resolved = candidate.resolve()
    if resolved == root or root in resolved.parents:
        return None, (inside_reason,)
    if not candidate.exists() or not candidate.is_file():
        return None, (missing_reason,)
    try:
        validate_runtime_artifact_path(
            candidate,
            repo_root=repo_root,
            allowed_root=allowed_root,
        )
        return read_reddog_runtime_json_mapping(
            candidate,
            allowed_root=allowed_root,
        ), ()
    except Exception:
        return None, (unreadable_reason,)


def read_reddog_authority_profile_effect_scope_outside_repo(
    repo_root: Path,
    allowed_root: Path,
    value: Path | str | None,
    *,
    missing_reason: str,
    inside_reason: str,
    unreadable_reason: str,
) -> tuple[Optional[Mapping[str, Any]], tuple[str, ...]]:
    """Read and type-check one legacy effect-bearing profile projection."""

    profile, reasons = read_reddog_runtime_json_outside_repo(
        repo_root, allowed_root, value, missing_reason=missing_reason,
        inside_reason=inside_reason, unreadable_reason=unreadable_reason,
    )
    if reasons or profile is None:
        return profile, reasons
    try:
        return rehydrate_authority_profile_effect_scope(dict(profile)), ()
    except ValueError:
        return None, (unreadable_reason,)


__all__ = [
    "MAX_REDDOG_RUNTIME_JSON_BYTES",
    "read_reddog_authority_profile_effect_scope_outside_repo",
    "read_reddog_runtime_json_mapping",
    "read_reddog_runtime_json_outside_repo",
]
