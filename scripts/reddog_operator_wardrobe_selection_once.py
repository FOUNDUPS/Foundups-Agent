"""One-shot RedDog operator wardrobe-selection bridge.

Reads a JSON packet from stdin, delegates to the deterministic wardrobe-selection
dry-run, and prints a JSON result. This bridge performs no execution, no enqueue,
no signing, no permission probe, and no HoloIndex mutation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.communication.moltbot_bridge.src.reddog_operator_loop_wardrobe_selection import (
    select_reddog_operator_loop_wardrobe_dryrun,
)


def _read_payload() -> Dict[str, Any]:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception as exc:
        return {"_bridge_error": "invalid_json", "_bridge_error_class": type(exc).__name__}
    return payload if isinstance(payload, dict) else {"_bridge_error": "payload_not_object"}


def _list(value: Any) -> Sequence[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _result(payload: Mapping[str, Any]) -> Dict[str, Any]:
    if payload.get("_bridge_error"):
        return {
            "decision": "WARDROBE_SELECTION_REJECT",
            "receipt": None,
            "governing_wsps": [],
            "authority_request": "unknown",
            "rejection_reasons": [str(payload["_bridge_error"])],
            "no_execution_performed": True,
            "no_enqueue_performed": True,
        }

    result = select_reddog_operator_loop_wardrobe_dryrun(
        str(payload.get("work_focus") or ""),
        principal_ref=str(payload.get("principal_ref") or "012"),
        authority_request=str(payload.get("authority_request") or "none"),
        selected_context_mode=str(payload.get("selected_context_mode") or "auto"),
        selected_model_mode=str(payload.get("selected_model_mode") or "auto"),
        selected_effort=str(payload.get("selected_effort") or "auto"),
        holoindex_evidence=_mapping(payload.get("holoindex_evidence")),
        required_targets=_list(payload.get("required_targets")),
        target_recall_ok=(
            payload.get("target_recall_ok") if isinstance(payload.get("target_recall_ok"), bool) else None
        ),
        grounding_preflight=_mapping(payload.get("grounding_preflight")),
        wsp_refs=_list(payload.get("wsp_refs")),
        lane_refs=_list(payload.get("lane_refs")),
        continuation_packet_digest=(
            str(payload.get("continuation_packet_digest"))
            if payload.get("continuation_packet_digest") is not None
            else None
        ),
    )
    output = result.to_dict()
    output["no_execution_performed"] = True
    output["no_enqueue_performed"] = True
    return output


def main() -> int:
    print(json.dumps(_result(_read_payload()), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
