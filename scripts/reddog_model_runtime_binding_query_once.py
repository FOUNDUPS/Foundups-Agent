"""One-shot RedDog model runtime binding query bridge."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.communication.moltbot_bridge.src.reddog_model_runtime_binding_query import (
    query_model_runtime_binding,
)


MAX_INPUT_BYTES = 32 * 1024


def main() -> int:
    payload = _read_payload()
    repo_root = Path(str(payload.get("repo_root") or Path.cwd())).resolve()
    result = query_model_runtime_binding(repo_root=repo_root)
    print(json.dumps(result.to_dict(), sort_keys=True, ensure_ascii=True))
    return 0


def _read_payload() -> Mapping[str, Any]:
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("model_runtime_binding_query_payload_too_large")
    if not raw.strip():
        return {}
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("model_runtime_binding_query_payload_not_mapping")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
