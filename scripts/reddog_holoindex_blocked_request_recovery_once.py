#!/usr/bin/env python3
"""Bounded stage/claim bridge for Holo blocked-request recovery."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.communication.moltbot_bridge.src.reddog_holoindex_blocked_request_recovery import (  # noqa: E402
    admit_holo_blocked_request_recovery,
    stage_holo_blocked_request_recovery,
)


MAX_INPUT_BYTES = 64 * 1024
PACKET_FIELDS = frozenset({
    "schema_version", "recovery_id", "request_digest", "query_digest", "query",
    "request", "incident_receipt", "created_at_epoch_ms", "expires_at_epoch_ms",
})
ENVELOPE_FIELDS = frozenset({"operation", "packet"})


def _payload() -> Mapping[str, Any]:
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("payload_too_large")
    value = json.loads(raw.decode("utf-8", errors="strict"))
    if not isinstance(value, Mapping):
        raise ValueError("payload_not_object")
    return value


def main() -> int:
    try:
        envelope = _payload()
        if set(envelope) != ENVELOPE_FIELDS or envelope.get("operation") not in {
            "claim", "stage",
        } or not isinstance(envelope.get("packet"), Mapping):
            raise ValueError("recovery_envelope_invalid")
        value = envelope["packet"]
        query, receipt, request = (
            value.get("query"), value.get("incident_receipt"), value.get("request")
        )
        if (
            set(value) != PACKET_FIELDS or type(query) is not str
            or not isinstance(receipt, Mapping) or not isinstance(request, Mapping)
        ):
            raise ValueError("recovery_fields_required")
        worker = (
            stage_holo_blocked_request_recovery
            if envelope["operation"] == "stage"
            else admit_holo_blocked_request_recovery
        )
        result = worker(
            repo_root=REPO_ROOT, query=query, request=request,
            recovery_id=value["recovery_id"], request_digest=value["request_digest"],
            query_digest=value["query_digest"],
            created_at_epoch_ms=value["created_at_epoch_ms"],
            expires_at_epoch_ms=value["expires_at_epoch_ms"],
            incident_receipt=receipt,
        )
    except Exception:
        result = {
            "ok": False,
            "status": "REJECTED",
            "reason": "recovery_bridge_failed_closed",
        }
    sys.stdout.write(json.dumps(result, ensure_ascii=True, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
