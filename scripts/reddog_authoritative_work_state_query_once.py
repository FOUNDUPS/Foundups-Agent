"""One-shot RedDog authoritative work-state query bridge."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_query import (
    query_authoritative_work_state,
)


MAX_INPUT_BYTES = 32 * 1024


def main() -> int:
    payload = _read_payload()
    repo_root = Path(str(payload.get("repo_root") or Path.cwd())).resolve()
    receipt = query_authoritative_work_state(
        repo_root=repo_root,
        work_state_path=os.getenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", ""),
        requested_queue_item_id=_optional_text(payload, "requested_queue_item_id"),
    )
    print(json.dumps(receipt.to_dict(), sort_keys=True, ensure_ascii=True))
    return 0


def _read_payload() -> Mapping[str, Any]:
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("work_state_query_payload_too_large")
    if not raw.strip():
        return {}
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("work_state_query_payload_not_mapping")
    return value


def _optional_text(payload: Mapping[str, Any], key: str) -> str | None:
    value = str(payload.get(key) or "").strip()
    return value or None


if __name__ == "__main__":
    raise SystemExit(main())
