"""Bounded secret-free public projection for the RedDog Holo query bundle."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Mapping

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    redact_runtime_text,
)

from .holo_query_path_projection import (
    project_repository_location,
    project_repository_path,
)


PUBLIC_SCHEMA = "reddog_holo_query_bundle_mcp.v1"
PUBLIC_MAX_BYTES = 256 * 1024
PUBLIC_MAX_DEPTH = 8
PUBLIC_MAX_ITEMS = 128
PUBLIC_MAX_TEXT_CHARS = 4096
_PATH_KEYS = frozenset({"path", "file", "module_path"})
_DROP_KEYS = frozenset({
    "authorization", "canonical_repo_root", "canonical_ssd_path",
    "interpreter_path", "query_replica_root", "runtime_root",
    "selected_root", "semantic_evidence_json", "service_token", "token",
})
_WINDOWS_ABSOLUTE = re.compile(r"(?i)(?<![a-z0-9])[a-z]:[\\/][^\s\"'<>]*")
_UNC_ABSOLUTE = re.compile(r"\\\\[^\s\\/]+[\\/][^\s\"'<>]*")
_POSIX_ABSOLUTE = re.compile(r"(?<![:a-zA-Z0-9])/(?!/)[^\s\"'<>]*")
_SENSITIVE_KEY = re.compile(
    r"(?i)(?:api[_-]?key|access[_-]?token|authorization|password|passwd|"
    r"secret|private[_-]?key|client[_-]?secret|cookie|session[_-]?id|token)"
)
_MAX_INTEGER_ABS = (1 << 63) - 1


def _public_text(value: str, repo_root: Path) -> str:
    text = redact_runtime_text(value, max_chars=PUBLIC_MAX_TEXT_CHARS).text
    for root_text in {str(repo_root), str(repo_root).replace("\\", "/")}:
        if root_text:
            text = text.replace(root_text, "[REDACTED_REPO_ROOT]")
    text = _WINDOWS_ABSOLUTE.sub("[REDACTED_ABSOLUTE_PATH]", text)
    text = _UNC_ABSOLUTE.sub("[REDACTED_ABSOLUTE_PATH]", text)
    return _POSIX_ABSOLUTE.sub("[REDACTED_ABSOLUTE_PATH]", text)


def _project_path(value: Any, repo_root: Path, *, location: bool = False) -> str:
    if not isinstance(value, str) or not value.strip():
        return "[REDACTED_PATH]"
    try:
        projector = project_repository_location if location else project_repository_path
        return projector(value, str(repo_root))
    except ValueError:
        return "[REDACTED_PATH]"


def _walk_mapping(value: Mapping, repo_root: Path, depth: int, active: set[int]):
    marker = id(value)
    if marker in active:
        raise ValueError("public_projection_cycle")
    active.add(marker)
    projected: dict[str, Any] = {}
    try:
        for index, (raw_key, item) in enumerate(value.items()):
            if index >= PUBLIC_MAX_ITEMS:
                projected["_truncated"] = True
                break
            key = _public_text(str(raw_key), repo_root)[:128]
            folded = key.casefold()
            if folded in _DROP_KEYS:
                continue
            if key in projected:
                raise ValueError("public_projection_key_collision")
            if _SENSITIVE_KEY.search(folded):
                projected[key] = "[REDACTED]"
            elif key == "location":
                projected[key] = _project_path(item, repo_root, location=True)
            elif key in _PATH_KEYS:
                projected[key] = _project_path(item, repo_root)
            else:
                projected[key] = _walk_public(item, repo_root, depth + 1, active)
        return projected
    finally:
        active.remove(marker)


def _walk_sequence(value, repo_root: Path, depth: int, active: set[int]):
    marker = id(value)
    if marker in active:
        raise ValueError("public_projection_cycle")
    active.add(marker)
    try:
        return [_walk_public(item, repo_root, depth + 1, active)
                for item in value[:PUBLIC_MAX_ITEMS]]
    finally:
        active.remove(marker)


def _walk_public(value: Any, repo_root: Path, depth=0, active=None) -> Any:
    if depth > PUBLIC_MAX_DEPTH:
        return "[REDACTED_DEPTH_LIMIT]"
    active = active if active is not None else set()
    if isinstance(value, Mapping):
        return _walk_mapping(value, repo_root, depth, active)
    if isinstance(value, (list, tuple)):
        return _walk_sequence(value, repo_root, depth, active)
    if isinstance(value, str):
        return _public_text(value, repo_root)
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        if abs(value) > _MAX_INTEGER_ABS:
            raise ValueError("public_projection_integer_invalid")
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("public_projection_float_invalid")
        return value
    return _public_text(str(value), repo_root)


def _finalize(payload: dict[str, Any]) -> dict[str, Any] | None:
    payload["public_projection_bounded"] = True
    payload["public_projection_bytes"] = 0
    for _ in range(4):
        encoded = json.dumps(
            payload, ensure_ascii=True, sort_keys=True, allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(encoded) > PUBLIC_MAX_BYTES:
            return None
        if payload["public_projection_bytes"] == len(encoded):
            return payload
        payload["public_projection_bytes"] = len(encoded)
    return None


def project_holo_query_bundle(result: Mapping[str, Any], repo_root: Path) -> dict[str, Any]:
    """Return one bounded public projection or a typed content-free rejection."""
    try:
        projected = _walk_public(result, Path(repo_root).resolve())
        projected["schema_version"] = PUBLIC_SCHEMA
        accepted = _finalize(projected)
        if accepted is not None:
            return accepted
        error = "public_projection_size_exceeded"
    except (TypeError, ValueError) as exc:
        error = str(exc) or "public_projection_invalid"
    rejection = {
        "schema_version": PUBLIC_SCHEMA,
        "ok": False,
        "error": error,
        "index_gap_detected": True,
        "no_holoindex_reindex_performed": True,
    }
    return _finalize(rejection) or rejection


__all__ = ["PUBLIC_MAX_BYTES", "PUBLIC_SCHEMA", "project_holo_query_bundle"]
