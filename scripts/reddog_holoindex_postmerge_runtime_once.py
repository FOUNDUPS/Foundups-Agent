#!/usr/bin/env python3
"""Run one bounded exact-main HoloIndex post-merge transaction."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.communication.moltbot_bridge.src.holoindex_postmerge_runtime_controller import (  # noqa: E402
    run_holoindex_postmerge_runtime_once,
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
        query = payload.get("query")
        timeout = payload.get("timeout_seconds", 14_400.0)
        if type(query) is not str or type(timeout) not in (int, float):
            raise ValueError("query_and_timeout_required")
        result = run_holoindex_postmerge_runtime_once(
            repo_root=REPO_ROOT, query=query, timeout_seconds=float(timeout)
        ).to_dict()
    except BaseException:
        result = {
            "schema_version": "reddog_holoindex_postmerge_runtime.v1",
            "accepted": False,
            "status": "REJECTED",
            "rejection_reasons": ["invalid_or_interrupted_request"],
        }
    sys.stdout.write(json.dumps(result, ensure_ascii=True, sort_keys=True) + "\n")
    return 0 if result.get("accepted") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
