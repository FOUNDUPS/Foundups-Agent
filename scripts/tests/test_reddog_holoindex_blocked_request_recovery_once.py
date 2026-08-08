from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "reddog_holoindex_blocked_request_recovery_once.py"
SPEC = importlib.util.spec_from_file_location("reddog_holo_recovery_bridge_test", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge)


def _packet() -> dict:
    return {
        "schema_version": "reddog_holoindex_blocked_request_recovery.v1",
        "recovery_id": "sha256:" + "1" * 64,
        "request_digest": "sha256:" + "2" * 64,
        "query_digest": "sha256:" + "3" * 64,
        "query": "audit HoloIndex",
        "request": {"command": "ask"},
        "incident_receipt": {"receipt_id": "sha256:" + "4" * 64},
        "created_at_epoch_ms": 1,
        "expires_at_epoch_ms": 2,
    }


@pytest.mark.parametrize(
    ("operation", "worker_name"),
    (("stage", "stage_holo_blocked_request_recovery"),
     ("claim", "admit_holo_blocked_request_recovery")),
)
def test_bridge_dispatches_strict_operation(monkeypatch, capsys, operation, worker_name):
    calls = []
    monkeypatch.setattr(bridge, "_payload", lambda: {
        "operation": operation, "packet": _packet(),
    })
    monkeypatch.setattr(
        bridge, worker_name,
        lambda **values: calls.append(values) or {
            "ok": True, "status": operation.upper(), "reason": "",
        },
    )

    assert bridge.main() == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == operation.upper()
    assert len(calls) == 1
    assert calls[0]["query"] == "audit HoloIndex"


def test_bridge_rejects_unknown_operation(monkeypatch, capsys):
    monkeypatch.setattr(bridge, "_payload", lambda: {
        "operation": "execute", "packet": _packet(),
    })

    assert bridge.main() == 0
    assert json.loads(capsys.readouterr().out) == {
        "ok": False,
        "reason": "recovery_bridge_failed_closed",
        "status": "REJECTED",
    }
