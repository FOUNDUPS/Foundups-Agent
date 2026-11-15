"""Bounded local producer/inspector for the existing 012 command queue.

Run from the selected checkout with ``python -m ...operator_manifest``.
Enqueueing never activates a policy or sends a public message. Inspection is
read-only; only the existing queue owner produces acknowledgements and state.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
import time
from uuid import uuid4

from modules.communication.livechat.src.operator_command_queue import (
    OperatorCommandQueue,
    enqueue_operator_command,
)

MAX_INPUT_BYTES = 16_384


def _reject_constant(_value):
    raise ValueError("invalid_command_input")


def read_command(input_path=None, stream=None):
    """Read one bounded JSON command without echoing private instructions."""
    if input_path is None:
        raw = (stream or sys.stdin.buffer).read(MAX_INPUT_BYTES + 1)
    else:
        with Path(input_path).open("rb") as handle:
            raw = handle.read(MAX_INPUT_BYTES + 1)
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("command_input_too_large")
    command = json.loads(raw.decode("utf-8-sig"), parse_constant=_reject_constant)
    if not isinstance(command, dict) or set(command) - {"id", "action", "payload"}:
        raise ValueError("invalid_command_input")
    if not isinstance(command.get("payload"), dict):
        raise ValueError("invalid_command_input")
    if "id" not in command:
        command["id"] = "operator-" + uuid4().hex
    if command.get("action") in {"set_context", "set_video_policy", "announce", "schedule_stream_shorts"}:
        payload = command["payload"]
        ttl = payload.setdefault("ttl_seconds", 3600)
        if type(ttl) is not int or not 60 <= ttl <= 86400:
            raise ValueError("invalid_command_input")
        deadline = payload.setdefault("expires_at_unix", time.time() + ttl)
        if type(deadline) not in (int, float) or not math.isfinite(deadline) or deadline <= 0:
            raise ValueError("invalid_command_input")
    return command


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("enqueue", "inspect"))
    parser.add_argument("--input", help="UTF-8 JSON command; default is stdin")
    parser.add_argument("--id", help="Existing command ID to inspect")
    parser.add_argument("--manifest", type=Path, help="Override the existing inbox")
    parser.add_argument("--acknowledgements", type=Path, help="Override its ledger")
    parser.add_argument("--state", type=Path, help="Override the queue-owned state")
    return parser


def run(args):
    # Resolve and check all three paths even though a producer writes only inbox.
    queue = OperatorCommandQueue(
        None, command_path=args.manifest,
        acknowledgement_path=args.acknowledgements, state_path=args.state,
    )
    if args.operation == "enqueue":
        command = read_command(args.input)
        command_id = enqueue_operator_command(
            command, command_path=args.manifest,
            acknowledgement_path=args.acknowledgements,
        )
        return {"id": command_id, "queued": True, "received": False,
                "active": False, "verification": "not_observed"}
    if not args.id:
        raise ValueError("command_id_required")
    return queue.inspect_command(args.id)


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:
        safe_errors = {"invalid_command_input", "command_input_too_large",
                       "command_id_required", "command_id_already_exists",
                       "invalid_or_full_manifest", "manifest_paths_must_be_distinct"}
        reason = str(exc) if str(exc) in safe_errors else type(exc).__name__
        print(json.dumps({"success": False, "reason": reason}))
        return 1
    print(json.dumps(result, ensure_ascii=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
