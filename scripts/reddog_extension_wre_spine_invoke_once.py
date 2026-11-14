"""One-shot extension bridge for RedDog WRE operational-spine invocation.

This script is intentionally narrow: it reads one JSON packet from stdin,
delegates to the landed explicit-valve guard, and prints one JSON result. It
does not parse command arguments for secrets, does not invoke OpenClaw/Hermes,
and does not merge or settle rewards.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.communication.moltbot_bridge.src.reddog_extension_wre_operational_spine_invoke import (
    invoke_reddog_extension_wre_operational_spine_explicit_valve,
)


def _read_payload() -> Dict[str, Any]:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw or "{}")
    except Exception as exc:
        return {"_bridge_error": "invalid_json", "_bridge_error_class": type(exc).__name__}
    return payload if isinstance(payload, dict) else {"_bridge_error": "payload_not_object"}


def _mapping(value: Any) -> Optional[Mapping[str, Any]]:
    return value if isinstance(value, Mapping) else None


def _result(payload: Mapping[str, Any]) -> Dict[str, Any]:
    if payload.get("_bridge_error"):
        return {
            "decision": "EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_REJECT",
            "rejection_reasons": [str(payload["_bridge_error"])],
            "bridge_error_class": str(payload.get("_bridge_error_class") or "BridgeInputError"),
            "python_invocation_performed": True,
            "wre_spine_invoked": False,
            "worktree_create_performed": False,
        }

    repo_root_text = payload.get("repo_root")
    repo_root = Path(str(repo_root_text)).resolve() if repo_root_text else None
    result = invoke_reddog_extension_wre_operational_spine_explicit_valve(
        _mapping(payload.get("work_order")) or {},
        explicit_wre_operational_spine_requested=(
            payload.get("explicit_wre_operational_spine_requested") is True
        ),
        selection_receipt=_mapping(payload.get("selection_receipt")),
        permission_snapshot=_mapping(payload.get("permission_snapshot")),
        valve_environment=_mapping(payload.get("valve_environment")),
        signature_verification_result=_mapping(payload.get("signature_verification_result")),
        require_signed_authority=payload.get("require_signed_authority") is not False,
        repo_root=repo_root,
        permission_expires_at=(
            str(payload.get("permission_expires_at"))
            if payload.get("permission_expires_at") is not None
            else None
        ),
    )
    output = result.to_dict()
    spine_result = output.get("worktree_spine_result")
    spine_payload = spine_result if isinstance(spine_result, Mapping) else {}
    worktree_payload = spine_payload.get("worktree_create_result")
    worktree_result = worktree_payload if isinstance(worktree_payload, Mapping) else {}
    output["python_invocation_performed"] = True
    output["wre_spine_invoked"] = bool(spine_payload)
    output["worktree_create_performed"] = bool(
        worktree_result.get("decision") == "WORKTREE_CREATE_ACCEPT"
    )
    output["file_edit_performed"] = False
    output["task_execution_performed"] = False
    output["pr_created"] = False
    output["openclaw_enqueue_performed"] = False
    output["hermes_dispatch_performed"] = False
    output["merge_performed"] = False
    output["reward_settlement_performed"] = False
    return output


def main() -> int:
    payload = _read_payload()
    print(json.dumps(_result(payload), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
