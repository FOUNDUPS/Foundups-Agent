from __future__ import annotations

import ast
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_memex_snapshot_projection_supplier import (
    supply_assignment_bound_memex_projection,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_memex_snapshot_projection_supplier.py"
)


def _memex_view() -> dict:
    return {
        "schema_version": "foundup_brain_current_state.v1",
        "foundup_brain_view_id": "sha256:brain-view",
        "foundup_id": "foundups-agent",
        "snapshot_id": "snapshot-1",
        "snapshot_content_digest": "sha256:snapshot-content",
        "identity": {
            "foundup_id": "foundups-agent",
            "name": "Foundups Agent",
        },
        "current_state": {
            "selected_slice": "REDDOG_MEMEX_SNAPSHOT_PROJECTION_SUPPLIER_PHASE1",
            "runtime_gap": "projection supplier",
        },
        "roadmap_state": {
            "next_slice": "REDDOG_OPERATIONAL_MEMORY_NEXT_PHASE1",
        },
    }


def _supply(**overrides):
    kwargs = {
        "memex_view": _memex_view(),
        "foundup_id": "foundups-agent",
        "principal_id": "principal-012",
        "work_order_id": "assignment-1",
        "source_scope": "foundup:foundups-agent:lane:repo_code_audit",
        "source_revision": "abc123",
        "snapshot_receipt_id": "snapshot-1",
        "snapshot_content_digest": "sha256:snapshot-content",
        "holoindex_generation_id": "sha256:memex-generation",
        "issued_at": "2026-07-16T00:00:00+00:00",
        "expires_at": "2026-07-16T01:00:00+00:00",
    }
    kwargs.update(overrides)
    return supply_assignment_bound_memex_projection(**kwargs)


def test_supplies_assignment_bound_projection_and_policy_receipt() -> None:
    result = _supply()

    assert result.accepted is True
    assert result.projection is not None
    assert result.access_policy_receipt is not None
    assert result.projection.receipt is not None
    assert result.projection.receipt.access_policy_digest == result.access_policy_receipt.receipt_id
    assert result.projection.receipt.holoindex_generation_id == "sha256:memex-generation"
    assert result.projection.records
    assert result.projection.records[0].metadata["snapshot_id"] == "snapshot-1"
    assert result.projection.records[0].metadata["snapshot_content_digest"] == "sha256:snapshot-content"


def test_rejects_memex_view_scope_or_snapshot_mismatch() -> None:
    view = _memex_view()
    view["foundup_id"] = "other-foundup"
    result = _supply(memex_view=view)

    assert result.accepted is False
    assert "memex_view_foundup_mismatch" in result.rejection_reasons

    snapshot_mismatch = _memex_view()
    snapshot_mismatch["snapshot_content_digest"] = "sha256:other"
    result = _supply(memex_view=snapshot_mismatch)
    assert result.accepted is False
    assert "memex_view_snapshot_digest_mismatch" in result.rejection_reasons


def test_rejects_missing_assignment_bindings() -> None:
    result = _supply(principal_id="", work_order_id="", holoindex_generation_id="")

    assert result.accepted is False
    assert "missing_principal_id" in result.rejection_reasons
    assert "missing_work_order_id" in result.rejection_reasons
    assert "missing_holoindex_generation_id" in result.rejection_reasons


def test_supplier_is_read_only_by_ast() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    forbidden_imports = {"subprocess", "requests", "httpx", "sqlite3", "os"}
    forbidden_calls = {"open", "write_text", "write_bytes", "system", "popen"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in forbidden_imports
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in forbidden_imports
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in forbidden_calls
            if isinstance(node.func, ast.Name):
                assert node.func.id not in forbidden_calls
