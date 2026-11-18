"""Bounded canonical JSON helpers for production-binding transactions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


MAX_PRODUCTION_ARTIFACT_BYTES = 1_048_576


def read_production_json(path: Path, error: str) -> Mapping[str, Any]:
    try:
        if not path.is_file() or path.stat().st_size > MAX_PRODUCTION_ARTIFACT_BYTES:
            raise ValueError(error)
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        raise ValueError(error) from None
    if not isinstance(payload, Mapping):
        raise ValueError(error)
    return payload


def canonical_json_mapping(value: Any, error: str) -> Mapping[str, Any]:
    payload = json.loads(json.dumps(value, sort_keys=True, separators=(",", ":")))
    if not isinstance(payload, Mapping):
        raise ValueError(error)
    return payload


__all__ = ["canonical_json_mapping", "read_production_json"]
