"""Canonical digest primitive shared by RedDog conversation-scope records."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_digest(payload: Any) -> str:
    raw = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


__all__ = ["canonical_digest"]
