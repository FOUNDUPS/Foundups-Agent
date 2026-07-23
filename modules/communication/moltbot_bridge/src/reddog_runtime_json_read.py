"""Bounded no-follow JSON reads for caller-owned RedDog runtime artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    secure_read_confined_bytes,
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


__all__ = ["MAX_REDDOG_RUNTIME_JSON_BYTES", "read_reddog_runtime_json_mapping"]
