"""NDJSON bridge for the RedDog start-operations control adapter."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping

SOURCE_ROOT = Path(__file__).resolve().parents[1]
if "REDDOG_TARGET_REPO_ROOT" not in globals() and str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))
TARGET_REPO_ROOT = Path(
    globals().get("REDDOG_TARGET_REPO_ROOT", SOURCE_ROOT)
).resolve()
VERIFIED_RUNTIME_READ_TEXT = globals().get("REDDOG_VERIFIED_RUNTIME_READ_TEXT")

from modules.communication.moltbot_bridge.src.reddog_start_operations_control import (  # noqa: E402
    result_json,
    run_start_operations_control,
)
from modules.communication.moltbot_bridge.src.reddog_start_operations_control_receipt import (  # noqa: E402
    reject,
)
from modules.communication.moltbot_bridge.src.reddog_start_operations_profile import (  # noqa: E402
    StartOperationsProfile,
)


MAX_INPUT_BYTES = 32 * 1024


def _read_payload() -> Mapping[str, Any]:
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("start_operations_control_payload_too_large")
    value = json.loads(raw.decode("utf-8") if raw else "{}")
    if not isinstance(value, Mapping):
        raise ValueError("start_operations_control_payload_not_mapping")
    return value


def _write(value: Mapping[str, Any]) -> None:
    sys.stdout.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def main() -> int:
    try:
        payload = _read_payload()
        result = run_start_operations_control(
            repo_root=TARGET_REPO_ROOT,
            operations_skill_root=SOURCE_ROOT,
            operations_skill_reader=VERIFIED_RUNTIME_READ_TEXT,
            request=payload,
            progress_writer=_write,
        )
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        result = reject(
            "invalid",
            StartOperationsProfile(),
            {},
            ("start_operations_bridge_input_invalid",),
        )
    sys.stdout.write(result_json(result) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
