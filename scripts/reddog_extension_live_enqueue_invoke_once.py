"""One-shot bridge for RedDog extension OpenClaw live-enqueue invocation.

Slice: REDDOG_EXTENSION_TO_OPENCLAW_LIVE_ENQUEUE_RUNTIME_BINDING_PHASE1

The editor runtime may call this script only after grounding, fusion quorum,
output validation, wardrobe selection, and runtime-consumption gates have
passed. This bridge delegates to the existing explicit live-enqueue invoke
guard, but it intentionally does not construct the concrete OpenClaw writer in
this slice. That keeps the extension runtime connected to the guarded seam
without making an editor subprocess the owner of durable live queue mutation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.communication.moltbot_bridge.src.reddog_extension_live_enqueue_invoke import (  # noqa: E402
    EXTENSION_LIVE_ENQUEUE_INVOKE_REJECT,
    invoke_reddog_extension_live_enqueue_explicit_valve,
)


def _read_payload() -> Dict[str, Any]:
    raw = sys.stdin.buffer.read()
    if not raw:
        return {}
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("payload_must_be_json_object")
    return payload


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _bool(value: Any) -> bool:
    return value is True


def _seen_keys(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item) for item in value if item is not None}


def _with_runtime_flags(output: Dict[str, Any]) -> Dict[str, Any]:
    live = output.get("live_enqueue_result")
    live_payload = live if isinstance(live, Mapping) else {}
    receipt = live_payload.get("receipt")
    receipt_payload = receipt if isinstance(receipt, Mapping) else {}
    work_order_id = str(live_payload.get("work_order_id") or receipt_payload.get("work_order_id") or "")
    adapter_digest = str(receipt_payload.get("adapter_dryrun_receipt_digest") or "")
    live_enqueue_key = f"{work_order_id}:{adapter_digest}" if work_order_id and adapter_digest else ""
    output.update(
        {
            "python_invocation_performed": True,
            "concrete_writer_enabled": False,
            "openclaw_enqueue_performed": live_payload.get("live_enqueue_performed") is True,
            "hermes_dispatch_performed": False,
            "worktree_create_performed": False,
            "task_execution_performed": False,
            "file_edit_performed": False,
            "pr_created": False,
            "merge_performed": False,
            "reward_settlement_performed": False,
        }
    )
    if live_enqueue_key:
        output["live_enqueue_key"] = live_enqueue_key
    return output


def _reject(reason: str) -> Dict[str, Any]:
    return _with_runtime_flags(
        {
            "decision": EXTENSION_LIVE_ENQUEUE_INVOKE_REJECT,
            "rejection_reasons": [reason],
            "explicit_live_enqueue_requested": False,
            "no_execution_performed": True,
            "no_reward_settlement_performed": True,
        }
    )


def main() -> int:
    try:
        payload = _read_payload()
        result = invoke_reddog_extension_live_enqueue_explicit_valve(
            explicit_live_enqueue_requested=_bool(payload.get("explicit_live_enqueue_requested")),
            selection_receipt=_mapping(payload.get("selection_receipt")),
            adapter_result=_mapping(payload.get("adapter_result")),
            policy_gate_receipt=_mapping(payload.get("policy_gate_receipt")),
            signed_receipt_chain_result=_mapping(payload.get("signed_receipt_chain_result")),
            valve_decision=_mapping(payload.get("valve_decision")),
            writer=None,
            seen_live_enqueue_keys=_seen_keys(payload.get("seen_live_enqueue_keys")),
        )
        sys.stdout.write(json.dumps(_with_runtime_flags(result.to_dict()), sort_keys=True))
        return 0
    except Exception as exc:
        sys.stdout.write(json.dumps(_reject(type(exc).__name__), sort_keys=True))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
