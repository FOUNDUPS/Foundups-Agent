#!/usr/bin/env python3
"""Bounded JSON bridge from a RedDog owner failure to WRE maintenance."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.communication.moltbot_bridge.src.reddog_holoindex_incident_repair_runtime import (  # noqa: E402
    coordinate_holoindex_incident_repair,
)


MAX_INPUT_BYTES = 64 * 1024


def _read_payload() -> Mapping[str, Any]:
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("payload_too_large")
    value = json.loads(raw.decode("utf-8", errors="strict"))
    if not isinstance(value, Mapping):
        raise ValueError("payload_not_object")
    return value


def main() -> int:
    try:
        payload = _read_payload()
        failure = payload.get("owner_failure")
        if not isinstance(failure, Mapping):
            raise ValueError("owner_failure_required")
        query = payload.get("query")
        if type(query) is not str:
            raise ValueError("query_required")
        result = coordinate_holoindex_incident_repair(
            repo_root=REPO_ROOT,
            query=query,
            owner_failure=failure,
        ).to_dict()
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        result = {
            "accepted": False,
            "status": "REJECTED",
            "rejection_reasons": [str(exc) or "invalid_json"],
        }
    sys.stdout.write(json.dumps(result, ensure_ascii=True, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
